"""Tests for AuthProvider ABC and factory."""

import pytest
from pydantic import ValidationError

from lib.auth.provider import AuthProvider


class TestAuthProviderABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AuthProvider()


class TestFactory:
    def test_local_provider_selected(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        from lib.auth import get_auth_provider
        from lib.config import get_settings

        get_settings.cache_clear()
        get_auth_provider.cache_clear()
        from lib.auth.providers.local import LocalAuthProvider

        assert isinstance(get_auth_provider(), LocalAuthProvider)

    def test_supabase_provider_no_longer_supported(self, monkeypatch):
        """`AUTH_PROVIDER=supabase` は #72 で廃止済み。Settings 検証で reject される。

        `model_validator(mode='after')` 内で投げる `ValueError` は pydantic v2 が
        `ValidationError` でラップするので、ここでも `ValidationError` を期待する。
        """
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        from lib.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(ValidationError, match="Unknown AUTH_PROVIDER"):
            get_settings()

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "unknown")
        from lib.auth import get_auth_provider
        from lib.config import get_settings

        get_settings.cache_clear()
        get_auth_provider.cache_clear()
        import pytest

        with pytest.raises(ValueError):
            get_auth_provider()


class TestConfigValidation:
    def test_local_without_jwt_secret_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        # 空文字列で .env の値を上書き
        monkeypatch.setenv("JWT_SECRET", "")
        from lib.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(Exception, match="JWT_SECRET"):
            get_settings()

    def test_smtp_without_host_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        monkeypatch.setenv("EMAIL_BACKEND", "smtp")
        monkeypatch.setenv("SMTP_HOST", "")
        from lib.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(Exception, match="SMTP_HOST"):
            get_settings()

    def test_samesite_none_without_secure_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        monkeypatch.setenv("COOKIE_SAMESITE", "none")
        monkeypatch.setenv("COOKIE_SECURE", "false")
        from lib.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(Exception, match="COOKIE_SECURE"):
            get_settings()
