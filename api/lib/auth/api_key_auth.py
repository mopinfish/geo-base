"""API キー検証 + AuthContext 化 + レート制限統合。

Rate limit ロジックは `api_key_rate_limit.py` の `RateLimiter` 抽象に切り出され
ており、`settings.rate_limit_backend` で DB / Redis (Phase 2 で追加) の実装を
切替可能（Issue #56）。
"""
import asyncio
import hashlib
import logging
from typing import Optional

from .api_key_rate_limit import make_rate_limiter
from .context import AuthContext
from .errors import RateLimited  # noqa: F401  # 公開 API として再 export

logger = logging.getLogger(__name__)


API_KEY_PREFIX = "gb_"  # gb_live_xxx or gb_test_xxx


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


async def validate_api_key(
    key: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[AuthContext]:
    """API キーを検証して AuthContext を返す。

    Returns:
        AuthContext: 有効なキーの場合
        None: キーが見つからない / 無効 / revoked / 期限切れ

    Raises:
        RateLimited: レート制限超過
    """
    return await asyncio.to_thread(_validate_sync, key, ip, user_agent)


def _validate_sync(key: str, ip: Optional[str], user_agent: Optional[str]) -> Optional[AuthContext]:
    from lib.database import get_db_connection

    key_hash = _hash_key(key)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, user_id, team_id, scopes,
                          rate_limit_per_minute, rate_limit_per_day,
                          is_active, expires_at, revoked_at
                   FROM api_keys WHERE key_hash = %s""",
                (key_hash,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        (key_id, user_id, team_id, scopes,
         rl_min, rl_day, is_active, expires_at, revoked_at) = row

        if not is_active or revoked_at is not None:
            return None

        if expires_at is not None:
            from datetime import datetime, timezone
            if expires_at < datetime.now(timezone.utc):
                return None

        # レート制限カウンタ更新（Issue #56: backend 抽象化）
        # backend は `settings.rate_limit_backend` で決まる（db / redis）。
        # 超過時は RateLimited を raise（caller の `validate_api_key` が伝播）。
        rate_limiter = make_rate_limiter(conn)
        rate_limiter.check_and_increment(str(key_id), rl_min, rl_day)
        conn.commit()

        # last_used_at 更新（既存 SQL 関数）
        with conn.cursor() as cur:
            cur.execute("SELECT update_api_key_last_used(%s)", (key_id,))
        conn.commit()

        return AuthContext.from_api_key({
            "id": key_id, "user_id": user_id, "team_id": team_id,
            "scopes": scopes,
        })


async def log_api_key_request(
    api_key_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """API キー使用ログを記録（サンプリング適用）。"""
    from lib.config import get_settings
    settings = get_settings()
    sample_rate = settings.api_key_log_sample_rate
    if sample_rate < 1.0:
        import random
        if random.random() > sample_rate:
            return  # サンプル対象外

    await asyncio.to_thread(
        _log_sync, api_key_id, endpoint, method, status_code,
        response_time_ms, ip, user_agent,
    )


def _log_sync(api_key_id, endpoint, method, status_code, response_time_ms, ip, user_agent):
    from lib.database import get_db_connection
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT log_api_key_usage(%s, %s, %s, %s, %s, %s, %s)",
                (api_key_id, endpoint, method, status_code,
                 response_time_ms, ip, user_agent),
            )
        conn.commit()
