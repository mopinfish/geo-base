"""
MCP Tools for geo-base.

This package provides tools for interacting with the geo-base tile server API.

Modules:
    tilesets: Tileset listing and retrieval
    features: Feature search and retrieval
    geocoding: Address/coordinate conversion
    crud: Create, update, delete operations
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
]
