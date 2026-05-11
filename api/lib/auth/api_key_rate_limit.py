"""API キー rate limit backend (Issue #56).

`settings.rate_limit_backend` (env: `RATE_LIMIT_BACKEND`) で実装を切替可能:

- `"db"` (既定): `DbRateLimiter`。`api_key_rate_limits` テーブルに INSERT/UPDATE で
  fixed-window 集計を行う既存実装。SQL 関数 `get_api_key_rate_limit_status` /
  `increment_api_key_rate_limit` を利用。Phase 1 で `api_key_auth.py` から
  inline ロジックを切り出した形。
- `"redis"`: `RedisRateLimiter`（Phase 2 で実装予定）。Redis INCR + EXPIRE で
  fixed-window 集計。Redis 失敗時は fail-open。

注: 本モジュールはログイン試行 rate limit (`auth/rate_limit.py`) とは別物。
こちらは **認証済み API キー** が「自分の rate_limit_per_minute / per_day を
超えてリクエストしていないか」をチェックするためのもの。

設計:
- `check_and_increment(key_id, rl_min, rl_day)` を呼ぶと、現在のカウントが limit を
  超過していれば `RateLimited` を raise し、超過していなければカウンタを +1 する
- 「先 check 後 increment」の TOCTOU は許容範囲。fixed-window 自体が境界で 2x の
  バーストを許容する設計なので、厳密な逐次性は不要

実装側の責務:
- `DbRateLimiter` は呼び出し側が用意した `conn` を使う（既存挙動のまま、commit は
  呼び出し側で行う）
- `RedisRateLimiter` (Phase 2) は `conn` を使わず Redis client を直接利用
"""
import logging
from typing import Protocol

from lib.config import get_settings

from .errors import RateLimited

logger = logging.getLogger(__name__)


class RateLimiter(Protocol):
    """API キー rate limit の抽象インターフェース。"""

    def check_and_increment(self, key_id: str, rl_min: int, rl_day: int) -> None:
        """現在のカウントを確認し、超過していなければカウンタを +1 する。

        Args:
            key_id: API キーの UUID 文字列
            rl_min: per-minute の上限。-1 なら制限なし（増分のみ実施）
            rl_day: per-day の上限。-1 なら制限なし

        Raises:
            RateLimited: per-minute または per-day の上限を超過している
        """
        ...


class DbRateLimiter:
    """DB ベースの rate limiter (既存実装)。

    `api_key_rate_limits` テーブルに `(api_key_id, window_type, window_start)`
    で row を upsert し、`request_count` をインクリメントして集計する。

    呼び出し側 (`api_key_auth.py`) が用意した `conn` を使う。Commit は呼び出し側で
    行う（既存挙動と同じ — `_validate_sync` の末尾で `conn.commit()` する）。
    """

    def __init__(self, conn):
        self._conn = conn

    def check_and_increment(self, key_id: str, rl_min: int, rl_day: int) -> None:
        # per-minute チェック
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_api_key_rate_limit_status(%s, 'minute')",
                (key_id,),
            )
            _count, _limit, _window_start, remaining = cur.fetchone()

        if remaining <= 0:
            raise RateLimited("API key rate limit exceeded (per minute)")

        # increment per-minute / per-day（既存実装に倣って per-day は事前 check しない
        # — per-minute で守りつつ、per-day は別途運用監視で管理する想定）
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT increment_api_key_rate_limit(%s, 'minute')",
                (key_id,),
            )
            cur.execute(
                "SELECT increment_api_key_rate_limit(%s, 'day')",
                (key_id,),
            )


def make_rate_limiter(conn) -> RateLimiter:
    """`settings.rate_limit_backend` に基づいて rate limiter を返す factory。

    Phase 1 では DbRateLimiter のみ実装。`backend="redis"` が指定された場合も
    現状は DbRateLimiter にフォールバックし、warn ログを出す（Phase 2 で
    RedisRateLimiter を追加実装）。

    Args:
        conn: DB connection（DbRateLimiter のみ使用、RedisRateLimiter では未使用）

    Returns:
        RateLimiter インスタンス
    """
    backend = get_settings().rate_limit_backend
    if backend == "redis":
        logger.warning(
            "RATE_LIMIT_BACKEND=redis was requested but RedisRateLimiter is "
            "not yet implemented (Phase 2 of Issue #56). Falling back to DbRateLimiter."
        )
    elif backend != "db":
        logger.warning(
            "Unknown RATE_LIMIT_BACKEND=%r; falling back to DbRateLimiter.", backend
        )
    return DbRateLimiter(conn)
