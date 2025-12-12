"""
Tileset-related MCP tools for geo-base.
"""

from typing import Any

import httpx

from config import get_settings

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

            # Add summary
            return {
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

        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text,
                "url": url,
            }
        except httpx.RequestError as e:
            return {
                "error": f"Request error: {str(e)}",
                "url": url,
            }


async def get_tileset(tileset_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific tileset.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        Dictionary containing tileset details
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    url = f"{tile_server_url}/api/tilesets/{tileset_id}"

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.get(
                url,
                headers=_get_auth_headers(),
            )
            response.raise_for_status()
            tileset = response.json()

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

            return {
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

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "error": "Tileset not found",
                    "tileset_id": tileset_id,
                }
            elif e.response.status_code == 401:
                return {
                    "error": "Authentication required",
                    "tileset_id": tileset_id,
                    "hint": "This tileset may be private. Configure API_TOKEN in environment.",
                }
            elif e.response.status_code == 403:
                return {
                    "error": "Access denied",
                    "tileset_id": tileset_id,
                    "hint": "You don't have permission to access this tileset.",
                }
            return {
                "error": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text,
                "tileset_id": tileset_id,
            }
        except httpx.RequestError as e:
            return {
                "error": f"Request error: {str(e)}",
                "tileset_id": tileset_id,
            }


async def get_tileset_tilejson(tileset_id: str) -> dict[str, Any]:
    """
    Get TileJSON metadata for a tileset.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        TileJSON object
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    url = f"{tile_server_url}/api/tilesets/{tileset_id}/tilejson.json"

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.get(
                url,
                headers=_get_auth_headers(),
            )
            response.raise_for_status()
            tilejson = response.json()

            return {
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

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "error": "TileJSON not found",
                    "tileset_id": tileset_id,
                    "hint": "The tileset may not exist or may not support TileJSON.",
                }
            return {
                "error": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text,
                "tileset_id": tileset_id,
            }
        except httpx.RequestError as e:
            return {
                "error": f"Request error: {str(e)}",
                "tileset_id": tileset_id,
            }
