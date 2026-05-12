"""Tests for api_key_auth module."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from lib.auth.api_key_auth import validate_api_key
from lib.auth.errors import RateLimited


@pytest.fixture
def make_api_key(db_conn, clean_auth_tables):
    """API キーを発行するファクトリ"""
    import secrets
    created_keys = []

    def _make(scopes=None, team_id=None, rate_limit_per_minute=60, rate_limit_per_day=10000,
              is_active=True, expires_at=None, revoked_at=None):
        scopes = scopes or ["read"]
        random_part = secrets.token_urlsafe(32)
        full_key = f"gb_test_{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        prefix = full_key[:12]
        user_id = "00000000-0000-0000-0000-000000000001"

        # ダミーユーザーがいなくても api_keys は user_id FK なしなので OK
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO api_keys
                      (name, prefix, key_hash, user_id, team_id, scopes,
                       rate_limit_per_minute, rate_limit_per_day, is_active, expires_at, revoked_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                ("test", prefix, key_hash, user_id, team_id, scopes,
                 rate_limit_per_minute, rate_limit_per_day, is_active, expires_at, revoked_at),
            )
            key_id = cur.fetchone()[0]
        db_conn.commit()
        created_keys.append((full_key, key_id))
        return full_key, key_id

    return _make


class TestValidateApiKey:
    @pytest.mark.asyncio
    async def test_valid_key(self, make_api_key, db_conn):
        full_key, key_id = make_api_key(scopes=["read", "write"])
        ctx = await validate_api_key(full_key)
        assert ctx is not None
        assert ctx.is_api_key
        assert "read" in ctx.scopes
        assert ctx.api_key_id == str(key_id)

    @pytest.mark.asyncio
    async def test_revoked_key(self, make_api_key, db_conn):
        full_key, _ = make_api_key(revoked_at=datetime.now(timezone.utc))
        ctx = await validate_api_key(full_key)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_inactive_key(self, make_api_key, db_conn):
        full_key, _ = make_api_key(is_active=False)
        ctx = await validate_api_key(full_key)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_expired_key(self, make_api_key, db_conn):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        full_key, _ = make_api_key(expires_at=past)
        ctx = await validate_api_key(full_key)
        assert ctx is None

    @pytest.mark.asyncio
    async def test_unknown_key(self):
        ctx = await validate_api_key("gb_live_unknown")
        assert ctx is None

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, make_api_key, db_conn):
        full_key, key_id = make_api_key(rate_limit_per_minute=2)
        # 2 回までは OK
        await validate_api_key(full_key)
        await validate_api_key(full_key)
        # 3 回目で RateLimited
        with pytest.raises(RateLimited):
            await validate_api_key(full_key)

    @pytest.mark.asyncio
    async def test_team_id_in_context(self, make_api_key, db_conn):
        full_key, _ = make_api_key(team_id=None)
        ctx = await validate_api_key(full_key)
        assert ctx.team_id is None
