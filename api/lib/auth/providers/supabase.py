"""SupabaseAuthProvider - Supabase Auth REST API のラッパー。"""
import logging
from typing import Optional

import httpx

from lib.config import get_settings

from ..errors import (
    InvalidCredentials,
    InvalidToken,
    ProviderError,
    UserAlreadyExists,
    UserNotFound,
)
from ..jwt_utils import claims_to_user, decode_access_token
from ..models import AuthResult, TokenPair, User
from ..provider import AuthProvider

logger = logging.getLogger(__name__)


class SupabaseAuthProvider(AuthProvider):
    """Supabase Auth REST API へ委譲する実装。"""

    def __init__(self):
        self._settings = get_settings()
        self._base = self._settings.supabase_url
        self._service_key = self._settings.supabase_service_role_key
        self._timeout = httpx.Timeout(30.0)

    def _admin_headers(self) -> dict:
        return {
            "apikey": self._service_key,
            "Authorization": f"Bearer {self._service_key}",
            "Content-Type": "application/json",
        }

    def _public_headers(self) -> dict:
        return {
            "apikey": self._service_key,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, headers: dict, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                return await client.request(
                    method, f"{self._base}{path}", headers=headers, **kwargs
                )
            except httpx.HTTPError as e:
                raise ProviderError(f"Supabase request failed: {e}")

    def _user_from_supabase(self, data: dict) -> User:
        return User(
            id=data["id"],
            email=data.get("email"),
            role=data.get("role", "authenticated"),
            name=(data.get("user_metadata") or {}).get("name"),
            app_metadata=data.get("app_metadata"),
            user_metadata=data.get("user_metadata"),
            email_verified=data.get("email_confirmed_at") is not None,
        )

    async def verify_access_token(self, token: str) -> AuthResult:
        try:
            claims = decode_access_token(
                token,
                secret=self._settings.effective_jwt_secret,
                audience=self._settings.jwt_audience,
            )
            return AuthResult(is_authenticated=True, user=claims_to_user(claims))
        except InvalidToken as e:
            return AuthResult(is_authenticated=False, error=str(e))

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        res = await self._request("GET", f"/auth/v1/admin/users/{user_id}", self._admin_headers())
        if res.status_code == 404:
            return None
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code != 200:
            return None
        return self._user_from_supabase(res.json())

    async def get_user_by_email(self, email: str) -> Optional[User]:
        res = await self._request(
            "GET", "/auth/v1/admin/users",
            self._admin_headers(),
            params={"filter": f"email=eq.{email.lower()}"},
        )
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        users = res.json().get("users", [])
        if not users:
            return None
        return self._user_from_supabase(users[0])

    async def authenticate(self, email, password, ip=None, user_agent=None) -> TokenPair:
        res = await self._request(
            "POST", "/auth/v1/token",
            self._public_headers(),
            params={"grant_type": "password"},
            json={"email": email, "password": password},
        )
        if res.status_code == 400:
            raise InvalidCredentials("Invalid email or password")
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code != 200:
            raise InvalidCredentials("Authentication failed")

        data = res.json()
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        )

    async def refresh_tokens(self, refresh_token, ip=None, user_agent=None) -> TokenPair:
        res = await self._request(
            "POST", "/auth/v1/token",
            self._public_headers(),
            params={"grant_type": "refresh_token"},
            json={"refresh_token": refresh_token},
        )
        if res.status_code == 400:
            raise InvalidToken("Invalid refresh token")
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")

        data = res.json()
        return TokenPair(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        )

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        # Supabase の logout は access_token 必要だが、Phase 3 では best-effort
        await self._request(
            "POST", "/auth/v1/logout",
            {**self._public_headers(), "Authorization": f"Bearer {refresh_token}"},
        )

    async def create_user(
        self, email, password, name=None, email_verified=False,
        app_metadata=None, user_metadata=None,
    ) -> User:
        body = {
            "email": email.lower(),
            "password": password,
            "email_confirm": email_verified,
        }
        if name is not None:
            body["user_metadata"] = {"name": name, **(user_metadata or {})}
        elif user_metadata is not None:
            body["user_metadata"] = user_metadata
        if app_metadata is not None:
            body["app_metadata"] = app_metadata

        res = await self._request("POST", "/auth/v1/admin/users", self._admin_headers(), json=body)
        if res.status_code in (422, 409):
            raise UserAlreadyExists("Email already registered")
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code not in (200, 201):
            raise ProviderError(f"User creation failed: {res.status_code}")

        return self._user_from_supabase(res.json())

    async def update_user(self, user_id, name=None, email=None, user_metadata=None) -> User:
        body = {}
        if email is not None:
            body["email"] = email.lower()
        if name is not None or user_metadata is not None:
            meta = user_metadata or {}
            if name is not None:
                meta["name"] = name
            body["user_metadata"] = meta

        if not body:
            user = await self.get_user_by_id(user_id)
            if user is None:
                raise UserNotFound(user_id)
            return user

        res = await self._request(
            "PUT",
            f"/auth/v1/admin/users/{user_id}",
            self._admin_headers(),
            json=body,
        )
        if res.status_code == 404:
            raise UserNotFound(user_id)
        if res.status_code >= 500:
            raise ProviderError(f"Supabase error: {res.status_code}")
        if res.status_code != 200:
            raise ProviderError(f"User update failed: {res.status_code}")
        return self._user_from_supabase(res.json())

    async def update_password(self, user_id: str, new_password: str) -> None:
        res = await self._request(
            "PUT", f"/auth/v1/admin/users/{user_id}",
            self._admin_headers(),
            json={"password": new_password},
        )
        if res.status_code == 404:
            raise UserNotFound(user_id)
        if res.status_code != 200:
            raise ProviderError(f"Password update failed: {res.status_code}")

    async def request_password_reset(self, email: str, ip=None) -> None:
        # Supabase が自動でメール送信する
        await self._request(
            "POST", "/auth/v1/recover",
            self._public_headers(),
            json={"email": email.lower()},
        )
        # エラーは無視（情報漏洩防止）

    async def confirm_password_reset(self, token: str, new_password: str) -> User:
        # Supabase の recovery token は OTP として verify する
        res = await self._request(
            "POST", "/auth/v1/verify",
            self._public_headers(),
            json={"type": "recovery", "token": token},
        )
        if res.status_code >= 400:
            raise InvalidToken("Invalid recovery token")

        data = res.json()
        access_token = data.get("access_token")
        user_id = data.get("user", {}).get("id")
        if not access_token or not user_id:
            raise InvalidToken("Recovery token did not return user")

        # 認証状態でパスワード更新
        res2 = await self._request(
            "PUT", "/auth/v1/user",
            {**self._public_headers(), "Authorization": f"Bearer {access_token}"},
            json={"password": new_password},
        )
        if res2.status_code != 200:
            raise ProviderError(f"Password update failed: {res2.status_code}")
        return self._user_from_supabase(res2.json())
