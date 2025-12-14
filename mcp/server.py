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
