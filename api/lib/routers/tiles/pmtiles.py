"""
PMTiles tile serving endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from lib.database import get_connection
from lib.pmtiles import (
    is_pmtiles_available,
    get_pmtiles_tile,
    get_pmtiles_metadata,
    get_pmtiles_media_type,
    get_pmtiles_content_encoding,
    get_pmtiles_cache_headers,
    generate_pmtiles_tilejson,
)
from lib.cache import get_cached_tileset_info, cache_tileset_info
from lib.auth import User, get_current_user, check_tileset_access


router = APIRouter(prefix="/pmtiles", tags=["tiles"])


def get_base_url(request: Request) -> str:
    """Get base URL from request headers."""
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    
    return str(request.base_url).rstrip("/")


@router.get("/{tileset_id}/{z}/{x}/{y}.{tile_format}")
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
    Get a tile from a PMTiles archive.
    
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
    if not is_pmtiles_available():
        raise HTTPException(
            status_code=501,
            detail="PMTiles service is not available. Install aiopmtiles: pip install aiopmtiles"
        )
    
    # Try to get tileset info from cache first
    cache_key = f"pmtiles:{tileset_id}"
    cached_info = get_cached_tileset_info(cache_key)
    
    if cached_info:
        pmtiles_url = cached_info["pmtiles_url"]
        tile_type = cached_info["tile_type"]
        compression = cached_info["compression"]
        min_zoom = cached_info["min_zoom"]
        max_zoom = cached_info["max_zoom"]
        is_public = cached_info["is_public"]
        owner_user_id = cached_info["owner_user_id"]
    else:
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
            
            # Cache the tileset info
            cache_tileset_info(cache_key, {
                "pmtiles_url": pmtiles_url,
                "tile_type": tile_type,
                "compression": compression,
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
    
    # Validate zoom level
    if min_zoom is not None and z < min_zoom:
        raise HTTPException(status_code=404, detail=f"Zoom level {z} below minimum {min_zoom}")
    if max_zoom is not None and z > max_zoom:
        raise HTTPException(status_code=404, detail=f"Zoom level {z} above maximum {max_zoom}")
    
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


@router.get("/{tileset_id}/tilejson.json")
async def get_pmtiles_tilejson_endpoint(
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


@router.get("/{tileset_id}/metadata")
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
