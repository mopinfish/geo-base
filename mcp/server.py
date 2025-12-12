"""
geo-base MCP Server

MCP Server for geo-base tile server.
Provides tools to access geographic data through Claude Desktop.

Supports both stdio (local) and HTTP/SSE (remote) transports.
"""

import os

from fastmcp import FastMCP

from config import get_settings
from tools.tilesets import (
    list_tilesets,
    get_tileset,
    get_tileset_tilejson,
)
from tools.features import (
    search_features,
    get_feature,
)

# Initialize settings
settings = get_settings()

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

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.get(f"{tile_server_url}/api/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
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
# Entry Point
# ============================================================

if __name__ == "__main__":
    # Get transport mode from environment variable
    # Options: "stdio" (default, for local Claude Desktop)
    #          "sse" (for remote HTTP connections via Fly.io)
    #          "streamable-http" (alternative HTTP transport)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    
    # Get host and port for HTTP transports
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))
    
    if transport == "stdio":
        # Run with stdio transport (default for Claude Desktop local)
        mcp.run()
    elif transport == "sse":
        # Run with SSE transport (for remote connections)
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        # Run with Streamable HTTP transport
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        print(f"Unknown transport: {transport}")
        print("Valid options: stdio, sse, streamable-http")
        exit(1)
