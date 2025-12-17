"""
FastAPI Tile Server for geo-base.

This is the main application entry point.
Endpoints are organized into routers for better maintainability.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from lib.config import get_settings
from lib.database import close_pool

# Import all routers
from lib.routers.health import router as health_router
from lib.routers.tilesets import router as tilesets_router
from lib.routers.features import router as features_router
from lib.routers.datasources import router as datasources_router
from lib.routers.colormaps import router as colormaps_router
from lib.routers.stats import router as stats_router
from lib.routers.tiles import router as tiles_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    close_pool()


# Create FastAPI app
app = FastAPI(
    title="geo-base Tile Server",
    description="Geospatial tile server API for vector and raster data distribution",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for tile serving
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Include Routers
# ============================================================================

# Health and Auth endpoints
app.include_router(health_router)

# Tileset CRUD endpoints
app.include_router(tilesets_router)

# Feature CRUD endpoints
app.include_router(features_router)

# Datasource CRUD endpoints
app.include_router(datasources_router)

# Colormap endpoints
app.include_router(colormaps_router)

# Stats endpoints
app.include_router(stats_router)

# Tile serving endpoints (combines all tile types)
app.include_router(tiles_router)


# ============================================================================
# Utility Functions
# ============================================================================


def get_base_url(request: Request) -> str:
    """Get base URL from request headers."""
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    
    return str(request.base_url).rstrip("/")


# ============================================================================
# Preview Page (Root endpoint)
# ============================================================================


@app.get("/", response_class=HTMLResponse)
def preview_page():
    """Serve a simple preview page for testing."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>geo-base Tile Server</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 4px; }
        .method { color: #0066cc; font-weight: bold; }
        a { color: #0066cc; }
    </style>
</head>
<body>
    <h1>🌍 geo-base Tile Server</h1>
    <p>Geospatial tile server API for vector and raster data distribution.</p>
    
    <h2>Quick Links</h2>
    <ul>
        <li><a href="/docs">📖 API Documentation (Swagger UI)</a></li>
        <li><a href="/redoc">📚 API Documentation (ReDoc)</a></li>
        <li><a href="/api/health">❤️ Health Check</a></li>
        <li><a href="/api/tilesets">📦 List Tilesets</a></li>
        <li><a href="/api/stats">📊 Statistics</a></li>
    </ul>
    
    <h2>Key Endpoints</h2>
    
    <div class="endpoint">
        <span class="method">GET</span> /api/health - Health check
    </div>
    <div class="endpoint">
        <span class="method">GET</span> /api/tilesets - List all tilesets
    </div>
    <div class="endpoint">
        <span class="method">GET</span> /api/tiles/features/{z}/{x}/{y}.pbf - Vector tiles
    </div>
    <div class="endpoint">
        <span class="method">GET</span> /api/tiles/pmtiles/{tileset_id}/{z}/{x}/{y}.pbf - PMTiles
    </div>
    <div class="endpoint">
        <span class="method">GET</span> /api/tiles/raster/{tileset_id}/{z}/{x}/{y}.png - Raster tiles
    </div>
    
    <h2>Version</h2>
    <p>v0.4.0</p>
</body>
</html>
"""
