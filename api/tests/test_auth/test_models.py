"""Tests for auth.models module."""
import pytest
from pydantic import ValidationError
from lib.auth.models import User, AuthResult, TokenPair


class TestUser:
    def test_minimal_construction(self):
        u = User(id="abc-123")
        assert u.id == "abc-123"
        assert u.email is None
        assert u.email_verified is False

    def test_full_construction(self):
        u = User(id="abc", email="x@y.com", role="authenticated",
                 name="Alice", email_verified=True,
                 app_metadata={"provider": "local"})
        assert u.email == "x@y.com"
        assert u.app_metadata == {"provider": "local"}


class TestAuthResult:
    def test_authenticated(self):
        u = User(id="abc")
        r = AuthResult(is_authenticated=True, user=u)
        assert r.is_authenticated is True
        assert r.user.id == "abc"
        assert r.error is None

    def test_failed(self):
        r = AuthResult(is_authenticated=False, error="expired")
        assert r.is_authenticated is False
        assert r.user is None
        assert r.error == "expired"


class TestTokenPair:
    def test_basic(self):
        t = TokenPair(access_token="at", refresh_token="rt", expires_in=900)
        assert t.access_token == "at"
        assert t.token_type == "Bearer"
        assert t.expires_in == 900

    def test_requires_fields(self):
        with pytest.raises(ValidationError):
            TokenPair(access_token="at")  # missing refresh_token, expires_in
