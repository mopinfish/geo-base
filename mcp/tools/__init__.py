"""
geo-base MCP Tools

MCP Tools for geo-base tile server.
"""

__version__ = "0.1.0"

from .tilesets import (
    list_tilesets,
    get_tileset,
    get_tileset_tilejson,
)
from .features import (
    search_features,
    get_feature,
    get_features_in_tile,
)
from .geocoding import (
    geocode,
    reverse_geocode,
)
from .crud import (
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
