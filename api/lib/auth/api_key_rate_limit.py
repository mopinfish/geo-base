"""API キー rate limit backend (Issue #56).

`settings.rate_limit_backend` (env: `RATE_LIMIT_BACKEND`) で実装を切替可能:

- `"db"` (既定): `DbRateLimiter`。`api_key_rate_limits` テーブルに INSERT/UPDATE で
  fixed-window 集計を行う既存実装。SQL 関数 `get_api_key_rate_limit_status` /
  `increment_api_key_rate_limit` を利用。Phase 1 で `api_key_auth.py` から
  inline ロジックを切り出した形。
- `"redis"`: `RedisRateLimiter`。Redis INCR + EXPIRE で fixed-window 集計。
  Redis 失敗時は **fail-open**（warn ログを出してリクエストを通す）。rate limit
  は quota 制御であって認可ではないため、Redis ダウンで 503 を返すより一時的に
  通過させる方が UX 上望ましい。

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
  呼び出し側で行う）。**per-minute のみチェック** し、per-day は increment するだけ
  （これは旧 `api_key_auth.py` の inline 挙動と一致 — 後方互換のため Phase 1 では
  維持）
- `RedisRateLimiter` は `conn` を使わず `lib.redis_client.get_redis()` を利用。
  Issue 仕様に従い **per-minute / per-day 両方をチェック** する（DB との挙動差
  — DB 側も将来揃える余地あり）
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Protocol

from lib.config import get_settings

from .errors import RateLimited

logger = logging.getLogger(__name__)


def _is_unlimited(limit: Optional[int]) -> bool:
    """rate_limit 値が「無制限」を意味するか判定する。

    `api_keys.rate_limit_per_*` カラムは INTEGER NOT NULL（既定 60 / 10000）だが、
    防御的にハンドリング:
    - None: 設定されていない → 無制限扱い
    - <= 0: 「0 = 全ブロック」より「無効値 = 無制限」と解釈するほうが運用ミスの被害が
      小さい（過剰な締め付けより素通りのほうがインシデント時の rollback が簡単）
    """
    return limit is None or limit <= 0


class RateLimiter(Protocol):
    """API キー rate limit の抽象インターフェース。"""

    def check_and_increment(
        self, key_id: str, rl_min: Optional[int], rl_day: Optional[int]
    ) -> None:
        """現在のカウントを確認し、超過していなければカウンタを +1 する。

        Args:
            key_id: API キーの UUID 文字列
            rl_min: per-minute の上限。None または <= 0 なら制限なし（check スキップ）
            rl_day: per-day の上限。None または <= 0 なら制限なし

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

    def check_and_increment(
        self, key_id: str, rl_min: Optional[int], rl_day: Optional[int]
    ) -> None:
        # per-minute チェック（rl_min が None / <= 0 なら無制限扱いでスキップ）
        if not _is_unlimited(rl_min):
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


class RedisRateLimiter:
    """Redis ベースの rate limiter (Issue #56)。

    Fixed-window 集計を Redis INCR + EXPIRE で実装。`api_key_rate_limits` テーブル
    と異なり書き込み競合がなく、高頻度アクセスでもスループット低下しにくい。

    キー設計（既定設定での実キー例）:
    - per-minute: `geo-base:rate:apikey:{key_id}:m:{epoch_minute}` (TTL 120s)
    - per-day: `geo-base:rate:apikey:{key_id}:d:{YYYYMMDD}` (TTL 90000s = 25h)

    `key_prefix` 既定値は `{REDIS_KEY_PREFIX}rate:apikey` (末尾 `:` なし、
    `check_and_increment` 内で `:{key_id}:m:{window}` の形に組み立てる)。
    `REDIS_KEY_PREFIX` env (`lib.redis_client.RedisConfig.key_prefix`、
    既定 `geo-base:`) によって環境ごとに namespace を分離できる。`safe_redis_*`
    経由の他キャッシュとも一貫した namespace になる。

    アルゴリズム:
    1. INCR でカウンタを加算（atomic）
    2. `EXPIRE key ttl NX` で TTL 未設定のキーにのみ TTL を付与
       （`nx=True` で既存 TTL を上書きしない → 何度呼んでも自己回復する）
    3. 戻り値が limit を超過していれば RateLimited を raise

    挙動上の注意:
    - INCR-then-check 方式のため、超過した「その 1 リクエスト」はカウンタに含まれる
      （TOCTOU を避けるためのトレードオフ）。次の窓に切り替わるまで、超過カウントは
      残るが、窓が短い (60s) ためユーザー体験への影響は限定的
    - DbRateLimiter は per-minute のみ check するが、本実装は **per-minute /
      per-day 両方を check** する（Issue 仕様準拠）

    Redis 障害時:
    - `get_redis()` が None を返す → fail-open（warn ログ + リクエスト通過）
    - Redis コマンド実行で例外 → fail-open（warn ログ + リクエスト通過）
    """

    # 窓のタイムアウト秒数 (秒)
    MINUTE_WINDOW_TTL = 120
    DAY_WINDOW_TTL = 90000

    def __init__(self, key_prefix: Optional[str] = None):
        """
        Args:
            key_prefix: キー名の prefix（**末尾 `:` 不要** — `check_and_increment`
                内で `:{key_id}:m:{window}` の形に組み立てる）。明示未指定なら
                `{REDIS_KEY_PREFIX}rate:apikey` (REDIS_KEY_PREFIX は redis_client
                の RedisConfig から取得、既定 `geo-base:`)。例: 既定設定だと最終キー
                は `geo-base:rate:apikey:{key_id}:m:{epoch_minute}` となる。
                テストでは独自 prefix を渡してアプリキャッシュと分離する。
        """
        if key_prefix is None:
            from lib.redis_client import get_redis_config
            # REDIS_KEY_PREFIX (既定 "geo-base:") + "rate:apikey" → "geo-base:rate:apikey"
            # key 組み立て側で `:{key_id}:m:{window}` を付加するため、末尾 `:` は不要
            key_prefix = f"{get_redis_config().key_prefix}rate:apikey"
        self._key_prefix = key_prefix

    def _now(self) -> datetime:
        # テストでパッチしやすいように分離
        return datetime.now(timezone.utc)

    def check_and_increment(
        self, key_id: str, rl_min: Optional[int], rl_day: Optional[int]
    ) -> None:
        from lib.redis_client import get_redis

        client = get_redis()
        if client is None:
            logger.warning(
                "Redis unavailable for rate limit check (api_key=%s); "
                "fail-open: allowing request through",
                key_id,
            )
            return

        now = self._now()
        minute_window = int(now.timestamp() // 60)
        day_window = now.strftime("%Y%m%d")
        minute_key = f"{self._key_prefix}:{key_id}:m:{minute_window}"
        day_key = f"{self._key_prefix}:{key_id}:d:{day_window}"

        check_minute = not _is_unlimited(rl_min)
        check_day = not _is_unlimited(rl_day)

        try:
            # per-minute: 制限ありの場合のみ INCR + check（無制限ならスキップ）
            if check_minute:
                m_count = client.incr(minute_key)
                # `EXPIRE key ttl NX` で「TTL 未設定のキーにのみ TTL を付与」する。
                # 旧実装 (m_count == 1 のとき EXPIRE) では、何らかの理由で前回の
                # EXPIRE が失敗した場合に TTL なしキーが永続化して以降カウントが
                # リセットされない事故があり得た。nx=True による idempotent な
                # TTL 付与で、TTL 未設定状態を毎回の呼び出しで自己回復する。
                client.expire(minute_key, self.MINUTE_WINDOW_TTL, nx=True)
                if m_count > rl_min:
                    raise RateLimited("API key rate limit exceeded (per minute)")

            # per-day: 同上
            if check_day:
                d_count = client.incr(day_key)
                client.expire(day_key, self.DAY_WINDOW_TTL, nx=True)
                if d_count > rl_day:
                    raise RateLimited("API key rate limit exceeded (per day)")
        except RateLimited:
            raise
        except Exception as e:
            # ネットワーク障害 / Redis コマンドエラー等。fail-open で通過させる。
            logger.warning(
                "Redis rate limit operation failed (api_key=%s); fail-open: %s",
                key_id,
                e,
            )


def make_rate_limiter(conn) -> RateLimiter:
    """`settings.rate_limit_backend` に基づいて rate limiter を返す factory。

    Args:
        conn: DB connection（`DbRateLimiter` のみ使用、`RedisRateLimiter` は無視）

    Returns:
        RateLimiter インスタンス
    """
    backend = get_settings().rate_limit_backend
    if backend == "redis":
        return RedisRateLimiter()
    if backend != "db":
        logger.warning(
            "Unknown RATE_LIMIT_BACKEND=%r; falling back to DbRateLimiter.", backend
        )
    return DbRateLimiter(conn)
