"""
Pydantic models for Tileset operations.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TilesetCreate(BaseModel):
    """Request model for creating a tileset."""
    name: str = Field(..., min_length=1, max_length=255, description="Tileset name")
    description: Optional[str] = Field(None, description="Tileset description")
    type: str = Field(..., pattern="^(vector|raster|pmtiles)$", description="Tileset type")
    format: str = Field(..., pattern="^(pbf|png|jpg|webp|geojson)$", description="Tile format")
    min_zoom: int = Field(0, ge=0, le=22, description="Minimum zoom level")
    max_zoom: int = Field(22, ge=0, le=22, description="Maximum zoom level")
    bounds: Optional[List[float]] = Field(None, description="Bounding box [west, south, east, north]")
    center: Optional[List[float]] = Field(None, description="Center point [lon, lat, zoom]")
    attribution: Optional[str] = Field(None, description="Attribution text")
    is_public: bool = Field(False, description="Whether the tileset is public")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class TilesetUpdate(BaseModel):
    """Request model for updating a tileset."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Tileset name")
    description: Optional[str] = Field(None, description="Tileset description")
    min_zoom: Optional[int] = Field(None, ge=0, le=22, description="Minimum zoom level")
    max_zoom: Optional[int] = Field(None, ge=0, le=22, description="Maximum zoom level")
    bounds: Optional[List[float]] = Field(None, description="Bounding box [west, south, east, north]")
    center: Optional[List[float]] = Field(None, description="Center point [lon, lat, zoom]")
    attribution: Optional[str] = Field(None, description="Attribution text")
    is_public: Optional[bool] = Field(None, description="Whether the tileset is public")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
