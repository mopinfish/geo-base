"""
CRUD tools for geo-base MCP Server

Tools for creating, updating, and deleting tilesets and features.
"""

import httpx
from typing import Optional, Dict, Any, List

from config import get_settings


settings = get_settings()


def _get_headers() -> dict:
    """Get HTTP headers including auth token if available."""
    headers = {
        "Content-Type": "application/json",
    }
    if settings.api_token:
        headers["Authorization"] = f"Bearer {settings.api_token}"
    return headers


# ============================================================
# Tileset CRUD Operations
# ============================================================


async def create_tileset(
    name: str,
    type: str,
    format: str,
    description: Optional[str] = None,
    min_zoom: int = 0,
    max_zoom: int = 22,
    bounds: Optional[List[float]] = None,
    center: Optional[List[float]] = None,
    attribution: Optional[str] = None,
    is_public: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Create a new tileset.
    
    Args:
        name: Tileset name (required)
        type: Tileset type ('vector', 'raster', 'pmtiles')
        format: Tile format ('pbf', 'png', 'jpg', 'webp', 'geojson')
        description: Tileset description
        min_zoom: Minimum zoom level (0-22, default: 0)
        max_zoom: Maximum zoom level (0-22, default: 22)
        bounds: Bounding box [west, south, east, north]
        center: Center point [longitude, latitude] or [lon, lat, zoom]
        attribution: Attribution text
        is_public: Whether the tileset is publicly accessible (default: False)
        metadata: Additional metadata as dictionary
    
    Returns:
        Created tileset object with id, name, etc.
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    
    payload = {
        "name": name,
        "type": type,
        "format": format,
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "is_public": is_public,
    }
    
    if description:
        payload["description"] = description
    if bounds:
        payload["bounds"] = bounds
    if center:
        payload["center"] = center
    if attribution:
        payload["attribution"] = attribution
    if metadata:
        payload["metadata"] = metadata
    
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.post(
                f"{tile_server_url}/api/tilesets",
                json=payload,
                headers=_get_headers(),
            )
            
            if response.status_code == 401:
                return {"error": "Authentication required. Please provide API_TOKEN."}
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            return {
                "error": f"HTTP error {e.response.status_code}: {error_detail}",
            }
        except httpx.HTTPError as e:
            return {"error": f"Network error: {str(e)}"}


async def update_tileset(
    tileset_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    min_zoom: Optional[int] = None,
    max_zoom: Optional[int] = None,
    bounds: Optional[List[float]] = None,
    center: Optional[List[float]] = None,
    attribution: Optional[str] = None,
    is_public: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Update an existing tileset.
    
    Args:
        tileset_id: UUID of the tileset to update
        name: New tileset name
        description: New tileset description
        min_zoom: New minimum zoom level (0-22)
        max_zoom: New maximum zoom level (0-22)
        bounds: New bounding box [west, south, east, north]
        center: New center point [longitude, latitude]
        attribution: New attribution text
        is_public: New public/private status
        metadata: New metadata (replaces existing)
    
    Returns:
        Updated tileset object
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    
    payload = {}
    
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if min_zoom is not None:
        payload["min_zoom"] = min_zoom
    if max_zoom is not None:
        payload["max_zoom"] = max_zoom
    if bounds is not None:
        payload["bounds"] = bounds
    if center is not None:
        payload["center"] = center
    if attribution is not None:
        payload["attribution"] = attribution
    if is_public is not None:
        payload["is_public"] = is_public
    if metadata is not None:
        payload["metadata"] = metadata
    
    if not payload:
        return {"error": "No fields to update"}
    
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.patch(
                f"{tile_server_url}/api/tilesets/{tileset_id}",
                json=payload,
                headers=_get_headers(),
            )
            
            if response.status_code == 401:
                return {"error": "Authentication required. Please provide API_TOKEN."}
            if response.status_code == 403:
                return {"error": "Not authorized to update this tileset."}
            if response.status_code == 404:
                return {"error": f"Tileset {tileset_id} not found."}
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            return {
                "error": f"HTTP error {e.response.status_code}: {error_detail}",
            }
        except httpx.HTTPError as e:
            return {"error": f"Network error: {str(e)}"}


async def delete_tileset(tileset_id: str) -> dict:
    """
    Delete a tileset and all its features.
    
    Args:
        tileset_id: UUID of the tileset to delete
    
    Returns:
        Success or error message
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.delete(
                f"{tile_server_url}/api/tilesets/{tileset_id}",
                headers=_get_headers(),
            )
            
            if response.status_code == 401:
                return {"error": "Authentication required. Please provide API_TOKEN."}
            if response.status_code == 403:
                return {"error": "Not authorized to delete this tileset."}
            if response.status_code == 404:
                return {"error": f"Tileset {tileset_id} not found."}
            if response.status_code == 204:
                return {"success": True, "message": f"Tileset {tileset_id} deleted successfully."}
            
            response.raise_for_status()
            return {"success": True}
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            return {
                "error": f"HTTP error {e.response.status_code}: {error_detail}",
            }
        except httpx.HTTPError as e:
            return {"error": f"Network error: {str(e)}"}


# ============================================================
# Feature CRUD Operations
# ============================================================


async def create_feature(
    tileset_id: str,
    geometry: Dict[str, Any],
    properties: Optional[Dict[str, Any]] = None,
    layer_name: str = "default",
) -> dict:
    """
    Create a new feature in a tileset.
    
    Args:
        tileset_id: UUID of the parent tileset
        geometry: GeoJSON geometry object
                  Examples:
                  - Point: {"type": "Point", "coordinates": [139.7671, 35.6812]}
                  - Polygon: {"type": "Polygon", "coordinates": [[[...]]]}
        properties: Feature properties as dictionary
        layer_name: Layer name for the feature (default: "default")
    
    Returns:
        Created feature as GeoJSON object
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    
    payload = {
        "tileset_id": tileset_id,
        "geometry": geometry,
        "layer_name": layer_name,
    }
    
    if properties:
        payload["properties"] = properties
    
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.post(
                f"{tile_server_url}/api/features",
                json=payload,
                headers=_get_headers(),
            )
            
            if response.status_code == 401:
                return {"error": "Authentication required. Please provide API_TOKEN."}
            if response.status_code == 403:
                return {"error": "Not authorized to add features to this tileset."}
            if response.status_code == 404:
                return {"error": f"Tileset {tileset_id} not found."}
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            return {
                "error": f"HTTP error {e.response.status_code}: {error_detail}",
            }
        except httpx.HTTPError as e:
            return {"error": f"Network error: {str(e)}"}


async def update_feature(
    feature_id: str,
    geometry: Optional[Dict[str, Any]] = None,
    properties: Optional[Dict[str, Any]] = None,
    layer_name: Optional[str] = None,
) -> dict:
    """
    Update an existing feature.
    
    Args:
        feature_id: UUID of the feature to update
        geometry: New GeoJSON geometry object
        properties: New properties (replaces existing)
        layer_name: New layer name
    
    Returns:
        Updated feature as GeoJSON object
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    
    payload = {}
    
    if geometry is not None:
        payload["geometry"] = geometry
    if properties is not None:
        payload["properties"] = properties
    if layer_name is not None:
        payload["layer_name"] = layer_name
    
    if not payload:
        return {"error": "No fields to update"}
    
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.patch(
                f"{tile_server_url}/api/features/{feature_id}",
                json=payload,
                headers=_get_headers(),
            )
            
            if response.status_code == 401:
                return {"error": "Authentication required. Please provide API_TOKEN."}
            if response.status_code == 403:
                return {"error": "Not authorized to update this feature."}
            if response.status_code == 404:
                return {"error": f"Feature {feature_id} not found."}
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            return {
                "error": f"HTTP error {e.response.status_code}: {error_detail}",
            }
        except httpx.HTTPError as e:
            return {"error": f"Network error: {str(e)}"}


async def delete_feature(feature_id: str) -> dict:
    """
    Delete a feature.
    
    Args:
        feature_id: UUID of the feature to delete
    
    Returns:
        Success or error message
    """
    tile_server_url = settings.tile_server_url.rstrip("/")
    
    async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
        try:
            response = await client.delete(
                f"{tile_server_url}/api/features/{feature_id}",
                headers=_get_headers(),
            )
            
            if response.status_code == 401:
                return {"error": "Authentication required. Please provide API_TOKEN."}
            if response.status_code == 403:
                return {"error": "Not authorized to delete this feature."}
            if response.status_code == 404:
                return {"error": f"Feature {feature_id} not found."}
            if response.status_code == 204:
                return {"success": True, "message": f"Feature {feature_id} deleted successfully."}
            
            response.raise_for_status()
            return {"success": True}
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            return {
                "error": f"HTTP error {e.response.status_code}: {error_detail}",
            }
        except httpx.HTTPError as e:
            return {"error": f"Network error: {str(e)}"}
