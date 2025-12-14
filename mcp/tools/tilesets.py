"""
Tileset-related MCP tools for geo-base.

Provides tools for listing, retrieving, and accessing tileset metadata
from the geo-base tile server API.
"""

from typing import Any

import httpx

from config import get_settings
from logger import get_logger, ToolCallLogger

# Initialize logger and settings
logger = get_logger(__name__)
settings = get_settings()


def _get_auth_headers() -> dict[str, str]:
    """Get authentication headers if API token is configured."""
    headers = {}
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"
    return headers


async def list_tilesets(
    type: str | None = None,
    is_public: bool | None = None,
) -> dict[str, Any]:
    """
    List available tilesets from the geo-base tile server.

    Args:
        type: Filter by tileset type ('vector', 'raster', 'pmtiles')
        is_public: Filter by public/private status

    Returns:
        Dictionary containing list of tilesets
    """
    with ToolCallLogger(logger, "list_tilesets", type=type, is_public=is_public) as log:
        tile_server_url = settings.tile_server_url.rstrip("/")
        url = f"{tile_server_url}/api/tilesets"

        # Build query parameters
        params: dict[str, str] = {}
        if type:
            params["type"] = type
        if is_public is not None:
            if not is_public:
                # Request private tilesets (requires auth)
                params["include_private"] = "true"

        logger.debug(f"Fetching tilesets from {url}", extra={"params": str(params)})

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                data = response.json()

                # Process and return tilesets
                tilesets = data if isinstance(data, list) else data.get("tilesets", [])

                logger.debug(f"Retrieved {len(tilesets)} tilesets")

                # Add summary
                result = {
                    "tilesets": [
                        {
                            "id": ts.get("id"),
                            "name": ts.get("name"),
                            "description": ts.get("description"),
                            "type": ts.get("type"),
                            "format": ts.get("format"),
                            "is_public": ts.get("is_public", True),
                            "min_zoom": ts.get("min_zoom", 0),
                            "max_zoom": ts.get("max_zoom", 22),
                        }
                        for ts in tilesets
                    ],
                    "count": len(tilesets),
                    "tile_server_url": tile_server_url,
                }
                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error listing tilesets: {e.response.status_code}",
                    extra={"status_code": e.response.status_code, "url": url},
                )
                result = {
                    "error": f"HTTP error: {e.response.status_code}",
                    "detail": e.response.text,
                    "url": url,
                }
                log.set_result(result)
                return result
            except httpx.RequestError as e:
                logger.error(f"Request error listing tilesets: {e}", extra={"url": url})
                result = {
                    "error": f"Request error: {str(e)}",
                    "url": url,
                }
                log.set_result(result)
                return result


async def get_tileset(tileset_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific tileset.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        Dictionary containing tileset details
    """
    with ToolCallLogger(logger, "get_tileset", tileset_id=tileset_id) as log:
        tile_server_url = settings.tile_server_url.rstrip("/")
        url = f"{tile_server_url}/api/tilesets/{tileset_id}"

        logger.debug(f"Fetching tileset {tileset_id} from {url}")

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    url,
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                tileset = response.json()

                logger.debug(f"Retrieved tileset: {tileset.get('name')}")

                # Parse bounds if present
                bounds = tileset.get("bounds")
                bounds_info = None
                if bounds:
                    if isinstance(bounds, dict) and "coordinates" in bounds:
                        # GeoJSON format
                        coords = bounds["coordinates"][0]
                        bounds_info = {
                            "min_lng": min(c[0] for c in coords),
                            "min_lat": min(c[1] for c in coords),
                            "max_lng": max(c[0] for c in coords),
                            "max_lat": max(c[1] for c in coords),
                        }

                # Parse center if present
                center = tileset.get("center")
                center_info = None
                if center:
                    if isinstance(center, dict) and "coordinates" in center:
                        center_info = {
                            "lng": center["coordinates"][0],
                            "lat": center["coordinates"][1],
                        }

                result = {
                    "id": tileset.get("id"),
                    "name": tileset.get("name"),
                    "description": tileset.get("description"),
                    "type": tileset.get("type"),
                    "format": tileset.get("format"),
                    "is_public": tileset.get("is_public", True),
                    "min_zoom": tileset.get("min_zoom", 0),
                    "max_zoom": tileset.get("max_zoom", 22),
                    "bounds": bounds_info,
                    "center": center_info,
                    "attribution": tileset.get("attribution"),
                    "metadata": tileset.get("metadata", {}),
                    "created_at": tileset.get("created_at"),
                    "updated_at": tileset.get("updated_at"),
                    "tile_server_url": tile_server_url,
                }
                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.warning(
                    f"HTTP error getting tileset {tileset_id}: {status_code}",
                    extra={"tileset_id": tileset_id, "status_code": status_code},
                )
                
                if status_code == 404:
                    result = {
                        "error": "Tileset not found",
                        "tileset_id": tileset_id,
                    }
                elif status_code == 401:
                    result = {
                        "error": "Authentication required",
                        "tileset_id": tileset_id,
                        "hint": "This tileset may be private. Configure API_TOKEN in environment.",
                    }
                elif status_code == 403:
                    result = {
                        "error": "Access denied",
                        "tileset_id": tileset_id,
                        "hint": "You don't have permission to access this tileset.",
                    }
                else:
                    result = {
                        "error": f"HTTP error: {status_code}",
                        "detail": e.response.text,
                        "tileset_id": tileset_id,
                    }
                log.set_result(result)
                return result
            except httpx.RequestError as e:
                logger.error(
                    f"Request error getting tileset {tileset_id}: {e}",
                    extra={"tileset_id": tileset_id},
                )
                result = {
                    "error": f"Request error: {str(e)}",
                    "tileset_id": tileset_id,
                }
                log.set_result(result)
                return result


async def get_tileset_tilejson(tileset_id: str) -> dict[str, Any]:
    """
    Get TileJSON metadata for a tileset.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        TileJSON object
    """
    with ToolCallLogger(logger, "get_tileset_tilejson", tileset_id=tileset_id) as log:
        tile_server_url = settings.tile_server_url.rstrip("/")
        url = f"{tile_server_url}/api/tilesets/{tileset_id}/tilejson.json"

        logger.debug(f"Fetching TileJSON for {tileset_id} from {url}")

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    url,
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                tilejson = response.json()

                logger.debug(f"Retrieved TileJSON for tileset: {tilejson.get('name')}")

                result = {
                    "tilejson": tilejson.get("tilejson", "3.0.0"),
                    "name": tilejson.get("name"),
                    "description": tilejson.get("description"),
                    "tiles": tilejson.get("tiles", []),
                    "minzoom": tilejson.get("minzoom", 0),
                    "maxzoom": tilejson.get("maxzoom", 22),
                    "bounds": tilejson.get("bounds"),
                    "center": tilejson.get("center"),
                    "attribution": tilejson.get("attribution"),
                    "vector_layers": tilejson.get("vector_layers", []),
                }
                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.warning(
                    f"HTTP error getting TileJSON for {tileset_id}: {status_code}",
                    extra={"tileset_id": tileset_id, "status_code": status_code},
                )
                
                if status_code == 404:
                    result = {
                        "error": "TileJSON not found",
                        "tileset_id": tileset_id,
                        "hint": "The tileset may not exist or may not support TileJSON.",
                    }
                else:
                    result = {
                        "error": f"HTTP error: {status_code}",
                        "detail": e.response.text,
                        "tileset_id": tileset_id,
                    }
                log.set_result(result)
                return result
            except httpx.RequestError as e:
                logger.error(
                    f"Request error getting TileJSON for {tileset_id}: {e}",
                    extra={"tileset_id": tileset_id},
                )
                result = {
                    "error": f"Request error: {str(e)}",
                    "tileset_id": tileset_id,
                }
                log.set_result(result)
                return result
