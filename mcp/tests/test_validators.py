"""
Tests for validators module.

This module tests all validation functions including:
- UUID validation
- Coordinate validation
- Bounding box validation
- Zoom level validation
- Tile coordinate validation
- Tileset type and format validation
- GeoJSON geometry validation
- String and numeric validation
"""

import pytest
from validators import (
    ValidationResult,
    validate_uuid,
    is_valid_uuid,
    validate_latitude,
    validate_longitude,
    validate_coordinates,
    validate_bbox,
    parse_bbox,
    validate_zoom,
    validate_tile_coordinates,
    validate_tileset_type,
    validate_tile_format,
    validate_geometry,
    validate_non_empty_string,
    validate_positive_number,
    validate_range,
    validate_limit,
    validate_filter,
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Valid result should have valid=True."""
        result = ValidationResult(valid=True, value="test")
        assert result.valid is True
        assert result.value == "test"
        assert result.error is None

    def test_invalid_result(self):
        """Invalid result should have error message."""
        result = ValidationResult(valid=False, error="Test error", code="TEST_ERROR")
        assert result.valid is False
        assert result.error == "Test error"
        assert result.code == "TEST_ERROR"

    def test_to_error_response(self):
        """to_error_response should return dict with error details."""
        result = ValidationResult(valid=False, error="Test error", code="TEST_ERROR")
        response = result.to_error_response(field="test_field")
        assert response["error"] == "Test error"
        assert response["code"] == "TEST_ERROR"
        assert response["field"] == "test_field"

    def test_to_error_response_valid(self):
        """to_error_response should return empty dict for valid result."""
        result = ValidationResult(valid=True)
        assert result.to_error_response() == {}


class TestUUIDValidation:
    """Tests for UUID validation."""

    def test_valid_uuid(self):
        """Should accept valid UUID."""
        result = validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        assert result.valid is True
        assert result.value == "550e8400-e29b-41d4-a716-446655440000"

    def test_valid_uuid_uppercase(self):
        """Should accept uppercase UUID."""
        result = validate_uuid("550E8400-E29B-41D4-A716-446655440000")
        assert result.valid is True

    def test_valid_uuid_no_dashes(self):
        """Should accept UUID without dashes."""
        result = validate_uuid("550e8400e29b41d4a716446655440000")
        assert result.valid is True

    def test_invalid_uuid(self):
        """Should reject invalid UUID."""
        result = validate_uuid("not-a-uuid")
        assert result.valid is False
        assert "Invalid" in result.error

    def test_empty_uuid(self):
        """Should reject empty UUID."""
        result = validate_uuid("")
        assert result.valid is False
        assert "required" in result.error

    def test_is_valid_uuid_helper(self):
        """is_valid_uuid should return boolean."""
        assert is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert is_valid_uuid("not-a-uuid") is False


class TestLatitudeValidation:
    """Tests for latitude validation."""

    def test_valid_latitude(self):
        """Should accept valid latitude."""
        result = validate_latitude(35.6812)
        assert result.valid is True
        assert result.value == 35.6812

    def test_valid_latitude_string(self):
        """Should accept latitude as string."""
        result = validate_latitude("35.6812")
        assert result.valid is True
        assert result.value == 35.6812

    def test_latitude_at_bounds(self):
        """Should accept latitude at bounds."""
        assert validate_latitude(90).valid is True
        assert validate_latitude(-90).valid is True
        assert validate_latitude(0).valid is True

    def test_latitude_out_of_range(self):
        """Should reject latitude out of range."""
        assert validate_latitude(91).valid is False
        assert validate_latitude(-91).valid is False

    def test_latitude_not_number(self):
        """Should reject non-numeric latitude."""
        result = validate_latitude("not-a-number")
        assert result.valid is False


class TestLongitudeValidation:
    """Tests for longitude validation."""

    def test_valid_longitude(self):
        """Should accept valid longitude."""
        result = validate_longitude(139.7671)
        assert result.valid is True
        assert result.value == 139.7671

    def test_longitude_at_bounds(self):
        """Should accept longitude at bounds."""
        assert validate_longitude(180).valid is True
        assert validate_longitude(-180).valid is True
        assert validate_longitude(0).valid is True

    def test_longitude_out_of_range(self):
        """Should reject longitude out of range."""
        assert validate_longitude(181).valid is False
        assert validate_longitude(-181).valid is False


class TestCoordinatesValidation:
    """Tests for coordinate pair validation."""

    def test_valid_coordinates(self):
        """Should accept valid coordinates."""
        result = validate_coordinates(35.6812, 139.7671)
        assert result.valid is True
        assert result.value == (35.6812, 139.7671)

    def test_invalid_latitude(self):
        """Should reject invalid latitude."""
        result = validate_coordinates(91, 139.7671)
        assert result.valid is False

    def test_invalid_longitude(self):
        """Should reject invalid longitude."""
        result = validate_coordinates(35.6812, 181)
        assert result.valid is False


class TestBboxValidation:
    """Tests for bounding box validation."""

    def test_valid_bbox_string(self):
        """Should accept valid bbox string."""
        result = validate_bbox("139.5,35.5,140.0,36.0")
        assert result.valid is True
        assert result.value == (139.5, 35.5, 140.0, 36.0)

    def test_valid_bbox_with_spaces(self):
        """Should accept bbox with spaces."""
        result = validate_bbox("139.5, 35.5, 140.0, 36.0")
        assert result.valid is True

    def test_valid_bbox_list(self):
        """Should accept bbox as list."""
        result = validate_bbox([139.5, 35.5, 140.0, 36.0])
        assert result.valid is True
        assert result.value == (139.5, 35.5, 140.0, 36.0)

    def test_invalid_bbox_format(self):
        """Should reject invalid bbox format."""
        result = validate_bbox("invalid")
        assert result.valid is False

    def test_bbox_wrong_count(self):
        """Should reject bbox with wrong number of values."""
        result = validate_bbox("1,2,3")
        assert result.valid is False
        assert "4 values" in result.error

    def test_bbox_min_greater_than_max(self):
        """Should reject bbox where min > max."""
        result = validate_bbox("140.0,35.5,139.5,36.0")
        assert result.valid is False
        assert "less than" in result.error

    def test_bbox_out_of_range(self):
        """Should reject bbox with out-of-range values."""
        result = validate_bbox("139.5,95,140.0,36.0")  # Invalid latitude
        assert result.valid is False

    def test_parse_bbox_helper(self):
        """parse_bbox should return tuple or None."""
        assert parse_bbox("139.5,35.5,140.0,36.0") == (139.5, 35.5, 140.0, 36.0)
        assert parse_bbox("invalid") is None


class TestZoomValidation:
    """Tests for zoom level validation."""

    def test_valid_zoom(self):
        """Should accept valid zoom."""
        result = validate_zoom(10)
        assert result.valid is True
        assert result.value == 10

    def test_zoom_at_bounds(self):
        """Should accept zoom at bounds."""
        assert validate_zoom(0).valid is True
        assert validate_zoom(22).valid is True

    def test_zoom_out_of_range(self):
        """Should reject zoom out of range."""
        assert validate_zoom(-1).valid is False
        assert validate_zoom(23).valid is False

    def test_zoom_custom_range(self):
        """Should respect custom min/max."""
        result = validate_zoom(5, min_zoom=5, max_zoom=15)
        assert result.valid is True
        
        result = validate_zoom(4, min_zoom=5, max_zoom=15)
        assert result.valid is False


class TestTileCoordinatesValidation:
    """Tests for tile coordinate validation."""

    def test_valid_tile_coordinates(self):
        """Should accept valid tile coordinates."""
        result = validate_tile_coordinates(10, 500, 300)
        assert result.valid is True
        assert result.value == (10, 500, 300)

    def test_tile_coordinates_at_bounds(self):
        """Should accept coordinates at bounds."""
        # At zoom 2, max tile is 3 (2^2 - 1)
        result = validate_tile_coordinates(2, 3, 3)
        assert result.valid is True

    def test_tile_coordinates_out_of_range(self):
        """Should reject coordinates out of range."""
        # At zoom 2, max tile is 3
        result = validate_tile_coordinates(2, 4, 0)
        assert result.valid is False


class TestTilesetTypeValidation:
    """Tests for tileset type validation."""

    def test_valid_types(self):
        """Should accept valid tileset types."""
        assert validate_tileset_type("vector").valid is True
        assert validate_tileset_type("raster").valid is True
        assert validate_tileset_type("pmtiles").valid is True

    def test_case_insensitive(self):
        """Should be case insensitive."""
        result = validate_tileset_type("VECTOR")
        assert result.valid is True
        assert result.value == "vector"

    def test_invalid_type(self):
        """Should reject invalid type."""
        result = validate_tileset_type("invalid")
        assert result.valid is False


class TestTileFormatValidation:
    """Tests for tile format validation."""

    def test_valid_formats(self):
        """Should accept valid tile formats."""
        assert validate_tile_format("pbf").valid is True
        assert validate_tile_format("png").valid is True
        assert validate_tile_format("jpg").valid is True
        assert validate_tile_format("webp").valid is True
        assert validate_tile_format("geojson").valid is True

    def test_invalid_format(self):
        """Should reject invalid format."""
        result = validate_tile_format("invalid")
        assert result.valid is False


class TestGeometryValidation:
    """Tests for GeoJSON geometry validation."""

    def test_valid_point(self):
        """Should accept valid Point geometry."""
        geom = {"type": "Point", "coordinates": [139.7671, 35.6812]}
        result = validate_geometry(geom)
        assert result.valid is True

    def test_valid_linestring(self):
        """Should accept valid LineString geometry."""
        geom = {
            "type": "LineString",
            "coordinates": [[0, 0], [1, 1], [2, 2]]
        }
        result = validate_geometry(geom)
        assert result.valid is True

    def test_valid_polygon(self):
        """Should accept valid Polygon geometry."""
        geom = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        result = validate_geometry(geom)
        assert result.valid is True

    def test_missing_type(self):
        """Should reject geometry without type."""
        geom = {"coordinates": [139.7671, 35.6812]}
        result = validate_geometry(geom)
        assert result.valid is False

    def test_invalid_type(self):
        """Should reject invalid geometry type."""
        geom = {"type": "InvalidType", "coordinates": [0, 0]}
        result = validate_geometry(geom)
        assert result.valid is False

    def test_missing_coordinates(self):
        """Should reject geometry without coordinates."""
        geom = {"type": "Point"}
        result = validate_geometry(geom)
        assert result.valid is False

    def test_invalid_point_coordinates(self):
        """Should reject Point with invalid coordinates."""
        geom = {"type": "Point", "coordinates": [139.7671]}  # Only one value
        result = validate_geometry(geom)
        assert result.valid is False

    def test_linestring_too_few_points(self):
        """Should reject LineString with < 2 points."""
        geom = {"type": "LineString", "coordinates": [[0, 0]]}
        result = validate_geometry(geom)
        assert result.valid is False

    def test_polygon_ring_too_few_points(self):
        """Should reject Polygon ring with < 4 points."""
        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 0]]]}
        result = validate_geometry(geom)
        assert result.valid is False

    def test_geometry_collection(self):
        """Should accept valid GeometryCollection."""
        geom = {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Point", "coordinates": [0, 0]},
                {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}
            ]
        }
        result = validate_geometry(geom)
        assert result.valid is True


class TestStringValidation:
    """Tests for string validation."""

    def test_valid_string(self):
        """Should accept non-empty string."""
        result = validate_non_empty_string("test", "field")
        assert result.valid is True
        assert result.value == "test"

    def test_empty_string(self):
        """Should reject empty string."""
        result = validate_non_empty_string("", "field")
        assert result.valid is False

    def test_whitespace_only(self):
        """Should reject whitespace-only string."""
        result = validate_non_empty_string("   ", "field")
        assert result.valid is False

    def test_max_length(self):
        """Should enforce max length."""
        result = validate_non_empty_string("test", "field", max_length=3)
        assert result.valid is False
        
        result = validate_non_empty_string("test", "field", max_length=10)
        assert result.valid is True


class TestNumericValidation:
    """Tests for numeric validation."""

    def test_positive_number(self):
        """Should accept positive numbers."""
        result = validate_positive_number(5.5, "field")
        assert result.valid is True
        assert result.value == 5.5

    def test_positive_rejects_zero(self):
        """Should reject zero by default."""
        result = validate_positive_number(0, "field")
        assert result.valid is False

    def test_positive_allows_zero(self):
        """Should allow zero when specified."""
        result = validate_positive_number(0, "field", allow_zero=True)
        assert result.valid is True

    def test_range_validation(self):
        """Should validate numeric range."""
        result = validate_range(5, "field", min_value=1, max_value=10)
        assert result.valid is True
        
        result = validate_range(0, "field", min_value=1, max_value=10)
        assert result.valid is False

    def test_limit_validation(self):
        """Should validate limit parameter."""
        result = validate_limit(50, "limit")
        assert result.valid is True
        assert result.value == 50
        
        result = validate_limit(0, "limit")
        assert result.valid is False
        
        result = validate_limit(1001, "limit")
        assert result.valid is False


class TestFilterValidation:
    """Tests for filter string validation."""

    def test_valid_filter(self):
        """Should accept valid filter."""
        result = validate_filter("name=Tokyo")
        assert result.valid is True
        assert result.value == ("name", "Tokyo")

    def test_filter_with_equals_in_value(self):
        """Should handle equals sign in value."""
        result = validate_filter("query=a=b")
        assert result.valid is True
        assert result.value == ("query", "a=b")

    def test_empty_filter(self):
        """Should accept empty filter."""
        result = validate_filter("")
        assert result.valid is True
        assert result.value is None

    def test_filter_without_equals(self):
        """Should reject filter without equals."""
        result = validate_filter("invalid")
        assert result.valid is False

    def test_filter_empty_key(self):
        """Should reject filter with empty key."""
        result = validate_filter("=value")
        assert result.valid is False
