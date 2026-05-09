"""API キー検証 + AuthContext 化 + レート制限統合。"""
import asyncio
import hashlib
import logging
from typing import Optional

from .context import AuthContext
from .errors import RateLimited

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

        # レート制限カウンタ更新（既存 SQL 関数を使用）
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_api_key_rate_limit_status(%s, 'minute')",
                (key_id,),
            )
            count, limit, _, remaining = cur.fetchone()

        if remaining <= 0:
            raise RateLimited("API key rate limit exceeded (per minute)")

        # カウント増加
        with conn.cursor() as cur:
            cur.execute(
                "SELECT increment_api_key_rate_limit(%s, 'minute')",
                (key_id,),
            )
            cur.execute(
                "SELECT increment_api_key_rate_limit(%s, 'day')",
                (key_id,),
            )
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
