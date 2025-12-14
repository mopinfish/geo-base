# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-14

### 🎉 First Stable Release

geo-base MCP Server v1.0.0 is now production-ready with a comprehensive set of geographic data tools.

### Added

#### Core Tools (16 total)
- **Tileset Tools**: `list_tilesets`, `get_tileset`, `get_tileset_tilejson`
- **Feature Tools**: `search_features`, `get_feature`, `get_features_in_tile`
- **Geocoding Tools**: `geocode`, `reverse_geocode`
- **Statistics Tools**: `get_tileset_stats`, `get_feature_distribution`, `get_layer_stats`, `get_area_stats`
- **Spatial Analysis Tools**: `analyze_area`, `calculate_distance`, `find_nearest_features`, `get_buffer_zone_features`
- **CRUD Tools**: `create_tileset`, `update_tileset`, `delete_tileset`, `create_feature`, `update_feature`, `delete_feature`
- **Utility Tools**: `get_tile_url`, `health_check`, `get_server_info`

#### Infrastructure
- Automatic retry with exponential backoff for transient network errors
- Comprehensive input validation using dedicated validators module
- Structured logging with tool call tracking
- Standardized error handling with error codes
- Support for both stdio (local) and SSE (remote) transport modes

#### Documentation
- Complete API reference with all parameters and response formats
- Detailed README with installation and usage instructions
- Code examples for all tools

### Changed

- Upgraded version to 1.0.0
- Improved error messages with actionable hints
- Enhanced docstrings with usage examples

### Technical Improvements

- `retry.py`: Configurable retry logic with `RETRY_MAX_ATTEMPTS`, `RETRY_MIN_WAIT`, `RETRY_MAX_WAIT`
- `validators.py`: Centralized validation for UUIDs, bboxes, coordinates, and more
- `errors.py`: Standardized error response format with error codes
- `logger.py`: Structured logging with ToolCallLogger context manager

---

## [0.2.5] - 2024-12-14

### Added
- Spatial analysis tools (`analyze_area`, `calculate_distance`, `find_nearest_features`, `get_buffer_zone_features`)
- Retry functionality using tenacity library
- Comprehensive input validators module

### Changed
- Refactored error handling to use centralized errors.py module
- Improved logging with structured context

---

## [0.2.0] - 2024-12-13

### Added
- Statistics tools (`get_tileset_stats`, `get_feature_distribution`, `get_layer_stats`, `get_area_stats`)
- Custom logging module with ToolCallLogger
- Comprehensive error handling module

### Changed
- Updated all tools to use new logging system
- Standardized API error responses

---

## [0.1.0] - 2024-12-12

### Added
- Initial MCP server implementation
- Tileset tools (list, get, tilejson)
- Feature tools (search, get)
- Geocoding tools (geocode, reverse_geocode)
- CRUD tools for tilesets and features
- Utility tools (tile_url, health_check, server_info)
- Fly.io deployment support
- Claude Desktop configuration examples

---

## Migration Guide

### From 0.2.x to 1.0.0

No breaking changes. Simply update and enjoy the new features:

```bash
cd mcp
git pull origin main
uv sync
```

For Claude Desktop users, no configuration changes are required.

### Environment Variables

New optional environment variables in 1.0.0:

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRY_MAX_ATTEMPTS` | `3` | Maximum retry attempts |
| `RETRY_MIN_WAIT` | `1` | Minimum wait between retries (seconds) |
| `RETRY_MAX_WAIT` | `10` | Maximum wait between retries (seconds) |
