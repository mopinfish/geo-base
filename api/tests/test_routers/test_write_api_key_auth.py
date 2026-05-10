"""Integration tests for issue #50 — write 系エンドポイントの API キー認証対応。

PR #62 (issue #49) で v2 認可ヘルパが API キー経路をサポートするように
なったが、エンドポイントは `Depends(require_auth)`（JWT のみ）だったため
API キーから書き込みできなかった。本 PR で `require_auth_context` に
切り替えて API キー経路を有効化。

ここでは以下を HTTP レイヤで検証:
- API キー (read scope) → PATCH/DELETE で 403
- API キー (write scope) → PATCH 成功
- API キー (delete scope) → DELETE 成功
- API キー (write のみ) → DELETE で 403（scope 不足）
- JWT 既存フロー → 引き続き動作（後方互換）

`db_conn` を `app.dependency_overrides` で共有することで、seed 時に
commit せずに済む（test 終了時の rollback で自動 cleanup）。
"""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth import AuthContext, get_auth_context_optional, require_auth_context
from lib.database import get_connection
from lib.routers.tilesets import router as tilesets_router


# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def app(db_conn):
    app = FastAPI()
    app.include_router(tilesets_router)

    def _get_conn():
        yield db_conn

    app.dependency_overrides[get_connection] = _get_conn
    return app


@pytest.fixture
def client_for(app):
    """`AuthContext`（JWT または API キー）を渡して TestClient を作る factory。"""

    def _make(ctx):
        async def _override():
            if ctx is None:
                # require_auth_context は ctx None を 401 で拒否するので、
                # テスト用に直接エラーを発生させる
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="No auth")
            return ctx

        # 両方の dependency を ctx に向ける（未認証は require_auth_context 側で 401）
        app.dependency_overrides[require_auth_context] = _override
        app.dependency_overrides[get_auth_context_optional] = _override
        return TestClient(app)

    return _make


# ---------------------------------------------------------------------------
# Seed fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_tileset(db_conn):
    """個人タイルセットを作る factory。"""

    def _make(owner_id=None, is_public=False):
        owner_id = owner_id or str(uuid.uuid4())
        ts_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'tx', 'vector', 'pbf', %s, %s)""",
                (ts_id, owner_id, is_public),
            )
        return {"id": ts_id, "user_id": owner_id}

    return _make


@pytest.fixture
def make_team_tileset(db_conn):
    """team + member + 共有 tileset を作って permission_level を返す。"""

    def _make(permission_level="write"):
        owner_id = str(uuid.uuid4())
        member_id = str(uuid.uuid4())
        team_id = str(uuid.uuid4())
        ts_id = str(uuid.uuid4())
        slug = f"t{team_id[:8]}"
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teams (id, name, slug, owner_id) VALUES (%s, %s, %s, %s)",
                (team_id, slug, slug, owner_id),
            )
            cur.execute(
                """INSERT INTO team_members (team_id, user_id, role)
                   VALUES (%s, %s, 'owner') ON CONFLICT (team_id, user_id) DO NOTHING""",
                (team_id, owner_id),
            )
            cur.execute(
                """INSERT INTO team_members (team_id, user_id, role)
                   VALUES (%s, %s, 'member') ON CONFLICT (team_id, user_id) DO NOTHING""",
                (team_id, member_id),
            )
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'tx', 'vector', 'pbf', %s, FALSE)""",
                (ts_id, owner_id),
            )
            cur.execute(
                """INSERT INTO team_tilesets (team_id, tileset_id, added_by, permission_level)
                   VALUES (%s, %s, %s, %s)""",
                (team_id, ts_id, owner_id, permission_level),
            )
        return {
            "tileset_id": ts_id,
            "team_id": team_id,
            "owner_id": owner_id,
            "member_id": member_id,
        }

    return _make


def jwt_ctx(user_id):
    return AuthContext(
        user_id=user_id,
        scopes=["read", "write", "delete", "admin"],
        is_api_key=False,
    )


def api_key_ctx(user_id=None, team_id=None, scopes=None):
    return AuthContext(
        user_id=user_id or str(uuid.uuid4()),
        team_id=str(team_id) if team_id else None,
        scopes=scopes if scopes is not None else ["read", "write"],
        is_api_key=True,
        api_key_id=str(uuid.uuid4()),
    )


# ---------------------------------------------------------------------------
# JWT 既存フロー（後方互換）
# ---------------------------------------------------------------------------


class TestJwtRegression:
    def test_jwt_owner_can_patch(self, client_for, make_tileset):
        ts = make_tileset()
        client = client_for(jwt_ctx(ts["user_id"]))
        res = client.patch(
            f"/api/tilesets/{ts['id']}",
            json={"name": "renamed"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["name"] == "renamed"

    def test_jwt_owner_can_delete(self, client_for, make_tileset):
        ts = make_tileset()
        client = client_for(jwt_ctx(ts["user_id"]))
        res = client.delete(f"/api/tilesets/{ts['id']}")
        assert res.status_code == 204

    def test_jwt_outsider_403(self, client_for, make_tileset):
        ts = make_tileset()
        outsider = jwt_ctx(str(uuid.uuid4()))
        client = client_for(outsider)
        res = client.patch(
            f"/api/tilesets/{ts['id']}",
            json={"name": "hijack"},
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# API キー — scope 不足
# ---------------------------------------------------------------------------


class TestApiKeyScopeGuards:
    def test_read_only_api_key_cannot_patch(self, client_for, make_tileset):
        ts = make_tileset()
        # read scope のみ → write 必要な PATCH は拒否
        ctx = api_key_ctx(user_id=ts["user_id"], scopes=["read"])
        client = client_for(ctx)
        res = client.patch(f"/api/tilesets/{ts['id']}", json={"name": "x"})
        assert res.status_code == 403

    def test_read_only_api_key_cannot_delete(self, client_for, make_tileset):
        ts = make_tileset()
        ctx = api_key_ctx(user_id=ts["user_id"], scopes=["read"])
        client = client_for(ctx)
        res = client.delete(f"/api/tilesets/{ts['id']}")
        assert res.status_code == 403

    def test_write_only_api_key_cannot_delete(self, client_for, make_tileset):
        ts = make_tileset()
        # write scope はあるが delete scope は無い → DELETE 拒否
        ctx = api_key_ctx(user_id=ts["user_id"], scopes=["read", "write"])
        client = client_for(ctx)
        res = client.delete(f"/api/tilesets/{ts['id']}")
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# API キー — owner 経路（個人タイルセット）
# ---------------------------------------------------------------------------


class TestApiKeyOwnerWrite:
    def test_owner_api_key_with_write_can_patch(self, client_for, make_tileset):
        ts = make_tileset()
        ctx = api_key_ctx(user_id=ts["user_id"], scopes=["read", "write"])
        client = client_for(ctx)
        res = client.patch(
            f"/api/tilesets/{ts['id']}",
            json={"name": "via-api-key"},
        )
        assert res.status_code == 200, res.text
        assert res.json()["name"] == "via-api-key"

    def test_owner_api_key_with_delete_can_delete(self, client_for, make_tileset):
        ts = make_tileset()
        ctx = api_key_ctx(
            user_id=ts["user_id"],
            scopes=["read", "write", "delete"],
        )
        client = client_for(ctx)
        res = client.delete(f"/api/tilesets/{ts['id']}")
        assert res.status_code == 204


# ---------------------------------------------------------------------------
# API キー — team 経路（共有タイルセット）
# ---------------------------------------------------------------------------


class TestApiKeyTeamWrite:
    def test_team_api_key_write_permission_can_patch(
        self, client_for, make_team_tileset
    ):
        team = make_team_tileset(permission_level="write")
        # API キーは team に紐付く（API キー所有者 user_id は member ではない）
        ctx = api_key_ctx(team_id=team["team_id"], scopes=["read", "write"])
        client = client_for(ctx)
        res = client.patch(
            f"/api/tilesets/{team['tileset_id']}",
            json={"name": "team-update"},
        )
        assert res.status_code == 200, res.text

    def test_team_api_key_read_permission_cannot_patch(
        self, client_for, make_team_tileset
    ):
        team = make_team_tileset(permission_level="read")
        # team_tilesets が read のみ → write 不可
        ctx = api_key_ctx(team_id=team["team_id"], scopes=["read", "write"])
        client = client_for(ctx)
        res = client.patch(
            f"/api/tilesets/{team['tileset_id']}",
            json={"name": "x"},
        )
        assert res.status_code == 403

    def test_team_api_key_admin_permission_can_delete(
        self, client_for, make_team_tileset
    ):
        team = make_team_tileset(permission_level="admin")
        ctx = api_key_ctx(
            team_id=team["team_id"],
            scopes=["read", "write", "delete"],
        )
        client = client_for(ctx)
        res = client.delete(f"/api/tilesets/{team['tileset_id']}")
        assert res.status_code == 204

    def test_team_api_key_write_permission_cannot_delete(
        self, client_for, make_team_tileset
    ):
        team = make_team_tileset(permission_level="write")
        # write のみ → delete (admin permission_level) 不可
        ctx = api_key_ctx(
            team_id=team["team_id"],
            scopes=["read", "write", "delete"],
        )
        client = client_for(ctx)
        res = client.delete(f"/api/tilesets/{team['tileset_id']}")
        assert res.status_code == 403

    def test_api_key_no_team_id_for_team_tileset_403(
        self, client_for, make_team_tileset
    ):
        team = make_team_tileset(permission_level="write")
        # team_id が無い API キー（オーナーでもない）→ 403
        ctx = api_key_ctx(team_id=None, scopes=["read", "write"])
        client = client_for(ctx)
        res = client.patch(
            f"/api/tilesets/{team['tileset_id']}",
            json={"name": "x"},
        )
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/tilesets（create）— write scope ガード
# ---------------------------------------------------------------------------


class TestApiKeyCreate:
    def test_api_key_with_write_can_create(self, client_for):
        user_id = str(uuid.uuid4())
        ctx = api_key_ctx(user_id=user_id, scopes=["read", "write"])
        client = client_for(ctx)
        res = client.post(
            "/api/tilesets",
            json={
                "name": "new-tileset",
                "type": "vector",
                "format": "pbf",
            },
        )
        assert res.status_code == 201, res.text
        assert res.json()["name"] == "new-tileset"

    def test_api_key_read_only_cannot_create(self, client_for):
        ctx = api_key_ctx(scopes=["read"])
        client = client_for(ctx)
        res = client.post(
            "/api/tilesets",
            json={
                "name": "new-tileset",
                "type": "vector",
                "format": "pbf",
            },
        )
        assert res.status_code == 403
