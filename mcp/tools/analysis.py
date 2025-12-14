"""
Spatial analysis tools for geo-base MCP Server.

Provides tools for spatial analysis operations including:
- Area analysis within bounding boxes
- Distance calculations between points
- Nearest neighbor searches
- Buffer zone analysis
- Spatial clustering
"""

import math
from typing import Any

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


def _haversine_distance(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
) -> float:
    """
    Calculate the great-circle distance between two points using Haversine formula.

    Args:
        lat1, lng1: First point coordinates in decimal degrees
        lat2, lng2: Second point coordinates in decimal degrees

    Returns:
        Distance in kilometers
    """
    R = 6371.0  # Earth's radius in km

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    # Haversine formula
    a = math.sin(d_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def _get_feature_centroid(feature: dict) -> tuple[float, float] | None:
    """
    Get the centroid coordinates of a feature.

    For Point: returns the coordinates directly
    For other geometries: calculates approximate centroid

    Args:
        feature: GeoJSON feature

    Returns:
        Tuple of (latitude, longitude) or None if cannot be calculated
    """
    geom = feature.get("geometry") or feature.get("geom") or {}
    geom_type = geom.get("type", "")
    coords = geom.get("coordinates", [])

    if not coords:
        return None

    if geom_type == "Point":
        return (coords[1], coords[0])  # (lat, lng)

    elif geom_type == "LineString":
        # Use midpoint
        if len(coords) >= 2:
            mid_idx = len(coords) // 2
            return (coords[mid_idx][1], coords[mid_idx][0])

    elif geom_type == "Polygon":
        # Calculate centroid of first ring
        if coords and len(coords[0]) > 0:
            ring = coords[0]
            avg_lng = sum(p[0] for p in ring) / len(ring)
            avg_lat = sum(p[1] for p in ring) / len(ring)
            return (avg_lat, avg_lng)

    elif geom_type == "MultiPoint":
        if coords:
            avg_lng = sum(p[0] for p in coords) / len(coords)
            avg_lat = sum(p[1] for p in coords) / len(coords)
            return (avg_lat, avg_lng)

    elif geom_type == "MultiPolygon":
        # Use first polygon's centroid
        if coords and coords[0] and len(coords[0][0]) > 0:
            ring = coords[0][0]
            avg_lng = sum(p[0] for p in ring) / len(ring)
            avg_lat = sum(p[1] for p in ring) / len(ring)
            return (avg_lat, avg_lng)

    return None


def _expand_bbox(
    min_lng: float, min_lat: float,
    max_lng: float, max_lat: float,
    buffer_km: float,
) -> tuple[float, float, float, float]:
    """
    Expand a bounding box by a buffer distance in kilometers.

    Args:
        min_lng, min_lat, max_lng, max_lat: Original bbox coordinates
        buffer_km: Buffer distance in kilometers

    Returns:
        Expanded bbox as (min_lng, min_lat, max_lng, max_lat)
    """
    # Approximate degrees per km at the center latitude
    center_lat = (min_lat + max_lat) / 2
    deg_per_km_lat = 1 / 111.0  # ~111 km per degree latitude
    deg_per_km_lng = 1 / (111.0 * math.cos(math.radians(center_lat)))

    buffer_lat = buffer_km * deg_per_km_lat
    buffer_lng = buffer_km * deg_per_km_lng

    return (
        min_lng - buffer_lng,
        min_lat - buffer_lat,
        max_lng + buffer_lng,
        max_lat + buffer_lat,
    )


async def analyze_area(
    bbox: str,
    tileset_id: str | None = None,
    include_density: bool = True,
    include_clustering: bool = True,
) -> dict[str, Any]:
    """
    Perform comprehensive spatial analysis on a geographic area.

    Analyzes features within the bounding box and provides:
    - Feature counts and distribution
    - Spatial density analysis
    - Simple clustering based on proximity
    - Coverage metrics

    Args:
        bbox: Bounding box in format "minx,miny,maxx,maxy" (WGS84)
              Example: "139.5,35.5,140.0,36.0" for Tokyo area
        tileset_id: Optional tileset ID to limit analysis
        include_density: Whether to calculate density metrics (default: True)
        include_clustering: Whether to perform clustering analysis (default: True)

    Returns:
        Dictionary containing:
        - bbox: Parsed bounding box
        - area_km2: Area in square kilometers
        - features: Feature summary
        - density: Density metrics (if enabled)
        - clusters: Cluster analysis (if enabled)
        - layers: Layer breakdown
    """
    with ToolCallLogger(
        logger, "analyze_area",
        bbox=bbox, tileset_id=tileset_id,
        include_density=include_density, include_clustering=include_clustering
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
        R = 6371.0
        lat1 = math.radians(min_lat)
        lat2 = math.radians(max_lat)
        d_lat = lat2 - lat1
        d_lng = math.radians(max_lng - min_lng)
        avg_lat = (lat1 + lat2) / 2
        height_km = d_lat * R
        width_km = d_lng * R * math.cos(avg_lat)
        area_km2 = abs(width_km * height_km)

        logger.debug(f"Analyzing area of {area_km2:.2f} km²")

        tile_server_url = settings.tile_server_url.rstrip("/")

        # Build query
        params: dict[str, Any] = {"bbox": bbox, "limit": 1000}
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

                logger.debug(f"Found {len(features)} features for analysis")

                # Basic feature analysis
                geometry_types: dict[str, int] = {}
                layers: dict[str, int] = {}
                centroids: list[tuple[float, float, str]] = []  # (lat, lng, id)

                for feature in features:
                    # Count geometry types
                    geom = feature.get("geometry") or feature.get("geom") or {}
                    geom_type = geom.get("type", "Unknown")
                    geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1

                    # Count layers
                    layer = feature.get("layer_name", "default")
                    layers[layer] = layers.get(layer, 0) + 1

                    # Collect centroids for clustering
                    if include_clustering:
                        centroid = _get_feature_centroid(feature)
                        if centroid:
                            centroids.append((centroid[0], centroid[1], feature.get("id", "")))

                feature_count = len(features)

                # Build result
                result: dict[str, Any] = {
                    "bbox": {
                        "min_lng": min_lng,
                        "min_lat": min_lat,
                        "max_lng": max_lng,
                        "max_lat": max_lat,
                    },
                    "area_km2": round(area_km2, 4),
                    "features": {
                        "count": feature_count,
                        "geometry_types": geometry_types,
                    },
                    "layers": layers,
                }

                # Density analysis
                if include_density and area_km2 > 0:
                    density_per_km2 = feature_count / area_km2

                    # Calculate grid density (divide area into cells)
                    grid_size = 3  # 3x3 grid
                    cell_width = (max_lng - min_lng) / grid_size
                    cell_height = (max_lat - min_lat) / grid_size

                    density_grid: list[list[int]] = [
                        [0 for _ in range(grid_size)] for _ in range(grid_size)
                    ]

                    for feature in features:
                        centroid = _get_feature_centroid(feature)
                        if centroid:
                            lat, lng = centroid
                            col = min(int((lng - min_lng) / cell_width), grid_size - 1)
                            row = min(int((lat - min_lat) / cell_height), grid_size - 1)
                            if 0 <= row < grid_size and 0 <= col < grid_size:
                                density_grid[row][col] += 1

                    # Find hotspots (cells with above-average density)
                    avg_per_cell = feature_count / (grid_size * grid_size)
                    hotspots = []
                    for row in range(grid_size):
                        for col in range(grid_size):
                            if density_grid[row][col] > avg_per_cell * 1.5:
                                cell_center_lng = min_lng + (col + 0.5) * cell_width
                                cell_center_lat = min_lat + (row + 0.5) * cell_height
                                hotspots.append({
                                    "lat": round(cell_center_lat, 6),
                                    "lng": round(cell_center_lng, 6),
                                    "count": density_grid[row][col],
                                })

                    result["density"] = {
                        "features_per_km2": round(density_per_km2, 4),
                        "grid": {
                            "size": f"{grid_size}x{grid_size}",
                            "cells": density_grid,
                        },
                        "hotspots": hotspots,
                    }

                # Clustering analysis (simple proximity-based)
                if include_clustering and centroids:
                    # Simple clustering: group nearby points
                    cluster_threshold_km = max(0.5, math.sqrt(area_km2) / 10)
                    clusters: list[dict] = []
                    assigned = set()

                    for i, (lat1, lng1, id1) in enumerate(centroids):
                        if i in assigned:
                            continue

                        cluster_members = [id1]
                        assigned.add(i)
                        cluster_lat_sum = lat1
                        cluster_lng_sum = lng1

                        for j, (lat2, lng2, id2) in enumerate(centroids):
                            if j in assigned:
                                continue
                            distance = _haversine_distance(lat1, lng1, lat2, lng2)
                            if distance <= cluster_threshold_km:
                                cluster_members.append(id2)
                                assigned.add(j)
                                cluster_lat_sum += lat2
                                cluster_lng_sum += lng2

                        if len(cluster_members) >= 2:  # Only report clusters of 2+
                            clusters.append({
                                "center": {
                                    "lat": round(cluster_lat_sum / len(cluster_members), 6),
                                    "lng": round(cluster_lng_sum / len(cluster_members), 6),
                                },
                                "member_count": len(cluster_members),
                            })

                    # Sort by size
                    clusters.sort(key=lambda x: x["member_count"], reverse=True)

                    result["clustering"] = {
                        "threshold_km": round(cluster_threshold_km, 3),
                        "cluster_count": len(clusters),
                        "top_clusters": clusters[:10],  # Top 10
                        "isolated_features": len(centroids) - sum(c["member_count"] for c in clusters),
                    }

                result["sample_limit"] = 1000
                result["is_sample"] = feature_count >= 1000

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error analyzing area: {e.response.status_code}")
                result = handle_api_error(e, {"bbox": bbox, "tileset_id": tileset_id})
                log.set_result(result)
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error analyzing area: {e}")
                result = {"error": f"Request error: {str(e)}", "bbox": bbox}
                log.set_result(result)
                return result


async def calculate_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> dict[str, Any]:
    """
    Calculate the distance between two geographic points.

    Uses the Haversine formula for great-circle distance calculation,
    which provides accurate results for most practical purposes.

    Args:
        lat1: Latitude of first point in decimal degrees
        lng1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lng2: Longitude of second point in decimal degrees

    Returns:
        Dictionary containing:
        - distance_km: Distance in kilometers
        - distance_m: Distance in meters
        - distance_miles: Distance in miles
        - bearing: Initial bearing from point 1 to point 2
        - points: The input coordinates
    """
    with ToolCallLogger(
        logger, "calculate_distance",
        lat1=lat1, lng1=lng1, lat2=lat2, lng2=lng2
    ) as log:
        # Validate coordinates
        if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
            result = create_error_response(
                "Latitude must be between -90 and 90",
                ErrorCode.VALIDATION_ERROR,
            )
            log.set_result(result)
            return result

        if not (-180 <= lng1 <= 180 and -180 <= lng2 <= 180):
            result = create_error_response(
                "Longitude must be between -180 and 180",
                ErrorCode.VALIDATION_ERROR,
            )
            log.set_result(result)
            return result

        # Calculate distance
        distance_km = _haversine_distance(lat1, lng1, lat2, lng2)

        # Calculate initial bearing
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        d_lng = math.radians(lng2 - lng1)

        x = math.sin(d_lng) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lng)

        bearing = math.atan2(x, y)
        bearing_deg = (math.degrees(bearing) + 360) % 360

        result = {
            "distance_km": round(distance_km, 6),
            "distance_m": round(distance_km * 1000, 2),
            "distance_miles": round(distance_km * 0.621371, 6),
            "bearing": round(bearing_deg, 2),
            "bearing_direction": _bearing_to_direction(bearing_deg),
            "points": {
                "from": {"lat": lat1, "lng": lng1},
                "to": {"lat": lat2, "lng": lng2},
            },
        }

        log.set_result(result)
        return result


def _bearing_to_direction(bearing: float) -> str:
    """Convert bearing in degrees to compass direction."""
    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW",
    ]
    index = round(bearing / 22.5) % 16
    return directions[index]


async def find_nearest_features(
    lat: float,
    lng: float,
    radius_km: float = 1.0,
    limit: int = 10,
    tileset_id: str | None = None,
    layer: str | None = None,
) -> dict[str, Any]:
    """
    Find features nearest to a given point.

    Searches for features within a radius and returns them sorted by distance.

    Args:
        lat: Latitude of the search center in decimal degrees
        lng: Longitude of the search center in decimal degrees
        radius_km: Search radius in kilometers (default: 1.0)
        limit: Maximum number of results (default: 10, max: 100)
        tileset_id: Optional tileset ID to limit search
        layer: Optional layer name to filter

    Returns:
        Dictionary containing:
        - center: The search center point
        - radius_km: The search radius
        - features: List of features with distance, sorted by proximity
        - count: Number of features found
    """
    with ToolCallLogger(
        logger, "find_nearest_features",
        lat=lat, lng=lng, radius_km=radius_km, limit=limit,
        tileset_id=tileset_id, layer=layer
    ) as log:
        # Validate coordinates
        if not (-90 <= lat <= 90):
            result = create_error_response(
                "Latitude must be between -90 and 90",
                ErrorCode.VALIDATION_ERROR,
            )
            log.set_result(result)
            return result

        if not (-180 <= lng <= 180):
            result = create_error_response(
                "Longitude must be between -180 and 180",
                ErrorCode.VALIDATION_ERROR,
            )
            log.set_result(result)
            return result

        # Cap limit
        limit = min(limit, 100)

        # Create expanded bbox for search
        expanded_bbox = _expand_bbox(lng, lat, lng, lat, radius_km * 1.5)
        bbox_str = f"{expanded_bbox[0]},{expanded_bbox[1]},{expanded_bbox[2]},{expanded_bbox[3]}"

        logger.debug(f"Searching for features within {radius_km}km of ({lat}, {lng})")

        tile_server_url = settings.tile_server_url.rstrip("/")

        # Build query
        params: dict[str, Any] = {"bbox": bbox_str, "limit": 500}
        if tileset_id:
            params["tileset_id"] = tileset_id
        if layer:
            params["layer"] = layer

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

                logger.debug(f"Retrieved {len(features)} candidates")

                # Calculate distances and filter by radius
                features_with_distance = []
                for feature in features:
                    centroid = _get_feature_centroid(feature)
                    if centroid:
                        distance = _haversine_distance(lat, lng, centroid[0], centroid[1])
                        if distance <= radius_km:
                            features_with_distance.append({
                                "id": feature.get("id"),
                                "distance_km": round(distance, 6),
                                "distance_m": round(distance * 1000, 2),
                                "geometry_type": (feature.get("geometry") or feature.get("geom") or {}).get("type"),
                                "layer": feature.get("layer_name"),
                                "properties": feature.get("properties", {}),
                                "centroid": {
                                    "lat": centroid[0],
                                    "lng": centroid[1],
                                },
                            })

                # Sort by distance
                features_with_distance.sort(key=lambda x: x["distance_km"])

                # Apply limit
                features_with_distance = features_with_distance[:limit]

                result = {
                    "center": {"lat": lat, "lng": lng},
                    "radius_km": radius_km,
                    "features": features_with_distance,
                    "count": len(features_with_distance),
                    "query": {
                        "tileset_id": tileset_id,
                        "layer": layer,
                        "limit": limit,
                    },
                }

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error finding nearest features: {e.response.status_code}")
                result = handle_api_error(e, {"lat": lat, "lng": lng})
                log.set_result(result)
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error finding nearest features: {e}")
                result = {"error": f"Request error: {str(e)}"}
                log.set_result(result)
                return result


async def get_buffer_zone_features(
    lat: float,
    lng: float,
    inner_radius_km: float,
    outer_radius_km: float,
    tileset_id: str | None = None,
) -> dict[str, Any]:
    """
    Get features within a ring buffer zone (donut shape) around a point.

    Useful for analyzing features at specific distances from a point,
    such as finding features between 1-2 km from a location.

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
        - features: List of features in the buffer zone with distances
        - count: Number of features found
        - ring_area_km2: Area of the ring buffer
    """
    with ToolCallLogger(
        logger, "get_buffer_zone_features",
        lat=lat, lng=lng, inner_radius_km=inner_radius_km,
        outer_radius_km=outer_radius_km, tileset_id=tileset_id
    ) as log:
        # Validate
        if inner_radius_km >= outer_radius_km:
            result = create_error_response(
                "inner_radius_km must be less than outer_radius_km",
                ErrorCode.VALIDATION_ERROR,
            )
            log.set_result(result)
            return result

        if not (-90 <= lat <= 90):
            result = create_error_response(
                "Latitude must be between -90 and 90",
                ErrorCode.VALIDATION_ERROR,
            )
            log.set_result(result)
            return result

        # Calculate ring area
        ring_area_km2 = math.pi * (outer_radius_km ** 2 - inner_radius_km ** 2)

        # Create bbox for outer radius
        expanded_bbox = _expand_bbox(lng, lat, lng, lat, outer_radius_km * 1.5)
        bbox_str = f"{expanded_bbox[0]},{expanded_bbox[1]},{expanded_bbox[2]},{expanded_bbox[3]}"

        logger.debug(f"Searching buffer zone {inner_radius_km}-{outer_radius_km}km around ({lat}, {lng})")

        tile_server_url = settings.tile_server_url.rstrip("/")

        params: dict[str, Any] = {"bbox": bbox_str, "limit": 1000}
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

                features = data.get("features", [])
                if isinstance(features, dict) and "features" in features:
                    features = features["features"]

                # Filter to ring buffer
                buffer_features = []
                for feature in features:
                    centroid = _get_feature_centroid(feature)
                    if centroid:
                        distance = _haversine_distance(lat, lng, centroid[0], centroid[1])
                        if inner_radius_km <= distance <= outer_radius_km:
                            buffer_features.append({
                                "id": feature.get("id"),
                                "distance_km": round(distance, 6),
                                "geometry_type": (feature.get("geometry") or feature.get("geom") or {}).get("type"),
                                "layer": feature.get("layer_name"),
                                "properties": feature.get("properties", {}),
                            })

                # Sort by distance
                buffer_features.sort(key=lambda x: x["distance_km"])

                density = len(buffer_features) / ring_area_km2 if ring_area_km2 > 0 else 0

                result = {
                    "center": {"lat": lat, "lng": lng},
                    "inner_radius_km": inner_radius_km,
                    "outer_radius_km": outer_radius_km,
                    "ring_area_km2": round(ring_area_km2, 4),
                    "features": buffer_features,
                    "count": len(buffer_features),
                    "density_per_km2": round(density, 4),
                    "query": {"tileset_id": tileset_id},
                }

                log.set_result(result)
                return result

            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error getting buffer zone: {e.response.status_code}")
                result = handle_api_error(e, {"lat": lat, "lng": lng})
                log.set_result(result)
                return result

            except httpx.RequestError as e:
                logger.error(f"Request error getting buffer zone: {e}")
                result = {"error": f"Request error: {str(e)}"}
                log.set_result(result)
                return result
