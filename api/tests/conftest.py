"""
Pytest configuration and fixtures for geo-base API tests.

This module provides:
- Path configuration for imports
- Common test fixtures
- Sample data for testing
"""

import os
import sys
from pathlib import Path
from typing import Generator, Optional
import json

import pytest

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(lib_path))

# Add scripts directory to path for fix_bounds tests
scripts_path = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))


# ============================================================================
# Sample GeoJSON Data Fixtures
# ============================================================================

@pytest.fixture
def sample_point():
    """Sample Point geometry."""
    return {
        "type": "Point",
        "coordinates": [139.7, 35.7]
    }


@pytest.fixture
def sample_linestring():
    """Sample LineString geometry."""
    return {
        "type": "LineString",
        "coordinates": [
            [139.7, 35.7],
            [139.8, 35.8],
            [139.9, 35.9]
        ]
    }


@pytest.fixture
def sample_polygon():
    """Sample Polygon geometry (closed ring)."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [139.7, 35.7],
            [139.8, 35.7],
            [139.8, 35.8],
            [139.7, 35.8],
            [139.7, 35.7]  # Closed
        ]]
    }


@pytest.fixture
def sample_polygon_with_hole():
    """Sample Polygon with a hole."""
    return {
        "type": "Polygon",
        "coordinates": [
            # Exterior ring
            [
                [139.7, 35.7],
                [139.9, 35.7],
                [139.9, 35.9],
                [139.7, 35.9],
                [139.7, 35.7]
            ],
            # Hole
            [
                [139.75, 35.75],
                [139.85, 35.75],
                [139.85, 35.85],
                [139.75, 35.85],
                [139.75, 35.75]
            ]
        ]
    }


@pytest.fixture
def sample_multipoint():
    """Sample MultiPoint geometry."""
    return {
        "type": "MultiPoint",
        "coordinates": [
            [139.7, 35.7],
            [139.8, 35.8],
            [139.9, 35.9]
        ]
    }


@pytest.fixture
def sample_multilinestring():
    """Sample MultiLineString geometry."""
    return {
        "type": "MultiLineString",
        "coordinates": [
            [[139.7, 35.7], [139.8, 35.8]],
            [[140.0, 36.0], [140.1, 36.1]]
        ]
    }


@pytest.fixture
def sample_multipolygon():
    """Sample MultiPolygon geometry."""
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [[[139.7, 35.7], [139.8, 35.7], [139.8, 35.8], [139.7, 35.8], [139.7, 35.7]]],
            [[[140.0, 36.0], [140.1, 36.0], [140.1, 36.1], [140.0, 36.1], [140.0, 36.0]]]
        ]
    }


@pytest.fixture
def sample_geometry_collection(sample_point, sample_linestring):
    """Sample GeometryCollection."""
    return {
        "type": "GeometryCollection",
        "geometries": [sample_point, sample_linestring]
    }


@pytest.fixture
def sample_feature(sample_point):
    """Sample GeoJSON Feature."""
    return {
        "type": "Feature",
        "geometry": sample_point,
        "properties": {
            "name": "Tokyo Tower",
            "height": 333
        }
    }


@pytest.fixture
def sample_feature_collection(sample_point, sample_polygon):
    """Sample GeoJSON FeatureCollection."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": sample_point,
                "properties": {"name": "Point 1"}
            },
            {
                "type": "Feature",
                "geometry": sample_polygon,
                "properties": {"name": "Polygon 1"}
            }
        ]
    }


# ============================================================================
# Bounds and Center Fixtures
# ============================================================================

@pytest.fixture
def sample_bounds_tokyo():
    """Sample bounds covering Tokyo area."""
    return [139.5, 35.5, 140.0, 36.0]


@pytest.fixture
def sample_bounds_world():
    """World bounds."""
    return [-180, -90, 180, 90]


@pytest.fixture
def sample_bounds_antimeridian():
    """Bounds crossing antimeridian (Pacific)."""
    return [170.0, -50.0, -170.0, -30.0]


@pytest.fixture
def sample_center_tokyo():
    """Sample center point in Tokyo."""
    return [139.75, 35.75]


@pytest.fixture
def sample_center_with_zoom():
    """Sample center point with zoom level."""
    return [139.75, 35.75, 10]


# ============================================================================
# Invalid Data Fixtures (for error testing)
# ============================================================================

@pytest.fixture
def invalid_geometry_no_type():
    """Invalid geometry missing type."""
    return {"coordinates": [139.7, 35.7]}


@pytest.fixture
def invalid_geometry_bad_type():
    """Invalid geometry with unknown type."""
    return {"type": "InvalidType", "coordinates": [139.7, 35.7]}


@pytest.fixture
def invalid_geometry_no_coords():
    """Invalid geometry missing coordinates."""
    return {"type": "Point"}


@pytest.fixture
def invalid_point_out_of_range():
    """Point with coordinates out of valid range."""
    return {"type": "Point", "coordinates": [200, 100]}


@pytest.fixture
def invalid_polygon_not_closed():
    """Polygon that is not closed."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [139.7, 35.7],
            [139.8, 35.7],
            [139.8, 35.8],
            [139.7, 35.8]
            # Missing closing point
        ]]
    }


@pytest.fixture
def invalid_bounds_south_greater():
    """Invalid bounds where south > north."""
    return [139.5, 40.0, 140.0, 35.0]


@pytest.fixture
def invalid_center_out_of_range():
    """Invalid center with longitude out of range."""
    return [200, 35.7]


# ============================================================================
# Tileset Data Fixtures
# ============================================================================

@pytest.fixture
def sample_tileset_create_data():
    """Sample data for creating a tileset."""
    return {
        "name": "Test Tileset",
        "description": "A test tileset for unit testing",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 18,
        "bounds": [139.5, 35.5, 140.0, 36.0],
        "center": [139.75, 35.75, 10],
        "attribution": "© Test",
        "is_public": True
    }


@pytest.fixture
def sample_tileset_update_data():
    """Sample data for updating a tileset."""
    return {
        "name": "Updated Tileset",
        "description": "Updated description",
        "bounds": [139.4, 35.4, 140.1, 36.1]
    }


# ============================================================================
# Feature Data Fixtures
# ============================================================================

@pytest.fixture
def sample_feature_create_data(sample_point):
    """Sample data for creating a feature."""
    return {
        "tileset_id": "test-tileset-id",
        "layer_name": "default",
        "geometry": sample_point,
        "properties": {"name": "Test Feature"}
    }


@pytest.fixture
def sample_bulk_features(sample_point, sample_polygon):
    """Sample data for bulk feature creation."""
    return [
        {
            "type": "Feature",
            "geometry": sample_point,
            "properties": {"name": "Feature 1"}
        },
        {
            "type": "Feature", 
            "geometry": sample_polygon,
            "properties": {"name": "Feature 2"}
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [140.0, 36.0]},
            "properties": {"name": "Feature 3"}
        }
    ]


# ============================================================================
# Database Fixtures (for integration tests)
# ============================================================================
#
# Tests that touch the database MUST connect via TEST_DATABASE_URL, never
# DATABASE_URL. `clean_auth_tables` and the auth/team factories TRUNCATE rows,
# so accidentally pointing them at the dev DB destroys local data (see issue
# #47). The fixtures below enforce this by failing loudly when
# TEST_DATABASE_URL is unset or equal to DATABASE_URL.

@pytest.fixture
def test_database_url():
    """テスト用 DB の接続文字列を TEST_DATABASE_URL から取得する。

    未設定 or dev DB と同一の場合は pytest.fail で停止する（#47）。
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL is not set. "
            "DB を触るテストは専用のテスト DB に接続する必要があります（dev DB の TRUNCATE 事故防止）。"
            "セットアップ手順: docs/AUTH_E2E_CHECKLIST.md / TESTING.md / api/.env.example",
            pytrace=False,
        )
    dev_url = os.environ.get("DATABASE_URL")
    if dev_url and url == dev_url:
        pytest.fail(
            f"TEST_DATABASE_URL must differ from DATABASE_URL ({dev_url}). "
            "dev DB を破壊しないよう、別 DB（例: geo_base_test）を指定してください。",
            pytrace=False,
        )
    return url


@pytest.fixture
def database_url(test_database_url):
    """後方互換: 既存テストが参照する fixture 名。test_database_url を返す。"""
    return test_database_url


@pytest.fixture
def db_connection(test_database_url):
    """
    Create a database connection for testing.

    Note: This fixture requires psycopg2 and a valid TEST_DATABASE_URL.
    It creates a connection that is rolled back after each test.
    """
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed")

    conn = psycopg2.connect(test_database_url)
    conn.autocommit = False

    yield conn

    # Rollback any changes made during the test
    conn.rollback()
    conn.close()


@pytest.fixture
def db_conn(test_database_url, monkeypatch):
    """テスト用 DB 接続。各テスト後に rollback。TEST_DATABASE_URL が必須。

    `lib.database` の connection pool もテスト DB に向けるため、
    DATABASE_URL を test_database_url に差し替え、settings cache を無効化する。
    こうしないとアプリ層（`LocalAuthProvider` 等）が dev DB に接続してしまう。
    """
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed")

    monkeypatch.setenv("DATABASE_URL", test_database_url)
    from lib.config import get_settings
    from lib.database import close_pool
    get_settings.cache_clear()
    close_pool()

    conn = psycopg2.connect(test_database_url)
    yield conn
    conn.rollback()
    conn.close()
    close_pool()
    get_settings.cache_clear()


@pytest.fixture
def clean_auth_tables(db_conn):
    """auth 関連テーブルをクリーンアップ"""
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE refresh_tokens, auth_login_attempts, password_reset_tokens, users CASCADE"
        )
    db_conn.commit()
    yield


# ============================================================================
# Utility Functions
# ============================================================================

def assert_valid_geojson_geometry(geometry: dict) -> None:
    """Assert that a geometry is valid GeoJSON."""
    assert isinstance(geometry, dict), "Geometry must be a dict"
    assert "type" in geometry, "Geometry must have 'type'"
    
    if geometry["type"] == "GeometryCollection":
        assert "geometries" in geometry, "GeometryCollection must have 'geometries'"
    else:
        assert "coordinates" in geometry, "Geometry must have 'coordinates'"


def assert_valid_geojson_feature(feature: dict) -> None:
    """Assert that a feature is valid GeoJSON."""
    assert isinstance(feature, dict), "Feature must be a dict"
    assert feature.get("type") == "Feature", "Feature type must be 'Feature'"
    assert "geometry" in feature, "Feature must have 'geometry'"
    assert "properties" in feature, "Feature must have 'properties'"


def assert_valid_bounds(bounds: list) -> None:
    """Assert that bounds are valid."""
    assert isinstance(bounds, list), "Bounds must be a list"
    assert len(bounds) == 4, "Bounds must have 4 values"
    west, south, east, north = bounds
    assert -180 <= west <= 180, "West must be in valid range"
    assert -180 <= east <= 180, "East must be in valid range"
    assert -90 <= south <= 90, "South must be in valid range"
    assert -90 <= north <= 90, "North must be in valid range"
    assert south <= north, "South must be <= North"


# ============================================================================
# Auth / Team / API Key / Tileset Fixtures (pluggable auth Phase 4)
# ============================================================================

@pytest.fixture
def null_email_backend(monkeypatch):
    """get_email_backend() を NullEmailBackend に差し替え。"""
    from lib.auth.email_backends import NullEmailBackend, get_email_backend
    backend = NullEmailBackend()
    monkeypatch.setattr("lib.auth.email_backends.get_email_backend", lambda: backend)
    get_email_backend.cache_clear()
    return backend


@pytest.fixture
def local_auth_settings(monkeypatch, test_database_url):
    """テスト用 local 認証設定オーバーライド。

    DATABASE_URL を TEST_DATABASE_URL に差し替えるので、ファクトリ経由で
    `lib.database` の connection pool が test DB に向く。dev DB を破壊しない
    ための要請（issue #47）。
    """
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-for-production-" + "x" * 40)
    monkeypatch.setenv("JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("JWT_ISSUER", "geo-base-test")
    monkeypatch.setenv("EMAIL_BACKEND", "null")
    monkeypatch.setenv("INVITATION_BASE_URL", "http://testserver")
    monkeypatch.setenv("CORS_ORIGINS", '["http://testserver"]')
    monkeypatch.setenv("DATABASE_URL", test_database_url)

    from lib.config import get_settings
    from lib.auth import get_auth_provider
    from lib.auth.email_backends import get_email_backend
    from lib.database import close_pool
    get_settings.cache_clear()
    get_auth_provider.cache_clear()
    get_email_backend.cache_clear()
    close_pool()
    yield
    get_settings.cache_clear()
    get_auth_provider.cache_clear()
    get_email_backend.cache_clear()
    close_pool()


@pytest.fixture
def make_user(db_conn, clean_auth_tables, local_auth_settings):
    """ローカル DB にユーザーを作成するファクトリ。"""
    import uuid as uuid_lib
    import asyncio
    from lib.auth.providers.local import LocalAuthProvider

    def _make(email=None, password="ValidPass123", name="Test User"):
        email = email or f"u-{uuid_lib.uuid4().hex[:8]}@example.test"
        provider = LocalAuthProvider()
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                provider.create_user(email, password, name=name, email_verified=True)
            )
        finally:
            loop.close()

    return _make


@pytest.fixture
def make_team(db_conn, make_user):
    """チーム作成ファクトリ。"""
    import uuid as uuid_lib

    def _make(owner=None, name=None):
        owner = owner or make_user()
        team_name = name or f"team-{uuid_lib.uuid4().hex[:6]}"
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teams (name, slug, owner_id) VALUES (%s, %s, %s) RETURNING id",
                (team_name, team_name.lower(), owner.id),
            )
            team_id = str(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO team_members (team_id, user_id, role) VALUES (%s, %s, 'owner')",
                (team_id, owner.id),
            )
        db_conn.commit()
        return {"id": team_id, "name": team_name, "owner": owner}

    return _make


@pytest.fixture
def make_api_key(db_conn, make_user):
    """API キー発行ファクトリ。"""
    import secrets, hashlib

    def _make(user=None, team_id=None, scopes=None):
        user = user or make_user()
        scopes = scopes or ["read"]
        random_part = secrets.token_urlsafe(32)
        full_key = f"gb_test_{random_part}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        prefix = full_key[:12]
        with db_conn.cursor() as cur:
            cur.execute(
                """INSERT INTO api_keys (name, prefix, key_hash, user_id, team_id, scopes)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                ("test", prefix, key_hash, user.id, team_id, scopes),
            )
            key_id = str(cur.fetchone()[0])
        db_conn.commit()
        return {"key": full_key, "id": key_id, "user": user}

    return _make


@pytest.fixture
def public_tileset(db_conn, make_user):
    """公開タイルセット"""
    import uuid as uuid_lib
    user = make_user()
    tid = str(uuid_lib.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
               VALUES (%s, 'public', 'vector', 'pbf', %s, TRUE)""",
            (tid, user.id),
        )
    db_conn.commit()
    return {"id": tid, "owner": user}


@pytest.fixture
def private_tileset(db_conn, make_user):
    """非公開タイルセット"""
    import uuid as uuid_lib
    user = make_user()
    tid = str(uuid_lib.uuid4())
    with db_conn.cursor() as cur:
        cur.execute(
            """INSERT INTO tilesets (id, name, type, format, user_id, is_public)
               VALUES (%s, 'private', 'vector', 'pbf', %s, FALSE)""",
            (tid, user.id),
        )
    db_conn.commit()
    return {"id": tid, "owner": user}
