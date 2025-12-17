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

@pytest.fixture
def database_url():
    """Get database URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest.fixture
def db_connection(database_url):
    """
    Create a database connection for testing.
    
    Note: This fixture requires psycopg2 and a valid DATABASE_URL.
    It creates a connection that is rolled back after each test.
    """
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed")
    
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    
    yield conn
    
    # Rollback any changes made during the test
    conn.rollback()
    conn.close()


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
