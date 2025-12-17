"""
Pydantic models for Tileset operations.

Provides request/response models for tileset CRUD operations with
validation for geographic bounds, center points, and zoom levels.
"""

from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Constants
# ============================================================================

LON_MIN, LON_MAX = -180.0, 180.0
LAT_MIN, LAT_MAX = -90.0, 90.0
ZOOM_MIN, ZOOM_MAX = 0, 22

VALID_TILESET_TYPES = {"vector", "raster", "pmtiles"}
VALID_TILE_FORMATS = {"pbf", "png", "jpg", "jpeg", "webp", "geojson", "mvt"}


# ============================================================================
# Validation Helper Functions
# ============================================================================

def validate_bounds_values(bounds: List[float]) -> Tuple[bool, Optional[str]]:
    """
    Validate bounding box values.
    
    Args:
        bounds: [west, south, east, north]
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(bounds) != 4:
        return False, f"bounds must have exactly 4 values [west, south, east, north], got {len(bounds)}"
    
    west, south, east, north = bounds
    
    # Check types
    try:
        west, south, east, north = float(west), float(south), float(east), float(north)
    except (ValueError, TypeError):
        return False, "bounds values must be numbers"
    
    # Validate longitude range
    if not (LON_MIN <= west <= LON_MAX):
        return False, f"west ({west}) must be between {LON_MIN} and {LON_MAX}"
    if not (LON_MIN <= east <= LON_MAX):
        return False, f"east ({east}) must be between {LON_MIN} and {LON_MAX}"
    
    # Validate latitude range
    if not (LAT_MIN <= south <= LAT_MAX):
        return False, f"south ({south}) must be between {LAT_MIN} and {LAT_MAX}"
    if not (LAT_MIN <= north <= LAT_MAX):
        return False, f"north ({north}) must be between {LAT_MIN} and {LAT_MAX}"
    
    # Validate south < north
    if south > north:
        return False, f"south ({south}) must be less than or equal to north ({north})"
    
    # Note: west > east is allowed for antimeridian crossing
    
    return True, None


def validate_center_values(center: List[float]) -> Tuple[bool, Optional[str]]:
    """
    Validate center point values.
    
    Args:
        center: [longitude, latitude] or [longitude, latitude, zoom]
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(center) < 2:
        return False, f"center must have at least 2 values [longitude, latitude], got {len(center)}"
    
    if len(center) > 3:
        return False, f"center must have at most 3 values [longitude, latitude, zoom], got {len(center)}"
    
    try:
        lon, lat = float(center[0]), float(center[1])
    except (ValueError, TypeError):
        return False, "center longitude and latitude must be numbers"
    
    # Validate longitude
    if not (LON_MIN <= lon <= LON_MAX):
        return False, f"center longitude ({lon}) must be between {LON_MIN} and {LON_MAX}"
    
    # Validate latitude
    if not (LAT_MIN <= lat <= LAT_MAX):
        return False, f"center latitude ({lat}) must be between {LAT_MIN} and {LAT_MAX}"
    
    # Validate optional zoom
    if len(center) == 3:
        try:
            zoom = float(center[2])
        except (ValueError, TypeError):
            return False, "center zoom must be a number"
        
        if not (ZOOM_MIN <= zoom <= ZOOM_MAX):
            return False, f"center zoom ({zoom}) must be between {ZOOM_MIN} and {ZOOM_MAX}"
    
    return True, None


# ============================================================================
# Tileset Create Model
# ============================================================================

class TilesetCreate(BaseModel):
    """
    Request model for creating a tileset.
    
    Attributes:
        name: Human-readable tileset name (1-255 characters)
        description: Optional description of the tileset
        type: Tileset type - vector, raster, or pmtiles
        format: Tile format - pbf, png, jpg, webp, or geojson
        min_zoom: Minimum zoom level (0-22, default: 0)
        max_zoom: Maximum zoom level (0-22, default: 22)
        bounds: Optional bounding box [west, south, east, north]
        center: Optional center point [longitude, latitude] or [longitude, latitude, zoom]
        attribution: Optional attribution text
        is_public: Whether the tileset is publicly accessible (default: False)
        metadata: Optional additional metadata as JSON object
    """
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Tileset name"
    )
    description: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Tileset description"
    )
    type: str = Field(
        ..., 
        description="Tileset type (vector, raster, pmtiles)"
    )
    format: str = Field(
        ..., 
        description="Tile format (pbf, png, jpg, webp, geojson)"
    )
    min_zoom: int = Field(
        0, 
        ge=ZOOM_MIN, 
        le=ZOOM_MAX, 
        description="Minimum zoom level"
    )
    max_zoom: int = Field(
        22, 
        ge=ZOOM_MIN, 
        le=ZOOM_MAX, 
        description="Maximum zoom level"
    )
    bounds: Optional[List[float]] = Field(
        None, 
        description="Bounding box [west, south, east, north]"
    )
    center: Optional[List[float]] = Field(
        None, 
        description="Center point [longitude, latitude] or [longitude, latitude, zoom]"
    )
    attribution: Optional[str] = Field(
        None, 
        max_length=500,
        description="Attribution text"
    )
    is_public: bool = Field(
        False, 
        description="Whether the tileset is public"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional metadata"
    )
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate tileset type."""
        v_lower = v.lower()
        if v_lower not in VALID_TILESET_TYPES:
            raise ValueError(
                f"Invalid tileset type '{v}'. Must be one of: {', '.join(sorted(VALID_TILESET_TYPES))}"
            )
        return v_lower
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate tile format."""
        v_lower = v.lower()
        if v_lower not in VALID_TILE_FORMATS:
            raise ValueError(
                f"Invalid tile format '{v}'. Must be one of: {', '.join(sorted(VALID_TILE_FORMATS))}"
            )
        return v_lower
    
    @field_validator('bounds')
    @classmethod
    def validate_bounds(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate bounding box."""
        if v is None:
            return None
        
        is_valid, error = validate_bounds_values(v)
        if not is_valid:
            raise ValueError(error)
        
        # Normalize to floats
        return [float(x) for x in v]
    
    @field_validator('center')
    @classmethod
    def validate_center(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate center point."""
        if v is None:
            return None
        
        is_valid, error = validate_center_values(v)
        if not is_valid:
            raise ValueError(error)
        
        # Normalize to floats
        return [float(x) for x in v]
    
    @model_validator(mode='after')
    def validate_zoom_range(self) -> 'TilesetCreate':
        """Validate that min_zoom <= max_zoom."""
        if self.min_zoom > self.max_zoom:
            raise ValueError(
                f"min_zoom ({self.min_zoom}) must be less than or equal to max_zoom ({self.max_zoom})"
            )
        return self
    
    @model_validator(mode='after')
    def validate_center_in_bounds(self) -> 'TilesetCreate':
        """Warn if center is outside bounds (not an error, just validation)."""
        if self.bounds is not None and self.center is not None:
            west, south, east, north = self.bounds
            lon, lat = self.center[0], self.center[1]
            
            # Check if center is within bounds (accounting for antimeridian)
            lat_in_bounds = south <= lat <= north
            
            if west <= east:
                # Normal case
                lon_in_bounds = west <= lon <= east
            else:
                # Antimeridian crossing
                lon_in_bounds = lon >= west or lon <= east
            
            # We don't raise an error, but this could be logged as a warning
            # The center might be intentionally outside bounds in some cases
        
        return self


# ============================================================================
# Tileset Update Model
# ============================================================================

class TilesetUpdate(BaseModel):
    """
    Request model for updating a tileset.
    
    All fields are optional - only provided fields will be updated.
    
    Attributes:
        name: Human-readable tileset name (1-255 characters)
        description: Description of the tileset
        min_zoom: Minimum zoom level (0-22)
        max_zoom: Maximum zoom level (0-22)
        bounds: Bounding box [west, south, east, north]
        center: Center point [longitude, latitude] or [longitude, latitude, zoom]
        attribution: Attribution text
        is_public: Whether the tileset is publicly accessible
        metadata: Additional metadata as JSON object
    """
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=255, 
        description="Tileset name"
    )
    description: Optional[str] = Field(
        None, 
        max_length=2000,
        description="Tileset description"
    )
    min_zoom: Optional[int] = Field(
        None, 
        ge=ZOOM_MIN, 
        le=ZOOM_MAX, 
        description="Minimum zoom level"
    )
    max_zoom: Optional[int] = Field(
        None, 
        ge=ZOOM_MIN, 
        le=ZOOM_MAX, 
        description="Maximum zoom level"
    )
    bounds: Optional[List[float]] = Field(
        None, 
        description="Bounding box [west, south, east, north]"
    )
    center: Optional[List[float]] = Field(
        None, 
        description="Center point [longitude, latitude] or [longitude, latitude, zoom]"
    )
    attribution: Optional[str] = Field(
        None, 
        max_length=500,
        description="Attribution text"
    )
    is_public: Optional[bool] = Field(
        None, 
        description="Whether the tileset is public"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional metadata"
    )
    
    @field_validator('bounds')
    @classmethod
    def validate_bounds(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate bounding box."""
        if v is None:
            return None
        
        is_valid, error = validate_bounds_values(v)
        if not is_valid:
            raise ValueError(error)
        
        # Normalize to floats
        return [float(x) for x in v]
    
    @field_validator('center')
    @classmethod
    def validate_center(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate center point."""
        if v is None:
            return None
        
        is_valid, error = validate_center_values(v)
        if not is_valid:
            raise ValueError(error)
        
        # Normalize to floats
        return [float(x) for x in v]
    
    @model_validator(mode='after')
    def validate_zoom_range(self) -> 'TilesetUpdate':
        """Validate that min_zoom <= max_zoom if both are provided."""
        if self.min_zoom is not None and self.max_zoom is not None:
            if self.min_zoom > self.max_zoom:
                raise ValueError(
                    f"min_zoom ({self.min_zoom}) must be less than or equal to max_zoom ({self.max_zoom})"
                )
        return self


# ============================================================================
# Tileset Response Model (for future use)
# ============================================================================

class TilesetResponse(BaseModel):
    """Response model for a tileset."""
    id: str
    name: str
    description: Optional[str] = None
    type: str
    format: str
    min_zoom: int
    max_zoom: int
    bounds: Optional[List[float]] = None
    center: Optional[List[float]] = None
    attribution: Optional[str] = None
    is_public: bool
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True
