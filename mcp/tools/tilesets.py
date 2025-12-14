"""
Tileset-related MCP tools for geo-base.

Provides tools for listing, retrieving, and accessing tileset metadata
from the geo-base tile server API.

Features:
- Automatic retry for transient network errors
- Input validation with clear error messages
- Structured logging for debugging and monitoring
"""

from typing import Any

import httpx
from tenacity import RetryError

from config import get_settings
from errors import handle_api_error, create_error_response, ErrorCode
from logger import get_logger, ToolCallLogger
from retry import fetch_with_retry
from validators import validate_uuid, validate_tileset_type

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
        is_public: Filter by public/private status (default: only public)

    Returns:
        Dictionary containing list of tilesets with their metadata
    """
    with ToolCallLogger(logger, "list_tilesets", type=type, is_public=is_public) as log:
        # Validate type if provided
        if type is not None:
            type_result = validate_tileset_type(type)
            if not type_result.valid:
                result = type_result.to_error_response(
                    tilesets=[],
                    count=0,
                )
                log.set_result(result)
                return result
            type = type_result.value
        
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

        try:
            # Use fetch_with_retry for automatic retry on transient failures
            data = await fetch_with_retry(
                url,
                params=params if params else None,
                headers=_get_auth_headers(),
            )

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
            result = handle_api_error(e, {"url": url})
            log.set_result(result)
            return result
        except (httpx.RequestError, RetryError) as e:
            logger.error(f"Request error listing tilesets: {e}", extra={"url": url})
            result = handle_api_error(e, {"url": url})
            log.set_result(result)
            return result
        except Exception as e:
            logger.error(f"Unexpected error listing tilesets: {e}", extra={"url": url})
            result = create_error_response(
                f"Unexpected error: {str(e)}",
                ErrorCode.UNKNOWN_ERROR,
                url=url,
            )
            log.set_result(result)
            return result


async def get_tileset(tileset_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific tileset.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        Dictionary containing tileset details including name, type,
        format, bounds, zoom levels, and metadata
    """
    with ToolCallLogger(logger, "get_tileset", tileset_id=tileset_id) as log:
        # Validate tileset_id
        uuid_result = validate_uuid(tileset_id, "tileset_id")
        if not uuid_result.valid:
            result = uuid_result.to_error_response(tileset_id=tileset_id)
            log.set_result(result)
            return result
        validated_tileset_id = uuid_result.value
        
        tile_server_url = settings.tile_server_url.rstrip("/")
        url = f"{tile_server_url}/api/tilesets/{validated_tileset_id}"

        logger.debug(f"Fetching tileset {validated_tileset_id} from {url}")

        try:
            # Use fetch_with_retry for automatic retry on transient failures
            tileset = await fetch_with_retry(
                url,
                headers=_get_auth_headers(),
            )

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
                f"HTTP error getting tileset {validated_tileset_id}: {status_code}",
                extra={"tileset_id": validated_tileset_id, "status_code": status_code},
            )
            
            if status_code == 404:
                result = create_error_response(
                    "Tileset not found",
                    ErrorCode.NOT_FOUND,
                    tileset_id=validated_tileset_id,
                )
            elif status_code == 401:
                result = create_error_response(
                    "Authentication required",
                    ErrorCode.AUTH_REQUIRED,
                    tileset_id=validated_tileset_id,
                    hint="This tileset may be private. Configure API_TOKEN in environment.",
                )
            elif status_code == 403:
                result = create_error_response(
                    "Access denied",
                    ErrorCode.FORBIDDEN,
                    tileset_id=validated_tileset_id,
                    hint="You don't have permission to access this tileset.",
                )
            else:
                result = handle_api_error(e, {"tileset_id": validated_tileset_id})
            
            log.set_result(result)
            return result
        except (httpx.RequestError, RetryError) as e:
            logger.error(
                f"Request error getting tileset {validated_tileset_id}: {e}",
                extra={"tileset_id": validated_tileset_id},
            )
            result = handle_api_error(e, {"tileset_id": validated_tileset_id})
            log.set_result(result)
            return result
        except Exception as e:
            logger.error(
                f"Unexpected error getting tileset {validated_tileset_id}: {e}",
                extra={"tileset_id": validated_tileset_id},
            )
            result = create_error_response(
                f"Unexpected error: {str(e)}",
                ErrorCode.UNKNOWN_ERROR,
                tileset_id=validated_tileset_id,
            )
            log.set_result(result)
            return result


async def get_tileset_tilejson(tileset_id: str) -> dict[str, Any]:
    """
    Get TileJSON metadata for a tileset.

    TileJSON is a standard format for describing tile sources,
    useful for integrating with map clients like MapLibre GL JS.

    Args:
        tileset_id: UUID of the tileset

    Returns:
        TileJSON object containing tiles URL, bounds, zoom range, etc.
    """
    with ToolCallLogger(logger, "get_tileset_tilejson", tileset_id=tileset_id) as log:
        # Validate tileset_id
        uuid_result = validate_uuid(tileset_id, "tileset_id")
        if not uuid_result.valid:
            result = uuid_result.to_error_response(tileset_id=tileset_id)
            log.set_result(result)
            return result
        validated_tileset_id = uuid_result.value
        
        tile_server_url = settings.tile_server_url.rstrip("/")
        url = f"{tile_server_url}/api/tilesets/{validated_tileset_id}/tilejson.json"

        logger.debug(f"Fetching TileJSON for {validated_tileset_id} from {url}")

        try:
            # Use fetch_with_retry for automatic retry on transient failures
            tilejson = await fetch_with_retry(
                url,
                headers=_get_auth_headers(),
            )

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
                f"HTTP error getting TileJSON for {validated_tileset_id}: {status_code}",
                extra={"tileset_id": validated_tileset_id, "status_code": status_code},
            )
            
            if status_code == 404:
                result = create_error_response(
                    "TileJSON not found",
                    ErrorCode.NOT_FOUND,
                    tileset_id=validated_tileset_id,
                    hint="The tileset may not exist or may not support TileJSON.",
                )
            else:
                result = handle_api_error(e, {"tileset_id": validated_tileset_id})
            
            log.set_result(result)
            return result
        except (httpx.RequestError, RetryError) as e:
            logger.error(
                f"Request error getting TileJSON for {validated_tileset_id}: {e}",
                extra={"tileset_id": validated_tileset_id},
            )
            result = handle_api_error(e, {"tileset_id": validated_tileset_id})
            log.set_result(result)
            return result
        except Exception as e:
            logger.error(
                f"Unexpected error getting TileJSON for {validated_tileset_id}: {e}",
                extra={"tileset_id": validated_tileset_id},
            )
            result = create_error_response(
                f"Unexpected error: {str(e)}",
                ErrorCode.UNKNOWN_ERROR,
                tileset_id=validated_tileset_id,
            )
            log.set_result(result)
            return result
