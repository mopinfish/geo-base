"""Tests for LocalAuthProvider."""
import pytest
import secrets
from unittest.mock import AsyncMock, patch

from lib.auth.providers.local import LocalAuthProvider
from lib.auth.errors import (
    InvalidCredentials, RateLimited, UserAlreadyExists,
    InvalidToken, WeakPassword,
)
from lib.auth.email_backends import NullEmailBackend


@pytest.fixture
def email_backend(monkeypatch):
    backend = NullEmailBackend()
    # Patch the LocalAuthProvider's reference to get_email_backend
    monkeypatch.setattr(
        "lib.auth.providers.local.get_email_backend",
        lambda: backend,
    )
    return backend


@pytest.fixture
def provider(monkeypatch):
    """テスト用 LocalAuthProvider"""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-" + "x" * 50)
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("JWT_ISSUER", "geo-base-test")
    from lib.config import get_settings
    get_settings.cache_clear()
    return LocalAuthProvider()


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_creates_user(self, provider, db_conn, clean_auth_tables):
        u = await provider.create_user("alice@example.com", "ValidPass123", name="Alice")
        assert u.id is not None
        assert u.email == "alice@example.com"
        assert u.name == "Alice"

    @pytest.mark.asyncio
    async def test_duplicate_email_raises(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("alice@example.com", "ValidPass123")
        with pytest.raises(UserAlreadyExists):
            await provider.create_user("alice@example.com", "AnotherPass456")

    @pytest.mark.asyncio
    async def test_weak_password_raises(self, provider, db_conn, clean_auth_tables):
        with pytest.raises(WeakPassword):
            await provider.create_user("a@b.com", "short")

    @pytest.mark.asyncio
    async def test_email_lowercased(self, provider, db_conn, clean_auth_tables):
        u = await provider.create_user("UPPER@example.com", "ValidPass123")
        assert u.email == "upper@example.com"

    @pytest.mark.asyncio
    async def test_default_role_is_authenticated(self, provider, db_conn, clean_auth_tables):
        """role 未指定でスキーマ default ('authenticated') が適用される (issue #78)。"""
        u = await provider.create_user("a@b.com", "ValidPass123")
        assert u.role == "authenticated"

    @pytest.mark.asyncio
    async def test_role_admin_is_persisted(self, provider, db_conn, clean_auth_tables):
        """role='admin' で作成すると users.role が 'admin' になる (issue #78)。

        旧実装では app_metadata={"role": "admin"} だけ渡していたため
        users.role は default の 'authenticated' のまま記録されていた。
        """
        u = await provider.create_user(
            "admin@example.com", "ValidPass123",
            role="admin",
            app_metadata={"role": "admin"},
        )
        assert u.role == "admin"
        assert u.app_metadata.get("role") == "admin"

        # DB から直接読んで永続化されていることを確認
        with db_conn.cursor() as cur:
            cur.execute("SELECT role FROM users WHERE email = %s", ("admin@example.com",))
            row = cur.fetchone()
            assert row[0] == "admin"


class TestUpdateUser:
    @pytest.mark.asyncio
    async def test_role_can_be_promoted(self, provider, db_conn, clean_auth_tables):
        """update_user(role=...) で既存ユーザーの role を昇格できる (issue #78 修復用)。"""
        created = await provider.create_user("a@b.com", "ValidPass123")
        assert created.role == "authenticated"

        updated = await provider.update_user(created.id, role="admin")
        assert updated.role == "admin"

    @pytest.mark.asyncio
    async def test_role_omitted_does_not_change(self, provider, db_conn, clean_auth_tables):
        """role=None なら他フィールド更新時も role は変わらない。"""
        created = await provider.create_user(
            "a@b.com", "ValidPass123", role="admin",
        )
        updated = await provider.update_user(created.id, name="renamed")
        assert updated.role == "admin"
        assert updated.name == "renamed"


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_correct_credentials(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        pair = await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")
        assert pair.access_token
        assert pair.refresh_token
        assert pair.expires_in == 900

    @pytest.mark.asyncio
    async def test_wrong_password(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("a@b.com", "WrongPass", ip="1.1.1.1")

    @pytest.mark.asyncio
    async def test_nonexistent_user_same_error(self, provider, db_conn, clean_auth_tables):
        # 存在しないユーザーでも InvalidCredentials（不存在を漏らさない）
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("nobody@example.com", "AnyPass", ip="1.1.1.1")

    @pytest.mark.asyncio
    async def test_rate_limit_after_failures(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        for _ in range(5):
            with pytest.raises(InvalidCredentials):
                await provider.authenticate("a@b.com", "Wrong", ip="1.1.1.1")
        with pytest.raises(RateLimited):
            await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")


class TestVerifyAccessToken:
    @pytest.mark.asyncio
    async def test_valid_token(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        pair = await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")
        result = await provider.verify_access_token(pair.access_token)
        assert result.is_authenticated
        assert result.user.email == "a@b.com"

    @pytest.mark.asyncio
    async def test_invalid_token(self, provider):
        result = await provider.verify_access_token("not-a-jwt")
        assert not result.is_authenticated


class TestRefreshTokens:
    @pytest.mark.asyncio
    async def test_rotation(self, provider, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        pair = await provider.authenticate("a@b.com", "MyPass123", ip="1.1.1.1")
        new_pair = await provider.refresh_tokens(pair.refresh_token, ip="1.1.1.1")
        assert new_pair.refresh_token != pair.refresh_token
        # 旧 refresh は使えない（盗難検知 → 全失効）
        with pytest.raises(InvalidToken):
            await provider.refresh_tokens(pair.refresh_token)


class TestPasswordReset:
    @pytest.mark.asyncio
    async def test_request_sends_email(self, provider, email_backend, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "MyPass123")
        await provider.request_password_reset("a@b.com")
        assert len(email_backend.sent) == 1
        assert "a@b.com" == email_backend.sent[0]["to"]

    @pytest.mark.asyncio
    async def test_request_nonexistent_silent(self, provider, email_backend, db_conn, clean_auth_tables):
        # 存在しない email でも例外なく成功（情報漏洩防止）
        await provider.request_password_reset("nobody@example.com")
        assert len(email_backend.sent) == 0  # メールは送られない

    @pytest.mark.asyncio
    async def test_confirm_changes_password(self, provider, email_backend, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "OldPass123")
        await provider.request_password_reset("a@b.com")
        # メール本文からトークンを抽出
        body = email_backend.sent[0]["body"]
        import re
        token_match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
        token = token_match.group(1)

        await provider.confirm_password_reset(token, "NewPass456")
        # 新パスワードでログインできる
        pair = await provider.authenticate("a@b.com", "NewPass456", ip="1.1.1.1")
        assert pair.access_token
        # 旧パスワードは不可
        with pytest.raises(InvalidCredentials):
            await provider.authenticate("a@b.com", "OldPass123", ip="1.1.1.1")

    @pytest.mark.asyncio
    async def test_confirm_token_only_once(self, provider, email_backend, db_conn, clean_auth_tables):
        await provider.create_user("a@b.com", "OldPass123")
        await provider.request_password_reset("a@b.com")
        import re
        token = re.search(r"token=([A-Za-z0-9_\-]+)", email_backend.sent[0]["body"]).group(1)
        await provider.confirm_password_reset(token, "NewPass456")
        # 同じトークンは 2 回目失敗
        with pytest.raises(InvalidToken):
            await provider.confirm_password_reset(token, "OtherPass789")
