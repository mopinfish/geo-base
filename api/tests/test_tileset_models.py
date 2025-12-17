"""
Tests for Tileset model validation.

This module tests the Pydantic models in lib/models/tileset.py:
- TilesetCreate validation
- TilesetUpdate validation
- TilesetResponse model
- bounds/center validation helpers
"""

import pytest
from pydantic import ValidationError
from lib.models.tileset import (
    TilesetCreate,
    TilesetUpdate,
    TilesetResponse,
    validate_bounds_values,
    validate_center_values,
)


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestBoundsValidation:
    """Tests for bounds validation helper."""
    
    def test_valid_bounds(self, sample_bounds_tokyo):
        """Test valid bounding box."""
        is_valid, error = validate_bounds_values(sample_bounds_tokyo)
        assert is_valid is True
        assert error is None
    
    def test_valid_bounds_world(self, sample_bounds_world):
        """Test world bounds."""
        is_valid, error = validate_bounds_values(sample_bounds_world)
        assert is_valid is True
    
    def test_valid_bounds_antimeridian(self, sample_bounds_antimeridian):
        """Test bounds crossing antimeridian (west > east)."""
        is_valid, error = validate_bounds_values(sample_bounds_antimeridian)
        assert is_valid is True  # Antimeridian crossing is allowed
    
    def test_invalid_bounds_wrong_count(self):
        """Test bounds with wrong number of values."""
        is_valid, error = validate_bounds_values([139.5, 35.5, 140.0])
        assert is_valid is False
        assert "4 values" in error
    
    def test_invalid_bounds_west_out_of_range(self):
        """Test bounds with west out of range."""
        is_valid, error = validate_bounds_values([-200, 35.5, 140.0, 36.0])
        assert is_valid is False
        assert "west" in error
    
    def test_invalid_bounds_south_out_of_range(self):
        """Test bounds with south out of range."""
        is_valid, error = validate_bounds_values([139.5, -100, 140.0, 36.0])
        assert is_valid is False
        assert "south" in error
    
    def test_invalid_bounds_south_greater_than_north(self, invalid_bounds_south_greater):
        """Test bounds where south > north."""
        is_valid, error = validate_bounds_values(invalid_bounds_south_greater)
        assert is_valid is False
        assert "south" in error and "north" in error


class TestCenterValidation:
    """Tests for center validation helper."""
    
    def test_valid_center_without_zoom(self, sample_center_tokyo):
        """Test valid center without zoom."""
        is_valid, error = validate_center_values(sample_center_tokyo)
        assert is_valid is True
        assert error is None
    
    def test_valid_center_with_zoom(self, sample_center_with_zoom):
        """Test valid center with zoom."""
        is_valid, error = validate_center_values(sample_center_with_zoom)
        assert is_valid is True
    
    def test_invalid_center_too_few_values(self):
        """Test center with too few values."""
        is_valid, error = validate_center_values([139.7])
        assert is_valid is False
        assert "at least 2" in error
    
    def test_invalid_center_too_many_values(self):
        """Test center with too many values."""
        is_valid, error = validate_center_values([139.7, 35.7, 10, 5])
        assert is_valid is False
        assert "at most 3" in error
    
    def test_invalid_center_longitude_out_of_range(self, invalid_center_out_of_range):
        """Test center with longitude out of range."""
        is_valid, error = validate_center_values(invalid_center_out_of_range)
        assert is_valid is False
        assert "longitude" in error
    
    def test_invalid_center_latitude_out_of_range(self):
        """Test center with latitude out of range."""
        is_valid, error = validate_center_values([139.7, 100])
        assert is_valid is False
        assert "latitude" in error
    
    def test_invalid_center_zoom_out_of_range(self):
        """Test center with zoom out of range."""
        is_valid, error = validate_center_values([139.7, 35.7, 25])
        assert is_valid is False
        assert "zoom" in error


# ============================================================================
# TilesetCreate Model Tests
# ============================================================================

class TestTilesetCreate:
    """Tests for TilesetCreate model."""
    
    def test_valid_minimal(self):
        """Test minimal valid tileset creation."""
        tileset = TilesetCreate(
            name="Test Tileset",
            type="vector",
            format="pbf"
        )
        assert tileset.name == "Test Tileset"
        assert tileset.type == "vector"
        assert tileset.format == "pbf"
        assert tileset.min_zoom == 0
        assert tileset.max_zoom == 22
        assert tileset.is_public is False
    
    def test_valid_full(self, sample_tileset_create_data):
        """Test full valid tileset creation."""
        tileset = TilesetCreate(**sample_tileset_create_data)
        assert tileset.bounds == sample_tileset_create_data["bounds"]
        assert tileset.center == [139.75, 35.75, 10.0]  # Normalized to floats
        assert tileset.is_public is True
    
    def test_type_case_insensitive(self):
        """Test that type is case-insensitive."""
        tileset = TilesetCreate(name="Test", type="VECTOR", format="pbf")
        assert tileset.type == "vector"
        
        tileset = TilesetCreate(name="Test", type="Raster", format="png")
        assert tileset.type == "raster"
    
    def test_format_case_insensitive(self):
        """Test that format is case-insensitive."""
        tileset = TilesetCreate(name="Test", type="vector", format="PBF")
        assert tileset.format == "pbf"
    
    def test_invalid_type(self):
        """Test invalid tileset type."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetCreate(name="Test", type="invalid", format="pbf")
        assert "Invalid tileset type" in str(exc_info.value)
    
    def test_invalid_format(self):
        """Test invalid tile format."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetCreate(name="Test", type="vector", format="invalid")
        assert "Invalid tile format" in str(exc_info.value)
    
    def test_invalid_bounds(self, invalid_bounds_south_greater):
        """Test invalid bounds."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetCreate(
                name="Test",
                type="vector",
                format="pbf",
                bounds=invalid_bounds_south_greater
            )
        assert "south" in str(exc_info.value)
    
    def test_invalid_center(self, invalid_center_out_of_range):
        """Test invalid center."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetCreate(
                name="Test",
                type="vector",
                format="pbf",
                center=invalid_center_out_of_range
            )
        assert "longitude" in str(exc_info.value)
    
    def test_min_zoom_greater_than_max_zoom(self):
        """Test that min_zoom > max_zoom is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetCreate(
                name="Test",
                type="vector",
                format="pbf",
                min_zoom=15,
                max_zoom=10
            )
        assert "min_zoom" in str(exc_info.value) and "max_zoom" in str(exc_info.value)
    
    def test_bounds_normalized_to_floats(self):
        """Test that bounds are normalized to floats."""
        tileset = TilesetCreate(
            name="Test",
            type="vector",
            format="pbf",
            bounds=[139, 35, 140, 36]  # Integers
        )
        assert tileset.bounds == [139.0, 35.0, 140.0, 36.0]
        assert all(isinstance(x, float) for x in tileset.bounds)
    
    def test_center_normalized_to_floats(self):
        """Test that center is normalized to floats."""
        tileset = TilesetCreate(
            name="Test",
            type="vector",
            format="pbf",
            center=[139, 35]  # Integers
        )
        assert tileset.center == [139.0, 35.0]
        assert all(isinstance(x, float) for x in tileset.center)
    
    def test_name_too_short(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError):
            TilesetCreate(name="", type="vector", format="pbf")
    
    def test_name_too_long(self):
        """Test that name over 255 chars is rejected."""
        with pytest.raises(ValidationError):
            TilesetCreate(name="x" * 256, type="vector", format="pbf")


# ============================================================================
# TilesetUpdate Model Tests
# ============================================================================

class TestTilesetUpdate:
    """Tests for TilesetUpdate model."""
    
    def test_empty_update(self):
        """Test that empty update is allowed."""
        update = TilesetUpdate()
        assert update.name is None
        assert update.bounds is None
    
    def test_partial_update(self, sample_tileset_update_data):
        """Test partial update."""
        update = TilesetUpdate(**sample_tileset_update_data)
        assert update.name == "Updated Tileset"
        assert update.bounds is not None
        assert update.is_public is None  # Not in update data
    
    def test_bounds_update(self, sample_bounds_tokyo):
        """Test bounds update with validation."""
        update = TilesetUpdate(bounds=sample_bounds_tokyo)
        assert update.bounds == sample_bounds_tokyo
    
    def test_center_update(self, sample_center_with_zoom):
        """Test center update with validation."""
        update = TilesetUpdate(center=sample_center_with_zoom)
        assert update.center == [139.75, 35.75, 10.0]  # Normalized
    
    def test_invalid_bounds_update(self, invalid_bounds_south_greater):
        """Test invalid bounds update."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetUpdate(bounds=invalid_bounds_south_greater)
        assert "south" in str(exc_info.value)
    
    def test_invalid_center_update(self):
        """Test invalid center update."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetUpdate(center=[139.7, 100])  # latitude out of range
        assert "latitude" in str(exc_info.value)
    
    def test_zoom_range_validation(self):
        """Test zoom range validation in update."""
        with pytest.raises(ValidationError) as exc_info:
            TilesetUpdate(min_zoom=15, max_zoom=10)
        assert "min_zoom" in str(exc_info.value)
    
    def test_zoom_range_partial_allowed(self):
        """Test that partial zoom update is allowed."""
        update = TilesetUpdate(min_zoom=5)
        assert update.min_zoom == 5
        assert update.max_zoom is None


# ============================================================================
# TilesetResponse Model Tests
# ============================================================================

class TestTilesetResponse:
    """Tests for TilesetResponse model."""
    
    def test_valid_response(self):
        """Test valid tileset response."""
        response = TilesetResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Test Tileset",
            type="vector",
            format="pbf",
            min_zoom=0,
            max_zoom=22,
            is_public=True
        )
        assert response.id == "123e4567-e89b-12d3-a456-426614174000"
        assert response.name == "Test Tileset"
    
    def test_full_response(self, sample_bounds_tokyo, sample_center_with_zoom):
        """Test full tileset response with all fields."""
        response = TilesetResponse(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="Full Tileset",
            description="Description",
            type="raster",
            format="png",
            min_zoom=5,
            max_zoom=18,
            bounds=sample_bounds_tokyo,
            center=sample_center_with_zoom,
            attribution="© Test",
            is_public=True,
            user_id="user-uuid",
            metadata={"key": "value"},
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z"
        )
        assert response.bounds == sample_bounds_tokyo
        assert response.metadata == {"key": "value"}
