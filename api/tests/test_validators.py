"""
Tests for geometry validation utilities.

This module tests the validation functions in lib/validators.py:
- Coordinate validation (longitude, latitude)
- Bounds validation
- Center validation
- GeoJSON geometry validation
- Feature and FeatureCollection validation
"""

import pytest
from lib.validators import (
    ValidationResult,
    validate_longitude,
    validate_latitude,
    validate_coordinate_pair,
    validate_bounds,
    validate_center,
    validate_geometry,
    validate_feature,
    validate_feature_collection,
    validate_features_batch,
    is_valid_geometry,
    is_valid_bounds,
    is_valid_center,
    normalize_bounds,
    normalize_center,
)


# ============================================================================
# ValidationResult Tests
# ============================================================================

class TestValidationResult:
    """Tests for ValidationResult dataclass."""
    
    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(valid=True, value="test")
        assert result.valid is True
        assert result.value == "test"
        assert result.error is None
        assert result.errors == []
    
    def test_invalid_result(self):
        """Test creating an invalid result."""
        result = ValidationResult(valid=False, error="test error")
        assert result.valid is False
        assert result.error == "test error"
    
    def test_add_error(self):
        """Test adding errors to a result."""
        result = ValidationResult(valid=True)
        result.add_error("first error")
        assert result.valid is False
        assert result.error == "first error"
        assert "first error" in result.errors
        
        result.add_error("second error")
        assert len(result.errors) == 2
    
    def test_add_warning(self):
        """Test adding warnings to a result."""
        result = ValidationResult(valid=True)
        result.add_warning("warning message")
        assert result.valid is True  # Warnings don't invalidate
        assert "warning message" in result.warnings
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = ValidationResult(valid=True)
        d = result.to_dict()
        assert d == {"valid": True}
        
        result = ValidationResult(valid=False, error="error", errors=["e1", "e2"], warnings=["w1"])
        d = result.to_dict()
        assert d["valid"] is False
        assert d["error"] == "error"
        assert d["errors"] == ["e1", "e2"]
        assert d["warnings"] == ["w1"]


# ============================================================================
# Coordinate Validation Tests
# ============================================================================

class TestCoordinateValidation:
    """Tests for coordinate validation functions."""
    
    def test_valid_longitude(self):
        """Test valid longitude values."""
        assert validate_longitude(0).valid is True
        assert validate_longitude(-180).valid is True
        assert validate_longitude(180).valid is True
        assert validate_longitude(139.7).valid is True
        assert validate_longitude("139.7").valid is True  # String parsing
    
    def test_invalid_longitude(self):
        """Test invalid longitude values."""
        assert validate_longitude(-181).valid is False
        assert validate_longitude(181).valid is False
        assert validate_longitude("invalid").valid is False
        assert validate_longitude(None).valid is False
    
    def test_valid_latitude(self):
        """Test valid latitude values."""
        assert validate_latitude(0).valid is True
        assert validate_latitude(-90).valid is True
        assert validate_latitude(90).valid is True
        assert validate_latitude(35.7).valid is True
    
    def test_invalid_latitude(self):
        """Test invalid latitude values."""
        assert validate_latitude(-91).valid is False
        assert validate_latitude(91).valid is False
        assert validate_latitude("invalid").valid is False
    
    def test_valid_coordinate_pair(self):
        """Test valid coordinate pairs."""
        result = validate_coordinate_pair([139.7, 35.7])
        assert result.valid is True
        assert result.value == (139.7, 35.7)
        
        # With altitude
        result = validate_coordinate_pair([139.7, 35.7, 100])
        assert result.valid is True
    
    def test_invalid_coordinate_pair(self):
        """Test invalid coordinate pairs."""
        assert validate_coordinate_pair([]).valid is False
        assert validate_coordinate_pair([139.7]).valid is False
        assert validate_coordinate_pair("139.7,35.7").valid is False  # String not allowed
        assert validate_coordinate_pair([200, 35.7]).valid is False  # Invalid longitude
        assert validate_coordinate_pair([139.7, 100]).valid is False  # Invalid latitude


# ============================================================================
# Bounds Validation Tests
# ============================================================================

class TestBoundsValidation:
    """Tests for bounding box validation."""
    
    def test_valid_bounds_list(self, sample_bounds_tokyo):
        """Test valid bounds as list."""
        result = validate_bounds(sample_bounds_tokyo)
        assert result.valid is True
        assert result.value == tuple(sample_bounds_tokyo)
    
    def test_valid_bounds_string(self):
        """Test valid bounds as comma-separated string."""
        result = validate_bounds("139.5,35.5,140.0,36.0")
        assert result.valid is True
        assert result.value == (139.5, 35.5, 140.0, 36.0)
    
    def test_valid_bounds_tuple(self):
        """Test valid bounds as tuple."""
        result = validate_bounds((139.5, 35.5, 140.0, 36.0))
        assert result.valid is True
    
    def test_valid_bounds_world(self, sample_bounds_world):
        """Test world bounds."""
        result = validate_bounds(sample_bounds_world)
        assert result.valid is True
    
    def test_none_bounds(self):
        """Test None bounds (allowed)."""
        result = validate_bounds(None)
        assert result.valid is True
        assert result.value is None
    
    def test_invalid_bounds_wrong_count(self):
        """Test bounds with wrong number of values."""
        assert validate_bounds([139.5, 35.5, 140.0]).valid is False
        assert validate_bounds([139.5, 35.5, 140.0, 36.0, 10]).valid is False
    
    def test_invalid_bounds_out_of_range(self):
        """Test bounds with out-of-range values."""
        assert validate_bounds([-200, 35.5, 140.0, 36.0]).valid is False  # west out of range
        assert validate_bounds([139.5, -100, 140.0, 36.0]).valid is False  # south out of range
    
    def test_invalid_bounds_south_greater_than_north(self, invalid_bounds_south_greater):
        """Test bounds where south > north."""
        result = validate_bounds(invalid_bounds_south_greater)
        assert result.valid is False
        assert "south" in result.error and "north" in result.error
    
    def test_bounds_antimeridian_warning(self, sample_bounds_antimeridian):
        """Test bounds crossing antimeridian (warning, not error)."""
        result = validate_bounds(sample_bounds_antimeridian)
        assert result.valid is True
        assert len(result.warnings) > 0
        assert "antimeridian" in result.warnings[0].lower()


# ============================================================================
# Center Validation Tests
# ============================================================================

class TestCenterValidation:
    """Tests for center point validation."""
    
    def test_valid_center_without_zoom(self, sample_center_tokyo):
        """Test valid center without zoom."""
        result = validate_center(sample_center_tokyo)
        assert result.valid is True
        assert result.value == tuple(sample_center_tokyo)
    
    def test_valid_center_with_zoom(self, sample_center_with_zoom):
        """Test valid center with zoom."""
        result = validate_center(sample_center_with_zoom)
        assert result.valid is True
        assert result.value == tuple(sample_center_with_zoom)
    
    def test_none_center(self):
        """Test None center (allowed)."""
        result = validate_center(None)
        assert result.valid is True
        assert result.value is None
    
    def test_invalid_center_zoom(self):
        """Test center with invalid zoom."""
        assert validate_center([139.7, 35.7, -1]).valid is False
        assert validate_center([139.7, 35.7, 25]).valid is False
    
    def test_invalid_center_coordinates(self, invalid_center_out_of_range):
        """Test center with invalid coordinates."""
        assert validate_center(invalid_center_out_of_range).valid is False
        assert validate_center([139.7, 100]).valid is False


# ============================================================================
# Geometry Validation Tests
# ============================================================================

class TestGeometryValidation:
    """Tests for GeoJSON geometry validation."""
    
    def test_valid_point(self, sample_point):
        """Test valid Point geometry."""
        result = validate_geometry(sample_point)
        assert result.valid is True
    
    def test_valid_linestring(self, sample_linestring):
        """Test valid LineString geometry."""
        result = validate_geometry(sample_linestring)
        assert result.valid is True
    
    def test_valid_polygon(self, sample_polygon):
        """Test valid Polygon geometry."""
        result = validate_geometry(sample_polygon)
        assert result.valid is True
    
    def test_valid_polygon_with_hole(self, sample_polygon_with_hole):
        """Test valid Polygon with hole."""
        result = validate_geometry(sample_polygon_with_hole)
        assert result.valid is True
    
    def test_valid_multipoint(self, sample_multipoint):
        """Test valid MultiPoint geometry."""
        result = validate_geometry(sample_multipoint)
        assert result.valid is True
    
    def test_valid_multilinestring(self, sample_multilinestring):
        """Test valid MultiLineString geometry."""
        result = validate_geometry(sample_multilinestring)
        assert result.valid is True
    
    def test_valid_multipolygon(self, sample_multipolygon):
        """Test valid MultiPolygon geometry."""
        result = validate_geometry(sample_multipolygon)
        assert result.valid is True
    
    def test_valid_geometry_collection(self, sample_geometry_collection):
        """Test valid GeometryCollection."""
        result = validate_geometry(sample_geometry_collection)
        assert result.valid is True
    
    def test_empty_geometry_collection(self):
        """Test empty GeometryCollection (valid with warning)."""
        geom = {"type": "GeometryCollection", "geometries": []}
        result = validate_geometry(geom)
        assert result.valid is True
        assert len(result.warnings) > 0
    
    def test_none_geometry(self):
        """Test None geometry."""
        result = validate_geometry(None)
        assert result.valid is False
        assert "required" in result.error
    
    def test_missing_type(self, invalid_geometry_no_type):
        """Test geometry without type."""
        result = validate_geometry(invalid_geometry_no_type)
        assert result.valid is False
        assert "type" in result.error
    
    def test_invalid_type(self, invalid_geometry_bad_type):
        """Test geometry with invalid type."""
        result = validate_geometry(invalid_geometry_bad_type)
        assert result.valid is False
        assert "Invalid geometry type" in result.error
    
    def test_missing_coordinates(self, invalid_geometry_no_coords):
        """Test geometry without coordinates."""
        result = validate_geometry(invalid_geometry_no_coords)
        assert result.valid is False
        assert "coordinates" in result.error
    
    def test_point_too_few_coords(self):
        """Test Point with too few coordinates."""
        result = validate_geometry({"type": "Point", "coordinates": [139.7]})
        assert result.valid is False
    
    def test_linestring_too_few_positions(self):
        """Test LineString with too few positions."""
        result = validate_geometry({
            "type": "LineString",
            "coordinates": [[139.7, 35.7]]  # Need at least 2
        })
        assert result.valid is False
    
    def test_polygon_not_closed_warning(self, invalid_polygon_not_closed):
        """Test Polygon that isn't closed (warning)."""
        result = validate_geometry(invalid_polygon_not_closed)
        # Should be valid but with a warning
        assert len(result.warnings) > 0
        assert "not closed" in result.warnings[0].lower()
    
    def test_polygon_too_few_positions(self):
        """Test Polygon ring with too few positions."""
        geom = {
            "type": "Polygon",
            "coordinates": [[[139.7, 35.7], [139.8, 35.7], [139.7, 35.7]]]  # Only 3 positions
        }
        result = validate_geometry(geom)
        assert result.valid is False
        assert "at least 4" in result.error
    
    def test_coordinate_out_of_range(self, invalid_point_out_of_range):
        """Test geometry with coordinates out of range."""
        result = validate_geometry(invalid_point_out_of_range, check_coordinates=True)
        assert result.valid is False
        assert "-180" in result.error or "180" in result.error
    
    def test_skip_coordinate_validation(self, invalid_point_out_of_range):
        """Test skipping coordinate value validation."""
        result = validate_geometry(invalid_point_out_of_range, check_coordinates=False)
        assert result.valid is True


# ============================================================================
# Feature Validation Tests
# ============================================================================

class TestFeatureValidation:
    """Tests for GeoJSON Feature validation."""
    
    def test_valid_feature(self, sample_feature):
        """Test valid Feature."""
        result = validate_feature(sample_feature)
        assert result.valid is True
    
    def test_valid_feature_null_geometry(self):
        """Test Feature with null geometry (allowed in GeoJSON)."""
        feature = {
            "type": "Feature",
            "geometry": None,
            "properties": {"name": "Unknown Location"}
        }
        result = validate_feature(feature)
        assert result.valid is True
    
    def test_valid_feature_null_properties(self, sample_point):
        """Test Feature with null properties."""
        feature = {
            "type": "Feature",
            "geometry": sample_point,
            "properties": None
        }
        result = validate_feature(feature)
        assert result.valid is True
    
    def test_invalid_feature_wrong_type(self, sample_point):
        """Test Feature with wrong type."""
        feature = {
            "type": "FeatureCollection",  # Wrong type
            "geometry": sample_point,
            "properties": {}
        }
        result = validate_feature(feature)
        assert result.valid is False
        assert "Feature" in result.error
    
    def test_invalid_feature_geometry(self, invalid_geometry_bad_type):
        """Test Feature with invalid geometry."""
        feature = {
            "type": "Feature",
            "geometry": invalid_geometry_bad_type,
            "properties": {}
        }
        result = validate_feature(feature)
        assert result.valid is False
    
    def test_invalid_feature_properties_not_object(self, sample_point):
        """Test Feature with non-object properties."""
        feature = {
            "type": "Feature",
            "geometry": sample_point,
            "properties": "not an object"
        }
        result = validate_feature(feature)
        assert result.valid is False


# ============================================================================
# FeatureCollection Validation Tests
# ============================================================================

class TestFeatureCollectionValidation:
    """Tests for GeoJSON FeatureCollection validation."""
    
    def test_valid_feature_collection(self, sample_feature_collection):
        """Test valid FeatureCollection."""
        result = validate_feature_collection(sample_feature_collection)
        assert result.valid is True
    
    def test_empty_feature_collection(self):
        """Test empty FeatureCollection."""
        fc = {"type": "FeatureCollection", "features": []}
        result = validate_feature_collection(fc)
        assert result.valid is True
    
    def test_invalid_feature_collection_wrong_type(self):
        """Test FeatureCollection with wrong type."""
        fc = {"type": "Feature", "features": []}
        result = validate_feature_collection(fc)
        assert result.valid is False
    
    def test_invalid_feature_collection_no_features(self):
        """Test FeatureCollection without features array."""
        fc = {"type": "FeatureCollection"}
        result = validate_feature_collection(fc)
        assert result.valid is False
    
    def test_feature_collection_exceeds_max(self):
        """Test FeatureCollection exceeding max features."""
        fc = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": None, "properties": {}} for _ in range(101)]
        }
        result = validate_feature_collection(fc, max_features=100)
        assert result.valid is False
        assert "100" in result.error
    
    def test_feature_collection_with_invalid_feature(self, sample_point, invalid_geometry_bad_type):
        """Test FeatureCollection containing invalid features."""
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": sample_point,
                    "properties": {}
                },
                {
                    "type": "Feature",
                    "geometry": invalid_geometry_bad_type,
                    "properties": {}
                }
            ]
        }
        result = validate_feature_collection(fc)
        assert result.valid is False


# ============================================================================
# Batch Validation Tests
# ============================================================================

class TestBatchValidation:
    """Tests for batch feature validation."""
    
    def test_validate_features_batch_all_valid(self, sample_bulk_features):
        """Test batch validation with all valid features."""
        valid, invalid = validate_features_batch(sample_bulk_features)
        assert len(valid) == 3
        assert len(invalid) == 0
    
    def test_validate_features_batch_some_invalid(self, sample_point, invalid_geometry_bad_type):
        """Test batch validation with some invalid features."""
        features = [
            {
                "type": "Feature",
                "geometry": sample_point,
                "properties": {}
            },
            {
                "type": "Feature",
                "geometry": invalid_geometry_bad_type,
                "properties": {}
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [140.0, 36.0]},
                "properties": {}
            }
        ]
        valid, invalid = validate_features_batch(features)
        assert len(valid) == 2
        assert len(invalid) == 1
        assert invalid[0]["index"] == 1


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_is_valid_geometry(self, sample_point, invalid_geometry_bad_type):
        """Test is_valid_geometry function."""
        assert is_valid_geometry(sample_point) is True
        assert is_valid_geometry(invalid_geometry_bad_type) is False
    
    def test_is_valid_bounds(self, sample_bounds_tokyo, invalid_bounds_south_greater):
        """Test is_valid_bounds function."""
        assert is_valid_bounds(sample_bounds_tokyo) is True
        assert is_valid_bounds(invalid_bounds_south_greater) is False
    
    def test_is_valid_center(self, sample_center_tokyo, invalid_center_out_of_range):
        """Test is_valid_center function."""
        assert is_valid_center(sample_center_tokyo) is True
        assert is_valid_center(invalid_center_out_of_range) is False
    
    def test_normalize_bounds(self, sample_bounds_tokyo):
        """Test normalize_bounds function."""
        assert normalize_bounds(sample_bounds_tokyo) == sample_bounds_tokyo
        assert normalize_bounds("139.5,35.5,140.0,36.0") == [139.5, 35.5, 140.0, 36.0]
        assert normalize_bounds(None) is None
        assert normalize_bounds("invalid") is None
    
    def test_normalize_center(self, sample_center_tokyo, sample_center_with_zoom):
        """Test normalize_center function."""
        assert normalize_center(sample_center_tokyo) == sample_center_tokyo
        assert normalize_center(sample_center_with_zoom) == [139.75, 35.75, 10.0]
        assert normalize_center(None) is None
        assert normalize_center([200, 35.7]) is None
