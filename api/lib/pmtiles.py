"""
PMTiles tile serving utilities for geo-base API.

Features:
- HTTP Range Request based tile reading
- Support for both vector (MVT) and raster tiles
- Metadata extraction from PMTiles header
- TileJSON generation
"""

from typing import Any, Optional
from functools import lru_cache

# aiopmtiles for async PMTiles reading via HTTP
try:
    from aiopmtiles import Reader as PMTilesReader
    PMTILES_AVAILABLE = True
except ImportError:
    PMTILES_AVAILABLE = False
    PMTilesReader = None


# =============================================================================
# Constants
# =============================================================================

# PMTiles tile type mapping
PMTILES_TILE_TYPES = {
    0: "unknown",
    1: "mvt",      # Mapbox Vector Tile
    2: "png",
    3: "jpeg",
    4: "webp",
    5: "avif",
}

# PMTiles compression mapping
PMTILES_COMPRESSION = {
    0: "unknown",
    1: "none",
    2: "gzip",
    3: "br",       # Brotli
    4: "zstd",
}

# Media types for PMTiles tile types
PMTILES_MEDIA_TYPES = {
    "mvt": "application/vnd.mapbox-vector-tile",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "avif": "image/avif",
    "unknown": "application/octet-stream",
}

# Content-Encoding for compression types
PMTILES_CONTENT_ENCODING = {
    "gzip": "gzip",
    "br": "br",
    "zstd": "zstd",
    "none": None,
    "unknown": None,
}


# =============================================================================
# Availability Check
# =============================================================================


def is_pmtiles_available() -> bool:
    """Check if aiopmtiles is available."""
    return PMTILES_AVAILABLE


# =============================================================================
# PMTiles Tile Reading
# =============================================================================


async def get_pmtiles_tile(
    pmtiles_url: str,
    z: int,
    x: int,
    y: int,
) -> Optional[bytes]:
    """
    Get a tile from a PMTiles file via HTTP Range Request.
    
    Args:
        pmtiles_url: URL to the PMTiles file
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
        
    Returns:
        Tile data as bytes, or None if tile not found
        
    Raises:
        RuntimeError: If aiopmtiles is not available or error occurs
    """
    if not PMTILES_AVAILABLE:
        raise RuntimeError("aiopmtiles is not available")
    
    try:
        async with PMTilesReader(pmtiles_url) as reader:
            tile_data = await reader.get_tile(z, x, y)
            return tile_data
    except Exception as e:
        # Log error and return None for missing tiles
        if "not found" in str(e).lower() or "404" in str(e):
            return None
        raise RuntimeError(f"Error reading PMTiles tile: {str(e)}") from e


async def get_pmtiles_metadata(pmtiles_url: str) -> dict[str, Any]:
    """
    Get metadata from a PMTiles file.
    
    Args:
        pmtiles_url: URL to the PMTiles file
        
    Returns:
        Dictionary with PMTiles metadata
        
    Raises:
        RuntimeError: If aiopmtiles is not available or error occurs
    """
    if not PMTILES_AVAILABLE:
        raise RuntimeError("aiopmtiles is not available")
    
    try:
        async with PMTilesReader(pmtiles_url) as reader:
            # Get header info
            header = reader.header()
            
            # Get JSON metadata if available
            metadata = {}
            try:
                metadata = await reader.metadata()
            except Exception:
                pass
            
            # Parse tile type and compression
            tile_type_id = header.get("tile_type", 0)
            compression_id = header.get("tile_compression", 0)
            
            tile_type = PMTILES_TILE_TYPES.get(tile_type_id, "unknown")
            compression = PMTILES_COMPRESSION.get(compression_id, "unknown")
            
            # Extract bounds
            bounds = None
            if all(k in header for k in ["min_lon_e7", "min_lat_e7", "max_lon_e7", "max_lat_e7"]):
                bounds = [
                    header["min_lon_e7"] / 1e7,
                    header["min_lat_e7"] / 1e7,
                    header["max_lon_e7"] / 1e7,
                    header["max_lat_e7"] / 1e7,
                ]
            
            # Extract center
            center = None
            if all(k in header for k in ["center_lon_e7", "center_lat_e7", "center_zoom"]):
                center = [
                    header["center_lon_e7"] / 1e7,
                    header["center_lat_e7"] / 1e7,
                    header["center_zoom"],
                ]
            
            return {
                "tile_type": tile_type,
                "tile_compression": compression,
                "min_zoom": header.get("min_zoom", 0),
                "max_zoom": header.get("max_zoom", 22),
                "bounds": bounds,
                "center": center,
                "metadata": metadata,
                # Vector layer info (if available in metadata)
                "layers": metadata.get("vector_layers", []),
            }
            
    except Exception as e:
        raise RuntimeError(f"Error reading PMTiles metadata: {str(e)}") from e


def get_pmtiles_media_type(tile_type: str) -> str:
    """
    Get media type for a PMTiles tile type.
    
    Args:
        tile_type: Tile type string (mvt, png, jpeg, webp, avif)
        
    Returns:
        Media type string
    """
    return PMTILES_MEDIA_TYPES.get(tile_type, "application/octet-stream")


def get_pmtiles_content_encoding(compression: str) -> Optional[str]:
    """
    Get Content-Encoding header value for a compression type.
    
    Args:
        compression: Compression type string
        
    Returns:
        Content-Encoding value or None
    """
    return PMTILES_CONTENT_ENCODING.get(compression)


# =============================================================================
# PMTiles Cache Headers
# =============================================================================


def get_pmtiles_cache_headers(z: int, is_static: bool = True) -> dict[str, str]:
    """
    Generate cache headers for PMTiles responses.
    
    PMTiles are typically static files, so we can use longer cache times.
    
    Args:
        z: Zoom level
        is_static: Whether the PMTiles file is static
        
    Returns:
        Dictionary of cache headers
    """
    if is_static:
        # Static PMTiles: long cache (1 day for high zoom, 1 week for low zoom)
        if z >= 14:
            max_age = 86400  # 1 day
        elif z >= 8:
            max_age = 259200  # 3 days
        else:
            max_age = 604800  # 1 week
    else:
        # Dynamic: shorter cache
        max_age = 3600  # 1 hour
    
    return {
        "Cache-Control": f"public, max-age={max_age}",
        "Access-Control-Allow-Origin": "*",
    }


# =============================================================================
# TileJSON Generation for PMTiles
# =============================================================================


def generate_pmtiles_tilejson(
    tileset_id: str,
    name: str,
    base_url: str,
    tile_type: str = "mvt",
    min_zoom: int = 0,
    max_zoom: int = 22,
    bounds: Optional[list[float]] = None,
    center: Optional[list[float]] = None,
    description: Optional[str] = None,
    attribution: Optional[str] = None,
    layers: Optional[list[dict]] = None,
) -> dict[str, Any]:
    """
    Generate TileJSON for a PMTiles tileset.
    
    Args:
        tileset_id: Tileset identifier
        name: Tileset name
        base_url: Base URL for tile requests
        tile_type: Tile type (mvt, png, jpeg, webp)
        min_zoom: Minimum zoom level
        max_zoom: Maximum zoom level
        bounds: Tileset bounds [west, south, east, north]
        center: Tileset center [lng, lat, zoom]
        description: Optional description
        attribution: Optional attribution
        layers: Optional vector layer info
        
    Returns:
        TileJSON dictionary
    """
    # Determine file extension based on tile type
    extensions = {
        "mvt": "pbf",
        "png": "png",
        "jpeg": "jpg",
        "webp": "webp",
        "avif": "avif",
    }
    ext = extensions.get(tile_type, "pbf")
    
    tile_url = f"{base_url}/api/tiles/pmtiles/{tileset_id}/{{z}}/{{x}}/{{y}}.{ext}"
    
    tilejson = {
        "tilejson": "3.0.0",
        "name": name,
        "tiles": [tile_url],
        "minzoom": min_zoom,
        "maxzoom": max_zoom,
    }
    
    if bounds:
        tilejson["bounds"] = bounds
    else:
        tilejson["bounds"] = [-180, -85.051129, 180, 85.051129]
    
    if center:
        tilejson["center"] = center
    else:
        # Default center (Tokyo)
        tilejson["center"] = [139.7, 35.7, 10]
    
    if description:
        tilejson["description"] = description
    
    if attribution:
        tilejson["attribution"] = attribution
    
    # Add vector_layers for MVT tiles
    if tile_type == "mvt" and layers:
        tilejson["vector_layers"] = layers
    
    return tilejson
