"""
Geometry and data validation utilities for geo-base API.

Provides validation functions for:
- GeoJSON geometry validation (structure and coordinate ranges)
- Bounding box validation
- Center point validation
- Database-level validation using PostGIS (ST_IsValid, etc.)
- GeoJSON Feature and FeatureCollection validation

All validators return a ValidationResult with success status and error details.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional, List, Tuple, Dict


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    valid: bool
    error: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    value: Any = None  # Parsed/normalized value
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.valid = False
        if not self.error:
            self.error = error
    
    def add_warning(self, warning: str) -> None:
        """Add a warning (doesn't invalidate result)."""
        self.warnings.append(warning)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = {"valid": self.valid}
        if self.error:
            result["error"] = self.error
        if self.errors:
            result["errors"] = self.errors
        if self.warnings:
            result["warnings"] = self.warnings
        return result


# ============================================================
# Constants
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

# WGS84 coordinate bounds
LON_MIN, LON_MAX = -180.0, 180.0
LAT_MIN, LAT_MAX = -90.0, 90.0


# ============================================================
# Coordinate Validation
# ============================================================

def validate_longitude(value: Any, field_name: str = "longitude") -> ValidationResult:
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
            error=f"{field_name} must be a number, got {type(value).__name__}",
        )
    
    if not LON_MIN <= lng <= LON_MAX:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be between {LON_MIN} and {LON_MAX} (got {lng})",
        )
    
    return ValidationResult(valid=True, value=lng)


def validate_latitude(value: Any, field_name: str = "latitude") -> ValidationResult:
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
            error=f"{field_name} must be a number, got {type(value).__name__}",
        )
    
    if not LAT_MIN <= lat <= LAT_MAX:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be between {LAT_MIN} and {LAT_MAX} (got {lat})",
        )
    
    return ValidationResult(valid=True, value=lat)


def validate_coordinate_pair(
    coords: Any,
    field_name: str = "coordinate"
) -> ValidationResult:
    """
    Validate a coordinate pair [longitude, latitude].
    
    Args:
        coords: Coordinate pair to validate [lng, lat] or [lng, lat, alt]
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with tuple (lng, lat) if valid
    """
    if not isinstance(coords, (list, tuple)):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be an array, got {type(coords).__name__}",
        )
    
    if len(coords) < 2:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must have at least 2 values [longitude, latitude], got {len(coords)}",
        )
    
    # Validate longitude
    lng_result = validate_longitude(coords[0], f"{field_name}[0] (longitude)")
    if not lng_result.valid:
        return lng_result
    
    # Validate latitude
    lat_result = validate_latitude(coords[1], f"{field_name}[1] (latitude)")
    if not lat_result.valid:
        return lat_result
    
    return ValidationResult(valid=True, value=(lng_result.value, lat_result.value))


# ============================================================
# Bounding Box Validation
# ============================================================

def validate_bounds(
    bounds: Any,
    field_name: str = "bounds"
) -> ValidationResult:
    """
    Validate a bounding box [west, south, east, north].
    
    Args:
        bounds: Bounding box as list/tuple or comma-separated string
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with tuple (west, south, east, north) if valid
    """
    if bounds is None:
        return ValidationResult(valid=True, value=None)
    
    # Parse string format
    if isinstance(bounds, str):
        try:
            parts = [float(x.strip()) for x in bounds.split(",")]
        except ValueError:
            return ValidationResult(
                valid=False,
                error=f"Invalid {field_name} format. Use 'west,south,east,north' (e.g., '139.5,35.5,140.0,36.0')",
            )
    elif isinstance(bounds, (list, tuple)):
        try:
            parts = [float(x) for x in bounds]
        except (ValueError, TypeError):
            return ValidationResult(
                valid=False,
                error=f"Invalid {field_name} format. All values must be numbers",
            )
    else:
        return ValidationResult(
            valid=False,
            error=f"Invalid {field_name} type. Expected array or string, got {type(bounds).__name__}",
        )
    
    if len(parts) != 4:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must have exactly 4 values [west, south, east, north], got {len(parts)}",
        )
    
    west, south, east, north = parts
    
    result = ValidationResult(valid=True)
    
    # Validate longitude range
    if not (LON_MIN <= west <= LON_MAX):
        result.add_error(f"west ({west}) must be between {LON_MIN} and {LON_MAX}")
    if not (LON_MIN <= east <= LON_MAX):
        result.add_error(f"east ({east}) must be between {LON_MIN} and {LON_MAX}")
    
    # Validate latitude range
    if not (LAT_MIN <= south <= LAT_MAX):
        result.add_error(f"south ({south}) must be between {LAT_MIN} and {LAT_MAX}")
    if not (LAT_MIN <= north <= LAT_MAX):
        result.add_error(f"north ({north}) must be between {LAT_MIN} and {LAT_MAX}")
    
    # Validate west < east (but allow antimeridian crossing warning)
    if west > east:
        result.add_warning(f"west ({west}) > east ({east}), assuming antimeridian crossing")
    
    # Validate south < north
    if south > north:
        result.add_error(f"south ({south}) must be less than north ({north})")
    
    if result.valid:
        result.value = (west, south, east, north)
    
    return result


def validate_center(
    center: Any,
    field_name: str = "center"
) -> ValidationResult:
    """
    Validate a center point [longitude, latitude] or [longitude, latitude, zoom].
    
    Args:
        center: Center point to validate
        field_name: Name of the field for error messages
        
    Returns:
        ValidationResult with tuple (lng, lat, zoom) or (lng, lat) if valid
    """
    if center is None:
        return ValidationResult(valid=True, value=None)
    
    if not isinstance(center, (list, tuple)):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be an array [longitude, latitude] or [longitude, latitude, zoom]",
        )
    
    if len(center) < 2:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must have at least 2 values [longitude, latitude], got {len(center)}",
        )
    
    # Validate coordinates
    coord_result = validate_coordinate_pair(center[:2], field_name)
    if not coord_result.valid:
        return coord_result
    
    lng, lat = coord_result.value
    
    # Optional zoom level
    if len(center) >= 3:
        try:
            zoom = float(center[2])
            if not (0 <= zoom <= 22):
                return ValidationResult(
                    valid=False,
                    error=f"{field_name}[2] (zoom) must be between 0 and 22, got {zoom}",
                )
            return ValidationResult(valid=True, value=(lng, lat, zoom))
        except (ValueError, TypeError):
            return ValidationResult(
                valid=False,
                error=f"{field_name}[2] (zoom) must be a number",
            )
    
    return ValidationResult(valid=True, value=(lng, lat))


# ============================================================
# GeoJSON Geometry Validation
# ============================================================

def validate_geometry(
    geometry: Any,
    field_name: str = "geometry",
    check_coordinates: bool = True
) -> ValidationResult:
    """
    Validate a GeoJSON geometry object.
    
    Performs structural validation:
    - Has 'type' field with valid geometry type
    - Has 'coordinates' field (except GeometryCollection)
    - Coordinates are properly nested arrays
    - Optionally validates coordinate values are in valid range
    
    Args:
        geometry: GeoJSON geometry object
        field_name: Name of the field for error messages
        check_coordinates: Whether to validate coordinate values
        
    Returns:
        ValidationResult with the geometry dict if valid
    """
    if geometry is None:
        return ValidationResult(
            valid=False,
            error=f"{field_name} is required",
        )
    
    if not isinstance(geometry, dict):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a GeoJSON geometry object, got {type(geometry).__name__}",
        )
    
    # Check type
    geom_type = geometry.get("type")
    if not geom_type:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must have a 'type' field",
        )
    
    if geom_type not in VALID_GEOMETRY_TYPES:
        return ValidationResult(
            valid=False,
            error=f"Invalid geometry type '{geom_type}'. Must be one of: {', '.join(sorted(VALID_GEOMETRY_TYPES))}",
        )
    
    # GeometryCollection has 'geometries' instead of 'coordinates'
    if geom_type == "GeometryCollection":
        return _validate_geometry_collection(geometry, field_name, check_coordinates)
    
    # Check coordinates
    coords = geometry.get("coordinates")
    if coords is None:
        return ValidationResult(
            valid=False,
            error=f"{field_name} must have a 'coordinates' field",
        )
    
    # Validate coordinate structure and optionally values
    return _validate_coordinates(coords, geom_type, field_name, check_coordinates)


def _validate_geometry_collection(
    geometry: dict,
    field_name: str,
    check_coordinates: bool
) -> ValidationResult:
    """Validate a GeometryCollection."""
    geometries = geometry.get("geometries")
    if not isinstance(geometries, list):
        return ValidationResult(
            valid=False,
            error=f"{field_name} GeometryCollection must have a 'geometries' array",
        )
    
    if len(geometries) == 0:
        return ValidationResult(
            valid=True,
            value=geometry,
            warnings=["GeometryCollection is empty"],
        )
    
    result = ValidationResult(valid=True, value=geometry)
    
    for i, geom in enumerate(geometries):
        geom_result = validate_geometry(geom, f"{field_name}.geometries[{i}]", check_coordinates)
        if not geom_result.valid:
            result.add_error(geom_result.error)
        result.warnings.extend(geom_result.warnings)
    
    return result


def _validate_coordinates(
    coords: Any,
    geom_type: str,
    field_name: str,
    check_values: bool
) -> ValidationResult:
    """Validate coordinate structure based on geometry type."""
    
    result = ValidationResult(valid=True)
    
    if geom_type == "Point":
        result = _validate_point_coords(coords, field_name, check_values)
    
    elif geom_type == "LineString":
        result = _validate_linestring_coords(coords, field_name, check_values)
    
    elif geom_type == "Polygon":
        result = _validate_polygon_coords(coords, field_name, check_values)
    
    elif geom_type == "MultiPoint":
        result = _validate_multipoint_coords(coords, field_name, check_values)
    
    elif geom_type == "MultiLineString":
        result = _validate_multilinestring_coords(coords, field_name, check_values)
    
    elif geom_type == "MultiPolygon":
        result = _validate_multipolygon_coords(coords, field_name, check_values)
    
    if result.valid:
        result.value = {"type": geom_type, "coordinates": coords}
    
    return result


def _validate_point_coords(
    coords: Any,
    field_name: str,
    check_values: bool
) -> ValidationResult:
    """Validate Point coordinates [lng, lat] or [lng, lat, alt]."""
    if not isinstance(coords, (list, tuple)):
        return ValidationResult(
            valid=False,
            error=f"{field_name} Point coordinates must be an array",
        )
    
    if len(coords) < 2:
        return ValidationResult(
            valid=False,
            error=f"{field_name} Point must have at least 2 coordinates [longitude, latitude]",
        )
    
    if not all(isinstance(c, (int, float)) for c in coords[:2]):
        return ValidationResult(
            valid=False,
            error=f"{field_name} Point coordinates must be numbers",
        )
    
    if check_values:
        return validate_coordinate_pair(coords, f"{field_name} Point")
    
    return ValidationResult(valid=True)


def _validate_linestring_coords(
    coords: Any,
    field_name: str,
    check_values: bool
) -> ValidationResult:
    """Validate LineString coordinates [[lng, lat], ...]."""
    if not isinstance(coords, list):
        return ValidationResult(
            valid=False,
            error=f"{field_name} LineString coordinates must be an array of positions",
        )
    
    if len(coords) < 2:
        return ValidationResult(
            valid=False,
            error=f"{field_name} LineString must have at least 2 positions, got {len(coords)}",
        )
    
    result = ValidationResult(valid=True)
    
    for i, pos in enumerate(coords):
        if check_values:
            pos_result = validate_coordinate_pair(pos, f"{field_name} LineString[{i}]")
            if not pos_result.valid:
                result.add_error(pos_result.error)
        elif not isinstance(pos, (list, tuple)) or len(pos) < 2:
            result.add_error(f"{field_name} LineString[{i}] must be a coordinate pair")
    
    return result


def _validate_polygon_coords(
    coords: Any,
    field_name: str,
    check_values: bool
) -> ValidationResult:
    """Validate Polygon coordinates [[[lng, lat], ...], ...]."""
    if not isinstance(coords, list):
        return ValidationResult(
            valid=False,
            error=f"{field_name} Polygon coordinates must be an array of linear rings",
        )
    
    if len(coords) < 1:
        return ValidationResult(
            valid=False,
            error=f"{field_name} Polygon must have at least one linear ring",
        )
    
    result = ValidationResult(valid=True)
    
    for i, ring in enumerate(coords):
        ring_name = "exterior ring" if i == 0 else f"hole {i}"
        
        if not isinstance(ring, list):
            result.add_error(f"{field_name} Polygon {ring_name} must be an array of positions")
            continue
        
        if len(ring) < 4:
            result.add_error(
                f"{field_name} Polygon {ring_name} must have at least 4 positions "
                f"(first and last must be the same), got {len(ring)}"
            )
            continue
        
        # Check if ring is closed (first == last)
        if ring[0] != ring[-1]:
            result.add_warning(
                f"{field_name} Polygon {ring_name} is not closed "
                f"(first position {ring[0]} != last position {ring[-1]})"
            )
        
        if check_values:
            for j, pos in enumerate(ring):
                pos_result = validate_coordinate_pair(pos, f"{field_name} Polygon {ring_name}[{j}]")
                if not pos_result.valid:
                    result.add_error(pos_result.error)
    
    return result


def _validate_multipoint_coords(
    coords: Any,
    field_name: str,
    check_values: bool
) -> ValidationResult:
    """Validate MultiPoint coordinates [[lng, lat], ...]."""
    if not isinstance(coords, list):
        return ValidationResult(
            valid=False,
            error=f"{field_name} MultiPoint coordinates must be an array of positions",
        )
    
    result = ValidationResult(valid=True)
    
    for i, pos in enumerate(coords):
        pos_result = _validate_point_coords(pos, f"{field_name} MultiPoint[{i}]", check_values)
        if not pos_result.valid:
            result.add_error(pos_result.error)
    
    return result


def _validate_multilinestring_coords(
    coords: Any,
    field_name: str,
    check_values: bool
) -> ValidationResult:
    """Validate MultiLineString coordinates [[[lng, lat], ...], ...]."""
    if not isinstance(coords, list):
        return ValidationResult(
            valid=False,
            error=f"{field_name} MultiLineString coordinates must be an array of LineString coordinate arrays",
        )
    
    result = ValidationResult(valid=True)
    
    for i, line in enumerate(coords):
        line_result = _validate_linestring_coords(line, f"{field_name} MultiLineString[{i}]", check_values)
        if not line_result.valid:
            for error in line_result.errors or [line_result.error]:
                result.add_error(error)
    
    return result


def _validate_multipolygon_coords(
    coords: Any,
    field_name: str,
    check_values: bool
) -> ValidationResult:
    """Validate MultiPolygon coordinates [[[[lng, lat], ...], ...], ...]."""
    if not isinstance(coords, list):
        return ValidationResult(
            valid=False,
            error=f"{field_name} MultiPolygon coordinates must be an array of Polygon coordinate arrays",
        )
    
    result = ValidationResult(valid=True)
    
    for i, polygon in enumerate(coords):
        poly_result = _validate_polygon_coords(polygon, f"{field_name} MultiPolygon[{i}]", check_values)
        if not poly_result.valid:
            for error in poly_result.errors or [poly_result.error]:
                result.add_error(error)
        result.warnings.extend(poly_result.warnings)
    
    return result


# ============================================================
# GeoJSON Feature Validation
# ============================================================

def validate_feature(
    feature: Any,
    field_name: str = "feature",
    check_coordinates: bool = True
) -> ValidationResult:
    """
    Validate a GeoJSON Feature object.
    
    Args:
        feature: GeoJSON Feature object
        field_name: Name of the field for error messages
        check_coordinates: Whether to validate coordinate values
        
    Returns:
        ValidationResult with the feature dict if valid
    """
    if not isinstance(feature, dict):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a GeoJSON Feature object",
        )
    
    # Check type
    feature_type = feature.get("type")
    if feature_type != "Feature":
        return ValidationResult(
            valid=False,
            error=f"{field_name} type must be 'Feature', got '{feature_type}'",
        )
    
    result = ValidationResult(valid=True, value=feature)
    
    # Validate geometry
    geometry = feature.get("geometry")
    if geometry is not None:  # null geometry is allowed in GeoJSON
        geom_result = validate_geometry(geometry, f"{field_name}.geometry", check_coordinates)
        if not geom_result.valid:
            result.add_error(geom_result.error)
            for err in geom_result.errors:
                result.add_error(err)
        result.warnings.extend(geom_result.warnings)
    
    # Properties should be an object or null
    properties = feature.get("properties")
    if properties is not None and not isinstance(properties, dict):
        result.add_error(f"{field_name}.properties must be an object or null")
    
    return result


def validate_feature_collection(
    fc: Any,
    field_name: str = "featureCollection",
    check_coordinates: bool = True,
    max_features: int = 10000
) -> ValidationResult:
    """
    Validate a GeoJSON FeatureCollection object.
    
    Args:
        fc: GeoJSON FeatureCollection object
        field_name: Name of the field for error messages
        check_coordinates: Whether to validate coordinate values
        max_features: Maximum number of features allowed
        
    Returns:
        ValidationResult with the FeatureCollection dict if valid
    """
    if not isinstance(fc, dict):
        return ValidationResult(
            valid=False,
            error=f"{field_name} must be a GeoJSON FeatureCollection object",
        )
    
    # Check type
    fc_type = fc.get("type")
    if fc_type != "FeatureCollection":
        return ValidationResult(
            valid=False,
            error=f"{field_name} type must be 'FeatureCollection', got '{fc_type}'",
        )
    
    # Check features
    features = fc.get("features")
    if not isinstance(features, list):
        return ValidationResult(
            valid=False,
            error=f"{field_name}.features must be an array",
        )
    
    if len(features) > max_features:
        return ValidationResult(
            valid=False,
            error=f"{field_name} exceeds maximum of {max_features} features (got {len(features)})",
        )
    
    result = ValidationResult(valid=True, value=fc)
    
    for i, feature in enumerate(features):
        feat_result = validate_feature(feature, f"{field_name}.features[{i}]", check_coordinates)
        if not feat_result.valid:
            result.add_error(feat_result.error)
            # Only collect first 10 errors to avoid huge error lists
            if len(result.errors) >= 10:
                result.add_error(f"... and more errors (stopped after 10)")
                break
        result.warnings.extend(feat_result.warnings)
    
    return result


# ============================================================
# Database-Level Validation (PostGIS)
# ============================================================

def validate_geometry_with_postgis(
    geometry_json: str,
    conn,
    fix_invalid: bool = False
) -> ValidationResult:
    """
    Validate geometry using PostGIS ST_IsValid.
    
    Also checks for:
    - Empty geometry
    - Self-intersection (for polygons)
    - Ring orientation
    
    Args:
        geometry_json: GeoJSON geometry as string
        conn: Database connection
        fix_invalid: Whether to attempt to fix invalid geometry with ST_MakeValid
        
    Returns:
        ValidationResult with validation details
    """
    result = ValidationResult(valid=True)
    
    try:
        with conn.cursor() as cur:
            # Check if geometry is valid
            cur.execute(
                """
                SELECT 
                    ST_IsValid(ST_GeomFromGeoJSON(%s)) as is_valid,
                    ST_IsValidReason(ST_GeomFromGeoJSON(%s)) as reason,
                    ST_IsEmpty(ST_GeomFromGeoJSON(%s)) as is_empty,
                    ST_GeometryType(ST_GeomFromGeoJSON(%s)) as geom_type
                """,
                (geometry_json, geometry_json, geometry_json, geometry_json),
            )
            row = cur.fetchone()
            
            if row is None:
                result.add_error("Failed to parse geometry")
                return result
            
            is_valid, reason, is_empty, geom_type = row
            
            if is_empty:
                result.add_warning("Geometry is empty")
            
            if not is_valid:
                if fix_invalid:
                    # Try to fix the geometry
                    cur.execute(
                        """
                        SELECT 
                            ST_AsGeoJSON(ST_MakeValid(ST_GeomFromGeoJSON(%s))) as fixed_geom,
                            ST_IsValid(ST_MakeValid(ST_GeomFromGeoJSON(%s))) as fixed_valid
                        """,
                        (geometry_json, geometry_json),
                    )
                    fixed_row = cur.fetchone()
                    
                    if fixed_row and fixed_row[1]:
                        result.add_warning(f"Geometry was invalid ({reason}), fixed with ST_MakeValid")
                        result.value = json.loads(fixed_row[0])
                    else:
                        result.add_error(f"Invalid geometry: {reason} (could not be fixed)")
                else:
                    result.add_error(f"Invalid geometry: {reason}")
            
            if result.valid and not result.value:
                result.value = json.loads(geometry_json)
                
    except Exception as e:
        result.add_error(f"Database validation error: {str(e)}")
    
    return result


def calculate_bounds_from_geometry(
    geometry_json: str,
    conn
) -> Optional[Tuple[float, float, float, float]]:
    """
    Calculate bounding box from a geometry using PostGIS.
    
    Args:
        geometry_json: GeoJSON geometry as string
        conn: Database connection
        
    Returns:
        Tuple (west, south, east, north) or None if calculation fails
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    ST_XMin(ST_Envelope(ST_GeomFromGeoJSON(%s))),
                    ST_YMin(ST_Envelope(ST_GeomFromGeoJSON(%s))),
                    ST_XMax(ST_Envelope(ST_GeomFromGeoJSON(%s))),
                    ST_YMax(ST_Envelope(ST_GeomFromGeoJSON(%s)))
                """,
                (geometry_json, geometry_json, geometry_json, geometry_json),
            )
            row = cur.fetchone()
            
            if row and all(v is not None for v in row):
                return (row[0], row[1], row[2], row[3])
                
    except Exception:
        pass
    
    return None


def calculate_centroid_from_geometry(
    geometry_json: str,
    conn
) -> Optional[Tuple[float, float]]:
    """
    Calculate centroid from a geometry using PostGIS.
    
    Args:
        geometry_json: GeoJSON geometry as string
        conn: Database connection
        
    Returns:
        Tuple (longitude, latitude) or None if calculation fails
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    ST_X(ST_Centroid(ST_GeomFromGeoJSON(%s))),
                    ST_Y(ST_Centroid(ST_GeomFromGeoJSON(%s)))
                """,
                (geometry_json, geometry_json),
            )
            row = cur.fetchone()
            
            if row and all(v is not None for v in row):
                return (row[0], row[1])
                
    except Exception:
        pass
    
    return None


# ============================================================
# Bulk Validation Utilities
# ============================================================

def validate_features_batch(
    features: List[dict],
    check_coordinates: bool = True,
    max_errors: int = 100
) -> Tuple[List[dict], List[dict]]:
    """
    Validate a batch of GeoJSON features.
    
    Args:
        features: List of GeoJSON feature objects
        check_coordinates: Whether to validate coordinate values
        max_errors: Maximum number of errors to collect
        
    Returns:
        Tuple (valid_features, invalid_features_with_errors)
    """
    valid_features = []
    invalid_features = []
    
    for i, feature in enumerate(features):
        result = validate_feature(feature, f"feature[{i}]", check_coordinates)
        
        if result.valid:
            valid_features.append(feature)
        else:
            invalid_features.append({
                "index": i,
                "feature": feature,
                "errors": result.errors or [result.error],
                "warnings": result.warnings,
            })
            
            if len(invalid_features) >= max_errors:
                break
    
    return valid_features, invalid_features


# ============================================================
# Convenience Functions
# ============================================================

def is_valid_geometry(geometry: dict) -> bool:
    """Quick check if a geometry is structurally valid."""
    return validate_geometry(geometry, check_coordinates=False).valid


def is_valid_bounds(bounds: Any) -> bool:
    """Quick check if bounds are valid."""
    return validate_bounds(bounds).valid


def is_valid_center(center: Any) -> bool:
    """Quick check if center is valid."""
    return validate_center(center).valid


def normalize_bounds(bounds: Any) -> Optional[List[float]]:
    """
    Normalize bounds to list format [west, south, east, north].
    
    Returns None if bounds are invalid.
    """
    result = validate_bounds(bounds)
    if result.valid and result.value:
        return list(result.value)
    return None


def normalize_center(center: Any) -> Optional[List[float]]:
    """
    Normalize center to list format [lng, lat] or [lng, lat, zoom].
    
    Returns None if center is invalid.
    """
    result = validate_center(center)
    if result.valid and result.value:
        return list(result.value)
    return None
