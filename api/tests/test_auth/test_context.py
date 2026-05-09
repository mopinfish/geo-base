"""Tests for AuthContext."""
import pytest
from lib.auth.context import AuthContext
from lib.auth.models import User


class TestFromJwtUser:
    def test_basic(self):
        u = User(id="abc", email="a@b.com", role="authenticated")
        ctx = AuthContext.from_jwt_user(u)
        assert ctx.user_id == "abc"
        assert ctx.email == "a@b.com"
        assert ctx.is_api_key is False
        assert ctx.team_id is None
        assert "read" in ctx.scopes
        assert "write" in ctx.scopes


class TestFromApiKey:
    def test_basic(self):
        key_data = {
            "id": "key-1", "user_id": "user-1", "team_id": "team-1",
            "scopes": ["read"],
        }
        ctx = AuthContext.from_api_key(key_data)
        assert ctx.is_api_key is True
        assert ctx.user_id == "user-1"
        assert ctx.team_id == "team-1"
        assert ctx.scopes == ["read"]
        assert ctx.api_key_id == "key-1"

    def test_no_team(self):
        key_data = {"id": "k", "user_id": "u", "team_id": None, "scopes": ["read"]}
        ctx = AuthContext.from_api_key(key_data)
        assert ctx.team_id is None


class TestHasScope:
    @pytest.mark.parametrize("scopes,required,expected", [
        (["read"], "read", True),
        (["read"], "write", False),
        (["write"], "read", True),  # write 含意 read
        (["delete"], "write", True),
        (["delete"], "read", True),
        (["admin"], "delete", True),
        (["admin"], "read", True),
        (["admin"], "admin", True),
        ([], "read", False),
    ])
    def test_scope_hierarchy(self, scopes, required, expected):
        ctx = AuthContext(user_id="u", scopes=scopes)
        assert ctx.has_scope(required) is expected
