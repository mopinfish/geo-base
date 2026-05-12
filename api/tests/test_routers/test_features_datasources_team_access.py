"""Integration tests for issue #51 — features / datasources router team-share read.

旧 `check_tileset_access` から `check_tileset_access_v2` に移行したことで、
team_tilesets 経由で共有された tileset 配下の feature / datasource を
チームメンバーが読めるようになることを HTTP レイヤで検証する。

最小限の FastAPI app + TestClient を立ち上げ、`get_connection` /
`get_auth_context_optional` を dependency_overrides で差し替える。

Note: seed fixture 内では `db_conn.commit()` を呼ばない。app は
`app.dependency_overrides` で同一 `db_conn` を共有するので、未コミット
でもデータが見える。test 終了時の `db_conn.rollback()` で自動 cleanup
される（テスト DB にデータが残留しない）。
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth import AuthContext, get_auth_context_optional
from lib.database import get_connection
from lib.routers.datasources import router as datasources_router
from lib.routers.features import router as features_router

# ---------------------------------------------------------------------------
# Test app + dependency overrides
# ---------------------------------------------------------------------------


@pytest.fixture
def app(db_conn):
    """features / datasources router だけを乗せた最小 FastAPI app。

    `get_connection` を db_conn fixture に差し替えて test DB を使う。
    `get_auth_context_optional` は per-test で AuthContext を流し込む。
    """
    app = FastAPI()
    app.include_router(features_router)
    app.include_router(datasources_router)

    def _get_conn():
        # generator pattern (FastAPI Depends 互換)
        yield db_conn

    app.dependency_overrides[get_connection] = _get_conn
    return app


@pytest.fixture
def client_for(app):
    """`AuthContext` (or None) を渡して TestClient を作る factory。"""

    def _make(ctx):
        async def _override():
            return ctx

        app.dependency_overrides[get_auth_context_optional] = _override
        return TestClient(app)

    return _make


# ---------------------------------------------------------------------------
# DB シード fixtures（make_user 等は async と相性が悪いので SQL 直挿入）
# ---------------------------------------------------------------------------


@pytest.fixture
def make_team_with_member(db_conn):
    """チーム + owner + member を作る。tileset を team に紐付ける作業は呼び出し側で。"""

    def _make():
        owner_id = str(uuid.uuid4())
        member_id = str(uuid.uuid4())
        team_id = str(uuid.uuid4())
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
        return {"team_id": team_id, "owner_id": owner_id, "member_id": member_id}

    return _make


@pytest.fixture
def make_tileset_with_feature(db_conn):
    """tileset + feature を 1 件作って ID を返す。"""

    def _make(owner_id=None, is_public=False):
        owner_id = owner_id or str(uuid.uuid4())
        ts_id = str(uuid.uuid4())
        feature_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'tx', 'vector', 'pbf', %s, %s)""",
                (ts_id, owner_id, is_public),
            )
            cur.execute(
                """INSERT INTO features (id, tileset_id, layer_name, geom, properties)
                   VALUES (%s, %s, 'default',
                           ST_SetSRID(ST_MakePoint(139.7, 35.7), 4326),
                           '{}'::jsonb)""",
                (feature_id, ts_id),
            )
        return {"tileset_id": ts_id, "feature_id": feature_id, "owner_id": owner_id}

    return _make


@pytest.fixture
def make_pmtiles_datasource(db_conn):
    """tileset + pmtiles_sources レコードを 1 件作って ID を返す。"""

    def _make(owner_id=None, is_public=False):
        owner_id = owner_id or str(uuid.uuid4())
        ts_id = str(uuid.uuid4())
        ds_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'tx', 'pmtiles', 'pmtiles', %s, %s)""",
                (ts_id, owner_id, is_public),
            )
            cur.execute(
                """INSERT INTO pmtiles_sources (id, tileset_id, pmtiles_url)
                   VALUES (%s, %s, 'https://example.test/foo.pmtiles')""",
                (ds_id, ts_id),
            )
        return {"tileset_id": ts_id, "datasource_id": ds_id, "owner_id": owner_id}

    return _make


@pytest.fixture
def make_cog_datasource(db_conn):
    """tileset + raster_sources (COG) レコードを 1 件作って ID を返す。"""

    def _make(owner_id=None, is_public=False):
        owner_id = owner_id or str(uuid.uuid4())
        ts_id = str(uuid.uuid4())
        ds_id = str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
                   VALUES (%s, 'tx', 'raster', 'cog', %s, %s)""",
                (ts_id, owner_id, is_public),
            )
            cur.execute(
                """INSERT INTO raster_sources (id, tileset_id, cog_url, storage_provider)
                   VALUES (%s, %s, 'https://example.test/foo.tif', 'http')""",
                (ds_id, ts_id),
            )
        return {"tileset_id": ts_id, "datasource_id": ds_id, "owner_id": owner_id}

    return _make


@pytest.fixture
def attach_to_team(db_conn):
    """team_tilesets に紐付ける factory。"""

    def _attach(team_id, tileset_id, *, permission_level=None, added_by=None):
        added_by = added_by or str(uuid.uuid4())
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO team_tilesets
                       (team_id, tileset_id, added_by, permission_level)
                   VALUES (%s, %s, %s, %s)""",
                (team_id, tileset_id, added_by, permission_level),
            )

    return _attach


def jwt_ctx(user_id):
    return AuthContext(
        user_id=user_id,
        scopes=["read", "write", "delete", "admin"],
        is_api_key=False,
    )


# ---------------------------------------------------------------------------
# features.py
# ---------------------------------------------------------------------------


class TestFeaturesTeamShare:
    def test_get_feature_team_member_can_read_shared(
        self,
        client_for,
        make_team_with_member,
        make_tileset_with_feature,
        attach_to_team,
    ):
        team = make_team_with_member()
        ts = make_tileset_with_feature()  # tileset owner ≠ team member
        attach_to_team(team["team_id"], ts["tileset_id"])  # permission_level=NULL → role 継承

        client = client_for(jwt_ctx(team["member_id"]))
        res = client.get(f"/api/features/{ts['feature_id']}")
        assert res.status_code == 200, res.text
        assert res.json()["id"] == ts["feature_id"]

    def test_get_feature_outsider_denied(
        self,
        client_for,
        make_tileset_with_feature,
    ):
        ts = make_tileset_with_feature()
        outsider = jwt_ctx(str(uuid.uuid4()))
        client = client_for(outsider)
        res = client.get(f"/api/features/{ts['feature_id']}")
        assert res.status_code == 403

    def test_get_feature_anonymous_on_private_returns_401(
        self,
        client_for,
        make_tileset_with_feature,
    ):
        ts = make_tileset_with_feature()
        client = client_for(None)
        res = client.get(f"/api/features/{ts['feature_id']}")
        assert res.status_code == 401

    def test_list_features_by_tileset_team_member(
        self,
        client_for,
        make_team_with_member,
        make_tileset_with_feature,
        attach_to_team,
    ):
        team = make_team_with_member()
        ts = make_tileset_with_feature()
        attach_to_team(team["team_id"], ts["tileset_id"])

        client = client_for(jwt_ctx(team["member_id"]))
        res = client.get(f"/api/features?tileset_id={ts['tileset_id']}")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["type"] == "FeatureCollection"
        assert any(f["properties"]["tileset_id"] == ts["tileset_id"] for f in body["features"])

    def test_list_features_outsider_denied(
        self,
        client_for,
        make_tileset_with_feature,
    ):
        ts = make_tileset_with_feature()
        client = client_for(jwt_ctx(str(uuid.uuid4())))
        res = client.get(f"/api/features?tileset_id={ts['tileset_id']}")
        assert res.status_code == 403


# ---------------------------------------------------------------------------
# datasources.py
# ---------------------------------------------------------------------------


class TestDatasourcesTeamShare:
    def test_get_datasource_team_member_can_read_shared(
        self,
        client_for,
        make_team_with_member,
        make_pmtiles_datasource,
        attach_to_team,
    ):
        team = make_team_with_member()
        ds = make_pmtiles_datasource()
        attach_to_team(team["team_id"], ds["tileset_id"])

        client = client_for(jwt_ctx(team["member_id"]))
        res = client.get(f"/api/datasources/{ds['datasource_id']}")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["id"] == ds["datasource_id"]
        assert body["type"] == "pmtiles"

    def test_get_datasource_outsider_denied(
        self,
        client_for,
        make_pmtiles_datasource,
    ):
        ds = make_pmtiles_datasource()
        client = client_for(jwt_ctx(str(uuid.uuid4())))
        res = client.get(f"/api/datasources/{ds['datasource_id']}")
        assert res.status_code == 403

    def test_get_datasource_anonymous_on_private_returns_401(
        self,
        client_for,
        make_pmtiles_datasource,
    ):
        ds = make_pmtiles_datasource()
        client = client_for(None)
        res = client.get(f"/api/datasources/{ds['datasource_id']}")
        assert res.status_code == 401

    def test_get_datasource_public_tileset_open_to_all(
        self,
        client_for,
        make_pmtiles_datasource,
    ):
        ds = make_pmtiles_datasource(is_public=True)
        client = client_for(None)  # anonymous
        res = client.get(f"/api/datasources/{ds['datasource_id']}")
        assert res.status_code == 200

    # COG (raster_sources) 経路 — get_datasource は PMTiles でヒットしなかった
    # 場合に raster_sources を引く 2 段構成のため、別経路として明示的にテスト
    def test_get_cog_datasource_team_member_can_read_shared(
        self,
        client_for,
        make_team_with_member,
        make_cog_datasource,
        attach_to_team,
    ):
        team = make_team_with_member()
        ds = make_cog_datasource()
        attach_to_team(team["team_id"], ds["tileset_id"])

        client = client_for(jwt_ctx(team["member_id"]))
        res = client.get(f"/api/datasources/{ds['datasource_id']}")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["id"] == ds["datasource_id"]
        assert body["type"] == "cog"

    def test_get_cog_datasource_outsider_denied(
        self,
        client_for,
        make_cog_datasource,
    ):
        ds = make_cog_datasource()
        client = client_for(jwt_ctx(str(uuid.uuid4())))
        res = client.get(f"/api/datasources/{ds['datasource_id']}")
        assert res.status_code == 403
