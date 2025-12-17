"""
Raster tile serving endpoints (COG-backed).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from lib.config import get_settings
from lib.database import get_connection
from lib.raster_tiles import (
    is_rasterio_available,
    get_raster_tile_async,
    get_raster_preview_async,
    get_cog_info,
    get_cog_statistics,
    generate_raster_tilejson,
    get_raster_cache_headers,
    get_raster_media_type,
    validate_tile_format,
)
from lib.cache import get_cached_tileset_info, cache_tileset_info
from lib.auth import User, get_current_user, check_tileset_access


router = APIRouter(prefix="/raster", tags=["tiles"])
settings = get_settings()


def get_base_url(request: Request) -> str:
    """Get base URL from request headers."""
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    
    return str(request.base_url).rstrip("/")


@router.get("/{tileset_id}/{z}/{x}/{y}.{tile_format}")
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
        tileset_id: Tileset ID
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
            detail="Raster tile service is not available. Install rasterio and rio-tiler."
        )
    
    # Validate format
    try:
        normalized_format = validate_tile_format(tile_format)
        media_type = get_raster_media_type(normalized_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Try to get tileset info from cache first
    cache_key = f"raster:{tileset_id}"
    cached_info = get_cached_tileset_info(cache_key)
    
    if cached_info:
        cog_url = cached_info["cog_url"]
        min_zoom = cached_info["min_zoom"]
        max_zoom = cached_info["max_zoom"]
        is_public = cached_info["is_public"]
        owner_user_id = cached_info["owner_user_id"]
    else:
        # Get COG URL from database with access check
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rs.cog_url, rs.recommended_min_zoom, rs.recommended_max_zoom,
                           t.is_public, t.user_id
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
            
            cog_url, min_zoom, max_zoom, is_public, owner_user_id = row
            owner_user_id = str(owner_user_id) if owner_user_id else None
            
            # Cache the tileset info
            cache_tileset_info(cache_key, {
                "cog_url": cog_url,
                "min_zoom": min_zoom,
                "max_zoom": max_zoom,
                "is_public": is_public,
                "owner_user_id": owner_user_id,
            })
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")
    
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
    
    # Parse band indexes
    band_indexes = None
    if indexes:
        try:
            band_indexes = tuple(int(i.strip()) for i in indexes.split(","))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid band indexes format")
    
    # NOTE: scale_min/scale_max are passed as-is (None allowed)
    # get_raster_tile_async will auto-detect appropriate scaling:
    # - RGB images (3+ bands) or uint8 data: 0-255
    # - Single-band or other types: use settings defaults
    
    # Generate tile
    try:
        tile_data = await get_raster_tile_async(
            cog_url=cog_url,
            z=z,
            x=x,
            y=y,
            tile_size=256,
            indexes=band_indexes,
            scale_min=scale_min,
            scale_max=scale_max,
            img_format=normalized_format,
            colormap=colormap,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")
    
    if tile_data is None:
        raise HTTPException(status_code=404, detail="Tile not found or out of bounds")
    
    # Build response headers
    headers = get_raster_cache_headers(z, is_static=True)
    
    return Response(content=tile_data, media_type=media_type, headers=headers)


@router.get("/{tileset_id}/tilejson.json")
def get_raster_tilejson_endpoint(
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
    if not is_rasterio_available():
        raise HTTPException(
            status_code=501,
            detail="Raster service is not available."
        )
    
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.name, t.description, t.format, t.attribution, t.is_public, t.user_id,
                       t.min_zoom, t.max_zoom,
                       ST_XMin(t.bounds), ST_YMin(t.bounds), ST_XMax(t.bounds), ST_YMax(t.bounds),
                       ST_X(t.center), ST_Y(t.center)
                FROM tilesets t
                WHERE t.id = %s AND t.type = 'raster'
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Raster tileset not found: {tileset_id}")
        
        (name, description, tile_format, attribution, is_public, owner_user_id,
         min_zoom, max_zoom, xmin, ymin, xmax, ymax, center_x, center_y) = row
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TileJSON: {str(e)}")


@router.get("/{tileset_id}/preview")
async def get_raster_preview(
    tileset_id: str,
    format: str = Query("png", description="Output format (png, jpg, webp)"),
    max_size: int = Query(512, ge=64, le=2048, description="Maximum dimension in pixels"),
    bands: str = Query(None, description="Comma-separated band indexes (e.g., '1,2,3')"),
    scale_min: float = Query(None, description="Minimum value for rescaling"),
    scale_max: float = Query(None, description="Maximum value for rescaling"),
    colormap: str = Query(None, description="Colormap name for single-band visualization"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Generate a preview image of the entire raster dataset.
    
    Args:
        tileset_id: Tileset ID
        format: Output format (png, jpg, webp)
        max_size: Maximum dimension in pixels (default: 512)
        bands: Comma-separated band indexes (e.g., '1,2,3' for RGB)
        scale_min: Minimum value for rescaling
        scale_max: Maximum value for rescaling
        colormap: Colormap name for single-band visualization
    """
    if not is_rasterio_available():
        raise HTTPException(
            status_code=503,
            detail="Raster preview service is not available"
        )
    
    try:
        # Validate format
        normalized_format = validate_tile_format(format)
        media_type = get_raster_media_type(normalized_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    try:
        with conn.cursor() as cur:
            # Get tileset and COG URL
            cur.execute(
                """
                SELECT t.id, t.is_public, t.user_id,
                       rs.cog_url, rs.recommended_min_zoom, rs.recommended_max_zoom
                FROM tilesets t
                LEFT JOIN raster_sources rs ON rs.tileset_id = t.id
                WHERE t.id = %s AND t.type = 'raster'
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Raster tileset not found")
            
            is_public = row[1]
            owner_id = str(row[2]) if row[2] else None
            cog_url = row[3]
            
            # Check access
            if not check_tileset_access(tileset_id, is_public, owner_id, user):
                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                raise HTTPException(status_code=403, detail="Access denied")
            
            if not cog_url:
                raise HTTPException(
                    status_code=404,
                    detail="No COG datasource configured for this tileset"
                )
        
        # Parse band indexes
        indexes = None
        if bands:
            try:
                indexes = tuple(int(b.strip()) for b in bands.split(","))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid band indexes")
        
        # NOTE: scale_min/scale_max are passed as-is (None allowed)
        # get_raster_preview_async will auto-detect appropriate scaling
        
        # Generate preview
        preview_data = await get_raster_preview_async(
            cog_url=cog_url,
            max_size=max_size,
            indexes=indexes,
            scale_min=scale_min,
            scale_max=scale_max,
            img_format=normalized_format,
            colormap=colormap,
        )
        
        return Response(
            content=preview_data,
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")


@router.get("/{tileset_id}/info")
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


@router.get("/{tileset_id}/statistics")
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
