"""Tests for auth.jwt_utils module."""
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time

from lib._auth_pkg.jwt_utils import (
    issue_access_token,
    decode_access_token,
    claims_to_user,
)
from lib._auth_pkg.models import User
from lib._auth_pkg.errors import InvalidToken


SECRET = "test-secret-do-not-use-in-prod-" + "x" * 40
AUD = "authenticated"
ISS = "geo-base-test"


class TestIssueAccessToken:
    def test_returns_string(self):
        u = User(id="abc-123", email="a@b.com", role="authenticated")
        token = issue_access_token(u, secret=SECRET, audience=AUD, issuer=ISS)
        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT 形式

    def test_includes_standard_claims(self):
        u = User(id="abc", email="a@b.com", role="authenticated")
        token = issue_access_token(u, secret=SECRET, audience=AUD, issuer=ISS, ttl_seconds=900)
        decoded = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience=AUD)
        assert decoded["sub"] == "abc"
        assert decoded["email"] == "a@b.com"
        assert decoded["role"] == "authenticated"
        assert decoded["iss"] == ISS
        assert decoded["aud"] == AUD
        assert "iat" in decoded
        assert "exp" in decoded

    def test_ttl_applied(self):
        u = User(id="abc")
        with freeze_time("2026-01-01 00:00:00"):
            token = issue_access_token(u, secret=SECRET, audience=AUD, ttl_seconds=900)
            decoded = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience=AUD)
            assert decoded["exp"] - decoded["iat"] == 900


class TestDecodeAccessToken:
    def test_valid_token(self):
        u = User(id="abc", email="a@b.com")
        token = issue_access_token(u, secret=SECRET, audience=AUD)
        claims = decode_access_token(token, secret=SECRET, audience=AUD)
        assert claims["sub"] == "abc"
        assert claims["email"] == "a@b.com"

    def test_invalid_signature_raises(self):
        u = User(id="abc")
        token = issue_access_token(u, secret=SECRET, audience=AUD)
        with pytest.raises(InvalidToken):
            decode_access_token(token, secret="wrong-secret", audience=AUD)

    def test_wrong_audience_raises(self):
        u = User(id="abc")
        token = issue_access_token(u, secret=SECRET, audience="aud1")
        with pytest.raises(InvalidToken):
            decode_access_token(token, secret=SECRET, audience="aud2")

    def test_expired_raises(self):
        u = User(id="abc")
        with freeze_time("2026-01-01 00:00:00"):
            token = issue_access_token(u, secret=SECRET, audience=AUD, ttl_seconds=60)
        with freeze_time("2026-01-01 00:02:00"):
            with pytest.raises(InvalidToken):
                decode_access_token(token, secret=SECRET, audience=AUD)

    def test_malformed_raises(self):
        with pytest.raises(InvalidToken):
            decode_access_token("not-a-jwt", secret=SECRET, audience=AUD)

    def test_none_alg_attack_rejected(self):
        # JWT 'none' algorithm 攻撃を拒否
        payload = {"sub": "abc", "aud": AUD}
        evil = pyjwt.encode(payload, "", algorithm="none")
        with pytest.raises(InvalidToken):
            decode_access_token(evil, secret=SECRET, audience=AUD)


class TestClaimsToUser:
    def test_basic(self):
        claims = {"sub": "abc", "email": "a@b.com", "role": "authenticated"}
        u = claims_to_user(claims)
        assert u.id == "abc"
        assert u.email == "a@b.com"
        assert u.role == "authenticated"

    def test_includes_metadata(self):
        claims = {
            "sub": "abc",
            "app_metadata": {"provider": "local"},
            "user_metadata": {"name": "Alice"},
        }
        u = claims_to_user(claims)
        assert u.app_metadata == {"provider": "local"}
        assert u.user_metadata == {"name": "Alice"}
