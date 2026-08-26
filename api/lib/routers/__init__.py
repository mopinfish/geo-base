"""
FastAPI Routers for geo-base API.

Each router handles a specific domain of functionality:
- health: Health check and authentication status endpoints
- tilesets: Tileset CRUD operations
- features: Feature CRUD operations
- datasources: Datasource management
- tiles/: Tile serving endpoints (mbtiles, dynamic, pmtiles, raster)
- stats: Statistics endpoints
- colormaps: Colormap endpoints
"""

# Note: Import individual routers in main.py to avoid circular imports
# This file serves as documentation for the router structure

__all__ = [
    "health",
    "tilesets",
    "features",
    "datasources",
    "colormaps",
    "stats",
    "tiles",
]
