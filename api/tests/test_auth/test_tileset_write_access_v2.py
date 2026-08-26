"""Tests for check_tileset_write_access_v2 (issue #49 / ACCESS_CONTROL_REVIEW C-1).

`team_tilesets.permission_level` を考慮した書き込み認可判定を検証する。
DB 関数 `can_user_perform_action()` に委譲する JWT 経路と、
team_tilesets を直接見る API キー経路の両方をカバー。

team_members.user_id には users への FK が無いので、ここでは
`make_user` を経由せず bare UUID を直接 INSERT して self-contained に保つ。
"""

import uuid

import pytest

from lib.auth import AuthContext, check_tileset_write_access_v2

# ---------------------------------------------------------------------------
# Sync-friendly fixtures（async テストから安全に呼べる）
# ---------------------------------------------------------------------------


@pytest.fixture
def jwt_ctx():
    """JWT ユーザー相当の AuthContext factory（フルスコープ）。"""

    def _make(user_id: str) -> AuthContext:
        return AuthContext(
            user_id=user_id,
            scopes=["read", "write", "delete", "admin"],
            is_api_key=False,
        )

    return _make


@pytest.fixture
def api_key_ctx():
    """API キー相当の AuthContext factory。"""

    def _make(user_id=None, team_id=None, scopes=None) -> AuthContext:
        return AuthContext(
            user_id=user_id or str(uuid.uuid4()),
            team_id=str(team_id) if team_id else None,
            scopes=scopes if scopes is not None else ["read", "write"],
            is_api_key=True,
            api_key_id=str(uuid.uuid4()),
        )

    return _make


@pytest.fixture
def make_tileset(db_conn):
    """個人タイルセットを作る factory。"""

    def _create(owner_id=None, is_public=False):
        owner_id = owner_id or str(uuid.uuid4())
        tid = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'wt-test', 'vector', 'pbf', %s, %s)""",
                (tid, owner_id, is_public),
            )
        db_conn.commit()
        return {"id": tid, "user_id": owner_id}

    return _create


@pytest.fixture
def make_team_with_owner(db_conn):
    """チームを作り、owner を team_members に登録。teams.owner_id にも入る。"""

    def _create(owner_id=None):
        owner_id = owner_id or str(uuid.uuid4())
        team_id = str(uuid.uuid4())
        slug = f"t{team_id[:8]}"
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO teams (id, name, slug, owner_id)
                   VALUES (%s, %s, %s, %s)""",
                (team_id, slug, slug, owner_id),
            )
            cur.execute(
                """INSERT INTO team_members (team_id, user_id, role)
                   VALUES (%s, %s, 'owner')
                   ON CONFLICT (team_id, user_id) DO NOTHING""",
                (team_id, owner_id),
            )
        db_conn.commit()
        return {"id": team_id, "owner_id": owner_id}

    return _create


@pytest.fixture
def add_team_member(db_conn):
    """team_members に member を追加（既存があれば role を更新）。"""

    def _add(team_id, user_id=None, role="member"):
        user_id = user_id or str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO team_members (team_id, user_id, role)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (team_id, user_id) DO UPDATE
                   SET role = EXCLUDED.role""",
                (team_id, user_id, role),
            )
        db_conn.commit()
        return user_id

    return _add


@pytest.fixture
def add_team_tileset(db_conn):
    """team_tilesets に紐付けを追加する factory。"""

    def _add(team_id, tileset_id, *, added_by=None, permission_level=None):
        added_by = added_by or str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO team_tilesets
                       (team_id, tileset_id, added_by, permission_level)
                   VALUES (%s, %s, %s, %s)""",
                (team_id, tileset_id, added_by, permission_level),
            )
        db_conn.commit()

    return _add


# ---------------------------------------------------------------------------
# Scope / 認証ガード
# ---------------------------------------------------------------------------


class TestAuthGuards:
    def test_no_ctx_denied(self, db_conn, make_tileset):
        ts = make_tileset()
        assert check_tileset_write_access_v2(db_conn, ts, None, "update") is False

    def test_no_write_scope_denied(self, db_conn, make_tileset):
        ts = make_tileset()
        ctx = AuthContext(
            user_id=ts["user_id"],
            scopes=["read"],
            is_api_key=True,
        )
        # owner だが scope 不足 → 拒否
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "update") is False

    def test_no_delete_scope_for_delete_action(self, db_conn, make_tileset):
        ts = make_tileset()
        ctx = AuthContext(
            user_id=ts["user_id"],
            scopes=["read", "write"],  # write はあるが delete は無い
            is_api_key=True,
        )
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "delete") is False

    def test_unknown_action_denied(self, db_conn, make_tileset, jwt_ctx):
        """未登録の action は許可されない（タイポ防止 / 未知 scope での意図せぬ通過防止）。"""
        ts = make_tileset()
        # owner かつフルスコープでも、未知 action は False
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(ts["user_id"]), "drop") is False


# ---------------------------------------------------------------------------
# 個人タイルセット（後方互換）
# ---------------------------------------------------------------------------


class TestPersonalTileset:
    def test_owner_can_update(self, db_conn, make_tileset, jwt_ctx):
        ts = make_tileset()
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(ts["user_id"]), "update") is True

    def test_owner_can_delete(self, db_conn, make_tileset, jwt_ctx):
        ts = make_tileset()
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(ts["user_id"]), "delete") is True

    def test_non_owner_denied(self, db_conn, make_tileset, jwt_ctx):
        ts = make_tileset()
        outsider = str(uuid.uuid4())
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(outsider), "update") is False


# ---------------------------------------------------------------------------
# チーム共有タイルセット（JWT ユーザー、DB 関数 can_user_perform_action 経由）
# ---------------------------------------------------------------------------


class TestTeamSharedJwt:
    def test_team_owner_default_permission_can_update(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        jwt_ctx,
    ):
        # tileset 所有者 ≠ team owner にしてチーム共有経路を確認
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"])  # permission_level なし → role 継承
        assert (
            check_tileset_write_access_v2(db_conn, ts, jwt_ctx(team["owner_id"]), "update") is True
        )

    def test_team_owner_default_permission_can_delete(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        jwt_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"])
        # team owner は role 継承で admin → delete 可
        assert (
            check_tileset_write_access_v2(db_conn, ts, jwt_ctx(team["owner_id"]), "delete") is True
        )

    def test_team_member_default_can_update_but_not_delete(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_member,
        add_team_tileset,
        jwt_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        member_id = add_team_member(team["id"], role="member")
        add_team_tileset(team["id"], ts["id"])  # permission_level なし → 'write'
        # member は default で write → update 可、delete 不可
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(member_id), "update") is True
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(member_id), "delete") is False

    def test_team_member_with_read_permission_denied(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_member,
        add_team_tileset,
        jwt_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        member_id = add_team_member(team["id"], role="member")
        add_team_tileset(team["id"], ts["id"], permission_level="read")
        # 明示 read → 更新不可
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(member_id), "update") is False

    def test_team_member_with_admin_permission_can_delete(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_member,
        add_team_tileset,
        jwt_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        member_id = add_team_member(team["id"], role="member")
        add_team_tileset(team["id"], ts["id"], permission_level="admin")
        # 明示 admin → delete 可
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(member_id), "delete") is True

    def test_non_member_denied(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        jwt_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"])
        outsider = str(uuid.uuid4())
        assert check_tileset_write_access_v2(db_conn, ts, jwt_ctx(outsider), "update") is False


# ---------------------------------------------------------------------------
# API キー経路（permission_level を直接判定、role 継承なし）
# ---------------------------------------------------------------------------


class TestApiKey:
    def test_api_key_owner_can_update(self, db_conn, make_tileset, api_key_ctx):
        ts = make_tileset()
        # API キーの user_id がオーナーなら team_id 不要で update 可
        ctx = api_key_ctx(user_id=ts["user_id"])
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "update") is True

    def test_api_key_no_team_denied_for_team_tileset(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        api_key_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"], permission_level="write")
        # team_id 無しの API キー（オーナーでもない）→ 拒否
        ctx = api_key_ctx(team_id=None)
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "update") is False

    def test_api_key_team_with_write_permission_can_update(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        api_key_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"], permission_level="write")
        ctx = api_key_ctx(team_id=team["id"])
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "update") is True

    def test_api_key_team_with_write_cannot_delete(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        api_key_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"], permission_level="write")
        # delete スコープを持っていても、permission_level=write では delete 不可
        ctx = api_key_ctx(team_id=team["id"], scopes=["read", "write", "delete"])
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "delete") is False

    def test_api_key_team_with_admin_permission_can_delete(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        api_key_ctx,
    ):
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"], permission_level="admin")
        ctx = api_key_ctx(team_id=team["id"], scopes=["read", "write", "delete"])
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "delete") is True

    def test_api_key_team_no_role_inheritance(
        self,
        db_conn,
        make_tileset,
        make_team_with_owner,
        add_team_tileset,
        api_key_ctx,
    ):
        # API キーは team の "代理" だが特定 user の role を継承しない仕様。
        # permission_level=NULL の場合、JWT ユーザーは role 継承で書ける可能性が
        # あるが、API キーは NULL のままでは書き込み不可。
        ts = make_tileset()
        team = make_team_with_owner()
        add_team_tileset(team["id"], ts["id"], permission_level=None)
        ctx = api_key_ctx(team_id=team["id"])
        assert check_tileset_write_access_v2(db_conn, ts, ctx, "update") is False
