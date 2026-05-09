"""リフレッシュトークンのライフサイクル管理。

セキュリティ機能:
- トークンローテーション: 検証時に新トークン発行 + 旧トークン revoke
- 再利用検知: revoked 済みトークンが再提示されたら、そのユーザーの全トークンを失効
"""
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple

from .errors import InvalidToken

logger = logging.getLogger(__name__)


REFRESH_TOKEN_TTL_DAYS = 30
TOKEN_BYTES = 48  # urlsafe(48) で約 64 文字


def _hash_token(token: str) -> str:
    """SHA-256 で token をハッシュ化。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_refresh_token(
    conn,
    user_id: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """新しい refresh token を発行し、ハッシュを DB に保存。平文を返す。"""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(token)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO refresh_tokens
                (user_id, token_hash, ip_address, user_agent, expires_at)
            VALUES
                (%s, %s, %s, %s, NOW() + (%s || ' days')::INTERVAL)
            """,
            (user_id, token_hash, ip, user_agent, REFRESH_TOKEN_TTL_DAYS),
        )
    conn.commit()
    return token


def verify_and_rotate_refresh_token(
    conn,
    refresh_token: str,
    *,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[str, str]:
    """検証 → 旧トークン revoke → 新トークン発行（rotation）。

    Returns: (user_id, new_refresh_token)
    Raises: InvalidToken if not_found / revoked (盗難検知付き) / expired
    """
    token_hash = _hash_token(refresh_token)

    with conn.cursor() as cur:
        # FOR UPDATE で行ロック（並行 refresh の race 防止）
        cur.execute(
            """
            SELECT id, user_id, revoked_at, expires_at
            FROM refresh_tokens
            WHERE token_hash = %s
            FOR UPDATE
            """,
            (token_hash,),
        )
        row = cur.fetchone()

        if row is None:
            conn.rollback()
            raise InvalidToken("Token not found")

        token_id, user_id, revoked_at, expires_at = row

        # ★ 再利用検知
        if revoked_at is not None:
            logger.warning(
                "Refresh token reuse detected", extra={"user_id": str(user_id)}
            )
            cur.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW(), revoked_reason = %s
                WHERE user_id = %s AND revoked_at IS NULL
                """,
                ("theft_detected", user_id),
            )
            conn.commit()
            raise InvalidToken("Token has been revoked (reuse detected)")

        if expires_at < datetime.now(timezone.utc):
            cur.execute(
                """UPDATE refresh_tokens
                      SET revoked_at = NOW(), revoked_reason = 'expired'
                   WHERE id = %s""",
                (token_id,),
            )
            conn.commit()
            raise InvalidToken("Token expired")

        # 新トークン発行
        new_token = secrets.token_urlsafe(TOKEN_BYTES)
        new_token_hash = _hash_token(new_token)
        cur.execute(
            """
            INSERT INTO refresh_tokens
                (user_id, token_hash, ip_address, user_agent, expires_at)
            VALUES
                (%s, %s, %s, %s, NOW() + (%s || ' days')::INTERVAL)
            RETURNING id
            """,
            (user_id, new_token_hash, ip, user_agent, REFRESH_TOKEN_TTL_DAYS),
        )
        new_token_id = cur.fetchone()[0]

        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = NOW(), revoked_reason = 'rotated', replaced_by = %s
            WHERE id = %s
            """,
            (new_token_id, token_id),
        )

    conn.commit()
    return str(user_id), new_token


def revoke_refresh_token(conn, refresh_token: str, reason: str = "logout") -> None:
    """指定トークンを revoke。冪等。"""
    token_hash = _hash_token(refresh_token)
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = NOW(), revoked_reason = %s
            WHERE token_hash = %s AND revoked_at IS NULL
            """,
            (reason, token_hash),
        )
    conn.commit()


def revoke_all_user_tokens(conn, user_id: str, reason: str) -> int:
    """ユーザーの全 active refresh token を revoke。Returns: 失効した件数。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE refresh_tokens
            SET revoked_at = NOW(), revoked_reason = %s
            WHERE user_id = %s AND revoked_at IS NULL
            """,
            (reason, user_id),
        )
        count = cur.rowcount
    conn.commit()
    return count


def cleanup_expired_tokens(conn) -> int:
    """期限切れトークンを物理削除。Returns: 削除件数。"""
    with conn.cursor() as cur:
        cur.execute("SELECT cleanup_expired_refresh_tokens()")
        count = cur.fetchone()[0]
    conn.commit()
    return count
