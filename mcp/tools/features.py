"""
Feature-related MCP tools for geo-base.
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


def _parse_bbox(bbox_str: str) -> tuple[float, float, float, float] | None:
    """Parse bbox string to tuple of floats."""
    try:
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) == 4:
            return (parts[0], parts[1], parts[2], parts[3])
    except (ValueError, AttributeError):
        pass
    return None


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
        limit: Maximum number of features to return
        tileset_id: Limit search to a specific tileset

    Returns:
        Dictionary containing features and metadata
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    url = f"{tile_server_url}/api/features"

    # Build query parameters
    params: dict[str, str | int] = {
        "limit": min(limit, 1000),  # Cap at 1000
    }
    if bbox:
        params["bbox"] = bbox
    if layer:
        params["layer"] = layer
    if filter:
        params["filter"] = filter
    if tileset_id:
        params["tileset_id"] = tileset_id

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
                    "limit": limit,
                },
            }

            # Add total if available
            if isinstance(data, dict) and "total" in data:
                result["total"] = data["total"]

            # Add bbox summary if provided
            if bbox:
                parsed = _parse_bbox(bbox)
                if parsed:
                    result["bbox_parsed"] = {
                        "min_lng": parsed[0],
                        "min_lat": parsed[1],
                        "max_lng": parsed[2],
                        "max_lat": parsed[3],
                    }

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return {
                    "error": "Invalid query parameters",
                    "detail": e.response.text,
                    "hint": "Check bbox format (minx,miny,maxx,maxy) and filter syntax (key=value).",
                }
            return {
                "error": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text,
            }
        except httpx.RequestError as e:
            return {
                "error": f"Request error: {str(e)}",
            }


async def get_feature(feature_id: str) -> dict[str, Any]:
    """
    Get detailed information about a specific feature.

    Args:
        feature_id: UUID of the feature

    Returns:
        GeoJSON feature object with geometry and properties
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    url = f"{tile_server_url}/api/features/{feature_id}"

    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.get(
                url,
                headers=_get_auth_headers(),
            )
            response.raise_for_status()
            feature = response.json()

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

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "error": "Feature not found",
                    "feature_id": feature_id,
                }
            elif e.response.status_code == 401:
                return {
                    "error": "Authentication required",
                    "feature_id": feature_id,
                    "hint": "This feature may belong to a private tileset. Configure API_TOKEN.",
                }
            return {
                "error": f"HTTP error: {e.response.status_code}",
                "detail": e.response.text,
                "feature_id": feature_id,
            }
        except httpx.RequestError as e:
            return {
                "error": f"Request error: {str(e)}",
                "feature_id": feature_id,
            }


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
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        layer: Optional layer name filter

    Returns:
        Dictionary containing features in the tile
    """
    # Convert tile coordinates to bbox
    # Using Web Mercator tile math
    import math

    n = 2.0 ** z

    # Calculate bbox from tile coordinates
    min_lng = x / n * 360.0 - 180.0
    max_lng = (x + 1) / n * 360.0 - 180.0

    min_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    max_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))

    bbox = f"{min_lng},{min_lat},{max_lng},{max_lat}"

    # Use search_features with calculated bbox
    result = await search_features(
        bbox=bbox,
        layer=layer,
        tileset_id=tileset_id,
        limit=1000,
    )

    # Add tile info to result
    result["tile"] = {
        "z": z,
        "x": x,
        "y": y,
        "tileset_id": tileset_id,
    }

    return result
