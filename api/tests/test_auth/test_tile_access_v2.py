"""Tests for check_tileset_access_v2 / get_tileset_with_access_check_v2."""
import pytest
import uuid
from lib.auth import check_tileset_access_v2, AuthContext


@pytest.fixture
def setup_tileset(db_conn, clean_auth_tables):
    """テスト用タイルセットを作成"""
    owner_id = str(uuid.uuid4())

    def _create(is_public=False):
        tid = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'test', 'vector', 'pbf', %s, %s)""",
                (tid, owner_id, is_public),
            )
        db_conn.commit()
        return tid, owner_id

    return _create


class TestCheckTilesetAccessV2:
    @pytest.mark.asyncio
    async def test_public_allows_anonymous(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=True)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert await check_tileset_access_v2(db_conn, row, None) is True

    @pytest.mark.asyncio
    async def test_private_denies_anonymous(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert await check_tileset_access_v2(db_conn, row, None) is False

    @pytest.mark.asyncio
    async def test_owner_allowed(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id=owner, scopes=["read", "write", "admin"])
        assert await check_tileset_access_v2(db_conn, row, ctx) is True

    @pytest.mark.asyncio
    async def test_non_owner_denied(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id="other-user", scopes=["read"])
        assert await check_tileset_access_v2(db_conn, row, ctx) is False

    @pytest.mark.asyncio
    async def test_api_key_no_read_scope_denied(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id=owner, is_api_key=True, scopes=[])  # 空スコープ
        assert await check_tileset_access_v2(db_conn, row, ctx) is False
