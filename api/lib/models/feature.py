"""
Pydantic models for Feature operations.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FeatureCreate(BaseModel):
    """Request model for creating a feature."""
    tileset_id: str = Field(..., description="Parent tileset UUID")
    layer_name: str = Field("default", description="Layer name")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry object")
    properties: Optional[Dict[str, Any]] = Field(None, description="Feature properties")


class FeatureUpdate(BaseModel):
    """Request model for updating a feature."""
    layer_name: Optional[str] = Field(None, description="Layer name")
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry object")
    properties: Optional[Dict[str, Any]] = Field(None, description="Feature properties")


class BulkFeatureCreate(BaseModel):
    """Request model for bulk creating features."""
    tileset_id: str = Field(..., description="Parent tileset UUID")
    layer_name: str = Field("default", description="Layer name for all features")
    features: List[Dict[str, Any]] = Field(
        ..., 
        description="List of GeoJSON features to import",
        min_length=1,
        max_length=10000  # Maximum 10000 features at once
    )
    update_bounds: bool = Field(
        True, 
        description="Automatically update tileset bounds after import"
    )
    validate_geometry: bool = Field(
        True,
        description="Validate geometry structure before import"
    )


class BulkFeatureResponse(BaseModel):
    """Response model for bulk feature creation."""
    success_count: int = Field(..., description="Number of successfully created features")
    failed_count: int = Field(..., description="Number of failed features")
    feature_ids: List[str] = Field(default_factory=list, description="List of created feature IDs")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    warnings: List[str] = Field(default_factory=list, description="List of warning messages")
    bounds_updated: bool = Field(False, description="Whether tileset bounds were updated")
    bounds: Optional[List[float]] = Field(
        None, 
        description="Updated bounds [west, south, east, north]"
    )
    center: Optional[List[float]] = Field(
        None, 
        description="Updated center [longitude, latitude]"
    )


class FeatureResponse(BaseModel):
    """Response model for a feature."""
    id: str
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]
