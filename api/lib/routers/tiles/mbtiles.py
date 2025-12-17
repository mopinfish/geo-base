"""
MBTiles tile serving endpoints.

Note: This endpoint is primarily for local development.
In production, use database-backed tiles instead.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from lib.tiles import (
    FORMAT_MEDIA_TYPES,
    get_tile_from_mbtiles,
    get_mbtiles_metadata,
    get_cache_headers,
)


router = APIRouter(prefix="/mbtiles", tags=["tiles"])


@router.get("/{tileset_name}/{z}/{x}/{y}.{tile_format}")
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


@router.get("/{tileset_name}/metadata.json")
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
