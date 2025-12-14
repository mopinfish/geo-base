"""
Input validation utilities for geo-base MCP Server.

Provides validation functions for common input types including:
- UUID validation
- Coordinate validation (latitude, longitude)
- Bounding box validation
- Zoom level validation
- Tileset type and format validation
- GeoJSON geometry validation

All validators return a ValidationResult with success status and error details.
"""

import re
import uuid
from dataclasses import dataclass
from typing import Any

from errors import ErrorCode


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    valid: bool
    error: str | None = None
    code: str | None = None
    value: Any = None  # Parsed/normalized value
    
    def to_error_response(self, **kwargs) -> dict:
        """Convert to error response dictionary."""
        if self.valid:
            return {}
        return {
            "error": self.error,
            "code": self.code or ErrorCode.VALIDATION_ERROR.value,
            **kwargs,
        }


# ============================================================
# UUID Validation
# ============================================================

def validate_uuid(value: str, field_name: str = "id") -> ValidationResult:
    """
    Validate that a string is a valid UUID.
    
    Args:
        value: String to validate
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with parsed UUID if valid
    """
    if not value:
        return ValidationResult(
            valid=False,
            error=f"{field_name} is required",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    try:
        # Try to parse as UUID
        parsed = uuid.UUID(str(value))
        return ValidationResult(valid=True, value=str(parsed))
    except (ValueError, AttributeError):
        return ValidationResult(
            valid=False,
            error=f"Invalid {field_name} format. Expected UUID (e.g., '550e8400-e29b-41d4-a716-446655440000')",
            code=ErrorCode.VALIDATION_ERROR.value,
        )


def is_valid_uuid(value: str) -> bool:
    """Quick check if a string is a valid UUID."""
    return validate_uuid(value).valid


# ============================================================
# Coordinate Validation
# ============================================================

def validate_latitude(value: float | str, field_name: str = "latitude") -> ValidationResult:
    """
    Validate latitude value (-90 to 90).
    
    Args:
        value: Latitude value to validate
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with float value if valid
    """
    try:
        lat = float(value)
    except (ValueError, TypeError):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a number",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if not -90 <= lat <= 90:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be between -90 and 90 (got {lat})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=lat)


def validate_longitude(value: float | str, field_name: str = "longitude") -> ValidationResult:
    """
    Validate longitude value (-180 to 180).
    
    Args:
        value: Longitude value to validate
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with float value if valid
    """
    try:
        lng = float(value)
    except (ValueError, TypeError):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a number",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if not -180 <= lng <= 180:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be between -180 and 180 (got {lng})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=lng)


def validate_coordinates(
    lat: float | str,
    lng: float | str,
) -> ValidationResult:
    """
    Validate a coordinate pair (latitude, longitude).
    
    Args:
        lat: Latitude value
        lng: Longitude value
        
    Returns:
        ValidationResult with tuple (lat, lng) if valid
    """
    lat_result = validate_latitude(lat)
    if not lat_result.valid:
        return lat_result
    
    lng_result = validate_longitude(lng)
    if not lng_result.valid:
        return lng_result
    
    return ValidationResult(valid=True, value=(lat_result.value, lng_result.value))


# ============================================================
# Bounding Box Validation
# ============================================================

def validate_bbox(
    bbox: str | list | tuple,
    field_name: str = "bbox",
) -> ValidationResult:
    """
    Validate a bounding box.
    
    Accepts:
    - String format: "minx,miny,maxx,maxy" (e.g., "139.5,35.5,140.0,36.0")
    - List/tuple format: [minx, miny, maxx, maxy]
    
    Args:
        bbox: Bounding box to validate
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with tuple (min_lng, min_lat, max_lng, max_lat) if valid
    """
    if not bbox:
        return ValidationResult(
            valid=False,
            error=f"{field_name} is required",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    # Parse string format
    if isinstance(bbox, str):
        try:
            parts = [float(x.strip()) for x in bbox.split(",")]
        except ValueError:
            return ValidationResult(
                valid=False,
                error=f"Invalid {field_name} format. Use 'minx,miny,maxx,maxy' (e.g., '139.5,35.5,140.0,36.0')",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    elif isinstance(bbox, (list, tuple)):
        try:
            parts = [float(x) for x in bbox]
        except (ValueError, TypeError):
            return ValidationResult(
                valid=False,
                error=f"Invalid {field_name} format. All values must be numbers",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    else:
        return ValidationResult(
            valid=False,
            error=f"Invalid {field_name} type. Expected string or list",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if len(parts) != 4:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must have exactly 4 values (minx,miny,maxx,maxy), got {len(parts)}",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    min_lng, min_lat, max_lng, max_lat = parts
    
    # Validate longitude range
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
        return ValidationResult(
            valid=False,
            error=f"Longitude values must be between -180 and 180",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    # Validate latitude range
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        return ValidationResult(
            valid=False,
            error=f"Latitude values must be between -90 and 90",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    # Validate min < max
    if min_lng > max_lng:
        return ValidationResult(
            valid=False,
            error=f"min_lng ({min_lng}) must be less than max_lng ({max_lng})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if min_lat > max_lat:
        return ValidationResult(
            valid=False,
            error=f"min_lat ({min_lat}) must be less than max_lat ({max_lat})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=(min_lng, min_lat, max_lng, max_lat))


def parse_bbox(bbox_str: str) -> tuple[float, float, float, float] | None:
    """
    Parse bbox string to tuple. Returns None if invalid.
    
    This is a convenience function for backward compatibility.
    """
    result = validate_bbox(bbox_str)
    return result.value if result.valid else None


# ============================================================
# Zoom Level Validation
# ============================================================

def validate_zoom(
    value: int | str,
    min_zoom: int = 0,
    max_zoom: int = 22,
    field_name: str = "zoom",
) -> ValidationResult:
    """
    Validate a map zoom level.
    
    Args:
        value: Zoom level to validate
        min_zoom: Minimum allowed zoom (default: 0)
        max_zoom: Maximum allowed zoom (default: 22)
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with int value if valid
    """
    try:
        zoom = int(value)
    except (ValueError, TypeError):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be an integer",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if not min_zoom <= zoom <= max_zoom:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be between {min_zoom} and {max_zoom} (got {zoom})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=zoom)


# ============================================================
# Tile Coordinate Validation
# ============================================================

def validate_tile_coordinates(
    z: int,
    x: int,
    y: int,
) -> ValidationResult:
    """
    Validate tile coordinates (z, x, y).
    
    Ensures x and y are within valid range for the given zoom level.
    At zoom z, valid range is 0 to 2^z - 1.
    
    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        
    Returns:
        ValidationResult with tuple (z, x, y) if valid
    """
    # First validate zoom
    zoom_result = validate_zoom(z)
    if not zoom_result.valid:
        return zoom_result
    
    z = zoom_result.value
    max_tile = 2 ** z - 1
    
    try:
        x = int(x)
        y = int(y)
    except (ValueError, TypeError):
        return ValidationResult(
            valid=False,
            error="Tile coordinates (x, y) must be integers",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if not 0 <= x <= max_tile:
        return ValidationResult(
            valid=False,
            error=f"x must be between 0 and {max_tile} at zoom {z} (got {x})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if not 0 <= y <= max_tile:
        return ValidationResult(
            valid=False,
            error=f"y must be between 0 and {max_tile} at zoom {z} (got {y})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=(z, x, y))


# ============================================================
# Tileset Type and Format Validation
# ============================================================

VALID_TILESET_TYPES = {"vector", "raster", "pmtiles"}
VALID_TILE_FORMATS = {"pbf", "png", "jpg", "jpeg", "webp", "geojson", "mvt"}


def validate_tileset_type(value: str) -> ValidationResult:
    """
    Validate tileset type.
    
    Valid types: vector, raster, pmtiles
    """
    if not value:
        return ValidationResult(
            valid=False,
            error="Tileset type is required",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    value_lower = str(value).lower()
    if value_lower not in VALID_TILESET_TYPES:
        return ValidationResult(
            valid=False,
            error=f"Invalid tileset type '{value}'. Must be one of: {', '.join(sorted(VALID_TILESET_TYPES))}",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=value_lower)


def validate_tile_format(value: str) -> ValidationResult:
    """
    Validate tile format.
    
    Valid formats: pbf, png, jpg, jpeg, webp, geojson, mvt
    """
    if not value:
        return ValidationResult(
            valid=False,
            error="Tile format is required",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    value_lower = str(value).lower()
    if value_lower not in VALID_TILE_FORMATS:
        return ValidationResult(
            valid=False,
            error=f"Invalid tile format '{value}'. Must be one of: {', '.join(sorted(VALID_TILE_FORMATS))}",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=value_lower)


# ============================================================
# GeoJSON Geometry Validation
# ============================================================

VALID_GEOMETRY_TYPES = {
    "Point",
    "LineString",
    "Polygon",
    "MultiPoint",
    "MultiLineString",
    "MultiPolygon",
    "GeometryCollection",
}


def validate_geometry(geometry: dict, field_name: str = "geometry") -> ValidationResult:
    """
    Validate a GeoJSON geometry object.
    
    Performs basic structural validation:
    - Has 'type' field with valid geometry type
    - Has 'coordinates' field (except GeometryCollection)
    - Coordinates are properly nested arrays
    
    Args:
        geometry: GeoJSON geometry object
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with the geometry dict if valid
    """
    if not geometry:
        return ValidationResult(
            valid=False,
            error=f"{field_name} is required",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if not isinstance(geometry, dict):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a GeoJSON geometry object",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    # Check type
    geom_type = geometry.get("type")
    if not geom_type:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must have a 'type' field",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if geom_type not in VALID_GEOMETRY_TYPES:
        return ValidationResult(
            valid=False,
            error=f"Invalid geometry type '{geom_type}'. Must be one of: {', '.join(sorted(VALID_GEOMETRY_TYPES))}",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    # GeometryCollection has 'geometries' instead of 'coordinates'
    if geom_type == "GeometryCollection":
        geometries = geometry.get("geometries")
        if not isinstance(geometries, list):
            return ValidationResult(
                valid=False,
                error="GeometryCollection must have a 'geometries' array",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
        # Recursively validate each geometry
        for i, geom in enumerate(geometries):
            result = validate_geometry(geom, f"geometries[{i}]")
            if not result.valid:
                return result
    else:
        # Check coordinates
        coords = geometry.get("coordinates")
        if coords is None:
            return ValidationResult(
                valid=False,
                error=f"{field_name} must have a 'coordinates' field",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
        
        # Validate coordinate structure based on type
        coord_result = _validate_coordinates_structure(coords, geom_type)
        if not coord_result.valid:
            return coord_result
    
    return ValidationResult(valid=True, value=geometry)


def _validate_coordinates_structure(coords: Any, geom_type: str) -> ValidationResult:
    """Validate the structure of coordinates based on geometry type."""
    
    if geom_type == "Point":
        # [lng, lat] or [lng, lat, alt]
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            return ValidationResult(
                valid=False,
                error="Point coordinates must be [longitude, latitude]",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
        if not all(isinstance(c, (int, float)) for c in coords[:2]):
            return ValidationResult(
                valid=False,
                error="Point coordinates must be numbers",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    
    elif geom_type == "LineString":
        # [[lng, lat], [lng, lat], ...]
        if not isinstance(coords, list) or len(coords) < 2:
            return ValidationResult(
                valid=False,
                error="LineString must have at least 2 coordinate positions",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    
    elif geom_type == "Polygon":
        # [[[lng, lat], [lng, lat], ...], ...]  (array of linear rings)
        if not isinstance(coords, list) or len(coords) < 1:
            return ValidationResult(
                valid=False,
                error="Polygon must have at least one linear ring",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
        for i, ring in enumerate(coords):
            if not isinstance(ring, list) or len(ring) < 4:
                return ValidationResult(
                    valid=False,
                    error=f"Polygon ring {i} must have at least 4 positions (first and last must be the same)",
                    code=ErrorCode.VALIDATION_ERROR.value,
                )
    
    elif geom_type == "MultiPoint":
        if not isinstance(coords, list):
            return ValidationResult(
                valid=False,
                error="MultiPoint coordinates must be an array of positions",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    
    elif geom_type == "MultiLineString":
        if not isinstance(coords, list):
            return ValidationResult(
                valid=False,
                error="MultiLineString coordinates must be an array of LineString coordinate arrays",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    
    elif geom_type == "MultiPolygon":
        if not isinstance(coords, list):
            return ValidationResult(
                valid=False,
                error="MultiPolygon coordinates must be an array of Polygon coordinate arrays",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    
    return ValidationResult(valid=True)


# ============================================================
# String Validation
# ============================================================

def validate_non_empty_string(
    value: str,
    field_name: str,
    max_length: int | None = None,
    pattern: str | None = None,
) -> ValidationResult:
    """
    Validate a non-empty string with optional constraints.
    
    Args:
        value: String to validate
        field_name: Name of the field for error messages
        max_length: Maximum allowed length
        pattern: Regex pattern to match
        
    Returns:
        ValidationResult with the string if valid
    """
    if not value or not str(value).strip():
        return ValidationResult(
            valid=False,
            error=f"{field_name} is required and cannot be empty",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    value = str(value).strip()
    
    if max_length and len(value) > max_length:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be at most {max_length} characters (got {len(value)})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if pattern and not re.match(pattern, value):
        return ValidationResult(
            valid=False,
            error=f"{field_name} has invalid format",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=value)


# ============================================================
# Numeric Range Validation
# ============================================================

def validate_positive_number(
    value: float | int | str,
    field_name: str,
    allow_zero: bool = False,
) -> ValidationResult:
    """
    Validate a positive number.
    
    Args:
        value: Number to validate
        field_name: Name of the field for error messages
        allow_zero: Whether to allow zero (default: False)
        
    Returns:
        ValidationResult with float value if valid
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a number",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if allow_zero:
        if num < 0:
            return ValidationResult(
                valid=False,
                error=f"{field_name} must be zero or positive (got {num})",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    else:
        if num <= 0:
            return ValidationResult(
                valid=False,
                error=f"{field_name} must be positive (got {num})",
                code=ErrorCode.VALIDATION_ERROR.value,
            )
    
    return ValidationResult(valid=True, value=num)


def validate_range(
    value: float | int | str,
    field_name: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> ValidationResult:
    """
    Validate a number is within a range.
    
    Args:
        value: Number to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        
    Returns:
        ValidationResult with float value if valid
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a number",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if min_value is not None and num < min_value:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be at least {min_value} (got {num})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if max_value is not None and num > max_value:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be at most {max_value} (got {num})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=num)


def validate_limit(
    value: int | str,
    field_name: str = "limit",
    min_value: int = 1,
    max_value: int = 1000,
) -> ValidationResult:
    """
    Validate a limit/count parameter.
    
    Args:
        value: Limit value to validate
        field_name: Name of the field for error messages
        min_value: Minimum allowed value (default: 1)
        max_value: Maximum allowed value (default: 1000)
        
    Returns:
        ValidationResult with int value if valid
    """
    try:
        limit = int(value)
    except (ValueError, TypeError):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be an integer",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    if not min_value <= limit <= max_value:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be between {min_value} and {max_value} (got {limit})",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=limit)


# ============================================================
# Filter String Validation
# ============================================================

def validate_filter(filter_str: str) -> ValidationResult:
    """
    Validate a property filter string.
    
    Expected format: "key=value"
    
    Args:
        filter_str: Filter string to validate
        
    Returns:
        ValidationResult with tuple (key, value) if valid
    """
    if not filter_str:
        return ValidationResult(valid=True, value=None)
    
    if "=" not in filter_str:
        return ValidationResult(
            valid=False,
            error="Filter must be in format 'key=value'",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    parts = filter_str.split("=", 1)
    if len(parts) != 2:
        return ValidationResult(
            valid=False,
            error="Filter must be in format 'key=value'",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    key, value = parts
    if not key.strip():
        return ValidationResult(
            valid=False,
            error="Filter key cannot be empty",
            code=ErrorCode.VALIDATION_ERROR.value,
        )
    
    return ValidationResult(valid=True, value=(key.strip(), value.strip()))
