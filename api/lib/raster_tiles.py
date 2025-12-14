
"""
Raster tile serving utilities for geo-base API.

Features:
- Cloud Optimized GeoTIFF (COG) tile generation
- Dynamic tile rendering with rio-tiler
- Multiple output formats (PNG, JPEG, WebP)
- Band selection and rescaling
- Preview image generation
"""

import asyncio
from functools import lru_cache
from io import BytesIO
from typing import Any, Optional

# Note: rio-tiler may not work in Vercel serverless due to GDAL dependencies
# If deployment fails, consider using AWS Lambda with Docker image
try:
    from rio_tiler.io import Reader as COGReader
    from rio_tiler.profiles import img_profiles
    from rio_tiler.errors import TileOutsideBounds
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    COGReader = None
    img_profiles = None
    TileOutsideBounds = Exception

# =============================================================================
# Constants
# =============================================================================

RASTER_MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}

DEFAULT_TILE_SIZE = 256
DEFAULT_SCALE_MIN = 0
DEFAULT_SCALE_MAX = 3000  # Typical for Sentinel-2 reflectance values
DEFAULT_RESAMPLING = "bilinear"

# =============================================================================
# Availability Check
# =============================================================================


def is_rasterio_available() -> bool:
    """Check if rasterio/rio-tiler is available."""
    return RASTERIO_AVAILABLE


# =============================================================================
# COG Tile Generation
# =============================================================================


def get_raster_tile(
    cog_url: str,
    z: int,
    x: int,
    y: int,
    indexes: Optional[tuple[int, ...]] = None,
    scale_min: float = DEFAULT_SCALE_MIN,
    scale_max: float = DEFAULT_SCALE_MAX,
    img_format: str = "png",
    tile_size: int = DEFAULT_TILE_SIZE,
    resampling: str = DEFAULT_RESAMPLING,
    colormap: Optional[str] = None,
) -> Optional[bytes]:
    """
    Generate a raster tile from a Cloud Optimized GeoTIFF.
    
    Args:
        cog_url: URL or path to the COG file
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
        indexes: Band indexes to read (e.g., (1, 2, 3) for RGB)
        scale_min: Minimum value for rescaling
        scale_max: Maximum value for rescaling
        img_format: Output image format (png, jpg, webp)
        tile_size: Output tile size in pixels
        resampling: Resampling method (bilinear, nearest, cubic, etc.)
        colormap: Optional colormap name for single-band visualization
        
    Returns:
        Tile image data as bytes, or None if tile is outside bounds
    """
    if not RASTERIO_AVAILABLE:
        raise RuntimeError("rio-tiler is not available. Install with: pip install rio-tiler")
    
    try:
        with COGReader(cog_url) as cog:
            # Check if tile exists within COG bounds
            if not cog.tile_exists(x, y, z):
                return None
            
            # Read tile data
            imgdata = cog.tile(
                x, y, z,
                indexes=indexes,
                tilesize=tile_size,
                resampling_method=resampling,
            )
            
            # Rescale values to 0-255
            imgdata.rescale(((scale_min, scale_max),))
            
            # Get render options
            render_options = {}
            if img_format.lower() in ("png", "webp"):
                render_options = img_profiles.get("png") if img_format.lower() == "png" else {}
            elif img_format.lower() in ("jpg", "jpeg"):
                render_options = img_profiles.get("jpeg") or {"quality": 85}
            
            # Apply colormap if specified for single-band
            if colormap and imgdata.count == 1:
                try:
                    from matplotlib import cm
                    render_options["colormap"] = cm.get_cmap(colormap)
                except ImportError:
                    pass
            
            # Render to bytes
            return imgdata.render(
                img_format=img_format.upper().replace("JPG", "JPEG"),
                **render_options
            )
            
    except TileOutsideBounds:
        return None
    except Exception as e:
        raise RuntimeError(f"Error generating raster tile: {str(e)}") from e


async def get_raster_tile_async(
    cog_url: str,
    z: int,
    x: int,
    y: int,
    **kwargs,
) -> Optional[bytes]:
    """
    Async wrapper for get_raster_tile.
    
    Runs the tile generation in a thread pool to avoid blocking.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_raster_tile(cog_url, z, x, y, **kwargs)
    )


# =============================================================================
# Preview Image Generation
# =============================================================================


def get_raster_preview(
    cog_url: str,
    max_size: int = 512,
    indexes: Optional[tuple[int, ...]] = None,
    scale_min: float = DEFAULT_SCALE_MIN,
    scale_max: float = DEFAULT_SCALE_MAX,
    img_format: str = "png",
    colormap: Optional[str] = None,
) -> bytes:
    """
    Generate a preview image from a COG.
    
    Args:
        cog_url: URL or path to the COG file
        max_size: Maximum width/height of the preview
        indexes: Band indexes to read
        scale_min: Minimum value for rescaling
        scale_max: Maximum value for rescaling
        img_format: Output image format
        colormap: Optional colormap name
        
    Returns:
        Preview image as bytes
    """
    if not RASTERIO_AVAILABLE:
        raise RuntimeError("rio-tiler is not available")
    
    try:
        with COGReader(cog_url) as cog:
            imgdata = cog.preview(
                indexes=indexes,
                max_size=max_size,
            )
            
            imgdata.rescale(((scale_min, scale_max),))
            
            render_options = {}
            if img_format.lower() in ("png", "webp"):
                render_options = img_profiles.get("png") if img_format.lower() == "png" else {}
            elif img_format.lower() in ("jpg", "jpeg"):
                render_options = img_profiles.get("jpeg") or {"quality": 85}
            
            if colormap and imgdata.count == 1:
                render_options["colormap"] = colormap
            
            return imgdata.render(
                img_format=img_format.upper().replace("JPG", "JPEG"),
                **render_options
            )
            
    except Exception as e:
        raise RuntimeError(f"Error generating preview: {str(e)}") from e


# =============================================================================
# Part/Crop Image Generation
# =============================================================================


def get_raster_part(
    cog_url: str,
    bbox: tuple[float, float, float, float],
    indexes: Optional[tuple[int, ...]] = None,
    scale_min: float = DEFAULT_SCALE_MIN,
    scale_max: float = DEFAULT_SCALE_MAX,
    img_format: str = "png",
    max_size: int = 1024,
    dst_crs: Optional[str] = None,
) -> bytes:
    """
    Generate an image for a specific bounding box from a COG.
    
    Args:
        cog_url: URL or path to the COG file
        bbox: Bounding box (west, south, east, north) in WGS84
        indexes: Band indexes to read
        scale_min: Minimum value for rescaling
        scale_max: Maximum value for rescaling
        img_format: Output image format
        max_size: Maximum output size
        dst_crs: Target CRS (default: use source CRS)
        
    Returns:
        Part image as bytes
    """
    if not RASTERIO_AVAILABLE:
        raise RuntimeError("rio-tiler is not available")
    
    try:
        with COGReader(cog_url) as cog:
            kwargs = {
                "bbox": bbox,
                "indexes": indexes,
                "max_size": max_size,
            }
            
            if dst_crs:
                kwargs["dst_crs"] = dst_crs
            
            imgdata = cog.part(**kwargs)
            imgdata.rescale(((scale_min, scale_max),))
            
            render_options = {}
            if img_format.lower() in ("png", "webp"):
                render_options = img_profiles.get("png") if img_format.lower() == "png" else {}
            elif img_format.lower() in ("jpg", "jpeg"):
                render_options = img_profiles.get("jpeg") or {"quality": 85}
            
            return imgdata.render(
                img_format=img_format.upper().replace("JPG", "JPEG"),
                **render_options
            )
            
    except Exception as e:
        raise RuntimeError(f"Error generating part image: {str(e)}") from e


# =============================================================================
# COG Metadata
# =============================================================================


def get_cog_info(cog_url: str) -> dict[str, Any]:
    """
    Get metadata information from a COG.
    
    Args:
        cog_url: URL or path to the COG file
        
    Returns:
        Dictionary with COG metadata including WGS84 bounds
    """
    if not RASTERIO_AVAILABLE:
        raise RuntimeError("rio-tiler is not available")
    
    try:
        from rasterio.crs import CRS as RasterioCRS
        
        with COGReader(cog_url) as cog:
            info = cog.info()
            
            # Get WGS84 bounds using get_geographic_bounds method
            # This converts native CRS bounds to WGS84 (EPSG:4326)
            geographic_bounds = None
            try:
                wgs84 = RasterioCRS.from_epsg(4326)
                geographic_bounds = cog.get_geographic_bounds(wgs84)
            except Exception as e:
                print(f"Warning: Could not get geographic bounds: {e}")
            
            # Build result with safe attribute access
            result = {
                "bounds": geographic_bounds,  # WGS84 bounds for web maps
                "native_bounds": getattr(info, 'bounds', None),  # Original CRS bounds
                "crs": str(info.crs) if getattr(info, 'crs', None) else None,
                "band_metadata": getattr(info, 'band_metadata', []),
                "band_descriptions": getattr(info, 'band_descriptions', []),
                "dtype": getattr(info, 'dtype', None),
                "nodata_type": getattr(info, 'nodata_type', None),
                "colorinterp": getattr(info, 'colorinterp', None),
                "count": getattr(info, 'count', None),
                "width": getattr(info, 'width', None),
                "height": getattr(info, 'height', None),
                "driver": getattr(info, 'driver', None),
            }
            
            # minzoom/maxzoom may not exist in all rio-tiler versions
            # Try to get from info, otherwise calculate from the reader
            if hasattr(info, 'minzoom'):
                result["minzoom"] = info.minzoom
            elif hasattr(cog, 'minzoom'):
                result["minzoom"] = cog.minzoom
            else:
                result["minzoom"] = 0
                
            if hasattr(info, 'maxzoom'):
                result["maxzoom"] = info.maxzoom
            elif hasattr(cog, 'maxzoom'):
                result["maxzoom"] = cog.maxzoom
            else:
                result["maxzoom"] = 22
            
            return result
            
    except Exception as e:
        raise RuntimeError(f"Error reading COG info: {str(e)}") from e


def get_cog_statistics(
    cog_url: str,
    indexes: Optional[tuple[int, ...]] = None,
) -> dict[str, Any]:
    """
    Get statistics for COG bands.
    
    Args:
        cog_url: URL or path to the COG file
        indexes: Band indexes to analyze
        
    Returns:
        Dictionary with band statistics
    """
    if not RASTERIO_AVAILABLE:
        raise RuntimeError("rio-tiler is not available")
    
    try:
        with COGReader(cog_url) as cog:
            stats = cog.statistics(indexes=indexes)
            
            return {
                band: {
                    "min": stat.min,
                    "max": stat.max,
                    "mean": stat.mean,
                    "std": stat.std,
                    "percentile_2": stat.percentile_2,
                    "percentile_98": stat.percentile_98,
                }
                for band, stat in stats.items()
            }
            
    except Exception as e:
        raise RuntimeError(f"Error reading COG statistics: {str(e)}") from e


# =============================================================================
# TileJSON Generation for Raster
# =============================================================================


def generate_raster_tilejson(
    tileset_id: str,
    name: str,
    base_url: str,
    tile_format: str = "png",
    min_zoom: int = 0,
    max_zoom: int = 22,
    bounds: Optional[list[float]] = None,
    center: Optional[list[float]] = None,
    description: Optional[str] = None,
    attribution: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate TileJSON for a raster tileset.
    
    Args:
        tileset_id: Tileset identifier
        name: Tileset name
        base_url: Base URL for tile requests
        tile_format: Tile format (png, jpg, webp)
        min_zoom: Minimum zoom level
        max_zoom: Maximum zoom level
        bounds: Tileset bounds [west, south, east, north]
        center: Tileset center [lng, lat, zoom]
        description: Tileset description
        attribution: Data attribution
        
    Returns:
        TileJSON specification dictionary
    """
    if bounds is None:
        bounds = [-180, -85.051129, 180, 85.051129]
    
    if center is None:
        center = [0, 0, 2]
    
    tilejson = {
        "tilejson": "3.0.0",
        "name": name,
        "tiles": [f"{base_url}/api/tiles/raster/{tileset_id}/{{z}}/{{x}}/{{y}}.{tile_format}"],
        "minzoom": min_zoom,
        "maxzoom": max_zoom,
        "bounds": bounds,
        "center": center,
    }
    
    if description:
        tilejson["description"] = description
    
    if attribution:
        tilejson["attribution"] = attribution
    
    return tilejson


# =============================================================================
# Cache Headers for Raster Tiles
# =============================================================================


def get_raster_cache_headers(z: int, is_static: bool = True) -> dict[str, str]:
    """
    Generate cache headers for raster tiles.
    
    Raster tiles from COG are generally static, so we use longer cache times.
    
    Args:
        z: Zoom level
        is_static: Whether the source data is static
        
    Returns:
        Dictionary of HTTP headers
    """
    # COG-based tiles are typically static
    if is_static:
        ttl = 604800  # 7 days
    else:
        # Dynamic raster processing (rare)
        if z <= 6:
            ttl = 86400  # 24 hours
        elif z <= 12:
            ttl = 3600  # 1 hour
        else:
            ttl = 300  # 5 minutes
    
    return {
        "Cache-Control": f"public, max-age={ttl}, s-maxage={ttl}",
        "Access-Control-Allow-Origin": "*",
    }


# =============================================================================
# Utility Functions
# =============================================================================


def validate_tile_format(tile_format: str) -> str:
    """
    Validate and normalize tile format.
    
    Args:
        tile_format: Input format string
        
    Returns:
        Normalized format string
        
    Raises:
        ValueError: If format is not supported
    """
    normalized = tile_format.lower()
    if normalized not in RASTER_MEDIA_TYPES:
        raise ValueError(f"Unsupported raster tile format: {tile_format}")
    return normalized


def get_raster_media_type(tile_format: str) -> str:
    """
    Get the media type for a raster tile format.
    
    Args:
        tile_format: Tile format string
        
    Returns:
        Media type string
    """
    normalized = validate_tile_format(tile_format)
    return RASTER_MEDIA_TYPES[normalized]

