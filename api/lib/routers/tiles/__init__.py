"""
Tile serving endpoints.

This module combines all tile-related routers:
- MBTiles (local development)
- Dynamic vector tiles (PostGIS)
- PMTiles
- Raster tiles (COG)
"""

from fastapi import APIRouter

from lib.routers.tiles.mbtiles import router as mbtiles_router
from lib.routers.tiles.dynamic import router as dynamic_router
from lib.routers.tiles.pmtiles import router as pmtiles_router
from lib.routers.tiles.raster import router as raster_router

# Combined tiles router
router = APIRouter(prefix="/api/tiles", tags=["tiles"])

# Include sub-routers (they already have their prefixes)
router.include_router(mbtiles_router)
router.include_router(dynamic_router)
router.include_router(pmtiles_router)
router.include_router(raster_router)
