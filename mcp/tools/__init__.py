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

from tools.analysis import (
    analyze_area,
    calculate_distance,
    find_nearest_features,
    get_buffer_zone_features,
)
from tools.crud import (
    create_feature,
    create_tileset,
    delete_feature,
    delete_tileset,
    update_feature,
    update_tileset,
)
from tools.features import (
    get_feature,
    get_features_in_tile,
    search_features,
)
from tools.geocoding import (
    geocode,
    reverse_geocode,
)
from tools.stats import (
    get_area_stats,
    get_feature_distribution,
    get_layer_stats,
    get_tileset_stats,
)
from tools.tilesets import (
    get_tileset,
    get_tileset_tilejson,
    list_tilesets,
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
