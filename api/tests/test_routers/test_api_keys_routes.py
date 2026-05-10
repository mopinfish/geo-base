"""Integration tests for issue #79 — POST/PUT /api/api-keys の JSONB バインド。

`api_keys.metadata` は JSONB カラムだが、以前は dict をそのまま psycopg2 に
渡していたため `can't adapt type 'dict'` で 500 を返していた。本テストは
HTTP レイヤから POST と PUT を叩いて metadata 有無の両ケースで成功することを
確認する。リグレッション防止が主目的。

テスト分離は test_write_api_key_auth.py と同じ `_CommitNoOpConn` 方式。
"""
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.auth import User, require_auth
from lib.database import get_connection
from lib.routers.api_keys import router as api_keys_router


class _CommitNoOpConn:
    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def commit(self):
        pass


@pytest.fixture
def stub_user():
    return User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User",
        role="authenticated",
        app_metadata={},
        user_metadata={},
        email_verified=True,
    )


@pytest.fixture
def app(db_conn, stub_user):
    no_commit_conn = _CommitNoOpConn(db_conn)

    app = FastAPI()
    # router 自身が prefix="/api/api-keys" を持つので追加 prefix は付けない
    app.include_router(api_keys_router)

    def _get_conn():
        yield no_commit_conn

    async def _require_auth():
        return stub_user

    app.dependency_overrides[get_connection] = _get_conn
    app.dependency_overrides[require_auth] = _require_auth
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestCreateApiKeyJsonbBinding:
    """issue #79: metadata が JSONB に正しく bind されること。"""

    def test_create_without_metadata_returns_201(self, client):
        # metadata を渡さない（デフォルト None）→ "{}" として書き込まれるはず
        res = client.post(
            "/api/api-keys",
            json={"name": "no-meta-key", "scopes": ["read"], "environment": "test"},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["name"] == "no-meta-key"
        assert "key" in body and body["key"].startswith("gb_test_")

    def test_create_with_empty_metadata_returns_201(self, client):
        # metadata={} の falsy 分岐を通る → "{}" として書き込まれる
        res = client.post(
            "/api/api-keys",
            json={
                "name": "empty-meta-key",
                "scopes": ["read"],
                "environment": "test",
                "metadata": {},
            },
        )
        assert res.status_code == 201, res.text

    def test_create_with_populated_metadata_returns_201(self, client, db_conn):
        # 値を持つ metadata の往復確認
        res = client.post(
            "/api/api-keys",
            json={
                "name": "rich-meta-key",
                "scopes": ["write"],
                "environment": "test",
                "metadata": {"project": "verify-79", "env": "ci"},
            },
        )
        assert res.status_code == 201, res.text
        key_id = res.json()["id"]

        with db_conn.cursor() as cur:
            cur.execute("SELECT metadata FROM api_keys WHERE id = %s", (key_id,))
            (stored,) = cur.fetchone()
        assert stored == {"project": "verify-79", "env": "ci"}


class TestUpdateApiKeyJsonbBinding:
    """PUT /{key_id} 経由の metadata 更新でも同じ adapter を通ること。"""

    def test_update_metadata_returns_200(self, client, db_conn):
        create = client.post(
            "/api/api-keys",
            json={"name": "to-update", "scopes": ["read"], "environment": "test"},
        )
        assert create.status_code == 201, create.text
        key_id = create.json()["id"]

        update = client.put(
            f"/api/api-keys/{key_id}",
            json={"metadata": {"updated": True, "rev": 2}},
        )
        assert update.status_code == 200, update.text

        with db_conn.cursor() as cur:
            cur.execute("SELECT metadata FROM api_keys WHERE id = %s", (key_id,))
            (stored,) = cur.fetchone()
        assert stored == {"updated": True, "rev": 2}
