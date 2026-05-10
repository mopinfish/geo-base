"""Issue #54: チームタイルセット追加/削除権限の対称性回帰テスト。

ACCESS_CONTROL_REVIEW.md I-1 で発覚した非対称（追加は member 可、削除は owner/admin
のみ）を案 B（両方 owner/admin のみ）に統一した変更の回帰防止。

最小限の FastAPI app + TestClient を立ち上げ、`get_connection` / `require_auth` を
dependency_overrides で差し替える方式は `test_features_datasources_team_access.py`
と同じ。
"""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth import User, require_auth
from lib.database import get_connection
from lib.routers.teams import router as teams_router


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def app(db_conn):
    """teams router のみ載せた最小 FastAPI app。"""
    a = FastAPI()
    a.include_router(teams_router)

    def _get_conn():
        yield db_conn

    a.dependency_overrides[get_connection] = _get_conn
    return a


@pytest.fixture
def client_for(app):
    """`User` を渡して TestClient を作る factory。`require_auth` を override。"""

    def _make(user: User):
        async def _override():
            return user

        app.dependency_overrides[require_auth] = _override
        return TestClient(app)

    return _make


# ---------------------------------------------------------------------------
# DB シード fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_team_with_roles(db_conn):
    """team + 各ロールのユーザーを 1 セット作る factory。

    Returns:
        dict with keys: team_id, owner_id, admin_id, member_id
    """

    def _make():
        team_id = str(uuid.uuid4())
        owner_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())
        member_id = str(uuid.uuid4())
        slug = f"t{team_id[:8]}"
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teams (id, name, slug, owner_id) VALUES (%s, %s, %s, %s)",
                (team_id, slug, slug, owner_id),
            )
            for uid, role in [
                (owner_id, "owner"),
                (admin_id, "administrator"),
                (member_id, "member"),
            ]:
                cur.execute(
                    """INSERT INTO team_members (team_id, user_id, role)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (team_id, user_id) DO NOTHING""",
                    (team_id, uid, role),
                )
        return {
            "team_id": team_id,
            "owner_id": owner_id,
            "admin_id": admin_id,
            "member_id": member_id,
        }

    return _make


@pytest.fixture
def make_tileset(db_conn):
    """tileset を 1 件作る。"""

    def _make(owner_id):
        ts_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'tx', 'vector', 'pbf', %s, false)""",
                (ts_id, owner_id),
            )
        return ts_id

    return _make


@pytest.fixture
def attach_to_team(db_conn):
    """team_tilesets に既存紐付けを作る（DELETE のテストで使う）。"""

    def _attach(team_id, tileset_id, added_by):
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO team_tilesets (team_id, tileset_id, added_by, permission_level)
                   VALUES (%s, %s, %s, 'read')""",
                (team_id, tileset_id, added_by),
            )

    return _attach


def _user(user_id: str) -> User:
    """`User` 値オブジェクトを最低限の項目で作る（require_auth override 用）。"""
    return User(
        id=user_id,
        email=f"u-{user_id[:8]}@example.test",
        role="user",
        name="Test User",
    )


# ---------------------------------------------------------------------------
# POST /api/teams/{id}/tilesets — Issue #54 案 B: owner / admin のみ
# ---------------------------------------------------------------------------


class TestAddTeamTilesetPermission:
    def test_owner_can_add(self, client_for, make_team_with_roles, make_tileset):
        team = make_team_with_roles()
        ts_id = make_tileset(owner_id=team["owner_id"])
        client = client_for(_user(team["owner_id"]))

        res = client.post(
            f"/api/teams/{team['team_id']}/tilesets",
            json={"tileset_id": ts_id, "permission_level": "read"},
        )
        assert res.status_code == 201, res.text

    def test_admin_can_add(self, client_for, make_team_with_roles, make_tileset):
        team = make_team_with_roles()
        ts_id = make_tileset(owner_id=team["admin_id"])
        client = client_for(_user(team["admin_id"]))

        res = client.post(
            f"/api/teams/{team['team_id']}/tilesets",
            json={"tileset_id": ts_id, "permission_level": "read"},
        )
        assert res.status_code == 201, res.text

    def test_member_cannot_add(self, client_for, make_team_with_roles, make_tileset):
        """Issue #54 案 B: member の追加権限を廃止 (旧仕様では 201 が返っていた)。"""
        team = make_team_with_roles()
        ts_id = make_tileset(owner_id=team["member_id"])
        client = client_for(_user(team["member_id"]))

        res = client.post(
            f"/api/teams/{team['team_id']}/tilesets",
            json={"tileset_id": ts_id, "permission_level": "read"},
        )
        assert res.status_code == 403, res.text


# ---------------------------------------------------------------------------
# DELETE /api/teams/{id}/tilesets/{tid} — owner / admin のみ（変更なし、対称確認）
# ---------------------------------------------------------------------------


class TestRemoveTeamTilesetPermission:
    def test_owner_can_remove(
        self, client_for, make_team_with_roles, make_tileset, attach_to_team
    ):
        team = make_team_with_roles()
        ts_id = make_tileset(owner_id=team["owner_id"])
        attach_to_team(team["team_id"], ts_id, added_by=team["owner_id"])
        client = client_for(_user(team["owner_id"]))

        res = client.delete(f"/api/teams/{team['team_id']}/tilesets/{ts_id}")
        assert res.status_code == 204, res.text

    def test_admin_can_remove(
        self, client_for, make_team_with_roles, make_tileset, attach_to_team
    ):
        team = make_team_with_roles()
        ts_id = make_tileset(owner_id=team["admin_id"])
        attach_to_team(team["team_id"], ts_id, added_by=team["admin_id"])
        client = client_for(_user(team["admin_id"]))

        res = client.delete(f"/api/teams/{team['team_id']}/tilesets/{ts_id}")
        assert res.status_code == 204, res.text

    def test_member_cannot_remove(
        self, client_for, make_team_with_roles, make_tileset, attach_to_team
    ):
        team = make_team_with_roles()
        ts_id = make_tileset(owner_id=team["member_id"])
        attach_to_team(team["team_id"], ts_id, added_by=team["member_id"])
        client = client_for(_user(team["member_id"]))

        res = client.delete(f"/api/teams/{team['team_id']}/tilesets/{ts_id}")
        assert res.status_code == 403, res.text
