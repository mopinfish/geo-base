"""Unit tests for lib.database SSL handling.

`_prepare_connection_string` の SSL 自動付与ロジックを検証する。本番 (Fly.io 上)
で `geo-base-pg.internal:5432` 等の private hostname に接続するときは、Fly の
6PN/WireGuard で既にネットワーク層暗号化されており、postgis/postgis 公式 image は
SSL 設定なしで起動するため、`sslmode=require` を付けてはならない。
"""
from urllib.parse import parse_qs, urlparse

import pytest

from lib.config import get_settings
from lib.database import _prepare_connection_string


def _sslmode(url: str):
    return parse_qs(urlparse(url).query).get("sslmode", [None])[0]


@pytest.fixture
def force_production(monkeypatch):
    """Settings.is_production が True になる状態を作る (FLY_APP_NAME 経由)。"""
    monkeypatch.setenv("FLY_APP_NAME", "geo-base-api")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def force_local(monkeypatch):
    """is_production が False の local-dev 相当の状態。"""
    monkeypatch.delenv("FLY_APP_NAME", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSSLAutoAppend:
    def test_production_supabase_gets_sslmode_require(self, force_production):
        url = "postgresql://user:pass@db.aws.supabase.co:6543/postgres"
        assert _sslmode(_prepare_connection_string(url)) == "require"

    def test_production_external_host_gets_sslmode_require(self, force_production):
        """通常のクラウド DB (RDS など) は SSL 必須のまま。"""
        url = "postgresql://user:pass@my-db.example.com:5432/geo_base"
        assert _sslmode(_prepare_connection_string(url)) == "require"

    def test_production_fly_internal_skips_sslmode(self, force_production):
        """Fly 6PN 内部接続では sslmode は付与されない (postgis/postgis は SSL 非対応)。"""
        url = "postgresql://postgres:pass@geo-base-pg.internal:5432/geo_base"
        assert _sslmode(_prepare_connection_string(url)) is None

    def test_production_fly_flycast_skips_sslmode(self, force_production):
        """`.flycast` ホスト (load balanced internal service) も同様にスキップ。"""
        url = "postgresql://postgres:pass@geo-base-pg.flycast:5432/geo_base"
        assert _sslmode(_prepare_connection_string(url)) is None

    def test_local_dev_no_sslmode_added(self, force_local):
        """ローカル開発時は sslmode 自動付与しない。"""
        url = "postgresql://postgres:postgres@localhost:5432/geo_base"
        assert _sslmode(_prepare_connection_string(url)) is None

    def test_local_dev_supabase_url_still_gets_sslmode(self, force_local):
        """is_production=False でも URL に supabase を含む場合は SSL を付ける。"""
        url = "postgresql://user:pass@db.aws.supabase.co:6543/postgres"
        assert _sslmode(_prepare_connection_string(url)) == "require"

    def test_explicit_sslmode_in_url_is_preserved(self, force_production):
        """ユーザーが明示的に sslmode を指定している場合は上書きしない。"""
        url = (
            "postgresql://postgres:pass@geo-base-pg.internal:5432/geo_base"
            "?sslmode=disable"
        )
        assert _sslmode(_prepare_connection_string(url)) == "disable"
