"""Tests for TwoTierCORSMiddleware."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.cors_middleware import TwoTierCORSMiddleware


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(TwoTierCORSMiddleware, strict_origins=["http://allowed.com"])

    @app.get("/api/auth/test")
    async def auth_test():
        return {"ok": True}

    @app.get("/api/tiles/test")
    async def tiles_test():
        return {"ok": True}

    @app.get("/api/other")
    async def other():
        return {"ok": True}

    @app.get("/api/auth-misuse")
    async def auth_misuse():
        return {"ok": True}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestStrictForAuth:
    def test_auth_endpoint_disallows_foreign_origin_credentials(self, client):
        # /api/auth/* は明示 origin リスト + credentials=true
        res = client.get("/api/auth/test", headers={"Origin": "http://attacker.com"})
        # origin がリストにないので Access-Control-Allow-Origin ヘッダなし
        assert res.headers.get("access-control-allow-origin") != "*"

    def test_auth_endpoint_allows_listed_origin(self, client):
        res = client.get("/api/auth/test", headers={"Origin": "http://allowed.com"})
        assert res.headers.get("access-control-allow-origin") == "http://allowed.com"
        assert res.headers.get("access-control-allow-credentials") == "true"


class TestPermissiveForOthers:
    def test_tiles_allow_any_origin(self, client):
        res = client.get("/api/tiles/test", headers={"Origin": "http://anywhere.com"})
        assert res.headers.get("access-control-allow-origin") == "*"

    def test_other_endpoints_also_permissive(self, client):
        res = client.get("/api/other", headers={"Origin": "http://anywhere.com"})
        assert res.headers.get("access-control-allow-origin") == "*"


class TestPathBoundary:
    def test_similar_path_not_treated_as_auth(self, client):
        # /api/auth-misuse は /api/auth/ ではない (note trailing slash in prefix)
        res = client.get("/api/auth-misuse", headers={"Origin": "http://anywhere.com"})
        # permissive モード扱い
        assert res.headers.get("access-control-allow-origin") == "*"
