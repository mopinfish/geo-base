"""Tests for check_tileset_access_v2 / get_tileset_with_access_check_v2."""
import pytest
import uuid
from lib.auth import (
    AuthContext,
    acheck_tileset_access_v2,
    check_tileset_access_v2,
)


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
    def test_public_allows_anonymous(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=True)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert check_tileset_access_v2(db_conn, row, None) is True

    def test_private_denies_anonymous(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert check_tileset_access_v2(db_conn, row, None) is False

    def test_owner_allowed(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id=owner, scopes=["read", "write", "admin"])
        assert check_tileset_access_v2(db_conn, row, ctx) is True

    def test_non_owner_denied(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id="other-user", scopes=["read"])
        assert check_tileset_access_v2(db_conn, row, ctx) is False

    def test_api_key_no_read_scope_denied(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

        ctx = AuthContext(user_id=owner, is_api_key=True, scopes=[])  # 空スコープ
        assert check_tileset_access_v2(db_conn, row, ctx) is False


class TestAcheckTilesetAccessV2:
    """async wrapper が sync 版と同じ結果を返すことの最低限カバレッジ。

    async wrapper は asyncio.to_thread で sync 版を呼ぶだけだが、
    `import asyncio` 漏れや wrapper シグネチャ誤りで黙って動かなくなる
    リグレッションを防ぐために 3 ケースを保持する。
    """

    @pytest.mark.asyncio
    async def test_public_returns_true(self, setup_tileset, db_conn):
        tid, _ = setup_tileset(is_public=True)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert await acheck_tileset_access_v2(db_conn, row, None) is True

    @pytest.mark.asyncio
    async def test_private_anonymous_returns_false(self, setup_tileset, db_conn):
        tid, _ = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        assert await acheck_tileset_access_v2(db_conn, row, None) is False

    @pytest.mark.asyncio
    async def test_owner_returns_true(self, setup_tileset, db_conn):
        tid, owner = setup_tileset(is_public=False)
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, user_id, is_public FROM tilesets WHERE id = %s", (tid,))
            row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        ctx = AuthContext(user_id=owner, scopes=["read", "write", "admin"])
        assert await acheck_tileset_access_v2(db_conn, row, ctx) is True
