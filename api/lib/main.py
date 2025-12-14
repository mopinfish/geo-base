"""
FastAPI Tile Server for geo-base.
"""

import os
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from lib.config import get_settings
from lib.database import (
    check_database_connection,
    check_postgis_extension,
    close_pool,
    get_connection,
)
from lib.tiles import (
    FORMAT_MEDIA_TYPES,
    VECTOR_TILE_MEDIA_TYPE,
    generate_features_mvt,
    generate_mvt_from_postgis,
    generate_tilejson,
    get_cache_headers,
    get_mbtiles_metadata,
    get_tile_from_mbtiles,
)
from lib.raster_tiles import (
    RASTER_MEDIA_TYPES,
    is_rasterio_available,
    get_raster_tile_async,
    get_raster_preview,
    get_cog_info,
    get_cog_statistics,
    generate_raster_tilejson,
    get_raster_cache_headers,
    get_raster_media_type,
    validate_tile_format,
)
from lib.pmtiles import (
    is_pmtiles_available,
    get_pmtiles_tile,
    get_pmtiles_metadata,
    get_pmtiles_media_type,
    get_pmtiles_content_encoding,
    get_pmtiles_cache_headers,
    generate_pmtiles_tilejson,
)
from lib.auth import (
    User,
    get_current_user,
    require_auth,
    check_tileset_access,
    get_tileset_with_access_check,
    is_auth_configured,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    close_pool()


# Create FastAPI app
app = FastAPI(
    title="geo-base Tile Server",
    description="Ã¥Å“Â°Ã§Ââ€ Ã§Â©ÂºÃ©â€“â€œÃ£â€šÂ¿Ã£â€šÂ¤Ã£Æ’Â«Ã©â€¦ÂÃ¤Â¿Â¡API",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS middleware - å…¨ã‚ªãƒªã‚¸ãƒ³ã‚’è¨±å¯ï¼ˆé–‹ç™ºãƒ»æœ¬ç•ªå…±é€šï¼‰
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # å…¨ã‚ªãƒªã‚¸ãƒ³ã‚’è¨±å¯
    allow_credentials=False,  # "*"ã®å ´åˆã¯FalseãŒå¿…è¦
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_base_url(request: Request) -> str:
    """Get base URL from request headers."""
    # Check for forwarded headers (used by proxies/Vercel)
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    
    # Fallback to request URL
    return str(request.base_url).rstrip("/")


# ============================================================================
# Pydantic Models for CRUD Operations
# ============================================================================


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


class FeatureResponse(BaseModel):
    """Response model for a feature."""
    id: str
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


# ============================================================================
# Pydantic Models for Datasources
# ============================================================================


class DatasourceType(str, Enum):
    """Datasource type enum."""
    pmtiles = "pmtiles"
    cog = "cog"


class StorageProvider(str, Enum):
    """Storage provider enum."""
    supabase = "supabase"
    s3 = "s3"
    http = "http"


class DatasourceCreate(BaseModel):
    """Request model for creating a datasource."""
    tileset_id: str = Field(..., description="Parent tileset UUID")
    type: DatasourceType = Field(..., description="Datasource type (pmtiles or cog)")
    url: str = Field(..., min_length=1, description="URL to the data source")
    storage_provider: StorageProvider = Field(StorageProvider.http, description="Storage provider")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DatasourceUpdate(BaseModel):
    """Request model for updating a datasource."""
    url: Optional[str] = Field(None, min_length=1, description="URL to the data source")
    storage_provider: Optional[StorageProvider] = Field(None, description="Storage provider")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/api/health")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "version": "0.4.0",
        "environment": settings.environment,
        "rasterio_available": is_rasterio_available(),
        "pmtiles_available": is_pmtiles_available(),
        "auth_configured": is_auth_configured(),
    }


@app.get("/api/health/db")
def health_check_db():
    """Database health check endpoint with detailed error info."""
    db_result = check_database_connection()
    db_connected = db_result.get("connected", False)
    
    postgis_result = check_postgis_extension() if db_connected else {"available": False}
    postgis_available = postgis_result.get("available", False)

    status = "ok" if db_connected and postgis_available else "error"

    response = {
        "status": status,
        "database": "connected" if db_connected else "disconnected",
        "postgis": "available" if postgis_available else "unavailable",
        "environment": settings.environment,
    }
    
    # Add error details if present
    if not db_connected and db_result.get("error"):
        response["db_error"] = db_result["error"]
    
    if db_connected and postgis_result.get("version"):
        response["postgis_version"] = postgis_result["version"]
    elif not postgis_available and postgis_result.get("error"):
        response["postgis_error"] = postgis_result["error"]
    
    return response


# ============================================================================
# Auth Test Endpoints
# ============================================================================


@app.get("/api/auth/me")
def get_current_user_info(user: User = Depends(require_auth)):
    """
    Get current authenticated user information.
    
    Requires authentication.
    """
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
    }


@app.get("/api/auth/status")
def get_auth_status(user: Optional[User] = Depends(get_current_user)):
    """
    Get authentication status.
    
    Returns authentication status without requiring authentication.
    """
    return {
        "authenticated": user is not None,
        "user_id": user.id if user else None,
        "email": user.email if user else None,
    }


# ============================================================================
# Tile Endpoints - Static (MBTiles) - For Local Development
# ============================================================================


@app.get("/api/tiles/mbtiles/{tileset_name}/{z}/{x}/{y}.{tile_format}")
def get_mbtiles_tile(
    tileset_name: str,
    z: int,
    x: int,
    y: int,
    tile_format: str,
):
    """
    Get a tile from an MBTiles file.
    
    Note: This endpoint is primarily for local development.
    In production (Vercel), use database-backed tiles instead.

    Args:
        tileset_name: Name of the MBTiles file (without extension)
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
        tile_format: Tile format (pbf, png, jpg)
    """
    # Validate format
    media_type = FORMAT_MEDIA_TYPES.get(tile_format.lower())
    if not media_type:
        raise HTTPException(status_code=400, detail=f"Unsupported tile format: {tile_format}")

    # Build path to MBTiles file
    mbtiles_path = Path(f"data/{tileset_name}.mbtiles")

    if not mbtiles_path.exists():
        raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_name}")

    # Get tile data
    tile_data = get_tile_from_mbtiles(mbtiles_path, z, x, y)

    if tile_data is None:
        raise HTTPException(status_code=404, detail="Tile not found")

    # Get optimized cache headers (static tiles = longer cache)
    headers = get_cache_headers(z, is_static=True)

    # Add content-encoding for gzipped vector tiles
    if tile_format.lower() in ("pbf", "mvt"):
        headers["Content-Encoding"] = "gzip"

    return Response(content=tile_data, media_type=media_type, headers=headers)


@app.get("/api/tiles/mbtiles/{tileset_name}/metadata.json")
def get_mbtiles_tileset_metadata(tileset_name: str):
    """
    Get metadata for an MBTiles tileset.

    Args:
        tileset_name: Name of the MBTiles file (without extension)
    """
    mbtiles_path = Path(f"data/{tileset_name}.mbtiles")

    if not mbtiles_path.exists():
        raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_name}")

    metadata = get_mbtiles_metadata(mbtiles_path)
    return metadata


# ============================================================================
# Tile Endpoints - Dynamic (PostGIS)
# ============================================================================


@app.get("/api/tiles/dynamic/{layer_name}/{z}/{x}/{y}.pbf")
def get_dynamic_vector_tile(
    layer_name: str,
    z: int,
    x: int,
    y: int,
    simplify: bool = Query(True, description="Apply zoom-based simplification"),
    conn=Depends(get_connection),
):
    """
    Generate a vector tile dynamically from PostGIS table.
    
    Features:
    - Automatic zoom-based geometry simplification
    - Optimized caching based on zoom level

    Args:
        layer_name: Name of the database table/layer
        z: Zoom level (0-22)
        x: X tile coordinate
        y: Y tile coordinate
        simplify: Whether to apply zoom-based geometry simplification (default: true)
    """
    try:
        tile_data = generate_mvt_from_postgis(
            conn=conn,
            table_name=layer_name,
            z=z,
            x=x,
            y=y,
            layer_name=layer_name,
            simplify=simplify,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")

    # Get optimized cache headers based on zoom level
    headers = get_cache_headers(z, is_static=False)

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


@app.get("/api/tiles/features/{z}/{x}/{y}.pbf")
def get_features_vector_tile(
    z: int,
    x: int,
    y: int,
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    filter: str = Query(None, description="Attribute filter (e.g., 'properties.type=station')"),
    simplify: bool = Query(True, description="Apply zoom-based simplification"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Generate a vector tile from the features table.
    
    Features:
    - Filter by tileset_id and layer name
    - Attribute filtering with expressions
    - Automatic zoom-based geometry simplification
    - Optimized caching based on zoom level
    - Access control for private tilesets

    Args:
        z: Zoom level (0-22)
        x: X tile coordinate
        y: Y tile coordinate
        tileset_id: Optional tileset ID filter
        layer: Optional layer name filter
        filter: Attribute filter expression
        simplify: Whether to apply zoom-based geometry simplification (default: true)
    """
    # If tileset_id is specified, check access
    if tileset_id:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_public, user_id FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if row:
            is_public, owner_user_id = row
            owner_user_id = str(owner_user_id) if owner_user_id else None
            
            if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required to access this tileset",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to access this tileset"
                )
    
    try:
        tile_data = generate_features_mvt(
            conn=conn,
            z=z,
            x=x,
            y=y,
            tileset_id=tileset_id,
            layer_name=layer,
            filter_expr=filter,
            simplify=simplify,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")

    # Get optimized cache headers based on zoom level
    headers = get_cache_headers(z, is_static=False)

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


# ============================================================================
# Tile Endpoints - PMTiles
# ============================================================================


@app.get("/api/tiles/pmtiles/{tileset_id}/{z}/{x}/{y}.{tile_format}")
async def get_pmtiles_tile_endpoint(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    tile_format: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get a tile from a PMTiles file via HTTP Range Request.
    
    PMTiles files are hosted on external storage (Supabase Storage, S3, etc.)
    and accessed via HTTP Range Requests for efficient tile retrieval.
    
    Access control:
    - Public tilesets: No authentication required
    - Private tilesets: Only the owner can access

    Args:
        tileset_id: Tileset ID
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
        tile_format: Tile format (pbf, png, jpg, webp)
    """
    # Check if PMTiles is available
    if not is_pmtiles_available():
        raise HTTPException(
            status_code=501,
            detail="PMTiles service is not available. aiopmtiles not installed."
        )
    
    # Get PMTiles source from database with access check
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ps.pmtiles_url, ps.tile_type, ps.tile_compression,
                       ps.min_zoom, ps.max_zoom,
                       t.is_public, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE t.id = %s
                LIMIT 1
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"PMTiles tileset not found: {tileset_id}")
        
        pmtiles_url, tile_type, compression, min_zoom, max_zoom, is_public, owner_user_id = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
        # Validate zoom level
        if min_zoom is not None and z < min_zoom:
            raise HTTPException(status_code=404, detail=f"Zoom level {z} below minimum {min_zoom}")
        if max_zoom is not None and z > max_zoom:
            raise HTTPException(status_code=404, detail=f"Zoom level {z} above maximum {max_zoom}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")
    
    # Get tile from PMTiles
    try:
        tile_data = await get_pmtiles_tile(pmtiles_url, z, x, y)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if tile_data is None:
        raise HTTPException(status_code=404, detail="Tile not found")
    
    # Determine media type
    media_type = get_pmtiles_media_type(tile_type or "mvt")
    
    # Build response headers
    headers = get_pmtiles_cache_headers(z, is_static=True)
    
    # Add content-encoding if compressed
    content_encoding = get_pmtiles_content_encoding(compression or "gzip")
    if content_encoding:
        headers["Content-Encoding"] = content_encoding
    
    return Response(content=tile_data, media_type=media_type, headers=headers)


@app.get("/api/tiles/pmtiles/{tileset_id}/tilejson.json")
async def get_pmtiles_tilejson(
    tileset_id: str,
    request: Request,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get TileJSON for a PMTiles tileset.
    
    Args:
        tileset_id: Tileset ID
    """
    if not is_pmtiles_available():
        raise HTTPException(
            status_code=501,
            detail="PMTiles service is not available."
        )
    
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.name, t.description, t.attribution, t.is_public, t.user_id,
                       ps.pmtiles_url, ps.tile_type, ps.min_zoom, ps.max_zoom,
                       ps.bounds, ps.center, ps.layers
                FROM tilesets t
                JOIN pmtiles_sources ps ON ps.tileset_id = t.id
                WHERE t.id = %s
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"PMTiles tileset not found: {tileset_id}")
        
        (name, description, attribution, is_public, owner_user_id,
         pmtiles_url, tile_type, min_zoom, max_zoom, bounds, center, layers) = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
        base_url = get_base_url(request)
        
        return generate_pmtiles_tilejson(
            tileset_id=tileset_id,
            name=name,
            base_url=base_url,
            tile_type=tile_type or "mvt",
            min_zoom=min_zoom or 0,
            max_zoom=max_zoom or 22,
            bounds=bounds,
            center=center,
            description=description,
            attribution=attribution,
            layers=layers,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TileJSON: {str(e)}")


@app.get("/api/tiles/pmtiles/{tileset_id}/metadata")
async def get_pmtiles_metadata_endpoint(
    tileset_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get metadata from a PMTiles file.
    
    This endpoint reads metadata directly from the PMTiles file header.
    
    Args:
        tileset_id: Tileset ID
    """
    if not is_pmtiles_available():
        raise HTTPException(
            status_code=501,
            detail="PMTiles service is not available."
        )
    
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ps.pmtiles_url, t.name, t.description, t.is_public, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE t.id = %s
                LIMIT 1
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"PMTiles tileset not found: {tileset_id}")
        
        pmtiles_url, name, description, is_public, owner_user_id = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")
    
    # Get metadata from PMTiles file
    try:
        metadata = await get_pmtiles_metadata(pmtiles_url)
        return {
            "tileset_id": tileset_id,
            "name": name,
            "description": description,
            "pmtiles_url": pmtiles_url,
            **metadata,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Tile Endpoints - Raster (COG)
# ============================================================================


@app.get("/api/tiles/raster/{tileset_id}/{z}/{x}/{y}.{tile_format}")
async def get_raster_tile(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    tile_format: str,
    indexes: str = Query(None, description="Comma-separated band indexes (e.g., '1,2,3')"),
    scale_min: float = Query(None, description="Minimum value for rescaling"),
    scale_max: float = Query(None, description="Maximum value for rescaling"),
    colormap: str = Query(None, description="Colormap name for single-band visualization"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get a raster tile from a Cloud Optimized GeoTIFF (COG).
    
    Access control:
    - Public tilesets: No authentication required
    - Private tilesets: Only the owner can access
    
    Args:
        tileset_id: Tileset ID or 'url' for direct COG URL access
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
        tile_format: Output format (png, jpg, webp)
        indexes: Comma-separated band indexes (e.g., '1,2,3' for RGB)
        scale_min: Minimum value for rescaling (default from settings)
        scale_max: Maximum value for rescaling (default from settings)
        colormap: Colormap name for single-band visualization
    """
    # Check if rio-tiler is available
    if not is_rasterio_available():
        raise HTTPException(
            status_code=501,
            detail="Raster tile service is not available. rio-tiler/rasterio not installed."
        )
    
    # Validate tile format
    try:
        normalized_format = validate_tile_format(tile_format)
        media_type = get_raster_media_type(normalized_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get COG URL from database with access check
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rs.cog_url, t.min_zoom, t.max_zoom, t.is_public, t.user_id,
                       COALESCE((t.metadata->>'scale_min')::float, %s) as scale_min,
                       COALESCE((t.metadata->>'scale_max')::float, %s) as scale_max,
                       COALESCE(t.metadata->>'bands', NULL) as default_bands
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE t.id = %s
                LIMIT 1
                """,
                (settings.raster_default_scale_min, settings.raster_default_scale_max, tileset_id),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Raster tileset not found: {tileset_id}")
        
        (cog_url, min_zoom, max_zoom, is_public, owner_user_id,
         db_scale_min, db_scale_max, default_bands) = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
        # Validate zoom level
        if min_zoom and z < min_zoom:
            raise HTTPException(status_code=404, detail=f"Zoom level {z} below minimum {min_zoom}")
        if max_zoom and z > max_zoom:
            raise HTTPException(status_code=404, detail=f"Zoom level {z} above maximum {max_zoom}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")
    
    # Parse band indexes
    band_indexes = None
    if indexes:
        try:
            band_indexes = tuple(int(i.strip()) for i in indexes.split(","))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid band indexes format")
    elif default_bands:
        try:
            band_indexes = tuple(int(i.strip()) for i in default_bands.split(","))
        except ValueError:
            pass
    
    # Use provided scale values or database defaults
    final_scale_min = scale_min if scale_min is not None else db_scale_min
    final_scale_max = scale_max if scale_max is not None else db_scale_max
    
    # Generate tile
    try:
        tile_data = await get_raster_tile_async(
            cog_url=cog_url,
            z=z,
            x=x,
            y=y,
            indexes=band_indexes,
            scale_min=final_scale_min,
            scale_max=final_scale_max,
            img_format=normalized_format,
            tile_size=settings.raster_tile_size,
            colormap=colormap,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if tile_data is None:
        # Return empty/transparent tile for out-of-bounds requests
        raise HTTPException(status_code=404, detail="Tile outside COG bounds")
    
    headers = get_raster_cache_headers(z, is_static=True)
    
    return Response(content=tile_data, media_type=media_type, headers=headers)


@app.get("/api/tiles/raster/{tileset_id}/tilejson.json")
def get_raster_tilejson(
    tileset_id: str,
    request: Request,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get TileJSON for a raster tileset.
    
    Args:
        tileset_id: Tileset ID
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.name, t.description, t.format, t.min_zoom, t.max_zoom,
                       t.attribution, t.is_public, t.user_id, rs.cog_url
                FROM tilesets t
                LEFT JOIN raster_sources rs ON rs.tileset_id = t.id
                WHERE t.id = %s AND t.type = 'raster'
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Raster tileset not found: {tileset_id}")
        
        (name, description, tile_format, min_zoom, max_zoom,
         attribution, is_public, owner_user_id, cog_url) = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
        base_url = get_base_url(request)
        
        # Try to get bounds from COG if available
        bounds = None
        center = None
        if cog_url and is_rasterio_available():
            try:
                cog_info = get_cog_info(cog_url)
                bounds = list(cog_info["bounds"])
                # Calculate center
                center_lng = (bounds[0] + bounds[2]) / 2
                center_lat = (bounds[1] + bounds[3]) / 2
                center = [center_lng, center_lat, (min_zoom or 0 + max_zoom or 18) // 2]
            except Exception:
                pass
        
        return generate_raster_tilejson(
            tileset_id=tileset_id,
            name=name,
            base_url=base_url,
            tile_format=tile_format or "png",
            min_zoom=min_zoom or 0,
            max_zoom=max_zoom or 22,
            bounds=bounds,
            center=center,
            description=description,
            attribution=attribution,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TileJSON: {str(e)}")


@app.get("/api/tiles/raster/{tileset_id}/preview")
async def get_raster_tile_preview(
    tileset_id: str,
    indexes: str = Query(None, description="Comma-separated band indexes"),
    scale_min: float = Query(None, description="Minimum value for rescaling"),
    scale_max: float = Query(None, description="Maximum value for rescaling"),
    max_size: int = Query(512, description="Maximum dimension of preview image"),
    format: str = Query("png", description="Output format (png, jpg, webp)"),
    colormap: str = Query(None, description="Colormap name"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get a preview image of a raster tileset.
    
    Args:
        tileset_id: Tileset ID
        indexes: Comma-separated band indexes
        scale_min: Minimum value for rescaling
        scale_max: Maximum value for rescaling
        max_size: Maximum dimension of the preview image
        format: Output format
        colormap: Colormap name
    """
    if not is_rasterio_available():
        raise HTTPException(
            status_code=501,
            detail="Raster preview service is not available."
        )
    
    # Validate format
    try:
        normalized_format = validate_tile_format(format)
        media_type = get_raster_media_type(normalized_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get COG URL from database with access check
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rs.cog_url, t.is_public, t.user_id,
                       COALESCE((t.metadata->>'scale_min')::float, %s) as scale_min,
                       COALESCE((t.metadata->>'scale_max')::float, %s) as scale_max,
                       COALESCE(t.metadata->>'bands', NULL) as default_bands
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE t.id = %s
                LIMIT 1
                """,
                (settings.raster_default_scale_min, settings.raster_default_scale_max, tileset_id),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Raster tileset not found: {tileset_id}")
        
        cog_url, is_public, owner_user_id, db_scale_min, db_scale_max, default_bands = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")
    
    # Parse band indexes
    band_indexes = None
    if indexes:
        try:
            band_indexes = tuple(int(i.strip()) for i in indexes.split(","))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid band indexes format")
    elif default_bands:
        try:
            band_indexes = tuple(int(i.strip()) for i in default_bands.split(","))
        except ValueError:
            pass
    
    # Use provided scale values or database defaults
    final_scale_min = scale_min if scale_min is not None else db_scale_min
    final_scale_max = scale_max if scale_max is not None else db_scale_max
    
    # Generate preview
    try:
        preview_data = await get_raster_preview(
            cog_url=cog_url,
            indexes=band_indexes,
            scale_min=final_scale_min,
            scale_max=final_scale_max,
            max_size=max_size,
            img_format=normalized_format,
            colormap=colormap,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if preview_data is None:
        raise HTTPException(status_code=500, detail="Failed to generate preview")
    
    return Response(content=preview_data, media_type=media_type)


@app.get("/api/tiles/raster/{tileset_id}/info")
def get_raster_info(
    tileset_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get metadata information about a raster tileset's COG.
    
    Args:
        tileset_id: Tileset ID
    """
    if not is_rasterio_available():
        raise HTTPException(
            status_code=501,
            detail="Raster info service is not available."
        )
    
    # Get COG URL from database with access check
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rs.cog_url, t.name, t.description, t.is_public, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE t.id = %s
                LIMIT 1
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Raster tileset not found: {tileset_id}")
        
        cog_url, name, description, is_public, owner_user_id = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")
    
    # Get COG info
    try:
        cog_info = get_cog_info(cog_url)
        return {
            "tileset_id": tileset_id,
            "name": name,
            "description": description,
            "cog_url": cog_url,
            **cog_info,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tiles/raster/{tileset_id}/statistics")
def get_raster_statistics(
    tileset_id: str,
    indexes: str = Query(None, description="Comma-separated band indexes"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get statistics for a raster tileset's bands.
    
    Args:
        tileset_id: Tileset ID
        indexes: Comma-separated band indexes to analyze
    """
    if not is_rasterio_available():
        raise HTTPException(
            status_code=501,
            detail="Raster statistics service is not available."
        )
    
    # Get COG URL from database with access check
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rs.cog_url, t.is_public, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE t.id = %s
                LIMIT 1
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Raster tileset not found: {tileset_id}")
        
        cog_url, is_public, owner_user_id = row
        owner_user_id = str(owner_user_id) if owner_user_id else None
        
        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")
    
    # Parse band indexes
    band_indexes = None
    if indexes:
        try:
            band_indexes = tuple(int(i.strip()) for i in indexes.split(","))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid band indexes format")
    
    # Get statistics
    try:
        stats = get_cog_statistics(cog_url, indexes=band_indexes)
        return {
            "tileset_id": tileset_id,
            "statistics": stats,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TileJSON Endpoints
# ============================================================================


@app.get("/api/tiles/dynamic/{layer_name}/tilejson.json")
def get_dynamic_tilejson(layer_name: str, request: Request):
    """
    Get TileJSON for a dynamic layer.

    Args:
        layer_name: Name of the database table/layer
    """
    base_url = get_base_url(request)

    tilejson = generate_tilejson(
        tileset_id=f"dynamic/{layer_name}",
        name=layer_name,
        base_url=base_url,
        tile_format="pbf",
        description=f"Dynamic vector tiles from {layer_name} table",
    )

    return tilejson


@app.get("/api/tiles/features/tilejson.json")
def get_features_tilejson(
    request: Request,
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    filter: str = Query(None, description="Attribute filter expression"),
):
    """
    Get TileJSON for the features layer.
    
    Query parameters are passed through to the tile URLs.
    """
    base_url = get_base_url(request)
    
    # Build tile URL with query params
    tile_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf"
    query_params = []
    if tileset_id:
        query_params.append(f"tileset_id={tileset_id}")
    if layer:
        query_params.append(f"layer={layer}")
    if filter:
        # URL encode the filter parameter
        from urllib.parse import quote
        query_params.append(f"filter={quote(filter)}")
    if query_params:
        tile_url += "?" + "&".join(query_params)

    return {
        "tilejson": "3.0.0",
        "name": "features",
        "tiles": [tile_url],
        "minzoom": 0,
        "maxzoom": 22,
        "bounds": [-180, -85.051129, 180, 85.051129],
        "center": [139.7, 35.7, 10],
    }


# ============================================================================
# Tilesets API (CRUD)
# ============================================================================


@app.get("/api/tilesets")
def list_tilesets(
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
    include_private: bool = Query(False, description="Include private tilesets (requires auth)"),
):
    """
    List all accessible tilesets.
    
    By default, only public tilesets are returned.
    With authentication and include_private=true, also returns user's private tilesets.
    """
    try:
        with conn.cursor() as cur:
            if include_private and user:
                # Return public tilesets + user's private tilesets
                cur.execute(
                    """
                    SELECT id, name, description, type, format, min_zoom, max_zoom,
                           is_public, user_id, created_at, updated_at
                    FROM tilesets
                    WHERE is_public = true OR user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user.id,),
                )
            else:
                # Return only public tilesets
                cur.execute(
                    """
                    SELECT id, name, description, type, format, min_zoom, max_zoom,
                           is_public, user_id, created_at, updated_at
                    FROM tilesets
                    WHERE is_public = true
                    ORDER BY created_at DESC
                    """
                )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        tilesets = [dict(zip(columns, row)) for row in rows]

        # Convert datetime and UUID to string
        for tileset in tilesets:
            if tileset.get("id"):
                tileset["id"] = str(tileset["id"])
            if tileset.get("user_id"):
                tileset["user_id"] = str(tileset["user_id"])
            if tileset.get("created_at"):
                tileset["created_at"] = tileset["created_at"].isoformat()
            if tileset.get("updated_at"):
                tileset["updated_at"] = tileset["updated_at"].isoformat()

        return {"tilesets": tilesets, "count": len(tilesets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tilesets: {str(e)}")


@app.get("/api/tilesets/{tileset_id}")
def get_tileset(
    tileset_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific tileset by ID with access control."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, type, format, min_zoom, max_zoom,
                       ST_AsGeoJSON(bounds) as bounds, ST_AsGeoJSON(center) as center,
                       attribution, is_public, user_id, metadata, created_at, updated_at
                FROM tilesets
                WHERE id = %s
                """,
                (tileset_id,),
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_id}")

        tileset = dict(zip(columns, row))
        is_public = tileset.get("is_public", True)
        owner_user_id = str(tileset.get("user_id")) if tileset.get("user_id") else None

        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )

        # Convert types
        if tileset.get("id"):
            tileset["id"] = str(tileset["id"])
        if tileset.get("user_id"):
            tileset["user_id"] = str(tileset["user_id"])
        if tileset.get("bounds"):
            tileset["bounds"] = json.loads(tileset["bounds"])
        if tileset.get("center"):
            tileset["center"] = json.loads(tileset["center"])
        if tileset.get("created_at"):
            tileset["created_at"] = tileset["created_at"].isoformat()
        if tileset.get("updated_at"):
            tileset["updated_at"] = tileset["updated_at"].isoformat()

        return tileset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")


@app.get("/api/tilesets/{tileset_id}/tilejson.json")
def get_tileset_tilejson(
    tileset_id: str,
    request: Request,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get TileJSON for a tileset.
    
    Routes to appropriate handler based on tileset type.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT type, is_public, user_id
                FROM tilesets
                WHERE id = %s
                """,
                (tileset_id,),
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_id}")

        tileset_type, is_public, owner_user_id = row
        owner_user_id = str(owner_user_id) if owner_user_id else None

        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )

        base_url = get_base_url(request)

        # Route based on type
        if tileset_type == "vector":
            return {
                "tilejson": "3.0.0",
                "tiles": [f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}"],
                "minzoom": 0,
                "maxzoom": 22,
            }
        elif tileset_type == "pmtiles":
            # Delegate to PMTiles endpoint (handled internally)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ps.pmtiles_url, ps.tile_type, ps.min_zoom, ps.max_zoom,
                           ps.bounds, ps.center, ps.layers,
                           t.name, t.description, t.attribution
                    FROM pmtiles_sources ps
                    JOIN tilesets t ON ps.tileset_id = t.id
                    WHERE t.id = %s
                    """,
                    (tileset_id,),
                )
                row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="PMTiles source not found")
            
            (pmtiles_url, tile_type, min_zoom, max_zoom, bounds, center, layers,
             name, description, attribution) = row
            
            # Build metadata dict for generate_pmtiles_tilejson
            metadata = {
                "tile_type": tile_type or "mvt",
                "min_zoom": min_zoom or 0,
                "max_zoom": max_zoom or 22,
                "bounds": bounds,
                "center": center,
                "layers": layers or [],
            }
            
            return generate_pmtiles_tilejson(
                tileset_id=tileset_id,
                tileset_name=name,
                metadata=metadata,
                base_url=base_url,
                description=description or "",
                attribution=attribution or "",
            )
        elif tileset_type == "raster":
            # Delegate to raster TileJSON
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT t.name, t.description, t.format, t.min_zoom, t.max_zoom,
                           t.attribution, rs.cog_url,
                           ST_XMin(t.bounds), ST_YMin(t.bounds), ST_XMax(t.bounds), ST_YMax(t.bounds),
                           ST_X(t.center), ST_Y(t.center)
                    FROM tilesets t
                    LEFT JOIN raster_sources rs ON rs.tileset_id = t.id
                    WHERE t.id = %s
                    """,
                    (tileset_id,),
                )
                row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Raster source not found")
            
            (name, description, tile_format, min_zoom, max_zoom, attribution, cog_url,
             xmin, ymin, xmax, ymax, center_x, center_y) = row
            
            # Build bounds and center arrays
            bounds = None
            if xmin is not None and ymin is not None and xmax is not None and ymax is not None:
                bounds = [xmin, ymin, xmax, ymax]
            
            center = None
            if center_x is not None and center_y is not None:
                center_zoom = min_zoom if min_zoom else 10
                center = [center_x, center_y, center_zoom]
            
            return generate_raster_tilejson(
                tileset_id=tileset_id,
                name=name,
                base_url=base_url,
                tile_format=tile_format or "png",
                min_zoom=min_zoom or 0,
                max_zoom=max_zoom or 22,
                bounds=bounds,
                center=center,
                description=description,
                attribution=attribution,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tileset type: {tileset_type}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TileJSON: {str(e)}")


@app.post("/api/tilesets", status_code=201)
def create_tileset(
    tileset: TilesetCreate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Create a new tileset.
    
    Requires authentication.
    """
    try:
        with conn.cursor() as cur:
            # Build geometry SQL
            bounds_sql = "NULL"
            center_sql = "NULL"
            
            if tileset.bounds and len(tileset.bounds) == 4:
                west, south, east, north = tileset.bounds
                bounds_sql = f"ST_MakeEnvelope({west}, {south}, {east}, {north}, 4326)"
            
            if tileset.center and len(tileset.center) >= 2:
                lon, lat = tileset.center[0], tileset.center[1]
                center_sql = f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)"
            
            metadata_json = json.dumps(tileset.metadata) if tileset.metadata else None
            
            cur.execute(
                f"""
                INSERT INTO tilesets (
                    name, description, type, format,
                    min_zoom, max_zoom, bounds, center,
                    attribution, is_public, user_id, metadata
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, {bounds_sql}, {center_sql},
                    %s, %s, %s, %s
                )
                RETURNING id, name, description, type, format,
                          min_zoom, max_zoom, attribution, is_public,
                          created_at, updated_at
                """,
                (
                    tileset.name,
                    tileset.description,
                    tileset.type,
                    tileset.format,
                    tileset.min_zoom,
                    tileset.max_zoom,
                    tileset.attribution,
                    tileset.is_public,
                    user.id,
                    metadata_json,
                ),
            )
            
            row = cur.fetchone()
            conn.commit()
            
            return {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "type": row[3],
                "format": row[4],
                "min_zoom": row[5],
                "max_zoom": row[6],
                "attribution": row[7],
                "is_public": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating tileset: {str(e)}")


@app.patch("/api/tilesets/{tileset_id}")
def update_tileset(
    tileset_id: str,
    tileset: TilesetUpdate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Update an existing tileset.
    
    Requires authentication and ownership of the tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to update this tileset")
            
            # Build update query dynamically
            updates = []
            params = []
            
            if tileset.name is not None:
                updates.append("name = %s")
                params.append(tileset.name)
            
            if tileset.description is not None:
                updates.append("description = %s")
                params.append(tileset.description)
            
            if tileset.min_zoom is not None:
                updates.append("min_zoom = %s")
                params.append(tileset.min_zoom)
            
            if tileset.max_zoom is not None:
                updates.append("max_zoom = %s")
                params.append(tileset.max_zoom)
            
            if tileset.bounds is not None and len(tileset.bounds) == 4:
                west, south, east, north = tileset.bounds
                updates.append(f"bounds = ST_MakeEnvelope({west}, {south}, {east}, {north}, 4326)")
            
            if tileset.center is not None and len(tileset.center) >= 2:
                lon, lat = tileset.center[0], tileset.center[1]
                updates.append(f"center = ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)")
            
            if tileset.attribution is not None:
                updates.append("attribution = %s")
                params.append(tileset.attribution)
            
            if tileset.is_public is not None:
                updates.append("is_public = %s")
                params.append(tileset.is_public)
            
            if tileset.metadata is not None:
                updates.append("metadata = %s")
                params.append(json.dumps(tileset.metadata))
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            updates.append("updated_at = NOW()")
            params.append(tileset_id)
            
            cur.execute(
                f"""
                UPDATE tilesets
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, name, description, type, format,
                          min_zoom, max_zoom, attribution, is_public,
                          created_at, updated_at
                """,
                params,
            )
            
            row = cur.fetchone()
            conn.commit()
            
            return {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "type": row[3],
                "format": row[4],
                "min_zoom": row[5],
                "max_zoom": row[6],
                "attribution": row[7],
                "is_public": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating tileset: {str(e)}")


@app.delete("/api/tilesets/{tileset_id}", status_code=204)
def delete_tileset(
    tileset_id: str,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete a tileset and all associated features.
    
    Requires authentication and ownership of the tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this tileset")
            
            # Delete tileset (cascades to features due to FK constraint)
            cur.execute("DELETE FROM tilesets WHERE id = %s", (tileset_id,))
            conn.commit()
            
            return Response(status_code=204)
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting tileset: {str(e)}")


# ============================================================================
# Feature CRUD Endpoints
# ============================================================================


@app.post("/api/features", status_code=201)
def create_feature(
    feature: FeatureCreate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Create a new feature in a tileset.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id FROM tilesets WHERE id = %s",
                (feature.tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to add features to this tileset")
            
            # Convert GeoJSON geometry to WKT
            geometry_json = json.dumps(feature.geometry)
            properties_json = json.dumps(feature.properties) if feature.properties else "{}"
            
            cur.execute(
                """
                INSERT INTO features (tileset_id, layer_name, geom, properties)
                VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s)
                RETURNING id, layer_name, ST_AsGeoJSON(geom)::json as geometry, properties,
                          created_at, updated_at
                """,
                (
                    feature.tileset_id,
                    feature.layer_name,
                    geometry_json,
                    properties_json,
                ),
            )
            
            row = cur.fetchone()
            conn.commit()
            
            return {
                "id": str(row[0]),
                "type": "Feature",
                "geometry": row[2],
                "properties": {
                    **(row[3] if row[3] else {}),
                    "layer_name": row[1],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating feature: {str(e)}")


@app.patch("/api/features/{feature_id}")
def update_feature(
    feature_id: str,
    feature: FeatureUpdate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Update an existing feature.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if feature exists and user owns the parent tileset
            cur.execute(
                """
                SELECT f.id, t.user_id
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE f.id = %s
                """,
                (feature_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to update this feature")
            
            # Build update query dynamically
            updates = []
            params = []
            
            if feature.layer_name is not None:
                updates.append("layer_name = %s")
                params.append(feature.layer_name)
            
            if feature.geometry is not None:
                updates.append("geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)")
                params.append(json.dumps(feature.geometry))
            
            if feature.properties is not None:
                updates.append("properties = %s")
                params.append(json.dumps(feature.properties))
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            updates.append("updated_at = NOW()")
            params.append(feature_id)
            
            cur.execute(
                f"""
                UPDATE features
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, layer_name, ST_AsGeoJSON(geom)::json as geometry, properties,
                          tileset_id, created_at, updated_at
                """,
                params,
            )
            
            row = cur.fetchone()
            conn.commit()
            
            return {
                "id": str(row[0]),
                "type": "Feature",
                "geometry": row[2],
                "properties": {
                    **(row[3] if row[3] else {}),
                    "layer_name": row[1],
                    "tileset_id": str(row[4]),
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating feature: {str(e)}")


@app.delete("/api/features/{feature_id}", status_code=204)
def delete_feature(
    feature_id: str,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete a feature.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if feature exists and user owns the parent tileset
            cur.execute(
                """
                SELECT f.id, t.user_id
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE f.id = %s
                """,
                (feature_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this feature")
            
            # Delete feature
            cur.execute("DELETE FROM features WHERE id = %s", (feature_id,))
            conn.commit()
            
            return Response(status_code=204)
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting feature: {str(e)}")


@app.get("/api/features")
def list_features(
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    bbox: str = Query(None, description="Bounding box filter (minx,miny,maxx,maxy)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of features"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    List features with optional filters.
    
    Returns GeoJSON FeatureCollection.
    """
    try:
        with conn.cursor() as cur:
            # Build query
            conditions = []
            params = []
            
            if tileset_id:
                # Check access to tileset
                cur.execute(
                    "SELECT is_public, user_id FROM tilesets WHERE id = %s",
                    (tileset_id,),
                )
                row = cur.fetchone()
                
                if row:
                    is_public, owner_user_id = row
                    owner_user_id = str(owner_user_id) if owner_user_id else None
                    
                    if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
                        if not user:
                            raise HTTPException(
                                status_code=401,
                                detail="Authentication required to access this tileset",
                                headers={"WWW-Authenticate": "Bearer"},
                            )
                        raise HTTPException(
                            status_code=403,
                            detail="You do not have permission to access this tileset"
                        )
                
                conditions.append("f.tileset_id = %s")
                params.append(tileset_id)
            else:
                # Only return features from public tilesets if no tileset_id specified
                conditions.append("t.is_public = true")
            
            if layer:
                conditions.append("f.layer_name = %s")
                params.append(layer)
            
            if bbox:
                try:
                    minx, miny, maxx, maxy = [float(x) for x in bbox.split(",")]
                    conditions.append(
                        "ST_Intersects(f.geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                    )
                    params.extend([minx, miny, maxx, maxy])
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid bbox format")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Get total count
            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE {where_clause}
                """,
                params,
            )
            total_count = cur.fetchone()[0]
            
            # Get features
            cur.execute(
                f"""
                SELECT f.id, f.layer_name, ST_AsGeoJSON(f.geom)::json as geometry,
                       f.properties, f.tileset_id, f.created_at, f.updated_at
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE {where_clause}
                ORDER BY f.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            rows = cur.fetchall()
            
            features = []
            for row in rows:
                features.append({
                    "id": str(row[0]),
                    "type": "Feature",
                    "geometry": row[2],
                    "properties": {
                        **(row[3] if row[3] else {}),
                        "layer_name": row[1],
                        "tileset_id": str(row[4]),
                        "created_at": row[5].isoformat() if row[5] else None,
                        "updated_at": row[6].isoformat() if row[6] else None,
                    },
                })
            
            return {
                "type": "FeatureCollection",
                "features": features,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing features: {str(e)}")


@app.get("/api/features/{feature_id}")
def get_feature(
    feature_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific feature by ID."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.id, f.layer_name, ST_AsGeoJSON(f.geom)::json as geometry,
                       f.properties, f.tileset_id, f.created_at, f.updated_at,
                       t.is_public, t.user_id
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE f.id = %s
                """,
                (feature_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            is_public = row[7]
            owner_user_id = str(row[8]) if row[8] else None
            
            # Check access
            if not check_tileset_access(str(row[4]), is_public, owner_user_id, user):
                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required to access this feature",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to access this feature"
                )
            
            return {
                "id": str(row[0]),
                "type": "Feature",
                "geometry": row[2],
                "properties": {
                    **(row[3] if row[3] else {}),
                    "layer_name": row[1],
                    "tileset_id": str(row[4]),
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feature: {str(e)}")


# ============================================================================
# Datasources API (CRUD)
# ============================================================================


@app.get("/api/datasources")
def list_datasources(
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
    type: Optional[str] = Query(None, description="Filter by type (pmtiles or cog)"),
    include_private: bool = Query(False, description="Include private datasources (requires auth)"),
):
    """
    List all accessible datasources (PMTiles and COG sources combined).
    
    By default, only datasources from public tilesets are returned.
    With authentication and include_private=true, also returns user's private datasources.
    """
    try:
        datasources = []
        
        with conn.cursor() as cur:
            # Build conditions for both queries
            if include_private and user:
                access_condition = "(t.is_public = true OR t.user_id = %s)"
                access_params = [user.id]
            else:
                access_condition = "t.is_public = true"
                access_params = []
            
            # Get PMTiles sources
            if type is None or type == "pmtiles":
                cur.execute(
                    f"""
                    SELECT ps.id, ps.tileset_id, ps.pmtiles_url, ps.storage_provider,
                           ps.tile_type, ps.tile_compression, ps.min_zoom, ps.max_zoom,
                           ps.bounds, ps.center, ps.metadata, ps.created_at, ps.updated_at,
                           t.name as tileset_name, t.is_public, t.user_id
                    FROM pmtiles_sources ps
                    JOIN tilesets t ON ps.tileset_id = t.id
                    WHERE {access_condition}
                    ORDER BY ps.created_at DESC
                    """,
                    access_params,
                )
                
                for row in cur.fetchall():
                    datasources.append({
                        "id": str(row[0]),
                        "tileset_id": str(row[1]),
                        "type": "pmtiles",
                        "url": row[2],
                        "storage_provider": row[3],
                        "tile_type": row[4],
                        "compression": row[5],
                        "min_zoom": row[6],
                        "max_zoom": row[7],
                        "bounds": row[8],
                        "center": row[9],
                        "metadata": row[10],
                        "created_at": row[11].isoformat() if row[11] else None,
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "tileset_name": row[13],
                        "is_public": row[14],
                        "user_id": str(row[15]) if row[15] else None,
                    })
            
            # Get COG sources
            if type is None or type == "cog":
                cur.execute(
                    f"""
                    SELECT rs.id, rs.tileset_id, rs.cog_url, rs.storage_provider,
                           rs.band_count, rs.native_crs, rs.recommended_min_zoom, rs.recommended_max_zoom,
                           rs.metadata, rs.created_at, rs.updated_at,
                           t.name as tileset_name, t.is_public, t.user_id
                    FROM raster_sources rs
                    JOIN tilesets t ON rs.tileset_id = t.id
                    WHERE {access_condition}
                    ORDER BY rs.created_at DESC
                    """,
                    access_params,
                )
                
                for row in cur.fetchall():
                    datasources.append({
                        "id": str(row[0]),
                        "tileset_id": str(row[1]),
                        "type": "cog",
                        "url": row[2],
                        "storage_provider": row[3],
                        "band_count": row[4],
                        "native_crs": row[5],
                        "min_zoom": row[6],
                        "max_zoom": row[7],
                        "metadata": row[8],
                        "created_at": row[9].isoformat() if row[9] else None,
                        "updated_at": row[10].isoformat() if row[10] else None,
                        "tileset_name": row[11],
                        "is_public": row[12],
                        "user_id": str(row[13]) if row[13] else None,
                    })
        
        # Sort by created_at descending
        datasources.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        return {"datasources": datasources, "count": len(datasources)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing datasources: {str(e)}")


@app.get("/api/datasources/{datasource_id}")
def get_datasource(
    datasource_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific datasource by ID."""
    try:
        with conn.cursor() as cur:
            # Try PMTiles first
            cur.execute(
                """
                SELECT ps.id, ps.tileset_id, ps.pmtiles_url, ps.storage_provider,
                       ps.tile_type, ps.tile_compression, ps.min_zoom, ps.max_zoom,
                       ps.bounds, ps.center, ps.layers, ps.metadata, ps.created_at, ps.updated_at,
                       t.name as tileset_name, t.is_public, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE ps.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                is_public = row[15]
                owner_user_id = str(row[16]) if row[16] else None
                
                # Check access
                if not check_tileset_access(str(row[1]), is_public, owner_user_id, user):
                    if not user:
                        raise HTTPException(
                            status_code=401,
                            detail="Authentication required to access this datasource",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have permission to access this datasource"
                    )
                
                return {
                    "id": str(row[0]),
                    "tileset_id": str(row[1]),
                    "type": "pmtiles",
                    "url": row[2],
                    "storage_provider": row[3],
                    "tile_type": row[4],
                    "compression": row[5],
                    "min_zoom": row[6],
                    "max_zoom": row[7],
                    "bounds": row[8],
                    "center": row[9],
                    "layers": row[10],
                    "metadata": row[11],
                    "created_at": row[12].isoformat() if row[12] else None,
                    "updated_at": row[13].isoformat() if row[13] else None,
                    "tileset_name": row[14],
                    "is_public": row[15],
                    "user_id": owner_user_id,
                }
            
            # Try COG
            cur.execute(
                """
                SELECT rs.id, rs.tileset_id, rs.cog_url, rs.storage_provider,
                       rs.band_count, rs.band_descriptions, rs.native_crs, rs.native_resolution,
                       rs.recommended_min_zoom, rs.recommended_max_zoom,
                       rs.metadata, rs.created_at, rs.updated_at,
                       t.name as tileset_name, t.is_public, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE rs.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                is_public = row[14]
                owner_user_id = str(row[15]) if row[15] else None
                
                # Check access
                if not check_tileset_access(str(row[1]), is_public, owner_user_id, user):
                    if not user:
                        raise HTTPException(
                            status_code=401,
                            detail="Authentication required to access this datasource",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have permission to access this datasource"
                    )
                
                return {
                    "id": str(row[0]),
                    "tileset_id": str(row[1]),
                    "type": "cog",
                    "url": row[2],
                    "storage_provider": row[3],
                    "band_count": row[4],
                    "band_descriptions": row[5],
                    "native_crs": row[6],
                    "native_resolution": row[7],
                    "min_zoom": row[8],
                    "max_zoom": row[9],
                    "metadata": row[10],
                    "created_at": row[11].isoformat() if row[11] else None,
                    "updated_at": row[12].isoformat() if row[12] else None,
                    "tileset_name": row[13],
                    "is_public": row[14],
                    "user_id": owner_user_id,
                }
            
            raise HTTPException(status_code=404, detail="Datasource not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching datasource: {str(e)}")


@app.post("/api/datasources", status_code=201)
async def create_datasource(
    datasource: DatasourceCreate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Create a new datasource.
    
    Requires authentication and ownership of the parent tileset.
    Automatically fetches metadata (bounds, center, zoom levels) from the data source
    and updates both the datasource record and the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id, type FROM tilesets WHERE id = %s",
                (datasource.tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to add datasource to this tileset")
            
            tileset_type = row[2]
            
            # Validate type matches tileset type
            if datasource.type == DatasourceType.pmtiles and tileset_type != "pmtiles":
                raise HTTPException(
                    status_code=400,
                    detail="PMTiles datasource can only be added to pmtiles type tileset"
                )
            if datasource.type == DatasourceType.cog and tileset_type != "raster":
                raise HTTPException(
                    status_code=400,
                    detail="COG datasource can only be added to raster type tileset"
                )
            
            metadata_json = json.dumps(datasource.metadata) if datasource.metadata else None
            
            if datasource.type == DatasourceType.pmtiles:
                # Check if datasource already exists for this tileset
                cur.execute(
                    "SELECT id FROM pmtiles_sources WHERE tileset_id = %s",
                    (datasource.tileset_id,),
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="Datasource already exists for this tileset"
                    )
                
                # Fetch PMTiles metadata
                pmtiles_meta = None
                source_bounds = None
                source_center = None
                source_min_zoom = None
                source_max_zoom = None
                tile_type = None
                tile_compression = None
                layers_json = None
                
                if is_pmtiles_available():
                    try:
                        pmtiles_meta = await get_pmtiles_metadata(datasource.url)
                        if pmtiles_meta:
                            source_bounds = pmtiles_meta.get("bounds")
                            source_center = pmtiles_meta.get("center")
                            source_min_zoom = pmtiles_meta.get("min_zoom")
                            source_max_zoom = pmtiles_meta.get("max_zoom")
                            tile_type = pmtiles_meta.get("tile_type")
                            tile_compression = pmtiles_meta.get("tile_compression")
                            layers = pmtiles_meta.get("layers", [])
                            if layers:
                                layers_json = json.dumps(layers)
                    except Exception as meta_error:
                        # Log but don't fail - metadata is optional
                        print(f"Warning: Could not fetch PMTiles metadata: {meta_error}")
                
                # Insert with metadata
                cur.execute(
                    """
                    INSERT INTO pmtiles_sources (
                        tileset_id, pmtiles_url, storage_provider, metadata,
                        tile_type, tile_compression, min_zoom, max_zoom,
                        bounds, center, layers
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, tileset_id, pmtiles_url, storage_provider, metadata,
                              created_at, updated_at, tile_type, tile_compression,
                              min_zoom, max_zoom, bounds, center, layers
                    """,
                    (
                        datasource.tileset_id,
                        datasource.url,
                        datasource.storage_provider.value,
                        metadata_json,
                        tile_type,
                        tile_compression,
                        source_min_zoom,
                        source_max_zoom,
                        json.dumps(source_bounds) if source_bounds else None,
                        json.dumps(source_center) if source_center else None,
                        layers_json,
                    ),
                )
                
                row = cur.fetchone()
                
                # Update parent tileset with bounds/center/zoom if available
                # Note: tilesets.bounds is GEOMETRY(POLYGON), center is GEOMETRY(POINT)
                if source_bounds or source_center or source_min_zoom is not None or source_max_zoom is not None:
                    update_parts = []
                    update_values = []
                    
                    if source_bounds and len(source_bounds) == 4:
                        # Convert [west, south, east, north] to PostGIS Polygon
                        west, south, east, north = source_bounds
                        update_parts.append("bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
                        update_values.extend([west, south, east, north])
                    
                    if source_center and len(source_center) >= 2:
                        # Convert [lon, lat, ...] to PostGIS Point
                        lon, lat = source_center[0], source_center[1]
                        update_parts.append("center = ST_SetSRID(ST_MakePoint(%s, %s), 4326)")
                        update_values.extend([lon, lat])
                    
                    if source_min_zoom is not None:
                        update_parts.append("min_zoom = %s")
                        update_values.append(source_min_zoom)
                    
                    if source_max_zoom is not None:
                        update_parts.append("max_zoom = %s")
                        update_values.append(source_max_zoom)
                    
                    if update_parts:
                        update_values.append(datasource.tileset_id)
                        cur.execute(
                            f"UPDATE tilesets SET {', '.join(update_parts)} WHERE id = %s",
                            update_values,
                        )
                
                conn.commit()
                
                return {
                    "id": str(row[0]),
                    "tileset_id": str(row[1]),
                    "type": "pmtiles",
                    "url": row[2],
                    "storage_provider": row[3],
                    "metadata": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                    "tile_type": row[7],
                    "tile_compression": row[8],
                    "min_zoom": row[9],
                    "max_zoom": row[10],
                    "bounds": row[11],
                    "center": row[12],
                    "layers": row[13],
                }
            
            else:  # COG
                # Check if datasource already exists for this tileset
                cur.execute(
                    "SELECT id FROM raster_sources WHERE tileset_id = %s",
                    (datasource.tileset_id,),
                )
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="Datasource already exists for this tileset"
                    )
                
                # Fetch COG metadata
                cog_info = None
                source_bounds = None
                source_center = None
                source_min_zoom = None
                source_max_zoom = None
                band_count = None
                band_descriptions_json = None
                native_crs = None
                
                if is_rasterio_available():
                    try:
                        cog_info = get_cog_info(datasource.url)
                        if cog_info:
                            # COG bounds are in [west, south, east, north] format
                            cog_bounds = cog_info.get("bounds")
                            if cog_bounds:
                                source_bounds = list(cog_bounds)
                                # Calculate center from bounds
                                source_center = [
                                    (cog_bounds[0] + cog_bounds[2]) / 2,  # lon
                                    (cog_bounds[1] + cog_bounds[3]) / 2,  # lat
                                    10  # default zoom
                                ]
                            source_min_zoom = cog_info.get("minzoom")
                            source_max_zoom = cog_info.get("maxzoom")
                            band_count = cog_info.get("count")
                            band_descriptions = cog_info.get("band_descriptions", [])
                            if band_descriptions:
                                band_descriptions_json = json.dumps(band_descriptions)
                            native_crs = cog_info.get("crs")
                    except Exception as meta_error:
                        # Log but don't fail - metadata is optional
                        print(f"Warning: Could not fetch COG info: {meta_error}")
                
                # Insert with metadata
                cur.execute(
                    """
                    INSERT INTO raster_sources (
                        tileset_id, cog_url, storage_provider, metadata,
                        band_count, band_descriptions, native_crs,
                        recommended_min_zoom, recommended_max_zoom,
                        bounds, center
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, tileset_id, cog_url, storage_provider, metadata,
                              created_at, updated_at, band_count, band_descriptions,
                              native_crs, recommended_min_zoom, recommended_max_zoom,
                              bounds, center
                    """,
                    (
                        datasource.tileset_id,
                        datasource.url,
                        datasource.storage_provider.value,
                        metadata_json,
                        band_count,
                        band_descriptions_json,
                        native_crs,
                        source_min_zoom,
                        source_max_zoom,
                        json.dumps(source_bounds) if source_bounds else None,
                        json.dumps(source_center) if source_center else None,
                    ),
                )
                
                row = cur.fetchone()
                
                # Update parent tileset with bounds/center/zoom if available
                # Note: tilesets.bounds is GEOMETRY(POLYGON), center is GEOMETRY(POINT)
                if source_bounds or source_center or source_min_zoom is not None or source_max_zoom is not None:
                    update_parts = []
                    update_values = []
                    
                    if source_bounds and len(source_bounds) == 4:
                        # Convert [west, south, east, north] to PostGIS Polygon
                        west, south, east, north = source_bounds
                        update_parts.append("bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
                        update_values.extend([west, south, east, north])
                    
                    if source_center and len(source_center) >= 2:
                        # Convert [lon, lat, ...] to PostGIS Point
                        lon, lat = source_center[0], source_center[1]
                        update_parts.append("center = ST_SetSRID(ST_MakePoint(%s, %s), 4326)")
                        update_values.extend([lon, lat])
                    
                    if source_min_zoom is not None:
                        update_parts.append("min_zoom = %s")
                        update_values.append(source_min_zoom)
                    
                    if source_max_zoom is not None:
                        update_parts.append("max_zoom = %s")
                        update_values.append(source_max_zoom)
                    
                    if update_parts:
                        update_values.append(datasource.tileset_id)
                        cur.execute(
                            f"UPDATE tilesets SET {', '.join(update_parts)} WHERE id = %s",
                            update_values,
                        )
                
                conn.commit()
                
                return {
                    "id": str(row[0]),
                    "tileset_id": str(row[1]),
                    "type": "cog",
                    "url": row[2],
                    "storage_provider": row[3],
                    "metadata": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                    "band_count": row[7],
                    "band_descriptions": row[8],
                    "native_crs": row[9],
                    "min_zoom": row[10],
                    "max_zoom": row[11],
                    "bounds": row[12],
                    "center": row[13],
                }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating datasource: {str(e)}")


@app.delete("/api/datasources/{datasource_id}", status_code=204)
def delete_datasource(
    datasource_id: str,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete a datasource.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Try PMTiles first
            cur.execute(
                """
                SELECT ps.id, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE ps.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[1]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to delete this datasource")
                
                cur.execute("DELETE FROM pmtiles_sources WHERE id = %s", (datasource_id,))
                conn.commit()
                return Response(status_code=204)
            
            # Try COG
            cur.execute(
                """
                SELECT rs.id, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE rs.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[1]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to delete this datasource")
                
                cur.execute("DELETE FROM raster_sources WHERE id = %s", (datasource_id,))
                conn.commit()
                return Response(status_code=204)
            
            raise HTTPException(status_code=404, detail="Datasource not found")
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting datasource: {str(e)}")


@app.post("/api/datasources/{datasource_id}/test")
async def test_datasource_connection(
    datasource_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth),
):
    """
    Test connection to a datasource.
    
    For PMTiles: Attempts to read metadata from the file.
    For COG: Attempts to read info from the file.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Try PMTiles first
            cur.execute(
                """
                SELECT ps.id, ps.pmtiles_url, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE ps.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[2]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to test this datasource")
                
                pmtiles_url = row[1]
                
                if not is_pmtiles_available():
                    return {
                        "status": "error",
                        "type": "pmtiles",
                        "message": "PMTiles service is not available",
                    }
                
                try:
                    metadata = await get_pmtiles_metadata(pmtiles_url)
                    return {
                        "status": "ok",
                        "type": "pmtiles",
                        "url": pmtiles_url,
                        "metadata": metadata,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "type": "pmtiles",
                        "url": pmtiles_url,
                        "message": str(e),
                    }
            
            # Try COG
            cur.execute(
                """
                SELECT rs.id, rs.cog_url, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE rs.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[2]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to test this datasource")
                
                cog_url = row[1]
                
                if not is_rasterio_available():
                    return {
                        "status": "error",
                        "type": "cog",
                        "message": "Raster service is not available",
                    }
                
                try:
                    info = get_cog_info(cog_url)
                    return {
                        "status": "ok",
                        "type": "cog",
                        "url": cog_url,
                        "info": info,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "type": "cog",
                        "url": cog_url,
                        "message": str(e),
                    }
            
            raise HTTPException(status_code=404, detail="Datasource not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing datasource: {str(e)}")


# ============================================================================
# Preview Page
# ============================================================================

PREVIEW_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>geo-base Tile Server</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.4.1/dist/maplibre-gl.css">
    <script src="https://unpkg.com/maplibre-gl@4.4.1/dist/maplibre-gl.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        .info-panel {
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1;
            max-width: 300px;
        }
        .info-panel h2 { margin: 0 0 10px 0; font-size: 18px; }
        .info-panel p { margin: 5px 0; font-size: 14px; color: #666; }
        .status { padding: 4px 8px; border-radius: 4px; font-size: 12px; display: inline-block; }
        .status.ok { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .layer-toggle { margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }
        .layer-toggle label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="info-panel">
        <h2>geo-base Tile Server</h2>
        <p>Version: 0.4.0</p>
        <p>DB Status: <span id="db-status" class="status">checking...</span></p>
        <div class="layer-toggle">
            <label>
                <input type="checkbox" id="toggle-features" checked>
                Show Features Layer
            </label>
        </div>
    </div>

    <script>
        // Check API health
        fetch('/api/health/db')
            .then(response => response.json())
            .then(data => {
                const el = document.getElementById('db-status');
                el.textContent = data.status === 'ok' ? 'Ã¢Å“â€ Connected' : 'Ã¢Å“â€“ ' + data.database;
                el.className = 'status ' + (data.status === 'ok' ? 'ok' : 'error');
            })
            .catch(() => {
                const el = document.getElementById('db-status');
                el.textContent = 'Ã¢Å“â€“ Error';
                el.className = 'status error';
            });

        // Initialize map
        const map = new maplibregl.Map({
            hash: true,
            container: 'map',
            style: {
                version: 8,
                sources: {
                    osm: {
                        type: 'raster',
                        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                        tileSize: 256,
                        attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
                    },
                    features: {
                        type: 'vector',
                        tiles: [window.location.origin + '/api/tiles/features/{z}/{x}/{y}.pbf'],
                        minzoom: 0,
                        maxzoom: 22,
                    },
                },
                layers: [
                    {
                        id: 'osm',
                        type: 'raster',
                        source: 'osm',
                    },
                    {
                        id: 'features-circle',
                        type: 'circle',
                        source: 'features',
                        'source-layer': 'features',
                        paint: {
                            'circle-radius': 8,
                            'circle-color': '#e74c3c',
                            'circle-stroke-width': 2,
                            'circle-stroke-color': '#ffffff',
                        },
                    },
                ],
            },
            center: [139.7, 35.68],
            zoom: 11,
        });

        map.addControl(new maplibregl.NavigationControl());

        // Layer toggles
        document.getElementById('toggle-features').addEventListener('change', (e) => {
            map.setLayoutProperty('features-circle', 'visibility', e.target.checked ? 'visible' : 'none');
        });

        // Popup on click
        map.on('click', 'features-circle', (e) => {
            const props = e.features[0].properties;
            let content = '<strong>' + (props.name || 'Feature') + '</strong>';
            if (props.properties) {
                try {
                    const p = JSON.parse(props.properties);
                    if (p.name_en) content += '<br>' + p.name_en;
                    if (p.type) content += '<br>Type: ' + p.type;
                } catch(e) {}
            }
            new maplibregl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(content)
                .addTo(map);
        });

        map.on('mouseenter', 'features-circle', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'features-circle', () => {
            map.getCanvas().style.cursor = '';
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def preview_page():
    """Tile preview page with MapLibre GL JS."""
    return PREVIEW_HTML


