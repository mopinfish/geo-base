"""
Feature-related MCP tools for geo-base.

Provides tools for searching and retrieving geographic features
from the geo-base tile server API.
"""

import math
from typing import Any

import httpx

from config import get_settings
from logger import get_logger, ToolCallLogger
from validators import (
    validate_uuid,
    validate_bbox,
    validate_limit,
    validate_range,
    validate_filter,
)

# Initialize logger and settings
logger = get_logger(__name__)
settings = get_settings()


def _get_auth_headers() -> dict[str, str]:
    """Get authentication headers if API token is configured."""
    headers = {}
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"
    return headers


def _format_geometry(geom: dict) -> dict:
    """Format geometry for display."""
    if not geom:
        return {}

    geom_type = geom.get("type", "Unknown")
    coords = geom.get("coordinates")

    result = {"type": geom_type}

    if geom_type == "Point" and coords:
        result["lng"] = coords[0]
        result["lat"] = coords[1]
    elif geom_type in ("LineString", "MultiPoint") and coords:
        result["point_count"] = len(coords)
    elif geom_type in ("Polygon", "MultiLineString") and coords:
        result["ring_count"] = len(coords)
    elif geom_type in ("MultiPolygon",) and coords:
        result["polygon_count"] = len(coords)

    return result


async def search_features(
    bbox: str | None = None,
    layer: str | None = None,
    filter: str | None = None,
    limit: int = 100,
    tileset_id: str | None = None,
) -> dict[str, Any]:
    """
    Search for geographic features within specified criteria.

    Args:
        bbox: Bounding box in format "minx,miny,maxx,maxy" (WGS84)
        layer: Filter by layer name
        filter: Property filter in format "key=value"
        limit: Maximum number of features to return (1-1000)
        tileset_id: Limit search to a specific tileset

    Returns:
        Dictionary containing features and metadata
    """
    with ToolCallLogger(
        logger, "search_features",
        bbox=bbox, layer=layer, filter=filter, limit=limit, tileset_id=tileset_id
    ) as log:
        # Validate bbox if provided
        bbox_parsed = None
        if bbox:
            bbox_result = validate_bbox(bbox)
            if not bbox_result.valid:
                result = bbox_result.to_error_response(
                    features=[],
                    count=0,
                )
                log.set_result(result)
                return result
            bbox_parsed = bbox_result.value
        
        # Validate limit
        limit_result = validate_limit(limit, max_value=1000)
        if not limit_result.valid:
            result = limit_result.to_error_response(
                features=[],
                count=0,
            )
            log.set_result(result)
            return result
        validated_limit = limit_result.value
        
        # Validate filter if provided
        if filter:
            filter_result = validate_filter(filter)
            if not filter_result.valid:
                result = filter_result.to_error_response(
                    features=[],
                    count=0,
                )
                log.set_result(result)
                return result
        
        # Validate tileset_id if provided
        if tileset_id:
            uuid_result = validate_uuid(tileset_id, "tileset_id")
            if not uuid_result.valid:
                result = uuid_result.to_error_response(
                    features=[],
                    count=0,
                )
                log.set_result(result)
                return result
            tileset_id = uuid_result.value
        
        tile_server_url = settings.tile_server_url.rstrip("/")
        url = f"{tile_server_url}/api/features"

        # Build query parameters
        params: dict[str, str | int] = {
            "limit": validated_limit,
        }
        if bbox:
            params["bbox"] = bbox
        if layer:
            params["layer"] = layer
        if filter:
            params["filter"] = filter
        if tileset_id:
            params["tileset_id"] = tileset_id

        logger.debug(f"Searching features at {url}", extra={"params": str(params)})

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                data = response.json()

                # Process features
                features = data.get("features", []) if isinstance(data, dict) else data
                if isinstance(features, dict) and "features" in features:
                    features = features["features"]

                logger.debug(f"Retrieved {len(features)} features")

                processed_features = []
                for feature in features:
                    processed = {
                        "id": feature.get("id"),
                        "type": "Feature",
                        "geometry": _format_geometry(feature.get("geometry", feature.get("geom"))),
                        "properties": feature.get("properties", {}),
                    }

                    # Add layer info if available
                    if feature.get("layer_name"):
                        processed["layer"] = feature["layer_name"]

                    # Add tileset info if available
                    if feature.get("tileset_id"):
                        processed["tileset_id"] = feature["tileset_id"]

                    processed_features.append(processed)

                result = {
                    "features": processed_features,
                    "count": len(processed_features),
                    "query": {
                        "bbox": bbox,
                        "layer": layer,
                        "filter": filter,
                        "tileset_id": tileset_id,
                        "limit": validated_limit,
                    },
                }

                # Add total if available
                if isinstance(data, dict) and "total" in data:
                    result["total"] = data["total"]

                # Add bbox summary if provided
                if bbox_parsed:
                    result["bbox_parsed"] = {
                        "min_lng": bbox_parsed[0],
                        "min_lat": bbox_parsed[1],
                        "max_lng": bbox_parsed[2],
                        "max_lat": bbox_parsed[3],
                    }

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.warning(
                    f"HTTP error searching features: {status_code}",
                    extra={"status_code": status_code, "url": url},
                )
                
                if status_code == 400:
                    result = {
                        "error": "Invalid query parameters",
                        "detail": e.response.text,
                        "hint": "Check bbox format (minx,miny,maxx,maxy) and filter syntax (key=value).",
                    }
                else:
                    result = {
                        "error": f"HTTP error: {status_code}",
                        "detail": e.response.text,
                    }
                log.set_result(result)
                return result
            except httpx.RequestError as e:
                logger.error(f"Request error searching features: {e}", extra={"url": url})
                result = {
                    "error": f"Request error: {str(e)}",
                }
                log.set_result(result)
                return result


async def get_feature(feature_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific feature.

    Args:
        feature_id: UUID of the feature

    Returns:
        GeoJSON feature object with geometry and properties
    """
    with ToolCallLogger(logger, "get_feature", feature_id=feature_id) as log:
        # Validate feature_id
        uuid_result = validate_uuid(feature_id, "feature_id")
        if not uuid_result.valid:
            result = uuid_result.to_error_response(feature_id=feature_id)
            log.set_result(result)
            return result
        validated_feature_id = uuid_result.value
        
        tile_server_url = settings.tile_server_url.rstrip("/")
        url = f"{tile_server_url}/api/features/{validated_feature_id}"

        logger.debug(f"Fetching feature {validated_feature_id} from {url}")

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    url,
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                feature = response.json()

                logger.debug(f"Retrieved feature: {feature.get('id')}")

                # Get geometry
                geom = feature.get("geometry") or feature.get("geom")

                result = {
                    "id": feature.get("id"),
                    "type": "Feature",
                    "geometry": geom,
                    "geometry_summary": _format_geometry(geom),
                    "properties": feature.get("properties", {}),
                }

                # Add optional fields
                if feature.get("layer_name"):
                    result["layer"] = feature["layer_name"]
                if feature.get("tileset_id"):
                    result["tileset_id"] = feature["tileset_id"]
                if feature.get("tileset_name"):
                    result["tileset_name"] = feature["tileset_name"]
                if feature.get("created_at"):
                    result["created_at"] = feature["created_at"]
                if feature.get("updated_at"):
                    result["updated_at"] = feature["updated_at"]

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                logger.warning(
                    f"HTTP error getting feature {validated_feature_id}: {status_code}",
                    extra={"feature_id": validated_feature_id, "status_code": status_code},
                )
                
                if status_code == 404:
                    result = {
                        "error": "Feature not found",
                        "feature_id": validated_feature_id,
                    }
                elif status_code == 401:
                    result = {
                        "error": "Authentication required",
                        "feature_id": validated_feature_id,
                        "hint": "This feature may belong to a private tileset. Configure API_TOKEN.",
                    }
                else:
                    result = {
                        "error": f"HTTP error: {status_code}",
                        "detail": e.response.text,
                        "feature_id": validated_feature_id,
                    }
                log.set_result(result)
                return result
            except httpx.RequestError as e:
                logger.error(
                    f"Request error getting feature {validated_feature_id}: {e}",
                    extra={"feature_id": validated_feature_id},
                )
                result = {
                    "error": f"Request error: {str(e)}",
                    "feature_id": validated_feature_id,
                }
                log.set_result(result)
                return result


async def get_features_in_tile(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    layer: str | None = None,
) -> dict[str, Any]:
    """
    Get features within a specific map tile.

    This is useful for getting features that would be rendered
    in a particular tile.

    Args:
        tileset_id: UUID of the tileset
        z: Zoom level (0-22)
        x: Tile X coordinate
        y: Tile Y coordinate
        layer: Optional layer name filter

    Returns:
        Dictionary containing features in the tile
    """
    with ToolCallLogger(
        logger, "get_features_in_tile",
        tileset_id=tileset_id, z=z, x=x, y=y, layer=layer
    ) as log:
        # Validate tileset_id
        uuid_result = validate_uuid(tileset_id, "tileset_id")
        if not uuid_result.valid:
            result = uuid_result.to_error_response(
                features=[],
                count=0,
                tile={"z": z, "x": x, "y": y, "tileset_id": tileset_id},
            )
            log.set_result(result)
            return result
        validated_tileset_id = uuid_result.value
        
        # Validate zoom level
        zoom_result = validate_range(z, "z", min_value=0, max_value=22)
        if not zoom_result.valid:
            result = zoom_result.to_error_response(
                features=[],
                count=0,
                tile={"z": z, "x": x, "y": y, "tileset_id": tileset_id},
            )
            log.set_result(result)
            return result
        validated_z = zoom_result.value
        
        # Validate x coordinate (must be 0 to 2^z - 1)
        max_tile = (2 ** validated_z) - 1
        x_result = validate_range(x, "x", min_value=0, max_value=max_tile)
        if not x_result.valid:
            result = x_result.to_error_response(
                features=[],
                count=0,
                tile={"z": z, "x": x, "y": y, "tileset_id": tileset_id},
            )
            log.set_result(result)
            return result
        validated_x = x_result.value
        
        # Validate y coordinate (must be 0 to 2^z - 1)
        y_result = validate_range(y, "y", min_value=0, max_value=max_tile)
        if not y_result.valid:
            result = y_result.to_error_response(
                features=[],
                count=0,
                tile={"z": z, "x": x, "y": y, "tileset_id": tileset_id},
            )
            log.set_result(result)
            return result
        validated_y = y_result.value
        
        logger.debug(f"Getting features in tile z={validated_z}, x={validated_x}, y={validated_y} for tileset {validated_tileset_id}")

        # Convert tile coordinates to bbox using Web Mercator tile math
        n = 2.0 ** validated_z

        # Calculate bbox from tile coordinates
        min_lng = validated_x / n * 360.0 - 180.0
        max_lng = (validated_x + 1) / n * 360.0 - 180.0
        min_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (validated_y + 1) / n))))
        max_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * validated_y / n))))

        bbox = f"{min_lng},{min_lat},{max_lng},{max_lat}"

        logger.debug(f"Calculated bbox for tile: {bbox}")

        # Use search_features with calculated bbox
        result = await search_features(
            bbox=bbox,
            layer=layer,
            tileset_id=validated_tileset_id,
            limit=1000,
        )

        # Add tile info to result
        result["tile"] = {
            "z": validated_z,
            "x": validated_x,
            "y": validated_y,
            "tileset_id": validated_tileset_id,
        }

        log.set_result(result)
        return result
