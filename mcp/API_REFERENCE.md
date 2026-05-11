# geo-base MCP Server API Reference

> 🌐 **English**: this page ・ **日本語**: [API_REFERENCE.ja.md](./API_REFERENCE.ja.md)

This document provides detailed API specifications for every tool available on the geo-base MCP server.

## Table of contents

1. [Tileset tools](#tileset-tools)
2. [Feature tools](#feature-tools)
3. [Geocoding tools](#geocoding-tools)
4. [Statistics tools](#statistics-tools)
5. [Spatial analysis tools](#spatial-analysis-tools)
6. [CRUD tools](#crud-tools)
7. [Utility tools](#utility-tools)
8. [Error responses](#error-responses)

---

## Tileset tools

### `list_tilesets`

Retrieves the list of tilesets available from the tile server.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `type` | string | No | null | Filter by tileset type (`vector`, `raster`, `pmtiles`) |
| `is_public` | boolean | No | null | Filter by public/private status |

#### Response

```json
{
  "tilesets": [
    {
      "id": "uuid",
      "name": "Tileset name",
      "description": "Description",
      "type": "vector",
      "format": "pbf",
      "min_zoom": 0,
      "max_zoom": 22,
      "is_public": true
    }
  ],
  "count": 1
}
```

---

### `get_tileset`

Retrieves detailed information for a specific tileset.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tileset_id` | string (UUID) | Yes | UUID of the tileset |

#### Response

```json
{
  "id": "uuid",
  "name": "Tileset name",
  "description": "Description",
  "type": "vector",
  "format": "pbf",
  "min_zoom": 0,
  "max_zoom": 22,
  "bounds": [-180, -90, 180, 90],
  "center": [139.7671, 35.6812],
  "attribution": "© OpenStreetMap",
  "is_public": true,
  "metadata": {},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### `get_tileset_tilejson`

Retrieves the TileJSON metadata for a tileset. Use it to integrate with map clients such as MapLibre GL JS.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tileset_id` | string (UUID) | Yes | UUID of the tileset |

#### Response

```json
{
  "tilejson": "3.0.0",
  "tiles": ["https://example.com/api/tilesets/{id}/tiles/{z}/{x}/{y}.pbf"],
  "bounds": [-180, -90, 180, 90],
  "minzoom": 0,
  "maxzoom": 22,
  "vector_layers": [
    {
      "id": "default",
      "fields": {}
    }
  ]
}
```

---

## Feature tools

### `search_features`

Searches geographic features.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `bbox` | string | No | null | Bounding box `"minx,miny,maxx,maxy"` (WGS84) |
| `layer` | string | No | null | Layer name filter |
| `filter` | string | No | null | Property filter `"key=value"` |
| `limit` | integer | No | 100 | Maximum number of features to return (1-1000) |
| `tileset_id` | string (UUID) | No | null | Restrict to a specific tileset |

#### Response

```json
{
  "features": [
    {
      "id": "uuid",
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [139.7671, 35.6812]
      },
      "properties": {
        "name": "Tokyo Station"
      },
      "layer": "stations",
      "tileset_id": "uuid"
    }
  ],
  "count": 1,
  "query": {
    "bbox": "139.5,35.5,140.0,36.0",
    "layer": null,
    "filter": null,
    "tileset_id": null,
    "limit": 100
  }
}
```

---

### `get_feature`

Retrieves detailed information for a specific feature.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `feature_id` | string (UUID) | Yes | UUID of the feature |

#### Response

```json
{
  "id": "uuid",
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [139.7671, 35.6812]
  },
  "geometry_summary": {
    "type": "Point",
    "coordinate_count": 1
  },
  "properties": {
    "name": "Tokyo Station"
  },
  "layer": "stations",
  "tileset_id": "uuid",
  "tileset_name": "Tokyo Stations",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

### `get_features_in_tile`

Retrieves features that fall inside a specific map tile.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tileset_id` | string (UUID) | Yes | - | UUID of the tileset |
| `z` | integer | Yes | - | Zoom level (0-22) |
| `x` | integer | Yes | - | Tile X coordinate |
| `y` | integer | Yes | - | Tile Y coordinate |
| `layer` | string | No | null | Layer name filter |

#### Response

```json
{
  "features": [...],
  "count": 10,
  "tile": {
    "z": 14,
    "x": 14370,
    "y": 6450,
    "tileset_id": "uuid"
  },
  "tile_bounds": {
    "min_lng": 139.7,
    "min_lat": 35.6,
    "max_lng": 139.8,
    "max_lat": 35.7
  }
}
```

---

## Geocoding tools

### `geocode`

Converts an address or place name into geographic coordinates. Uses the OpenStreetMap Nominatim API.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | Yes | - | Address or place name to search |
| `limit` | integer | No | 5 | Maximum number of results (1-50) |
| `country_codes` | string | No | null | ISO 3166-1 country codes (comma-separated) |
| `language` | string | No | "ja" | Language for the results |

#### Response

```json
{
  "results": [
    {
      "name": "Tokyo Station, Marunouchi, Chiyoda, Tokyo, Japan",
      "latitude": 35.6812,
      "longitude": 139.7671,
      "type": "station",
      "category": "railway",
      "importance": 0.85,
      "place_id": 123456,
      "osm_type": "node",
      "osm_id": 7890,
      "address": {
        "country": "Japan",
        "city": "Chiyoda",
        "road": "Marunouchi"
      },
      "bounds": {
        "south": 35.68,
        "north": 35.69,
        "west": 139.76,
        "east": 139.77
      }
    }
  ],
  "count": 1,
  "query": "Tokyo Station"
}
```

---

### `reverse_geocode`

Converts geographic coordinates into an address.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `latitude` | float | Yes | - | Latitude (-90 to 90) |
| `longitude` | float | Yes | - | Longitude (-180 to 180) |
| `zoom` | integer | No | 18 | Level of detail (0-18) |
| `language` | string | No | "ja" | Language for the results |

**Zoom level guide:**
- 0: Country level
- 10: City/town level
- 14: Neighborhood level
- 16: Street level
- 18: Building level

#### Response

```json
{
  "display_name": "Tokyo Station, Marunouchi, Chiyoda, Tokyo, Japan",
  "coordinates": {
    "latitude": 35.6812,
    "longitude": 139.7671
  },
  "type": "station",
  "category": "railway",
  "place_id": 123456,
  "osm_type": "node",
  "osm_id": 7890,
  "address": {
    "country": "Japan",
    "city": "Chiyoda",
    "road": "Marunouchi"
  },
  "bounds": {
    "south": 35.68,
    "north": 35.69,
    "west": 139.76,
    "east": 139.77
  }
}
```

---

## Statistics tools

### `get_tileset_stats`

Retrieves comprehensive statistics for a tileset.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tileset_id` | string (UUID) | Yes | UUID of the tileset |

#### Response

```json
{
  "tileset_id": "uuid",
  "tileset_name": "Tileset name",
  "tileset_type": "vector",
  "feature_count": 150,
  "geometry_types": {
    "Point": 100,
    "LineString": 30,
    "Polygon": 20
  },
  "layers": {
    "stations": {
      "feature_count": 100,
      "geometry_types": {"Point": 100}
    },
    "routes": {
      "feature_count": 50,
      "geometry_types": {"LineString": 30, "Polygon": 20}
    }
  },
  "coordinate_count": 5000,
  "bounds": [-180, -90, 180, 90],
  "zoom_range": {"min": 0, "max": 22},
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `get_feature_distribution`

Retrieves the distribution of feature geometry types.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tileset_id` | string (UUID) | No | null | Restrict to a specific tileset |
| `bbox` | string | No | null | Bounding box `"minx,miny,maxx,maxy"` |

#### Response

```json
{
  "total_features": 150,
  "geometry_types": {
    "Point": 100,
    "LineString": 30,
    "Polygon": 20
  },
  "percentages": {
    "Point": 66.67,
    "LineString": 20.0,
    "Polygon": 13.33
  },
  "query": {
    "tileset_id": "uuid",
    "bbox": null
  },
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `get_layer_stats`

Retrieves per-layer statistics.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tileset_id` | string (UUID) | Yes | UUID of the tileset |

#### Response

```json
{
  "tileset_id": "uuid",
  "total_features": 150,
  "layer_count": 3,
  "layers": {
    "stations": {
      "feature_count": 100,
      "geometry_types": {"Point": 100},
      "percentage": 66.67,
      "property_keys": ["name", "type", "passengers"]
    },
    "routes": {
      "feature_count": 50,
      "geometry_types": {"LineString": 50},
      "percentage": 33.33,
      "property_keys": ["name", "length"]
    }
  },
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `get_area_stats`

Retrieves statistics for a specified area.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `bbox` | string | Yes | - | Bounding box `"minx,miny,maxx,maxy"` |
| `tileset_id` | string (UUID) | No | null | Restrict to a specific tileset |

#### Response

```json
{
  "bbox": {
    "min_lng": 139.5,
    "min_lat": 35.5,
    "max_lng": 140.0,
    "max_lat": 36.0
  },
  "area_km2": 2500.0,
  "feature_count": 150,
  "density": {
    "features_per_km2": 0.06,
    "features_per_100km2": 6.0
  },
  "geometry_types": {
    "Point": 100,
    "LineString": 50
  },
  "layers": ["stations", "routes"],
  "tilesets_found": 2,
  "query": {
    "bbox": "139.5,35.5,140.0,36.0",
    "tileset_id": null
  },
  "sample_limit": 1000,
  "is_sample": false
}
```

---

## Spatial analysis tools

### `analyze_area`

Runs a comprehensive spatial analysis on a specified area.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `bbox` | string | Yes | - | Bounding box `"minx,miny,maxx,maxy"` |
| `tileset_id` | string (UUID) | No | null | Restrict to a specific tileset |
| `include_density` | boolean | No | true | Include density analysis |
| `include_clustering` | boolean | No | true | Include clustering analysis |

#### Response

```json
{
  "bbox": {
    "min_lng": 139.5,
    "min_lat": 35.5,
    "max_lng": 140.0,
    "max_lat": 36.0
  },
  "area_km2": 2500.0,
  "features": {
    "count": 150,
    "geometry_types": {"Point": 100, "LineString": 50}
  },
  "density": {
    "features_per_km2": 0.06,
    "grid": {
      "size": "3x3",
      "cells": [[10, 20, 15], [25, 30, 20], [10, 15, 5]]
    },
    "hotspots": [
      {"lat": 35.75, "lng": 139.75, "count": 30}
    ]
  },
  "clustering": {
    "threshold_km": 5.0,
    "cluster_count": 5,
    "top_clusters": [
      {"center": {"lat": 35.7, "lng": 139.7}, "member_count": 25}
    ],
    "isolated_features": 10
  },
  "layers": {"stations": 100, "routes": 50},
  "sample_limit": 1000,
  "is_sample": false
}
```

---

### `calculate_distance`

Calculates the distance between two points (Haversine formula).

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lat1` | float | Yes | Latitude of the start point |
| `lng1` | float | Yes | Longitude of the start point |
| `lat2` | float | Yes | Latitude of the end point |
| `lng2` | float | Yes | Longitude of the end point |

#### Response

```json
{
  "distance_km": 15.5,
  "distance_m": 15500,
  "distance_miles": 9.63,
  "bearing": 45.0,
  "bearing_direction": "NE",
  "points": {
    "start": {"latitude": 35.6812, "longitude": 139.7671},
    "end": {"latitude": 35.6580, "longitude": 139.7016}
  }
}
```

---

### `find_nearest_features`

Searches for features near a specified point.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `lat` | float | Yes | - | Latitude of the search center |
| `lng` | float | Yes | - | Longitude of the search center |
| `radius_km` | float | No | 1.0 | Search radius (km) |
| `limit` | integer | No | 10 | Maximum number of results (1-100) |
| `tileset_id` | string (UUID) | No | null | Restrict to a specific tileset |
| `layer` | string | No | null | Layer name filter |

#### Response

```json
{
  "center": {
    "latitude": 35.6812,
    "longitude": 139.7671
  },
  "radius_km": 1.0,
  "features": [
    {
      "id": "uuid",
      "type": "Feature",
      "geometry": {...},
      "properties": {"name": "Tokyo Station"},
      "distance_km": 0.15,
      "distance_m": 150
    }
  ],
  "count": 5
}
```

---

### `get_buffer_zone_features`

Retrieves features inside a ring buffer (donut shape).

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lat` | float | Yes | Latitude of the center point |
| `lng` | float | Yes | Longitude of the center point |
| `inner_radius_km` | float | Yes | Inner radius (km) |
| `outer_radius_km` | float | Yes | Outer radius (km) |
| `tileset_id` | string (UUID) | No | Restrict to a specific tileset |

#### Response

```json
{
  "center": {
    "latitude": 35.6812,
    "longitude": 139.7671
  },
  "inner_radius_km": 1.0,
  "outer_radius_km": 2.0,
  "ring_area_km2": 9.42,
  "features": [...],
  "count": 15,
  "density_per_km2": 1.59
}
```

---

## CRUD tools

> **Note:** All CRUD tools require authentication. Set a valid JWT token in the `API_TOKEN` environment variable.

### `create_tileset`

Creates a new tileset.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `name` | string | Yes | - | Tileset name |
| `type` | string | Yes | - | Type (`vector`, `raster`, `pmtiles`) |
| `format` | string | Yes | - | Format (`pbf`, `png`, `jpg`, `webp`, `geojson`) |
| `description` | string | No | null | Description |
| `min_zoom` | integer | No | 0 | Minimum zoom level (0-22) |
| `max_zoom` | integer | No | 22 | Maximum zoom level (0-22) |
| `bounds` | array | No | null | Bounding box [west, south, east, north] |
| `center` | array | No | null | Center point [longitude, latitude] |
| `attribution` | string | No | null | Attribution text |
| `is_public` | boolean | No | false | Public visibility |
| `metadata` | object | No | null | Additional metadata |

#### Response

```json
{
  "id": "uuid",
  "name": "Tileset name",
  "type": "vector",
  "format": "pbf",
  ...
}
```

---

### `update_tileset`

Updates an existing tileset.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tileset_id` | string (UUID) | Yes | UUID of the tileset to update |
| Other fields | - | No | Same as `create_tileset` (only the specified fields are updated) |

---

### `delete_tileset`

Deletes a tileset and all of its features.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `tileset_id` | string (UUID) | Yes | UUID of the tileset to delete |

#### Response

```json
{
  "success": true,
  "message": "Tileset {uuid} deleted successfully."
}
```

---

### `create_feature`

Creates a new feature in a tileset.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tileset_id` | string (UUID) | Yes | - | UUID of the parent tileset |
| `geometry` | object | Yes | - | GeoJSON geometry object |
| `properties` | object | No | null | Feature properties |
| `layer_name` | string | No | "default" | Layer name |

#### Geometry examples

```json
// Point
{"type": "Point", "coordinates": [139.7671, 35.6812]}

// LineString
{"type": "LineString", "coordinates": [[139.7, 35.6], [139.8, 35.7]]}

// Polygon
{"type": "Polygon", "coordinates": [[[139.7, 35.6], [139.8, 35.6], [139.8, 35.7], [139.7, 35.7], [139.7, 35.6]]]}
```

---

### `update_feature`

Updates an existing feature.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `feature_id` | string (UUID) | Yes | UUID of the feature to update |
| `geometry` | object | No | New geometry |
| `properties` | object | No | New properties (replaces all existing ones) |
| `layer_name` | string | No | New layer name |

---

### `delete_feature`

Deletes a feature.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `feature_id` | string (UUID) | Yes | UUID of the feature to delete |

---

## Utility tools

### `get_tile_url`

Generates the URL for a specific map tile.

#### Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tileset_id` | string (UUID) | Yes | - | UUID of the tileset |
| `z` | integer | Yes | - | Zoom level (0-22) |
| `x` | integer | Yes | - | Tile X coordinate |
| `y` | integer | Yes | - | Tile Y coordinate |
| `format` | string | No | "pbf" | Tile format (`pbf`, `png`, `jpg`, `webp`) |

#### Response

```json
{
  "url": "https://example.com/api/tilesets/{id}/tiles/14/14370/6450.pbf",
  "tileset_id": "uuid",
  "coordinates": {"z": 14, "x": 14370, "y": 6450},
  "format": "pbf"
}
```

---

### `health_check`

Checks the health status of the tile server.

#### Parameters

None.

#### Response

```json
{
  "status": "healthy",
  "database": "ok",
  "pmtiles": "ok",
  "rasterio": "unavailable"
}
```

---

### `get_server_info`

Retrieves the MCP server configuration.

#### Parameters

None.

#### Response

```json
{
  "tile_server_url": "https://geo-base-api.fly.dev",
  "mcp_server_name": "geo-base",
  "mcp_server_version": "1.0.0",
  "environment": "production"
}
```

---

## Error responses

When an error occurs, every tool returns a response with at least the following two fields. All other fields are optional and depend on the error path:

```json
{
  "error": "Error message",            // required
  "code": "ERROR_CODE",                // required, one of the codes below
  "hint": "Resolution hint",           // optional
  "details": { "field": "value" },     // optional, populated by MCPError subclasses
  "detail": "Single-line detail",      // optional, populated by the httpx fallback path
  "status_code": 503,                  // optional, present on HTTP-origin errors
  "response": "...",                   // optional, raw upstream body (truncated to 500 chars)
  "tileset_id": "...",                 // optional, added at the top level by individual tools via `create_error_response(..., tileset_id=...)`
  "feature_id": "..."                  // optional, added at the top level by individual tools via `create_error_response(..., feature_id=...)`
}
```

`details` is a structured object populated by `MCPError` subclasses (`ValidationError` / `APIError` / `NotFoundError` / `AuthenticationError` / `NetworkError`). `NotFoundError` specifically nests `resource_type` and `resource_id` *inside* `details`. `detail` is a single-line string used by the httpx fallback handler in `mcp/errors.py`. Both can appear depending on the error path; prefer `details` when both are present.

Additional top-level context keys (`status_code` / `response` / `tileset_id` / `feature_id`) come from `mcp/errors.py:create_error_response(..., **kwargs)`, called by individual tools when they want to surface IDs at the top level for client convenience. Clients should treat all extra top-level keys as optional and ignore unknown ones to stay forward-compatible.

### Error codes

| Code | Status | Description |
|------|--------|-------------|
| `VALIDATION_ERROR` | active | Invalid input parameter |
| `NOT_FOUND` | active | Resource not found |
| `AUTH_REQUIRED` | active | Authentication required |
| `FORBIDDEN` | active | No access permission |
| `TIMEOUT` | active | Request timed out |
| `NETWORK_ERROR` | active | Network error |
| `CONNECTION_ERROR` | active | Could not connect to the upstream service |
| `SERVER_ERROR` | active | Upstream server error (5xx) |
| `HTTP_ERROR` | active | Other HTTP error |
| `UNKNOWN_ERROR` | active | Unexpected error |
| `INVALID_TOKEN` | reserved | Reserved for future token-validation paths; no current code path emits this. |
| `SERVICE_UNAVAILABLE` | reserved | Reserved for HTTP 503 mapping; not currently emitted by `mcp/errors.py`. |

`active` codes can be returned by the current implementation. `reserved` codes are defined in `ErrorCode` and listed here so clients can match them once the corresponding implementation lands; current `mcp/` does not emit them yet.

### Examples

```json
{
  "error": "Invalid tileset_id format. Expected UUID.",
  "code": "VALIDATION_ERROR",
  "tileset_id": "invalid-id"
}
```

```json
{
  "error": "Feature not found",
  "code": "NOT_FOUND",
  "feature_id": "00000000-0000-0000-0000-000000000000"
}
```

```json
{
  "error": "Authentication required",
  "code": "AUTH_REQUIRED",
  "hint": "This feature may belong to a private tileset. Configure API_TOKEN."
}
```
