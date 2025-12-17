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
from lib.routers.batch_features import router as batch_features_router
from lib.routers.datasources import router as datasources_router
from lib.routers.colormaps import router as colormaps_router
from lib.routers.stats import router as stats_router
from lib.routers.tiles import router as tiles_router
from lib.routers.teams import router as teams_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield
    close_pool()


app = FastAPI(
    title="geo-base Tile Server",
    description="Geospatial tile server API for vector and raster data distribution",
    version="0.4.5",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(tilesets_router)
app.include_router(features_router)
app.include_router(batch_features_router)
app.include_router(datasources_router)
app.include_router(colormaps_router)
app.include_router(stats_router)
app.include_router(tiles_router)
app.include_router(teams_router)


def get_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


PREVIEW_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>geo-base Tile Server</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { margin: 0; padding: 20px; font-family: system-ui, sans-serif; }
        h1 { color: #333; }
        .info { background: #f5f5f5; padding: 15px; border-radius: 8px; }
        .info code { background: #e0e0e0; padding: 2px 6px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>geo-base Tile Server v0.4.5</h1>
    <div class="info">
        <p>API Documentation: <a href="/docs">/docs</a> | <a href="/redoc">/redoc</a></p>
        <p>New in v0.4.5: Team management endpoints at <code>/api/teams</code></p>
    </div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def preview_page():
    return PREVIEW_HTML
