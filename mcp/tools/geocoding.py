"""
Geocoding tools for geo-base MCP Server.

Uses OpenStreetMap Nominatim API for geocoding and reverse geocoding.
"""

from typing import Optional

import httpx

from logger import get_logger, ToolCallLogger
from validators import (
    validate_latitude,
    validate_longitude,
    validate_non_empty_string,
    validate_range,
)

# Initialize logger
logger = get_logger(__name__)

# Nominatim API base URL
NOMINATIM_URL = "https://nominatim.openstreetmap.org"

# User-Agent header (required by Nominatim)
USER_AGENT = "geo-base-mcp/1.0 (https://github.com/mopinfish/geo-base)"


async def geocode(
    query: str,
    limit: int = 5,
    country_codes: Optional[str] = None,
    language: str = "ja",
) -> dict:
    """
    Convert address/place name to coordinates (geocoding).
    
    Args:
        query: Address or place name to search
        limit: Maximum number of results (1-50, default: 5)
        country_codes: Limit search to specific countries (comma-separated ISO 3166-1 codes)
                      Example: "jp" for Japan, "jp,us" for Japan and US
        language: Preferred language for results (default: "ja" for Japanese)
    
    Returns:
        Dictionary containing:
        - results: List of matching locations with coordinates
        - count: Number of results
        - query: Original search query
    """
    with ToolCallLogger(
        logger, "geocode",
        query=query, limit=limit, country_codes=country_codes, language=language
    ) as log:
        # Validate query
        query_result = validate_non_empty_string(query, "query")
        if not query_result.valid:
            result = query_result.to_error_response(
                results=[],
                count=0,
                query=query,
            )
            log.set_result(result)
            return result
        
        # Validate limit
        limit_result = validate_range(limit, "limit", min_value=1, max_value=50)
        if not limit_result.valid:
            result = limit_result.to_error_response(
                results=[],
                count=0,
                query=query,
            )
            log.set_result(result)
            return result
        validated_limit = limit_result.value
        
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": validated_limit,
            "addressdetails": 1,
            "accept-language": language,
        }
        
        if country_codes:
            params["countrycodes"] = country_codes
        
        headers = {
            "User-Agent": USER_AGENT,
        }
        
        logger.debug(f"Geocoding query: '{query}'", extra={"country_codes": country_codes})
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{NOMINATIM_URL}/search",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                
                logger.debug(f"Nominatim returned {len(data)} results for '{query}'")
                
                results = []
                for item in data:
                    result = {
                        "name": item.get("display_name", ""),
                        "latitude": float(item.get("lat", 0)),
                        "longitude": float(item.get("lon", 0)),
                        "type": item.get("type", ""),
                        "category": item.get("category", ""),
                        "importance": item.get("importance", 0),
                        "place_id": item.get("place_id"),
                        "osm_type": item.get("osm_type"),
                        "osm_id": item.get("osm_id"),
                    }
                    
                    # Add address details if available
                    if "address" in item:
                        result["address"] = item["address"]
                    
                    # Add bounding box if available
                    if "boundingbox" in item:
                        bbox = item["boundingbox"]
                        result["bounds"] = {
                            "south": float(bbox[0]),
                            "north": float(bbox[1]),
                            "west": float(bbox[2]),
                            "east": float(bbox[3]),
                        }
                    
                    results.append(result)
                
                response_data = {
                    "results": results,
                    "count": len(results),
                    "query": query,
                }
                log.set_result(response_data)
                return response_data
                
            except httpx.ProxyError as e:
                logger.warning(f"Proxy error during geocoding: {e}", extra={"query": query})
                result = {
                    "results": [],
                    "count": 0,
                    "query": query,
                    "error": f"Proxy error: {str(e)}. This may be due to network restrictions.",
                }
                log.set_result(result)
                return result
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error during geocoding: {e.response.status_code}",
                    extra={"query": query, "status_code": e.response.status_code},
                )
                result = {
                    "results": [],
                    "count": 0,
                    "query": query,
                    "error": f"HTTP error {e.response.status_code}: {str(e)}",
                }
                log.set_result(result)
                return result
            except httpx.HTTPError as e:
                logger.error(f"Network error during geocoding: {e}", extra={"query": query})
                result = {
                    "results": [],
                    "count": 0,
                    "query": query,
                    "error": f"Network error: {str(e)}",
                }
                log.set_result(result)
                return result
            except Exception as e:
                logger.error(
                    f"Unexpected error during geocoding: {type(e).__name__}: {e}",
                    extra={"query": query},
                    exc_info=True,
                )
                result = {
                    "results": [],
                    "count": 0,
                    "query": query,
                    "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
                }
                log.set_result(result)
                return result


async def reverse_geocode(
    latitude: float,
    longitude: float,
    zoom: int = 18,
    language: str = "ja",
) -> dict:
    """
    Convert coordinates to address (reverse geocoding).
    
    Args:
        latitude: Latitude in decimal degrees (WGS84), must be between -90 and 90
        longitude: Longitude in decimal degrees (WGS84), must be between -180 and 180
        zoom: Level of detail for the address (0-18, default: 18)
              0 = country, 10 = city, 14 = suburb, 16 = street, 18 = building
        language: Preferred language for results (default: "ja" for Japanese)
    
    Returns:
        Dictionary containing:
        - address: Structured address components
        - display_name: Full formatted address string
        - coordinates: Input coordinates
        - place_id: OpenStreetMap place ID
    """
    with ToolCallLogger(
        logger, "reverse_geocode",
        latitude=latitude, longitude=longitude, zoom=zoom, language=language
    ) as log:
        # Validate latitude
        lat_result = validate_latitude(latitude, "latitude")
        if not lat_result.valid:
            result = lat_result.to_error_response(
                address=None,
                display_name=None,
                coordinates={"latitude": latitude, "longitude": longitude},
            )
            log.set_result(result)
            return result
        validated_lat = lat_result.value
        
        # Validate longitude
        lng_result = validate_longitude(longitude, "longitude")
        if not lng_result.valid:
            result = lng_result.to_error_response(
                address=None,
                display_name=None,
                coordinates={"latitude": latitude, "longitude": longitude},
            )
            log.set_result(result)
            return result
        validated_lng = lng_result.value
        
        # Validate zoom
        zoom_result = validate_range(zoom, "zoom", min_value=0, max_value=18)
        if not zoom_result.valid:
            result = zoom_result.to_error_response(
                address=None,
                display_name=None,
                coordinates={"latitude": latitude, "longitude": longitude},
            )
            log.set_result(result)
            return result
        validated_zoom = zoom_result.value
        
        params = {
            "lat": validated_lat,
            "lon": validated_lng,
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": validated_zoom,
            "accept-language": language,
        }
        
        headers = {
            "User-Agent": USER_AGENT,
        }
        
        logger.debug(
            f"Reverse geocoding: lat={validated_lat}, lon={validated_lng}",
            extra={"latitude": validated_lat, "longitude": validated_lng, "zoom": validated_zoom},
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{NOMINATIM_URL}/reverse",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    logger.warning(
                        f"Nominatim returned error for reverse geocoding: {data['error']}",
                        extra={"latitude": validated_lat, "longitude": validated_lng},
                    )
                    result = {
                        "address": None,
                        "display_name": None,
                        "coordinates": {
                            "latitude": validated_lat,
                            "longitude": validated_lng,
                        },
                        "error": data["error"],
                    }
                    log.set_result(result)
                    return result
                
                logger.debug(
                    f"Reverse geocoding successful: {data.get('display_name', '')[:50]}...",
                    extra={"latitude": validated_lat, "longitude": validated_lng},
                )
                
                result = {
                    "display_name": data.get("display_name", ""),
                    "coordinates": {
                        "latitude": validated_lat,
                        "longitude": validated_lng,
                    },
                    "type": data.get("type", ""),
                    "category": data.get("category", ""),
                    "place_id": data.get("place_id"),
                    "osm_type": data.get("osm_type"),
                    "osm_id": data.get("osm_id"),
                }
                
                # Add structured address
                if "address" in data:
                    result["address"] = data["address"]
                
                # Add bounding box if available
                if "boundingbox" in data:
                    bbox = data["boundingbox"]
                    result["bounds"] = {
                        "south": float(bbox[0]),
                        "north": float(bbox[1]),
                        "west": float(bbox[2]),
                        "east": float(bbox[3]),
                    }
                
                log.set_result(result)
                return result
                
            except httpx.ProxyError as e:
                logger.warning(
                    f"Proxy error during reverse geocoding: {e}",
                    extra={"latitude": validated_lat, "longitude": validated_lng},
                )
                result = {
                    "address": None,
                    "display_name": None,
                    "coordinates": {
                        "latitude": validated_lat,
                        "longitude": validated_lng,
                    },
                    "error": f"Proxy error: {str(e)}. This may be due to network restrictions.",
                }
                log.set_result(result)
                return result
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error during reverse geocoding: {e.response.status_code}",
                    extra={
                        "latitude": validated_lat,
                        "longitude": validated_lng,
                        "status_code": e.response.status_code,
                    },
                )
                result = {
                    "address": None,
                    "display_name": None,
                    "coordinates": {
                        "latitude": validated_lat,
                        "longitude": validated_lng,
                    },
                    "error": f"HTTP error {e.response.status_code}: {str(e)}",
                }
                log.set_result(result)
                return result
            except httpx.HTTPError as e:
                logger.error(
                    f"Network error during reverse geocoding: {e}",
                    extra={"latitude": validated_lat, "longitude": validated_lng},
                )
                result = {
                    "address": None,
                    "display_name": None,
                    "coordinates": {
                        "latitude": validated_lat,
                        "longitude": validated_lng,
                    },
                    "error": f"Network error: {str(e)}",
                }
                log.set_result(result)
                return result
            except Exception as e:
                logger.error(
                    f"Unexpected error during reverse geocoding: {type(e).__name__}: {e}",
                    extra={"latitude": validated_lat, "longitude": validated_lng},
                    exc_info=True,
                )
                result = {
                    "address": None,
                    "display_name": None,
                    "coordinates": {
                        "latitude": validated_lat,
                        "longitude": validated_lng,
                    },
                    "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
                }
                log.set_result(result)
                return result
