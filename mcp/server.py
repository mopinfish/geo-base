"""
geo-base MCP Server

MCP Server for geo-base tile server.
Provides tools to access geographic data through Claude Desktop.

Supports both stdio (local) and HTTP/SSE (remote) transports.
"""

import os

from fastmcp import FastMCP

from config import get_settings
from logger import get_logger
from tools.tilesets import (
    list_tilesets,
    get_tileset,
    get_tileset_tilejson,
)
from tools.features import (
    search_features,
    get_feature,
)
from tools.geocoding import (
    geocode,
    reverse_geocode,
)
from tools.crud import (
    create_tileset,
    update_tileset,
    delete_tileset,
    create_feature,
    update_feature,
    delete_feature,
)
from tools.stats import (
    get_tileset_stats,
    get_feature_distribution,
    get_layer_stats,
    get_area_stats,
)
from tools.analysis import (
    analyze_area,
    calculate_distance,
    find_nearest_features,
    get_buffer_zone_features,
)

# Initialize settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Create MCP server instance
mcp = FastMCP(
    name=settings.server_name,
    version=settings.server_version,
)


# ============================================================
# Tileset Tools
# ============================================================

@mcp.tool()
async def tool_list_tilesets(
    type: str | None = None,
    is_public: bool | None = None,
) -> dict:
    """
    List available tilesets from the geo-base tile server.

    Args:
        type: Filter by tileset type ('vector', 'raster', 'pmtiles')
        is_public: Filter by public/private status (default: only public)

    Returns:
        Dictionary containing list of tilesets with their metadata
    """
    return await list_tilesets(type=type, is_public=is_public)


@mcp.tool()
async def tool_get_tileset(tileset_id: str) -> dict:
    """
    Get detailed information about a specific tileset.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        Dictionary containing tileset details including name, type,
        format, bounds, zoom levels, and metadata
    """
    return await get_tileset(tileset_id=tileset_id)


@mcp.tool()
async def tool_get_tileset_tilejson(tileset_id: str) -> dict:
    """
    Get TileJSON metadata for a tileset.

    TileJSON is a standard format for describing tile sources,
    useful for integrating with map clients like MapLibre GL JS.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        TileJSON object containing tiles URL, bounds, zoom range, etc.
    """
    return await get_tileset_tilejson(tileset_id=tileset_id)


# ============================================================
# Feature Tools
# ============================================================

@mcp.tool()
async def tool_search_features(
    bbox: str | None = None,
    layer: str | None = None,
    filter: str | None = None,
    limit: int = 100,
    tileset_id: str | None = None,
) -> dict:
    """
    Search for geographic features within specified criteria.

    Args:
        bbox: Bounding box in format "minx,miny,maxx,maxy" (WGS84)
              Example: "139.5,35.5,140.0,36.0" for Tokyo area
        layer: Filter by layer name
        filter: Property filter in format "key=value"
        limit: Maximum number of features to return (default: 100)
        tileset_id: Limit search to a specific tileset

    Returns:
        Dictionary containing:
        - features: List of GeoJSON features with geometry and properties
        - count: Number of features returned
        - total: Total count of matching features (if available)
    """
    return await search_features(
        bbox=bbox,
        layer=layer,
        filter=filter,
        limit=limit,
        tileset_id=tileset_id,
    )


@mcp.tool()
async def tool_get_feature(feature_id: str) -> dict:
    """
    Get detailed information about a specific feature.

    Args:
        feature_id: UUID of the feature

    Returns:
        GeoJSON feature object with geometry and all properties
    """
    return await get_feature(feature_id=feature_id)


# ============================================================
# Tile Tools
# ============================================================

@mcp.tool()
async def tool_get_tile_url(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    format: str = "pbf",
) -> dict:
    """
    Generate the URL for a specific map tile.

    This is useful for getting direct tile URLs that can be
    used in map clients or for debugging.

    Args:
        tileset_id: UUID of the tileset
        z: Zoom level (0-22)
        x: Tile X coordinate
        y: Tile Y coordinate
        format: Tile format ('pbf' for vector, 'png'/'jpg'/'webp' for raster)

    Returns:
        Dictionary containing:
        - url: Full URL to the tile
        - tileset_id: The tileset ID
        - coordinates: {z, x, y}
        - format: The tile format
    """
    tile_server_url = settings.tile_server_url.rstrip("/")

    # Determine tile endpoint based on tileset type
    # For now, use the generic pattern
    url = f"{tile_server_url}/api/tiles/pmtiles/{tileset_id}/{z}/{x}/{y}.{format}"

    return {
        "url": url,
        "tileset_id": tileset_id,
        "coordinates": {"z": z, "x": x, "y": y},
        "format": format,
    }


# ============================================================
# Utility Tools
# ============================================================

@mcp.tool()
async def tool_health_check() -> dict:
    """
    Check the health status of the geo-base tile server.

    Returns:
        Dictionary containing server health status including:
        - status: 'healthy' or 'unhealthy'
        - database: Database connection status
        - pmtiles: PMTiles support status
        - rasterio: Raster support status (may be unavailable on Vercel)
    """
    import httpx

    tile_server_url = settings.tile_server_url.rstrip("/")

    logger.debug(f"Checking health of tile server at {tile_server_url}")

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.get(f"{tile_server_url}/api/health")
            response.raise_for_status()
            result = response.json()
            logger.info(f"Health check completed: {result.get('status', 'unknown')}")
            return result
        except httpx.HTTPError as e:
            logger.warning(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "tile_server_url": tile_server_url,
            }


@mcp.tool()
async def tool_get_server_info() -> dict:
    """
    Get information about the geo-base tile server configuration.

    Returns:
        Dictionary containing:
        - tile_server_url: Base URL of the tile server
        - mcp_server_name: Name of this MCP server
        - mcp_server_version: Version of this MCP server
        - environment: Current environment (development/production)
    """
    return {
        "tile_server_url": settings.tile_server_url,
        "mcp_server_name": settings.server_name,
        "mcp_server_version": settings.server_version,
        "environment": settings.environment,
    }


# ============================================================
# Geocoding Tools
# ============================================================

@mcp.tool()
async def tool_geocode(
    query: str,
    limit: int = 5,
    country_codes: str | None = None,
    language: str = "ja",
) -> dict:
    """
    Convert address or place name to geographic coordinates (geocoding).

    Uses OpenStreetMap Nominatim API for geocoding.

    Args:
        query: Address or place name to search
               Examples: "東京駅", "渋谷区神南1-1-1", "Tokyo Tower"
        limit: Maximum number of results (1-50, default: 5)
        country_codes: Limit search to specific countries (comma-separated ISO 3166-1 codes)
                      Examples: "jp" for Japan, "jp,us" for Japan and US
        language: Preferred language for results (default: "ja" for Japanese)

    Returns:
        Dictionary containing:
        - results: List of matching locations with coordinates, address details
        - count: Number of results found
        - query: Original search query
    """
    return await geocode(
        query=query,
        limit=limit,
        country_codes=country_codes,
        language=language,
    )


@mcp.tool()
async def tool_reverse_geocode(
    latitude: float,
    longitude: float,
    zoom: int = 18,
    language: str = "ja",
) -> dict:
    """
    Convert geographic coordinates to address (reverse geocoding).

    Uses OpenStreetMap Nominatim API for reverse geocoding.

    Args:
        latitude: Latitude in decimal degrees (WGS84)
                 Example: 35.6812 for Tokyo Station
        longitude: Longitude in decimal degrees (WGS84)
                  Example: 139.7671 for Tokyo Station
        zoom: Level of detail for the address (0-18, default: 18)
              0 = country level
              10 = city level
              14 = suburb level
              16 = street level
              18 = building level (most detailed)
        language: Preferred language for results (default: "ja" for Japanese)

    Returns:
        Dictionary containing:
        - display_name: Full formatted address string
        - address: Structured address components (country, city, road, etc.)
        - coordinates: Input coordinates
        - bounds: Bounding box of the location
    """
    return await reverse_geocode(
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        language=language,
    )


# ============================================================
# CRUD Tools
# ============================================================


@mcp.tool()
async def tool_create_tileset(
    name: str,
    type: str,
    format: str,
    description: str | None = None,
    min_zoom: int = 0,
    max_zoom: int = 22,
    bounds: list[float] | None = None,
    center: list[float] | None = None,
    attribution: str | None = None,
    is_public: bool = False,
    metadata: dict | None = None,
) -> dict:
    """
    Create a new tileset.

    Requires authentication (API_TOKEN environment variable).

    Args:
        name: Tileset name (required)
        type: Tileset type - 'vector', 'raster', or 'pmtiles'
        format: Tile format - 'pbf', 'png', 'jpg', 'webp', or 'geojson'
        description: Optional description of the tileset
        min_zoom: Minimum zoom level (0-22, default: 0)
        max_zoom: Maximum zoom level (0-22, default: 22)
        bounds: Bounding box as [west, south, east, north] in WGS84
        center: Center point as [longitude, latitude] or [lon, lat, zoom]
        attribution: Attribution text for the tileset
        is_public: Whether the tileset is publicly accessible (default: False)
        metadata: Additional metadata as key-value pairs

    Returns:
        Created tileset object with id, name, type, format, etc.
    """
    return await create_tileset(
        name=name,
        type=type,
        format=format,
        description=description,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        bounds=bounds,
        center=center,
        attribution=attribution,
        is_public=is_public,
        metadata=metadata,
    )


@mcp.tool()
async def tool_update_tileset(
    tileset_id: str,
    name: str | None = None,
    description: str | None = None,
    min_zoom: int | None = None,
    max_zoom: int | None = None,
    bounds: list[float] | None = None,
    center: list[float] | None = None,
    attribution: str | None = None,
    is_public: bool | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Update an existing tileset.

    Requires authentication and ownership of the tileset.

    Args:
        tileset_id: UUID of the tileset to update
        name: New tileset name
        description: New description
        min_zoom: New minimum zoom level (0-22)
        max_zoom: New maximum zoom level (0-22)
        bounds: New bounding box as [west, south, east, north]
        center: New center point as [longitude, latitude]
        attribution: New attribution text
        is_public: New public/private visibility setting
        metadata: New metadata (replaces existing metadata)

    Returns:
        Updated tileset object
    """
    return await update_tileset(
        tileset_id=tileset_id,
        name=name,
        description=description,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        bounds=bounds,
        center=center,
        attribution=attribution,
        is_public=is_public,
        metadata=metadata,
    )


@mcp.tool()
async def tool_delete_tileset(tileset_id: str) -> dict:
    """
    Delete a tileset and all its associated features.

    WARNING: This action is irreversible. All features belonging to
    this tileset will also be deleted.

    Requires authentication and ownership of the tileset.

    Args:
        tileset_id: UUID of the tileset to delete

    Returns:
        Success message or error details
    """
    return await delete_tileset(tileset_id=tileset_id)


@mcp.tool()
async def tool_create_feature(
    tileset_id: str,
    geometry: dict,
    properties: dict | None = None,
    layer_name: str = "default",
) -> dict:
    """
    Create a new geographic feature in a tileset.

    Requires authentication and ownership of the parent tileset.

    Args:
        tileset_id: UUID of the parent tileset
        geometry: GeoJSON geometry object. Examples:
                  - Point: {"type": "Point", "coordinates": [139.7671, 35.6812]}
                  - LineString: {"type": "LineString", "coordinates": [[lon1, lat1], [lon2, lat2]]}
                  - Polygon: {"type": "Polygon", "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]}
        properties: Feature properties as key-value pairs (e.g., {"name": "Tokyo Station", "type": "station"})
        layer_name: Layer name for organizing features (default: "default")

    Returns:
        Created feature as GeoJSON Feature object with id, geometry, and properties
    """
    return await create_feature(
        tileset_id=tileset_id,
        geometry=geometry,
        properties=properties,
        layer_name=layer_name,
    )


@mcp.tool()
async def tool_update_feature(
    feature_id: str,
    geometry: dict | None = None,
    properties: dict | None = None,
    layer_name: str | None = None,
) -> dict:
    """
    Update an existing feature.

    Requires authentication and ownership of the parent tileset.

    Args:
        feature_id: UUID of the feature to update
        geometry: New GeoJSON geometry object
        properties: New properties (replaces all existing properties)
        layer_name: New layer name

    Returns:
        Updated feature as GeoJSON Feature object
    """
    return await update_feature(
        feature_id=feature_id,
        geometry=geometry,
        properties=properties,
        layer_name=layer_name,
    )


@mcp.tool()
async def tool_delete_feature(feature_id: str) -> dict:
    """
    Delete a feature.

    WARNING: This action is irreversible.

    Requires authentication and ownership of the parent tileset.

    Args:
        feature_id: UUID of the feature to delete

    Returns:
        Success message or error details
    """
    return await delete_feature(feature_id=feature_id)


# ============================================================
# Statistics Tools
# ============================================================


@mcp.tool()
async def tool_get_tileset_stats(tileset_id: str) -> dict:
    """
    Get comprehensive statistics for a tileset.

    Retrieves features from the tileset and calculates various statistics
    including feature count, geometry type distribution, and layer breakdown.

    Args:
        tileset_id: UUID of the tileset to analyze

    Returns:
        Dictionary containing:
        - tileset_id: The tileset ID
        - tileset_name: Name of the tileset
        - feature_count: Total number of features
        - geometry_types: Distribution of geometry types (Point, LineString, Polygon, etc.)
        - layers: Statistics per layer
        - coordinate_count: Total coordinate points
        - zoom_range: Min/max zoom levels
    """
    return await get_tileset_stats(tileset_id=tileset_id)


@mcp.tool()
async def tool_get_feature_distribution(
    tileset_id: str | None = None,
    bbox: str | None = None,
) -> dict:
    """
    Get distribution of feature geometry types.

    Analyzes features and returns the distribution of geometry types
    (Point, LineString, Polygon, etc.) either for a specific tileset
    or within a bounding box.

    Args:
        tileset_id: Optional tileset ID to limit analysis
        bbox: Optional bounding box in format "minx,miny,maxx,maxy" (WGS84)
              Example: "139.5,35.5,140.0,36.0" for Tokyo area

    Returns:
        Dictionary containing:
        - total_features: Total number of features analyzed
        - geometry_types: Count per geometry type
        - percentages: Percentage per geometry type
    """
    return await get_feature_distribution(tileset_id=tileset_id, bbox=bbox)


@mcp.tool()
async def tool_get_layer_stats(tileset_id: str) -> dict:
    """
    Get statistics broken down by layer for a tileset.

    Analyzes features grouped by their layer_name field and provides
    detailed statistics for each layer.

    Args:
        tileset_id: UUID of the tileset to analyze

    Returns:
        Dictionary containing:
        - tileset_id: The tileset ID
        - total_features: Total feature count
        - layer_count: Number of unique layers
        - layers: Per-layer statistics including feature_count, geometry_types, property_keys
    """
    return await get_layer_stats(tileset_id=tileset_id)


@mcp.tool()
async def tool_get_area_stats(
    bbox: str,
    tileset_id: str | None = None,
) -> dict:
    """
    Get statistics for a geographic area defined by a bounding box.

    Calculates area-based statistics including feature density,
    geometry distribution, and coverage metrics. This is useful for
    understanding the data coverage and density in a specific region.

    Args:
        bbox: Bounding box in format "minx,miny,maxx,maxy" (WGS84)
              Example: "139.5,35.5,140.0,36.0" for Tokyo area
        tileset_id: Optional tileset ID to limit analysis

    Returns:
        Dictionary containing:
        - bbox: Parsed bounding box coordinates
        - area_km2: Area of the bounding box in square kilometers
        - feature_count: Number of features in the area
        - density: Features per square kilometer
        - geometry_types: Distribution of geometry types
        - layers: Layers present in the area
    """
    return await get_area_stats(bbox=bbox, tileset_id=tileset_id)


# ============================================================
# Spatial Analysis Tools
# ============================================================


@mcp.tool()
async def tool_analyze_area(
    bbox: str,
    tileset_id: str | None = None,
    include_density: bool = True,
    include_clustering: bool = True,
) -> dict:
    """
    Perform comprehensive spatial analysis on a geographic area.

    Analyzes features within the bounding box and provides feature distribution,
    spatial density analysis with hotspot detection, and proximity-based clustering.

    Args:
        bbox: Bounding box in format "minx,miny,maxx,maxy" (WGS84)
              Example: "139.5,35.5,140.0,36.0" for Tokyo area
        tileset_id: Optional tileset ID to limit analysis
        include_density: Calculate density metrics with grid analysis (default: True)
        include_clustering: Perform clustering analysis (default: True)

    Returns:
        Dictionary containing:
        - bbox: Parsed bounding box
        - area_km2: Area in square kilometers
        - features: Feature counts and geometry type distribution
        - density: Density metrics including grid analysis and hotspots
        - clustering: Cluster analysis with member counts
        - layers: Layer breakdown
    """
    return await analyze_area(
        bbox=bbox,
        tileset_id=tileset_id,
        include_density=include_density,
        include_clustering=include_clustering,
    )


@mcp.tool()
async def tool_calculate_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> dict:
    """
    Calculate the distance between two geographic points.

    Uses the Haversine formula for accurate great-circle distance calculation.
    Also calculates the initial bearing (compass direction) from point 1 to point 2.

    Args:
        lat1: Latitude of first point in decimal degrees (e.g., 35.6812 for Tokyo Station)
        lng1: Longitude of first point in decimal degrees (e.g., 139.7671 for Tokyo Station)
        lat2: Latitude of second point in decimal degrees
        lng2: Longitude of second point in decimal degrees

    Returns:
        Dictionary containing:
        - distance_km: Distance in kilometers
        - distance_m: Distance in meters
        - distance_miles: Distance in miles
        - bearing: Initial bearing in degrees (0-360)
        - bearing_direction: Compass direction (N, NE, E, etc.)
        - points: The input coordinates
    """
    return await calculate_distance(
        lat1=lat1,
        lng1=lng1,
        lat2=lat2,
        lng2=lng2,
    )


@mcp.tool()
async def tool_find_nearest_features(
    lat: float,
    lng: float,
    radius_km: float = 1.0,
    limit: int = 10,
    tileset_id: str | None = None,
    layer: str | None = None,
) -> dict:
    """
    Find features nearest to a given point.

    Searches for features within a radius and returns them sorted by distance
    from the search center. Useful for "what's nearby" queries.

    Args:
        lat: Latitude of the search center in decimal degrees
        lng: Longitude of the search center in decimal degrees
        radius_km: Search radius in kilometers (default: 1.0)
        limit: Maximum number of results (default: 10, max: 100)
        tileset_id: Optional tileset ID to limit search
        layer: Optional layer name to filter results

    Returns:
        Dictionary containing:
        - center: The search center point
        - radius_km: The search radius
        - features: List of features with distance_km, distance_m, sorted by proximity
        - count: Number of features found
    """
    return await find_nearest_features(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        limit=limit,
        tileset_id=tileset_id,
        layer=layer,
    )


@mcp.tool()
async def tool_get_buffer_zone_features(
    lat: float,
    lng: float,
    inner_radius_km: float,
    outer_radius_km: float,
    tileset_id: str | None = None,
) -> dict:
    """
    Get features within a ring buffer zone (donut shape) around a point.

    Useful for analyzing features at specific distances from a point,
    such as finding all features between 1-2 km from a location.

    Args:
        lat: Latitude of the center point in decimal degrees
        lng: Longitude of the center point in decimal degrees
        inner_radius_km: Inner radius of the buffer zone in kilometers
        outer_radius_km: Outer radius of the buffer zone in kilometers
        tileset_id: Optional tileset ID to limit search

    Returns:
        Dictionary containing:
        - center: The center point
        - inner_radius_km: Inner radius
        - outer_radius_km: Outer radius
        - ring_area_km2: Area of the ring buffer
        - features: List of features in the buffer zone with distances
        - count: Number of features found
        - density_per_km2: Feature density in the ring
    """
    return await get_buffer_zone_features(
        lat=lat,
        lng=lng,
        inner_radius_km=inner_radius_km,
        outer_radius_km=outer_radius_km,
        tileset_id=tileset_id,
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    # Log startup information
    logger.info(
        f"Starting {settings.server_name} v{settings.server_version}",
        extra={
            "tile_server_url": settings.tile_server_url,
            "environment": settings.environment,
            "log_level": settings.log_level,
        },
    )

    # Get transport mode from environment variable
    # Options: "stdio" (default, for local Claude Desktop)
    #          "sse" (for remote HTTP connections via Fly.io)
    #          "streamable-http" (alternative HTTP transport)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    # Get host and port for HTTP transports
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))
    
    logger.info(f"Using transport: {transport}")
    
    if transport == "stdio":
        # Run with stdio transport (default for Claude Desktop local)
        mcp.run()
    elif transport == "sse":
        # Run with SSE transport (for remote connections)
        logger.info(f"Starting SSE server on {host}:{port}")
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        # Run with Streamable HTTP transport
        logger.info(f"Starting Streamable HTTP server on {host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        logger.error(f"Unknown transport: {transport}")
        print(f"Unknown transport: {transport}")
        print("Valid options: stdio, sse, streamable-http")
        exit(1)
