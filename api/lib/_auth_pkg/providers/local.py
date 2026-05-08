"""LocalAuthProvider - geo-base が users テーブルを所有し JWT を発行する実装。"""
import asyncio
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from lib.config import get_settings
from lib.database import get_db_connection  # 既存の context manager

from ..errors import (
    AuthError, InvalidCredentials, RateLimited, UserAlreadyExists,
    UserNotFound, InvalidToken, WeakPassword,
)
from ..models import User, AuthResult, TokenPair
from ..provider import AuthProvider
from ..jwt_utils import issue_access_token, decode_access_token, claims_to_user
from ..password import hash_password, verify_password, check_password_policy
from ..tokens import (
    issue_refresh_token, verify_and_rotate_refresh_token,
    revoke_refresh_token, revoke_all_user_tokens,
)
from ..rate_limit import check_login_rate_limit, record_login_attempt
from ..email_backends import get_email_backend
from ..email_backends.templates import render_password_reset_email


logger = logging.getLogger(__name__)


# タイミング攻撃対策用のダミーハッシュ（モジュール load 時に 1 回だけ計算）
_DUMMY_HASH = hash_password("__dummy_for_timing_attack_mitigation__")

PASSWORD_RESET_TTL_HOURS = 1


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LocalAuthProvider(AuthProvider):
    """素の PostgreSQL 上で動く認証プロバイダ。"""

    def __init__(self):
        self._settings = get_settings()

    # ============ Token verification ============

    async def verify_access_token(self, token: str) -> AuthResult:
        try:
            secret = self._settings.effective_jwt_secret
            claims = await asyncio.to_thread(
                decode_access_token,
                token,
                secret=secret,
                audience=self._settings.jwt_audience,
            )
            user = claims_to_user(claims)
            return AuthResult(is_authenticated=True, user=user)
        except InvalidToken as e:
            return AuthResult(is_authenticated=False, error=str(e))
        except Exception as e:
            logger.error("Unexpected error verifying token", exc_info=e)
            return AuthResult(is_authenticated=False, error="Token verification failed")

    # ============ User lookup ============

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        return await asyncio.to_thread(self._get_user_by_id_sync, user_id)

    def _get_user_by_id_sync(self, user_id: str) -> Optional[User]:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, email, name, role, app_metadata, user_metadata, email_verified_at, is_active
                       FROM users WHERE id = %s""",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return User(
                    id=str(row[0]), email=row[1], name=row[2], role=row[3],
                    app_metadata=row[4] or {}, user_metadata=row[5] or {},
                    email_verified=row[6] is not None,
                )

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await asyncio.to_thread(self._get_user_by_email_sync, email)

    def _get_user_by_email_sync(self, email: str) -> Optional[User]:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, email, name, role, app_metadata, user_metadata, email_verified_at
                       FROM users WHERE email = %s AND is_active = TRUE""",
                    (email.lower(),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return User(
                    id=str(row[0]), email=row[1], name=row[2], role=row[3],
                    app_metadata=row[4] or {}, user_metadata=row[5] or {},
                    email_verified=row[6] is not None,
                )

    # ============ Authentication ============

    async def authenticate(
        self,
        email: str,
        password: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        return await asyncio.to_thread(
            self._authenticate_sync, email, password, ip, user_agent
        )

    def _authenticate_sync(self, email, password, ip, user_agent) -> TokenPair:
        with get_db_connection() as conn:
            check_login_rate_limit(conn, email=email, ip=ip)

            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, password_hash, name, role, app_metadata, user_metadata, email, email_verified_at
                       FROM users WHERE email = %s AND is_active = TRUE""",
                    (email.lower(),),
                )
                row = cur.fetchone()

            if row is None:
                # タイミング攻撃対策: ユーザー不存在でも bcrypt 検証
                verify_password(password, _DUMMY_HASH)
                record_login_attempt(conn, email=email, success=False, ip=ip, user_agent=user_agent)
                raise InvalidCredentials("Invalid email or password")

            user_id, password_hash, name, role, app_meta, user_meta, db_email, email_verified_at = row

            if not verify_password(password, password_hash):
                record_login_attempt(conn, email=email, success=False, ip=ip, user_agent=user_agent)
                raise InvalidCredentials("Invalid email or password")

            record_login_attempt(conn, email=email, success=True, ip=ip, user_agent=user_agent)

            # last_login_at 更新
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user_id,))
            conn.commit()

            user = User(
                id=str(user_id), email=db_email, name=name, role=role,
                app_metadata=app_meta or {}, user_metadata=user_meta or {},
                email_verified=email_verified_at is not None,
            )

            access_token = issue_access_token(
                user,
                secret=self._settings.effective_jwt_secret,
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                ttl_seconds=self._settings.access_token_ttl_seconds,
            )
            refresh_token = issue_refresh_token(
                conn, str(user_id), ip=ip, user_agent=user_agent
            )

            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self._settings.access_token_ttl_seconds,
            )

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenPair:
        return await asyncio.to_thread(
            self._refresh_tokens_sync, refresh_token, ip, user_agent
        )

    def _refresh_tokens_sync(self, refresh_token, ip, user_agent) -> TokenPair:
        with get_db_connection() as conn:
            user_id, new_refresh = verify_and_rotate_refresh_token(
                conn, refresh_token, ip=ip, user_agent=user_agent
            )

        # Get user info in a separate connection to keep code clean
        user = self._get_user_by_id_sync(user_id)
        if user is None:
            raise InvalidToken("User not found")

        access_token = issue_access_token(
            user,
            secret=self._settings.effective_jwt_secret,
            audience=self._settings.jwt_audience,
            issuer=self._settings.jwt_issuer,
            ttl_seconds=self._settings.access_token_ttl_seconds,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=self._settings.access_token_ttl_seconds,
        )

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        await asyncio.to_thread(self._revoke_refresh_sync, refresh_token)

    def _revoke_refresh_sync(self, refresh_token: str) -> None:
        with get_db_connection() as conn:
            revoke_refresh_token(conn, refresh_token, reason="logout")

    # ============ User CRUD ============

    async def create_user(
        self,
        email: str,
        password: str,
        name: Optional[str] = None,
        email_verified: bool = False,
        app_metadata: Optional[dict] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        check_password_policy(password)
        return await asyncio.to_thread(
            self._create_user_sync, email, password, name,
            email_verified, app_metadata, user_metadata,
        )

    def _create_user_sync(self, email, password, name, email_verified, app_meta, user_meta) -> User:
        import json
        password_hash_str = hash_password(password)
        email_lower = email.lower()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE email = %s", (email_lower,))
                if cur.fetchone():
                    raise UserAlreadyExists(f"User with email {email_lower} already exists")

                cur.execute(
                    """INSERT INTO users
                          (email, password_hash, name, email_verified_at, app_metadata, user_metadata)
                       VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
                       RETURNING id, email, name, role, app_metadata, user_metadata, email_verified_at""",
                    (
                        email_lower, password_hash_str, name,
                        datetime.now(timezone.utc) if email_verified else None,
                        json.dumps(app_meta or {}),
                        json.dumps(user_meta or {}),
                    ),
                )
                row = cur.fetchone()
            conn.commit()

        return User(
            id=str(row[0]), email=row[1], name=row[2], role=row[3],
            app_metadata=row[4] or {}, user_metadata=row[5] or {},
            email_verified=row[6] is not None,
        )

    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        user_metadata: Optional[dict] = None,
    ) -> User:
        return await asyncio.to_thread(
            self._update_user_sync, user_id, name, email, user_metadata
        )

    def _update_user_sync(self, user_id, name, email, user_metadata) -> User:
        import json
        updates = []
        params = []
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if email is not None:
            updates.append("email = %s")
            params.append(email.lower())
        if user_metadata is not None:
            updates.append("user_metadata = %s::jsonb")
            params.append(json.dumps(user_metadata))

        if not updates:
            user = self._get_user_by_id_sync(user_id)
            if not user:
                raise UserNotFound(user_id)
            return user

        params.append(user_id)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        f"""UPDATE users SET {', '.join(updates)}, updated_at = NOW()
                            WHERE id = %s
                            RETURNING id, email, name, role, app_metadata, user_metadata, email_verified_at""",
                        tuple(params),
                    )
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                        raise UserAlreadyExists(f"Email already in use")
                    raise
                row = cur.fetchone()
                if not row:
                    raise UserNotFound(user_id)
            conn.commit()

        return User(
            id=str(row[0]), email=row[1], name=row[2], role=row[3],
            app_metadata=row[4] or {}, user_metadata=row[5] or {},
            email_verified=row[6] is not None,
        )

    async def update_password(self, user_id: str, new_password: str) -> None:
        check_password_policy(new_password)
        await asyncio.to_thread(self._update_password_sync, user_id, new_password)

    def _update_password_sync(self, user_id, new_password):
        password_hash_str = hash_password(new_password)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                    (password_hash_str, user_id),
                )
                if cur.rowcount == 0:
                    raise UserNotFound(user_id)
            conn.commit()

    # ============ Password reset ============

    async def request_password_reset(self, email: str, ip: Optional[str] = None) -> None:
        await asyncio.to_thread(self._request_reset_sync, email, ip)

    def _request_reset_sync(self, email, ip):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name FROM users WHERE email = %s AND is_active = TRUE",
                    (email.lower(),),
                )
                row = cur.fetchone()

            if row is None:
                logger.info("Password reset requested for nonexistent email", extra={"email": email})
                return  # 情報漏洩防止: 何もしないが正常終了

            user_id, user_name = row

            token = secrets.token_urlsafe(48)
            token_hash = _hash_token(token)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TTL_HOURS)

            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, ip_address)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, token_hash, expires_at, ip),
                )
            conn.commit()

        # メール送信（同期コンテキストから coroutine を実行するため新規 event loop で実行）
        reset_url = f"{self._settings.invitation_base_url}/password-reset/confirm?token={token}"
        subject, body = render_password_reset_email(
            user_name=user_name, reset_url=reset_url, expires_at=expires_at,
        )
        backend = get_email_backend()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(backend.send(email, subject, body))
        finally:
            loop.close()

    async def confirm_password_reset(self, token: str, new_password: str) -> User:
        check_password_policy(new_password)
        return await asyncio.to_thread(self._confirm_reset_sync, token, new_password)

    def _confirm_reset_sync(self, token, new_password) -> User:
        token_hash = _hash_token(token)
        password_hash_str = hash_password(new_password)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, user_id, used_at, expires_at
                       FROM password_reset_tokens WHERE token_hash = %s
                       FOR UPDATE""",
                    (token_hash,),
                )
                row = cur.fetchone()

                if not row:
                    raise InvalidToken("Reset token not found")

                token_id, user_id, used_at, expires_at = row

                if used_at is not None:
                    raise InvalidToken("Reset token already used")

                if expires_at < datetime.now(timezone.utc):
                    raise InvalidToken("Reset token expired")

                cur.execute(
                    "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                    (password_hash_str, user_id),
                )
                cur.execute(
                    "UPDATE password_reset_tokens SET used_at = NOW() WHERE id = %s",
                    (token_id,),
                )
                # 全 refresh token 失効
                cur.execute(
                    """UPDATE refresh_tokens SET revoked_at = NOW(), revoked_reason = 'password_reset'
                       WHERE user_id = %s AND revoked_at IS NULL""",
                    (user_id,),
                )

                cur.execute(
                    """SELECT id, email, name, role, app_metadata, user_metadata, email_verified_at
                       FROM users WHERE id = %s""",
                    (user_id,),
                )
                user_row = cur.fetchone()
            conn.commit()

        return User(
            id=str(user_row[0]), email=user_row[1], name=user_row[2], role=user_row[3],
            app_metadata=user_row[4] or {}, user_metadata=user_row[5] or {},
            email_verified=user_row[6] is not None,
        )
