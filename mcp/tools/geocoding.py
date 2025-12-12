"""
Geocoding tools for geo-base MCP Server

Uses OpenStreetMap Nominatim API for geocoding and reverse geocoding.
"""

import httpx
from typing import Optional

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
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": min(max(1, limit), 50),  # Clamp between 1 and 50
        "addressdetails": 1,
        "accept-language": language,
    }
    
    if country_codes:
        params["countrycodes"] = country_codes
    
    headers = {
        "User-Agent": USER_AGENT,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{NOMINATIM_URL}/search",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            
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
            
            return {
                "results": results,
                "count": len(results),
                "query": query,
            }
            
        except httpx.ProxyError as e:
            return {
                "results": [],
                "count": 0,
                "query": query,
                "error": f"Proxy error: {str(e)}. This may be due to network restrictions.",
            }
        except httpx.HTTPStatusError as e:
            return {
                "results": [],
                "count": 0,
                "query": query,
                "error": f"HTTP error {e.response.status_code}: {str(e)}",
            }
        except httpx.HTTPError as e:
            return {
                "results": [],
                "count": 0,
                "query": query,
                "error": f"Network error: {str(e)}",
            }
        except Exception as e:
            return {
                "results": [],
                "count": 0,
                "query": query,
                "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
            }


async def reverse_geocode(
    latitude: float,
    longitude: float,
    zoom: int = 18,
    language: str = "ja",
) -> dict:
    """
    Convert coordinates to address (reverse geocoding).
    
    Args:
        latitude: Latitude in decimal degrees (WGS84)
        longitude: Longitude in decimal degrees (WGS84)
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
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": min(max(0, zoom), 18),  # Clamp between 0 and 18
        "accept-language": language,
    }
    
    headers = {
        "User-Agent": USER_AGENT,
    }
    
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
                return {
                    "address": None,
                    "display_name": None,
                    "coordinates": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "error": data["error"],
                }
            
            result = {
                "display_name": data.get("display_name", ""),
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
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
            
            return result
            
        except httpx.ProxyError as e:
            return {
                "address": None,
                "display_name": None,
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "error": f"Proxy error: {str(e)}. This may be due to network restrictions.",
            }
        except httpx.HTTPStatusError as e:
            return {
                "address": None,
                "display_name": None,
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "error": f"HTTP error {e.response.status_code}: {str(e)}",
            }
        except httpx.HTTPError as e:
            return {
                "address": None,
                "display_name": None,
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "error": f"Network error: {str(e)}",
            }
        except Exception as e:
            return {
                "address": None,
                "display_name": None,
                "coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
            }
