"""Tests for SupabaseAuthProvider (HTTP mocked)."""
import pytest
import respx
from httpx import Response

from lib._auth_pkg.providers.supabase import SupabaseAuthProvider
from lib._auth_pkg.errors import (
    InvalidCredentials, UserAlreadyExists, InvalidToken, ProviderError,
)


SUPABASE_URL = "https://test.supabase.co"


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-jwt-secret-" + "x" * 50)
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    from lib.config import get_settings
    get_settings.cache_clear()
    return SupabaseAuthProvider()


class TestAuthenticate:
    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/token").mock(
            return_value=Response(200, json={
                "access_token": "fake.jwt.token",
                "refresh_token": "fake-refresh",
                "expires_in": 3600,
                "user": {"id": "user-123", "email": "a@b.com", "role": "authenticated"},
            })
        )
        pair = await provider.authenticate("a@b.com", "MyPass123")
        assert pair.access_token == "fake.jwt.token"
        assert pair.refresh_token == "fake-refresh"

    @pytest.mark.asyncio
    @respx.mock
    async def test_invalid_credentials(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/token").mock(
            return_value=Response(400, json={
                "error": "invalid_grant",
                "error_description": "Invalid login credentials",
            })
        )
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("a@b.com", "wrong")

    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_raises_provider_error(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/token").mock(
            return_value=Response(500)
        )
        with pytest.raises(ProviderError):
            await provider.authenticate("a@b.com", "MyPass123")


class TestCreateUser:
    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(200, json={
                "id": "user-456", "email": "new@example.com",
                "user_metadata": {"name": "Bob"}, "email_confirmed_at": "2026-05-08T00:00:00Z",
            })
        )
        u = await provider.create_user("new@example.com", "ValidPass123", name="Bob")
        assert u.id == "user-456"
        assert u.email == "new@example.com"

    @pytest.mark.asyncio
    @respx.mock
    async def test_duplicate(self, provider):
        respx.post(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(422, json={"error": "user_already_exists"})
        )
        with pytest.raises(UserAlreadyExists):
            await provider.create_user("dupe@example.com", "ValidPass123")


class TestVerifyAccessToken:
    @pytest.mark.asyncio
    async def test_uses_local_jwt_verification(self, provider):
        # Supabase mode でも JWT 検証はローカルで行われる
        from lib._auth_pkg.jwt_utils import issue_access_token
        from lib._auth_pkg.models import User
        u = User(id="abc", email="a@b.com", role="authenticated")
        token = issue_access_token(
            u, secret="test-jwt-secret-" + "x" * 50,
            audience="authenticated",
        )
        result = await provider.verify_access_token(token)
        assert result.is_authenticated
        assert result.user.id == "abc"


class TestGetUserByEmail:
    @pytest.mark.asyncio
    @respx.mock
    async def test_found(self, provider):
        respx.get(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(200, json={
                "users": [{"id": "u1", "email": "a@b.com"}]
            })
        )
        u = await provider.get_user_by_email("a@b.com")
        assert u.id == "u1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found(self, provider):
        respx.get(f"{SUPABASE_URL}/auth/v1/admin/users").mock(
            return_value=Response(200, json={"users": []})
        )
        u = await provider.get_user_by_email("nobody@example.com")
        assert u is None
