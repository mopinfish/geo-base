"""
Raster tile serving utilities for geo-base API.

Features:
- Cloud Optimized GeoTIFF (COG) tile generation
- Dynamic tile rendering with rio-tiler
- Multiple output formats (PNG, JPEG, WebP)
- Band selection and rescaling
- Preview image generation
- Enhanced colormap presets (NDVI, terrain, temperature, etc.)
"""

import asyncio
from functools import lru_cache
from io import BytesIO
from typing import Any, Optional
import math

# Note: rio-tiler may not work in Vercel serverless due to GDAL dependencies
# If deployment fails, consider using AWS Lambda with Docker image
try:
    from rio_tiler.io import Reader as COGReader
    from rio_tiler.profiles import img_profiles
    from rio_tiler.errors import TileOutsideBounds
    from rio_tiler.colormap import cmap as rio_cmap
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    COGReader = None
    img_profiles = None
    TileOutsideBounds = Exception
    rio_cmap = None

# Try to import numpy for custom colormaps
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

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
# Colormap Presets
# =============================================================================

# Custom colormap definitions (0-255 -> RGBA)
# Format: {value: (R, G, B, A)}

# NDVI (Normalized Difference Vegetation Index)
# -1 to 1, typically rescaled to 0-255 where 127 = 0
NDVI_COLORMAP = {
    0: (165, 0, 38, 255),      # Dark red (-1.0)
    32: (215, 48, 39, 255),    # Red (-0.75)
    64: (244, 109, 67, 255),   # Orange (-0.5)
    96: (253, 174, 97, 255),   # Light orange (-0.25)
    127: (255, 255, 191, 255), # Yellow (0.0)
    159: (166, 217, 106, 255), # Light green (0.25)
    191: (102, 189, 99, 255),  # Green (0.5)
    223: (26, 152, 80, 255),   # Dark green (0.75)
    255: (0, 104, 55, 255),    # Very dark green (1.0)
}

# Terrain/Elevation colormap (for DEMs)
TERRAIN_COLORMAP = {
    0: (0, 97, 71, 255),       # Deep green (low)
    25: (16, 122, 47, 255),    # Green
    51: (79, 163, 51, 255),    # Light green
    76: (170, 203, 85, 255),   # Yellow-green
    102: (254, 254, 172, 255), # Pale yellow
    127: (254, 226, 145, 255), # Light brown
    153: (221, 162, 76, 255),  # Brown
    178: (186, 117, 68, 255),  # Darker brown
    204: (160, 100, 80, 255),  # Rocky brown
    229: (200, 200, 200, 255), # Gray (high altitude)
    255: (255, 255, 255, 255), # White (snow caps)
}

# Temperature colormap (coolwarm)
TEMPERATURE_COLORMAP = {
    0: (59, 76, 192, 255),     # Cold blue
    32: (99, 125, 206, 255),   # Blue
    64: (141, 160, 203, 255),  # Light blue
    96: (186, 197, 227, 255),  # Pale blue
    127: (238, 238, 238, 255), # White/neutral
    159: (246, 197, 179, 255), # Light pink
    191: (239, 149, 116, 255), # Light red
    223: (213, 96, 80, 255),   # Red
    255: (180, 4, 38, 255),    # Hot red
}

# Precipitation colormap (blues to purple)
PRECIPITATION_COLORMAP = {
    0: (255, 255, 255, 255),   # White (no rain)
    25: (240, 249, 255, 255),  # Very light blue
    51: (198, 219, 239, 255),  # Light blue
    76: (158, 202, 225, 255),  # Blue
    102: (107, 174, 214, 255), # Medium blue
    127: (66, 146, 198, 255),  # Darker blue
    153: (33, 113, 181, 255),  # Dark blue
    178: (8, 81, 156, 255),    # Very dark blue
    204: (8, 48, 107, 255),    # Navy
    229: (75, 0, 130, 255),    # Indigo
    255: (128, 0, 128, 255),   # Purple (extreme)
}

# Ocean depth colormap (bathymetry)
BATHYMETRY_COLORMAP = {
    0: (8, 29, 88, 255),       # Deep ocean
    51: (37, 52, 148, 255),    # Deep blue
    102: (34, 94, 168, 255),   # Medium blue
    153: (65, 182, 196, 255),  # Light blue
    204: (127, 205, 187, 255), # Turquoise
    229: (199, 233, 180, 255), # Light green (shallow)
    255: (237, 248, 177, 255), # Very shallow
}

# Grayscale/Hillshade
GRAYSCALE_COLORMAP = {
    i: (i, i, i, 255) for i in range(0, 256, 16)
}
GRAYSCALE_COLORMAP[255] = (255, 255, 255, 255)

# Viridis-like colormap (perceptually uniform)
VIRIDIS_COLORMAP = {
    0: (68, 1, 84, 255),       # Dark purple
    32: (72, 35, 116, 255),    # Purple
    64: (64, 67, 135, 255),    # Blue-purple
    96: (52, 94, 141, 255),    # Blue
    127: (41, 120, 142, 255),  # Teal
    159: (32, 144, 140, 255),  # Green-teal
    191: (53, 183, 121, 255),  # Green
    223: (109, 205, 89, 255),  # Light green
    255: (253, 231, 37, 255),  # Yellow
}

# Available preset colormaps
COLORMAP_PRESETS = {
    "ndvi": NDVI_COLORMAP,
    "terrain": TERRAIN_COLORMAP,
    "elevation": TERRAIN_COLORMAP,  # Alias
    "dem": TERRAIN_COLORMAP,        # Alias
    "temperature": TEMPERATURE_COLORMAP,
    "coolwarm": TEMPERATURE_COLORMAP,  # Alias
    "precipitation": PRECIPITATION_COLORMAP,
    "rainfall": PRECIPITATION_COLORMAP,  # Alias
    "bathymetry": BATHYMETRY_COLORMAP,
    "ocean": BATHYMETRY_COLORMAP,    # Alias
    "grayscale": GRAYSCALE_COLORMAP,
    "hillshade": GRAYSCALE_COLORMAP,  # Alias
    "viridis": VIRIDIS_COLORMAP,
}


def get_colormap(name: str) -> Optional[dict]:
    """
    Get a colormap by name.
    
    Args:
        name: Colormap name (case-insensitive)
        
    Returns:
        Colormap dictionary or None if not found
    """
    name_lower = name.lower()
    
    # Check preset colormaps first
    if name_lower in COLORMAP_PRESETS:
        return COLORMAP_PRESETS[name_lower]
    
    # Try rio-tiler's built-in colormaps
    if rio_cmap is not None:
        try:
            return rio_cmap.get(name)
        except Exception:
            pass
    
    return None


def list_colormaps() -> list[str]:
    """
    List all available colormap names.
    
    Returns:
        List of colormap names
    """
    presets = list(COLORMAP_PRESETS.keys())
    
    # Add rio-tiler colormaps
    if rio_cmap is not None:
        try:
            presets.extend(rio_cmap.list())
        except Exception:
            pass
    
    return sorted(set(presets))


def interpolate_colormap(colormap: dict, num_values: int = 256) -> dict:
    """
    Interpolate a sparse colormap to full 256 values.
    
    Args:
        colormap: Sparse colormap dictionary
        num_values: Number of output values
        
    Returns:
        Full colormap dictionary with all values
    """
    if not NUMPY_AVAILABLE:
        return colormap
    
    # Sort keys
    keys = sorted(colormap.keys())
    
    # Create output colormap
    result = {}
    
    for i in range(num_values):
        # Find surrounding key values
        lower_key = None
        upper_key = None
        
        for k in keys:
            if k <= i:
                lower_key = k
            if k >= i and upper_key is None:
                upper_key = k
        
        if lower_key is None:
            result[i] = colormap[keys[0]]
        elif upper_key is None:
            result[i] = colormap[keys[-1]]
        elif lower_key == upper_key:
            result[i] = colormap[lower_key]
        else:
            # Linear interpolation
            t = (i - lower_key) / (upper_key - lower_key)
            lower_color = colormap[lower_key]
            upper_color = colormap[upper_key]
            result[i] = tuple(
                int(lower_color[j] + t * (upper_color[j] - lower_color[j]))
                for j in range(4)
            )
    
    return result


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
                cmap_data = get_colormap(colormap)
                if cmap_data:
                    # Interpolate to full 256 values if needed
                    if len(cmap_data) < 256:
                        cmap_data = interpolate_colormap(cmap_data)
                    render_options["colormap"] = cmap_data
            
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
            
            # Apply colormap if specified for single-band
            if colormap and imgdata.count == 1:
                cmap_data = get_colormap(colormap)
                if cmap_data:
                    if len(cmap_data) < 256:
                        cmap_data = interpolate_colormap(cmap_data)
                    render_options["colormap"] = cmap_data
            
            return imgdata.render(
                img_format=img_format.upper().replace("JPG", "JPEG"),
                **render_options
            )
            
    except Exception as e:
        raise RuntimeError(f"Error generating preview: {str(e)}") from e


async def get_raster_preview_async(
    cog_url: str,
    **kwargs,
) -> bytes:
    """
    Async wrapper for get_raster_preview.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_raster_preview(cog_url, **kwargs)
    )


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
    colormap: Optional[str] = None,
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
        colormap: Optional colormap name
        
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
            
            # Apply colormap if specified for single-band
            if colormap and imgdata.count == 1:
                cmap_data = get_colormap(colormap)
                if cmap_data:
                    if len(cmap_data) < 256:
                        cmap_data = interpolate_colormap(cmap_data)
                    render_options["colormap"] = cmap_data
            
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


def calculate_recommended_zoom_levels(
    cog_url: str,
) -> tuple[int, int]:
    """
    Calculate recommended min/max zoom levels based on COG resolution.
    
    Args:
        cog_url: URL or path to the COG file
        
    Returns:
        Tuple of (min_zoom, max_zoom)
    """
    if not RASTERIO_AVAILABLE:
        return (0, 18)
    
    try:
        info = get_cog_info(cog_url)
        
        # Use info's minzoom/maxzoom if available
        minzoom = info.get("minzoom", 0)
        maxzoom = info.get("maxzoom", 18)
        
        # Ensure reasonable defaults
        minzoom = max(0, min(minzoom, 10))
        maxzoom = max(minzoom, min(maxzoom, 22))
        
        return (minzoom, maxzoom)
        
    except Exception:
        return (0, 18)


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
    colormap: Optional[str] = None,
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
        colormap: Optional default colormap for the tileset
        
    Returns:
        TileJSON specification dictionary
    """
    if bounds is None:
        bounds = [-180, -85.051129, 180, 85.051129]
    
    if center is None:
        center = [0, 0, 2]
    
    # Build tile URL with optional colormap parameter
    tile_url = f"{base_url}/api/tiles/raster/{tileset_id}/{{z}}/{{x}}/{{y}}.{tile_format}"
    if colormap:
        tile_url += f"?colormap={colormap}"
    
    tilejson = {
        "tilejson": "3.0.0",
        "name": name,
        "tiles": [tile_url],
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
    normalized = tile_format.lower()
    return RASTER_MEDIA_TYPES.get(normalized, "application/octet-stream")


def parse_indexes(indexes_str: Optional[str]) -> Optional[tuple[int, ...]]:
    """
    Parse band indexes from a comma-separated string.
    
    Args:
        indexes_str: Comma-separated band indexes (e.g., "1,2,3")
        
    Returns:
        Tuple of band indexes or None
    """
    if not indexes_str:
        return None
    
    try:
        return tuple(int(i.strip()) for i in indexes_str.split(","))
    except ValueError:
        return None


# =============================================================================
# COG Validation
# =============================================================================


def validate_cog(cog_url: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a file is a valid Cloud Optimized GeoTIFF.
    
    Args:
        cog_url: URL or path to the COG file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not RASTERIO_AVAILABLE:
        return True, None  # Can't validate without rasterio
    
    try:
        info = get_cog_info(cog_url)
        
        # Check driver is GTiff
        if info.get("driver") not in ("GTiff", "COG"):
            return False, f"File is not a GeoTIFF (driver: {info.get('driver')})"
        
        # Check has bands
        if not info.get("count") or info["count"] < 1:
            return False, "File has no bands"
        
        # Check has valid bounds
        if not info.get("bounds"):
            return False, "File has no valid bounds"
        
        return True, None
        
    except Exception as e:
        return False, f"Error validating COG: {str(e)}"
