"""Tests for AuthProvider ABC and factory."""
import pytest
from lib.auth.provider import AuthProvider


class TestAuthProviderABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AuthProvider()


class TestFactory:
    def test_local_provider_selected(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "local")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        from lib.config import get_settings
        from lib.auth import get_auth_provider
        get_settings.cache_clear()
        get_auth_provider.cache_clear()
        from lib.auth.providers.local import LocalAuthProvider
        assert isinstance(get_auth_provider(), LocalAuthProvider)

    def test_supabase_provider_selected(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "x" * 64)
        from lib.config import get_settings
        from lib.auth import get_auth_provider
        get_settings.cache_clear()
        get_auth_provider.cache_clear()
        from lib.auth.providers.supabase import SupabaseAuthProvider
        assert isinstance(get_auth_provider(), SupabaseAuthProvider)

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "unknown")
        from lib.config import get_settings
        from lib.auth import get_auth_provider
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
        monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
        from lib.config import get_settings
        get_settings.cache_clear()
        with pytest.raises(Exception, match="JWT_SECRET"):
            get_settings()

    def test_supabase_without_url_fails(self, monkeypatch):
        monkeypatch.setenv("AUTH_PROVIDER", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "")
        from lib.config import get_settings
        get_settings.cache_clear()
        with pytest.raises(Exception, match="SUPABASE_URL"):
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
