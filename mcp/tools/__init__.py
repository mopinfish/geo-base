"""
MCP Tools for geo-base.

This package provides tools for interacting with the geo-base tile server API.

Modules:
    tilesets: Tileset listing and retrieval
    features: Feature search and retrieval
    geocoding: Address/coordinate conversion
    crud: Create, update, delete operations
    stats: Statistics and analysis
    analysis: Spatial analysis tools
"""

from tools.tilesets import (
    list_tilesets,
    get_tileset,
    get_tileset_tilejson,
)

from tools.features import (
    search_features,
    get_feature,
    get_features_in_tile,
)

from tools.geocoding import (
    geocode,
    reverse_geocode,
)

from tools.crud import (
    create_tileset,
    update_tileset,
    delete_tileset,
    create_feature,
    update_feature,
    delete_feature,
)

from tools.stats import (
    get_tileset_stats,
    get_feature_distribution,
    get_layer_stats,
    get_area_stats,
)

from tools.analysis import (
    analyze_area,
    calculate_distance,
    find_nearest_features,
    get_buffer_zone_features,
)

__all__ = [
    # Tilesets
    "list_tilesets",
    "get_tileset",
    "get_tileset_tilejson",
    # Features
    "search_features",
    "get_feature",
    "get_features_in_tile",
    # Geocoding
    "geocode",
    "reverse_geocode",
    # CRUD
    "create_tileset",
    "update_tileset",
    "delete_tileset",
    "create_feature",
    "update_feature",
    "delete_feature",
    # Stats
    "get_tileset_stats",
    "get_feature_distribution",
    "get_layer_stats",
    "get_area_stats",
    # Analysis
    "analyze_area",
    "calculate_distance",
    "find_nearest_features",
    "get_buffer_zone_features",
]
