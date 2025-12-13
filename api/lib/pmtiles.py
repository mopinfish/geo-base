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

# PMTiles tile type mapping (by enum value)
PMTILES_TILE_TYPES = {
    0: "unknown",
    1: "mvt",      # Mapbox Vector Tile
    2: "png",
    3: "jpeg",
    4: "webp",
    5: "avif",
}

# PMTiles compression mapping (by enum value)
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
    
    aiopmtiles Reader API:
    - await src.metadata(): dict - PMTiles JSON metadata
    - src.bounds: tuple - (west, south, east, north)
    - src.center: tuple - (lon, lat, zoom)
    - src.minzoom: int - Minimum zoom level
    - src.maxzoom: int - Maximum zoom level
    - src.is_vector: bool - True if vector tiles
    - src.tile_type: TileType enum - Tile type
    - src.tile_compression: Compression enum - Compression type
    
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
        async with PMTilesReader(pmtiles_url) as src:
            # Get JSON metadata (it's an async method)
            metadata = {}
            try:
                metadata = await src.metadata()
                if not isinstance(metadata, dict):
                    metadata = {}
            except Exception:
                pass
            
            # Get tile type - it's an Enum, extract .value
            tile_type_str = "unknown"
            try:
                tile_type_enum = src.tile_type
                # Handle Enum - get the integer value
                if hasattr(tile_type_enum, 'value'):
                    tile_type_id = tile_type_enum.value
                else:
                    tile_type_id = int(tile_type_enum)
                tile_type_str = PMTILES_TILE_TYPES.get(tile_type_id, "unknown")
            except Exception:
                # Fallback: infer from is_vector
                try:
                    tile_type_str = "mvt" if src.is_vector else "png"
                except Exception:
                    pass
            
            # Get compression - it's an Enum, extract .value
            compression_str = "unknown"
            try:
                comp_enum = src.tile_compression
                # Handle Enum - get the integer value
                if hasattr(comp_enum, 'value'):
                    comp_id = comp_enum.value
                else:
                    comp_id = int(comp_enum)
                compression_str = PMTILES_COMPRESSION.get(comp_id, "unknown")
            except Exception:
                pass
            
            # Get bounds - it's a tuple
            bounds = None
            try:
                if src.bounds:
                    b = src.bounds
                    if isinstance(b, (list, tuple)) and len(b) >= 4:
                        bounds = list(b[:4])
            except Exception:
                pass
            
            # Get center - it's a tuple (lon, lat, zoom)
            center = None
            try:
                if src.center:
                    c = src.center
                    if isinstance(c, (list, tuple)) and len(c) >= 3:
                        center = list(c[:3])
            except Exception:
                pass
            
            # Get zoom levels
            min_zoom = 0
            max_zoom = 22
            try:
                if hasattr(src, 'minzoom') and src.minzoom is not None:
                    min_zoom = int(src.minzoom)
                if hasattr(src, 'maxzoom') and src.maxzoom is not None:
                    max_zoom = int(src.maxzoom)
            except Exception:
                pass
            
            return {
                "tile_type": tile_type_str,
                "tile_compression": compression_str,
                "min_zoom": min_zoom,
                "max_zoom": max_zoom,
                "bounds": bounds,
                "center": center,
                "metadata": metadata,
                # Vector layer info (if available in metadata)
                "layers": metadata.get("vector_layers", []) if isinstance(metadata, dict) else [],
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
    tileset_name: str,
    metadata: dict[str, Any],
    base_url: str,
    description: str = "",
    attribution: str = "",
) -> dict[str, Any]:
    """
    Generate TileJSON for a PMTiles tileset.
    
    Args:
        tileset_id: Tileset ID
        tileset_name: Human-readable tileset name
        metadata: PMTiles metadata from get_pmtiles_metadata()
        base_url: Base URL for tile requests
        description: Optional tileset description
        attribution: Optional attribution string
        
    Returns:
        TileJSON dictionary
    """
    tile_type = metadata.get("tile_type", "mvt")
    
    # Determine format extension
    format_ext = {
        "mvt": "pbf",
        "png": "png",
        "jpeg": "jpg",
        "webp": "webp",
        "avif": "avif",
    }.get(tile_type, "pbf")
    
    # Build tile URL template
    tile_url = f"{base_url}/api/tiles/pmtiles/{tileset_id}/{{z}}/{{x}}/{{y}}.{format_ext}"
    
    tilejson = {
        "tilejson": "3.0.0",
        "name": tileset_name,
        "description": description,
        "version": "1.0.0",
        "attribution": attribution,
        "scheme": "xyz",
        "tiles": [tile_url],
        "minzoom": metadata.get("min_zoom", 0),
        "maxzoom": metadata.get("max_zoom", 22),
    }
    
    # Add bounds if available
    bounds = metadata.get("bounds")
    if bounds:
        tilejson["bounds"] = bounds
    
    # Add center if available
    center = metadata.get("center")
    if center:
        tilejson["center"] = center
    
    # Add vector layers if available (for MVT)
    layers = metadata.get("layers", [])
    if layers and tile_type == "mvt":
        tilejson["vector_layers"] = layers
    
    return tilejson
