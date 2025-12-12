"""
FastAPI Tile Server for geo-base.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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
    description="åœ°ç†ç©ºé–“ã‚¿ã‚¤ãƒ«é…ä¿¡API",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
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
# Health Check Endpoints
# ============================================================================


@app.get("/api/health")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "version": "0.3.0",
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
        max_size: Maximum dimension of preview
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
    
    # Limit max_size
    max_size = min(max_size, settings.raster_max_preview_size)
    
    # Get COG URL from database with access check
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rs.cog_url, t.is_public, t.user_id,
                       COALESCE((t.metadata->>'scale_min')::float, %s) as scale_min,
                       COALESCE((t.metadata->>'scale_max')::float, %s) as scale_max
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
        
        cog_url, is_public, owner_user_id, db_scale_min, db_scale_max = row
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
    
    # Use provided scale values or database defaults
    final_scale_min = scale_min if scale_min is not None else db_scale_min
    final_scale_max = scale_max if scale_max is not None else db_scale_max
    
    # Generate preview
    try:
        preview_data = get_raster_preview(
            cog_url=cog_url,
            indexes=band_indexes,
            scale_min=final_scale_min,
            scale_max=final_scale_max,
            img_format=normalized_format,
            max_size=max_size,
            colormap=colormap,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    headers = {
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
    }
    
    return Response(content=preview_data, media_type=media_type, headers=headers)


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

        # Convert datetime and UUID to string
        if tileset.get("id"):
            tileset["id"] = str(tileset["id"])
        if tileset.get("user_id"):
            tileset["user_id"] = str(tileset["user_id"])
        if tileset.get("created_at"):
            tileset["created_at"] = tileset["created_at"].isoformat()
        if tileset.get("updated_at"):
            tileset["updated_at"] = tileset["updated_at"].isoformat()

        return tileset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tileset: {str(e)}")


@app.get("/api/tilesets/{tileset_id}/tilejson.json")
def get_tileset_tilejson(
    tileset_id: str,
    request: Request,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """Get TileJSON for a specific tileset with access control."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, description, type, format, min_zoom, max_zoom,
                       attribution, is_public, user_id
                FROM tilesets
                WHERE id = %s
                """,
                (tileset_id,),
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_id}")

        (name, description, tile_type, tile_format,
         min_zoom, max_zoom, attribution, is_public, owner_user_id) = row
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

        # Determine tile URL based on type
        if tile_type == "vector":
            tile_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}"
        elif tile_type == "raster":
            tile_url = f"{base_url}/api/tiles/raster/{tileset_id}/{{z}}/{{x}}/{{y}}.{tile_format or 'png'}"
        elif tile_type == "pmtiles":
            # Check PMTiles source
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tile_type FROM pmtiles_sources WHERE tileset_id = %s",
                    (tileset_id,),
                )
                pmtiles_row = cur.fetchone()
            
            if pmtiles_row:
                ext = "pbf" if pmtiles_row[0] == "mvt" else (pmtiles_row[0] or "pbf")
                tile_url = f"{base_url}/api/tiles/pmtiles/{tileset_id}/{{z}}/{{x}}/{{y}}.{ext}"
            else:
                tile_url = f"{base_url}/api/tiles/pmtiles/{tileset_id}/{{z}}/{{x}}/{{y}}.pbf"
        else:
            tile_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}"

        return {
            "tilejson": "3.0.0",
            "name": name,
            "description": description,
            "tiles": [tile_url],
            "minzoom": min_zoom or 0,
            "maxzoom": max_zoom or 22,
            "attribution": attribution,
            "bounds": [-180, -85.051129, 180, 85.051129],
            "center": [139.7, 35.7, 10],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TileJSON: {str(e)}")



# ============================================================================
# Features API Endpoints
# ============================================================================


@app.get("/api/features")
def search_features(
    request: Request,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
    bbox: Optional[str] = Query(None, description="Bounding box: minx,miny,maxx,maxy"),
    layer: Optional[str] = Query(None, description="Layer name filter"),
    tileset_id: Optional[str] = Query(None, description="Tileset ID filter"),
    filter: Optional[str] = Query(None, description="Attribute filter (key=value)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of features"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Search and list features with optional filters.
    
    Supports:
    - Bounding box spatial filter
    - Layer name filter
    - Tileset ID filter
    - Attribute filter (simple key=value)
    - Pagination (limit/offset)
    """
    try:
        with conn.cursor() as cur:
            # Build query dynamically
            conditions = []
            params = []
            
            # Tileset access control
            if tileset_id:
                # Check tileset access
                cur.execute(
                    "SELECT is_public, user_id FROM tilesets WHERE id = %s",
                    (tileset_id,)
                )
                tileset_row = cur.fetchone()
                if tileset_row:
                    is_public, owner_user_id = tileset_row
                    owner_user_id = str(owner_user_id) if owner_user_id else None
                    if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
                        if not user:
                            raise HTTPException(
                                status_code=401,
                                detail="Authentication required to access features from this tileset",
                                headers={"WWW-Authenticate": "Bearer"},
                            )
                        raise HTTPException(
                            status_code=403,
                            detail="You do not have permission to access features from this tileset"
                        )
                conditions.append("f.tileset_id = %s")
                params.append(tileset_id)
            else:
                # Only show features from public tilesets or user's tilesets
                if user:
                    conditions.append("(t.is_public = true OR t.user_id = %s)")
                    params.append(user.id)
                else:
                    conditions.append("t.is_public = true")
            
            # Bounding box filter
            if bbox:
                try:
                    minx, miny, maxx, maxy = map(float, bbox.split(","))
                    conditions.append(
                        "ST_Intersects(f.geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                    )
                    params.extend([minx, miny, maxx, maxy])
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid bbox format. Use: minx,miny,maxx,maxy"
                    )
            
            # Layer filter
            if layer:
                conditions.append("f.layer_name = %s")
                params.append(layer)
            
            # Attribute filter (simple key=value)
            if filter:
                if "=" in filter:
                    key, value = filter.split("=", 1)
                    conditions.append("f.properties->>%s = %s")
                    params.extend([key.strip(), value.strip()])
            
            # Build WHERE clause
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Count query
            count_sql = f"""
                SELECT COUNT(*)
                FROM features f
                LEFT JOIN tilesets t ON f.tileset_id = t.id
                WHERE {where_clause}
            """
            cur.execute(count_sql, params)
            total_count = cur.fetchone()[0]
            
            # Main query
            sql = f"""
                SELECT 
                    f.id,
                    f.tileset_id,
                    f.layer_name,
                    f.properties,
                    ST_AsGeoJSON(f.geom)::json as geometry,
                    f.created_at,
                    f.updated_at
                FROM features f
                LEFT JOIN tilesets t ON f.tileset_id = t.id
                WHERE {where_clause}
                ORDER BY f.created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            cur.execute(sql, params)
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        
        # Format features as GeoJSON
        features = []
        for row in rows:
            feature_dict = dict(zip(columns, row))
            feature = {
                "type": "Feature",
                "id": str(feature_dict["id"]),
                "geometry": feature_dict["geometry"],
                "properties": {
                    **(feature_dict["properties"] or {}),
                    "layer_name": feature_dict["layer_name"],
                    "tileset_id": str(feature_dict["tileset_id"]) if feature_dict["tileset_id"] else None,
                    "created_at": feature_dict["created_at"].isoformat() if feature_dict["created_at"] else None,
                    "updated_at": feature_dict["updated_at"].isoformat() if feature_dict["updated_at"] else None,
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "count": len(features),
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "query": {
                "bbox": bbox,
                "layer": layer,
                "tileset_id": tileset_id,
                "filter": filter,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching features: {str(e)}")


@app.get("/api/features/layers")
def list_feature_layers(
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
    tileset_id: Optional[str] = Query(None, description="Filter by tileset ID"),
):
    """
    List available feature layers.
    
    Returns distinct layer names with feature counts.
    """
    try:
        with conn.cursor() as cur:
            conditions = []
            params = []
            
            if tileset_id:
                conditions.append("f.tileset_id = %s")
                params.append(tileset_id)
            
            # Access control
            if user:
                conditions.append("(t.is_public = true OR t.user_id = %s)")
                params.append(user.id)
            else:
                conditions.append("t.is_public = true")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            sql = f"""
                SELECT 
                    f.layer_name,
                    COUNT(*) as feature_count,
                    f.tileset_id,
                    t.name as tileset_name
                FROM features f
                LEFT JOIN tilesets t ON f.tileset_id = t.id
                WHERE {where_clause}
                GROUP BY f.layer_name, f.tileset_id, t.name
                ORDER BY f.layer_name
            """
            cur.execute(sql, params)
            rows = cur.fetchall()
        
        layers = [
            {
                "layer_name": row[0],
                "feature_count": row[1],
                "tileset_id": str(row[2]) if row[2] else None,
                "tileset_name": row[3],
            }
            for row in rows
        ]
        
        return {
            "layers": layers,
            "count": len(layers),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing layers: {str(e)}")


@app.get("/api/features/{feature_id}")
def get_feature(
    feature_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get a specific feature by ID.
    
    Returns the feature as a GeoJSON Feature object.
    """
    try:
        with conn.cursor() as cur:
            # Get feature with tileset info for access control
            cur.execute(
                """
                SELECT 
                    f.id,
                    f.tileset_id,
                    f.layer_name,
                    f.properties,
                    ST_AsGeoJSON(f.geom)::json as geometry,
                    f.created_at,
                    f.updated_at,
                    t.is_public,
                    t.user_id as tileset_user_id
                FROM features f
                LEFT JOIN tilesets t ON f.tileset_id = t.id
                WHERE f.id = %s
                """,
                (feature_id,)
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Feature not found: {feature_id}")
        
        columns = ["id", "tileset_id", "layer_name", "properties", "geometry", 
                   "created_at", "updated_at", "is_public", "tileset_user_id"]
        feature_dict = dict(zip(columns, row))
        
        # Check access via tileset
        is_public = feature_dict.get("is_public", True)
        owner_user_id = str(feature_dict["tileset_user_id"]) if feature_dict["tileset_user_id"] else None
        tileset_id = str(feature_dict["tileset_id"]) if feature_dict["tileset_id"] else None
        
        if tileset_id and not check_tileset_access(tileset_id, is_public, owner_user_id, user):
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
        
        # Format as GeoJSON Feature
        return {
            "type": "Feature",
            "id": str(feature_dict["id"]),
            "geometry": feature_dict["geometry"],
            "properties": {
                **(feature_dict["properties"] or {}),
                "layer_name": feature_dict["layer_name"],
                "tileset_id": str(feature_dict["tileset_id"]) if feature_dict["tileset_id"] else None,
                "created_at": feature_dict["created_at"].isoformat() if feature_dict["created_at"] else None,
                "updated_at": feature_dict["updated_at"].isoformat() if feature_dict["updated_at"] else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting feature: {str(e)}")



# ============================================================================
# Preview Page
# ============================================================================


PREVIEW_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>geo-base Tile Preview</title>
    <script src="https://unpkg.com/maplibre-gl@^4.0/dist/maplibre-gl.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@^4.0/dist/maplibre-gl.css" />
    <style>
        body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        .info-panel {
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 1;
            max-width: 320px;
        }
        .info-panel h3 { margin: 0 0 10px 0; font-size: 18px; }
        .info-panel p { margin: 5px 0; font-size: 14px; color: #666; }
        .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .status.ok { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.loading { background: #fff3cd; color: #856404; }
        .endpoints { margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; }
        .endpoints h4 { margin: 0 0 8px 0; font-size: 14px; }
        .endpoints a { display: block; font-size: 12px; color: #007bff; margin: 4px 0; text-decoration: none; }
        .endpoints a:hover { text-decoration: underline; }
        .layer-toggle { margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; }
        .layer-toggle h4 { margin: 0 0 8px 0; font-size: 14px; }
        .layer-toggle label { display: block; font-size: 12px; margin: 4px 0; cursor: pointer; }
    </style>
</head>
<body>
    <div class="info-panel">
        <h3>ðŸ—ºï¸ geo-base Tile Server</h3>
        <p>API: <span id="api-status" class="status loading">checking...</span></p>
        <p>DB: <span id="db-status" class="status loading">checking...</span></p>
        <p>PMTiles: <span id="pmtiles-status" class="status loading">checking...</span></p>
        <p>Auth: <span id="auth-status" class="status loading">checking...</span></p>
        <div class="endpoints">
            <h4>API Endpoints</h4>
            <a href="/api/health" target="_blank">/api/health</a>
            <a href="/api/health/db" target="_blank">/api/health/db</a>
            <a href="/api/tilesets" target="_blank">/api/tilesets</a>
            <a href="/api/tiles/features/tilejson.json" target="_blank">/api/tiles/features/tilejson.json</a>
            <a href="/api/auth/status" target="_blank">/api/auth/status</a>
        </div>
        <div class="layer-toggle">
            <h4>Layers</h4>
            <label><input type="checkbox" id="toggle-features" checked> Vector Features</label>
        </div>
    </div>
    <div id="map"></div>
    <script>
        // Check API health
        fetch('/api/health')
            .then(res => res.json())
            .then(data => {
                const el = document.getElementById('api-status');
                el.textContent = data.status === 'ok' ? 'âœ” OK' : 'âœ— Error';
                el.className = 'status ' + (data.status === 'ok' ? 'ok' : 'error');
                
                // Check PMTiles availability
                const pmtilesEl = document.getElementById('pmtiles-status');
                pmtilesEl.textContent = data.pmtiles_available ? 'âœ” Available' : 'âœ— Not installed';
                pmtilesEl.className = 'status ' + (data.pmtiles_available ? 'ok' : 'error');
                
                // Check Auth configuration
                const authEl = document.getElementById('auth-status');
                authEl.textContent = data.auth_configured ? 'âœ” Configured' : 'âœ— Not configured';
                authEl.className = 'status ' + (data.auth_configured ? 'ok' : 'error');
            })
            .catch(() => {
                const el = document.getElementById('api-status');
                el.textContent = 'âœ— Error';
                el.className = 'status error';
            });

        // Check DB health
        fetch('/api/health/db')
            .then(res => res.json())
            .then(data => {
                const el = document.getElementById('db-status');
                el.textContent = data.status === 'ok' ? 'âœ” Connected' : 'âœ— ' + data.database;
                el.className = 'status ' + (data.status === 'ok' ? 'ok' : 'error');
            })
            .catch(() => {
                const el = document.getElementById('db-status');
                el.textContent = 'âœ— Error';
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


