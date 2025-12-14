"""
Statistics tools for geo-base MCP Server.

Provides tools for analyzing geographic data statistics including:
- Tileset statistics (feature counts, geometry types)
- Feature distribution analysis
- Layer statistics
- Area-based statistics and density calculations
"""

import math
from typing import Any
from collections import Counter

import httpx

from config import get_settings
from logger import get_logger, ToolCallLogger
from errors import handle_api_error, create_error_response, ErrorCode

# Initialize logger and settings
logger = get_logger(__name__)
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


def _calculate_bbox_area_km2(
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
) -> float:
    """
    Calculate approximate area of a bounding box in square kilometers.

    Uses a simple spherical approximation that works well for small areas.

    Args:
        min_lng: Minimum longitude (west)
        min_lat: Minimum latitude (south)
        max_lng: Maximum longitude (east)
        max_lat: Maximum latitude (north)

    Returns:
        Approximate area in square kilometers
    """
    # Earth's radius in km
    R = 6371.0

    # Convert to radians
    lat1 = math.radians(min_lat)
    lat2 = math.radians(max_lat)
    lng1 = math.radians(min_lng)
    lng2 = math.radians(max_lng)

    # Width and height in radians
    d_lat = lat2 - lat1
    d_lng = lng2 - lng1

    # Average latitude for width calculation
    avg_lat = (lat1 + lat2) / 2

    # Calculate dimensions in km
    height_km = d_lat * R
    width_km = d_lng * R * math.cos(avg_lat)

    return abs(width_km * height_km)


def _extract_geometry_type(feature: dict) -> str:
    """Extract geometry type from a feature."""
    geom = feature.get("geometry") or feature.get("geom") or {}
    return geom.get("type", "Unknown")


def _count_coordinates(feature: dict) -> int:
    """Count the number of coordinate points in a feature."""
    geom = feature.get("geometry") or feature.get("geom") or {}
    coords = geom.get("coordinates", [])
    geom_type = geom.get("type", "")

    if geom_type == "Point":
        return 1
    elif geom_type == "LineString":
        return len(coords)
    elif geom_type == "Polygon":
        return sum(len(ring) for ring in coords)
    elif geom_type == "MultiPoint":
        return len(coords)
    elif geom_type == "MultiLineString":
        return sum(len(line) for line in coords)
    elif geom_type == "MultiPolygon":
        return sum(sum(len(ring) for ring in polygon) for polygon in coords)

    return 0


async def get_tileset_stats(tileset_id: str) -> dict[str, Any]:
    """
    Get comprehensive statistics for a tileset.

    Retrieves features from the tileset and calculates various statistics
    including feature count, geometry type distribution, and layer breakdown.

    Args:
        tileset_id: UUID of the tileset to analyze

    Returns:
        Dictionary containing:
        - tileset_id: The tileset ID
        - tileset_name: Name of the tileset (if available)
        - feature_count: Total number of features
        - geometry_types: Distribution of geometry types
        - layers: Statistics per layer
        - bounds: Tileset bounds (if available)
        - coordinate_count: Total coordinate points
    """
    with ToolCallLogger(logger, "get_tileset_stats", tileset_id=tileset_id) as log:
        tile_server_url = settings.tile_server_url.rstrip("/")

        logger.debug(f"Fetching stats for tileset {tileset_id}")

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                # First, get tileset info
                tileset_response = await client.get(
                    f"{tile_server_url}/api/tilesets/{tileset_id}",
                    headers=_get_auth_headers(),
                )
                tileset_response.raise_for_status()
                tileset_info = tileset_response.json()

                logger.debug(f"Got tileset info: {tileset_info.get('name')}")

                # Get features for this tileset (up to 1000 for stats)
                features_response = await client.get(
                    f"{tile_server_url}/api/features",
                    params={"tileset_id": tileset_id, "limit": 1000},
                    headers=_get_auth_headers(),
                )
                features_response.raise_for_status()
                features_data = features_response.json()

                # Extract features list
                features = features_data.get("features", [])
                if isinstance(features, dict) and "features" in features:
                    features = features["features"]

                logger.debug(f"Retrieved {len(features)} features for analysis")

                # Calculate statistics
                geometry_types = Counter()
                layer_stats: dict[str, dict] = {}
                total_coordinates = 0

                for feature in features:
                    # Count geometry types
                    geom_type = _extract_geometry_type(feature)
                    geometry_types[geom_type] += 1

                    # Count coordinates
                    total_coordinates += _count_coordinates(feature)

                    # Count by layer
                    layer = feature.get("layer_name", "default")
                    if layer not in layer_stats:
                        layer_stats[layer] = {
                            "feature_count": 0,
                            "geometry_types": Counter(),
                        }
                    layer_stats[layer]["feature_count"] += 1
                    layer_stats[layer]["geometry_types"][geom_type] += 1

                # Convert Counter to dict for JSON serialization
                for layer in layer_stats:
                    layer_stats[layer]["geometry_types"] = dict(
                        layer_stats[layer]["geometry_types"]
                    )

                # Build result
                result = {
                    "tileset_id": tileset_id,
                    "tileset_name": tileset_info.get("name"),
                    "tileset_type": tileset_info.get("type"),
                    "feature_count": len(features),
                    "geometry_types": dict(geometry_types),
                    "layers": layer_stats,
                    "coordinate_count": total_coordinates,
                    "sample_limit": 1000,
                    "is_sample": len(features) >= 1000,
                }

                # Add bounds if available
                if tileset_info.get("bounds"):
                    result["bounds"] = tileset_info["bounds"]

                # Add tileset metadata if available
                if tileset_info.get("min_zoom") is not None:
                    result["zoom_range"] = {
                        "min": tileset_info.get("min_zoom"),
                        "max": tileset_info.get("max_zoom"),
                    }

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error getting tileset stats: {e.response.status_code}",
                    extra={"tileset_id": tileset_id},
                )
                result = handle_api_error(e, {"tileset_id": tileset_id})
                log.set_result(result)
                return result

            except httpx.RequestError as e:
                logger.error(
                    f"Request error getting tileset stats: {e}",
                    extra={"tileset_id": tileset_id},
                )
                result = {
                    "error": f"Request error: {str(e)}",
                    "tileset_id": tileset_id,
                }
                log.set_result(result)
                return result


async def get_feature_distribution(
    tileset_id: str | None = None,
    bbox: str | None = None,
) -> dict[str, Any]:
    """
    Get distribution of feature geometry types.

    Analyzes features and returns the distribution of geometry types
    (Point, LineString, Polygon, etc.) either for a specific tileset
    or within a bounding box.

    Args:
        tileset_id: Optional tileset ID to limit analysis
        bbox: Optional bounding box in format "minx,miny,maxx,maxy"

    Returns:
        Dictionary containing:
        - total_features: Total number of features analyzed
        - geometry_types: Count per geometry type
        - percentages: Percentage per geometry type
        - query: The query parameters used
    """
    with ToolCallLogger(
        logger, "get_feature_distribution",
        tileset_id=tileset_id, bbox=bbox
    ) as log:
        tile_server_url = settings.tile_server_url.rstrip("/")

        logger.debug(f"Getting feature distribution (tileset={tileset_id}, bbox={bbox})")

        # Build query parameters
        params: dict[str, Any] = {"limit": 1000}
        if tileset_id:
            params["tileset_id"] = tileset_id
        if bbox:
            params["bbox"] = bbox

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    f"{tile_server_url}/api/features",
                    params=params,
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                data = response.json()

                # Extract features
                features = data.get("features", [])
                if isinstance(features, dict) and "features" in features:
                    features = features["features"]

                logger.debug(f"Analyzing {len(features)} features")

                # Count geometry types
                geometry_types = Counter()
                for feature in features:
                    geom_type = _extract_geometry_type(feature)
                    geometry_types[geom_type] += 1

                total = len(features)

                # Calculate percentages
                percentages = {}
                if total > 0:
                    for geom_type, count in geometry_types.items():
                        percentages[geom_type] = round(count / total * 100, 2)

                result = {
                    "total_features": total,
                    "geometry_types": dict(geometry_types),
                    "percentages": percentages,
                    "query": {
                        "tileset_id": tileset_id,
                        "bbox": bbox,
                    },
                    "sample_limit": 1000,
                    "is_sample": total >= 1000,
                }

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error getting feature distribution: {e.response.status_code}",
                )
                result = handle_api_error(e, {"tileset_id": tileset_id, "bbox": bbox})
                log.set_result(result)
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error getting feature distribution: {e}")
                result = {
                    "error": f"Request error: {str(e)}",
                }
                log.set_result(result)
                return result


async def get_layer_stats(tileset_id: str) -> dict[str, Any]:
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
        - layers: Per-layer statistics including:
            - feature_count
            - geometry_types
            - percentage of total
    """
    with ToolCallLogger(logger, "get_layer_stats", tileset_id=tileset_id) as log:
        tile_server_url = settings.tile_server_url.rstrip("/")

        logger.debug(f"Getting layer stats for tileset {tileset_id}")

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    f"{tile_server_url}/api/features",
                    params={"tileset_id": tileset_id, "limit": 1000},
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                data = response.json()

                # Extract features
                features = data.get("features", [])
                if isinstance(features, dict) and "features" in features:
                    features = features["features"]

                logger.debug(f"Analyzing {len(features)} features for layer stats")

                # Group by layer
                layers: dict[str, dict] = {}
                for feature in features:
                    layer = feature.get("layer_name", "default")

                    if layer not in layers:
                        layers[layer] = {
                            "feature_count": 0,
                            "geometry_types": Counter(),
                            "properties_sample": [],
                        }

                    layers[layer]["feature_count"] += 1
                    geom_type = _extract_geometry_type(feature)
                    layers[layer]["geometry_types"][geom_type] += 1

                    # Collect sample of property keys (first 3 features per layer)
                    if len(layers[layer]["properties_sample"]) < 3:
                        props = feature.get("properties", {})
                        if props:
                            layers[layer]["properties_sample"].append(list(props.keys()))

                total = len(features)

                # Post-process layers
                for layer_name, layer_data in layers.items():
                    # Convert Counter to dict
                    layer_data["geometry_types"] = dict(layer_data["geometry_types"])

                    # Calculate percentage
                    if total > 0:
                        layer_data["percentage"] = round(
                            layer_data["feature_count"] / total * 100, 2
                        )

                    # Extract unique property keys from samples
                    all_keys = set()
                    for sample in layer_data["properties_sample"]:
                        all_keys.update(sample)
                    layer_data["property_keys"] = sorted(list(all_keys))
                    del layer_data["properties_sample"]

                result = {
                    "tileset_id": tileset_id,
                    "total_features": total,
                    "layer_count": len(layers),
                    "layers": layers,
                    "sample_limit": 1000,
                    "is_sample": total >= 1000,
                }

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error getting layer stats: {e.response.status_code}",
                    extra={"tileset_id": tileset_id},
                )
                result = handle_api_error(e, {"tileset_id": tileset_id})
                log.set_result(result)
                return result

            except httpx.RequestError as e:
                logger.error(
                    f"Request error getting layer stats: {e}",
                    extra={"tileset_id": tileset_id},
                )
                result = {
                    "error": f"Request error: {str(e)}",
                    "tileset_id": tileset_id,
                }
                log.set_result(result)
                return result


async def get_area_stats(
    bbox: str,
    tileset_id: str | None = None,
) -> dict[str, Any]:
    """
    Get statistics for a geographic area defined by a bounding box.

    Calculates area-based statistics including feature density,
    geometry distribution, and coverage metrics.

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
    with ToolCallLogger(
        logger, "get_area_stats",
        bbox=bbox, tileset_id=tileset_id
    ) as log:
        # Parse bbox
        parsed_bbox = _parse_bbox(bbox)
        if not parsed_bbox:
            result = create_error_response(
                "Invalid bbox format. Use 'minx,miny,maxx,maxy'",
                ErrorCode.VALIDATION_ERROR,
                bbox=bbox,
            )
            log.set_result(result)
            return result

        min_lng, min_lat, max_lng, max_lat = parsed_bbox

        # Calculate area
        area_km2 = _calculate_bbox_area_km2(min_lng, min_lat, max_lng, max_lat)

        logger.debug(f"Analyzing area: {area_km2:.2f} km²")

        tile_server_url = settings.tile_server_url.rstrip("/")

        # Build query parameters
        params: dict[str, Any] = {
            "bbox": bbox,
            "limit": 1000,
        }
        if tileset_id:
            params["tileset_id"] = tileset_id

        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            try:
                response = await client.get(
                    f"{tile_server_url}/api/features",
                    params=params,
                    headers=_get_auth_headers(),
                )
                response.raise_for_status()
                data = response.json()

                # Extract features
                features = data.get("features", [])
                if isinstance(features, dict) and "features" in features:
                    features = features["features"]

                logger.debug(f"Found {len(features)} features in area")

                # Calculate statistics
                geometry_types = Counter()
                layers = set()
                tilesets = set()

                for feature in features:
                    geom_type = _extract_geometry_type(feature)
                    geometry_types[geom_type] += 1

                    layer = feature.get("layer_name", "default")
                    layers.add(layer)

                    ts_id = feature.get("tileset_id")
                    if ts_id:
                        tilesets.add(ts_id)

                feature_count = len(features)

                # Calculate density
                density = feature_count / area_km2 if area_km2 > 0 else 0

                result = {
                    "bbox": {
                        "min_lng": min_lng,
                        "min_lat": min_lat,
                        "max_lng": max_lng,
                        "max_lat": max_lat,
                    },
                    "area_km2": round(area_km2, 4),
                    "feature_count": feature_count,
                    "density": {
                        "features_per_km2": round(density, 4),
                        "features_per_100km2": round(density * 100, 2),
                    },
                    "geometry_types": dict(geometry_types),
                    "layers": sorted(list(layers)),
                    "tilesets_found": len(tilesets),
                    "query": {
                        "bbox": bbox,
                        "tileset_id": tileset_id,
                    },
                    "sample_limit": 1000,
                    "is_sample": feature_count >= 1000,
                }

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error getting area stats: {e.response.status_code}",
                )
                result = handle_api_error(e, {"bbox": bbox, "tileset_id": tileset_id})
                log.set_result(result)
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error getting area stats: {e}")
                result = {
                    "error": f"Request error: {str(e)}",
                    "bbox": bbox,
                }
                log.set_result(result)
                return result
