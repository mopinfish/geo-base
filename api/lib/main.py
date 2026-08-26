"""
FastAPI Tile Server for geo-base.

This is the main application entry point.
Endpoints are organized into routers for better maintainability.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from lib.config import get_settings
from lib.cors_middleware import TwoTierCORSMiddleware
from lib.database import close_pool
from lib.errors import is_envelope_detail
from lib.routers.api_keys import router as api_keys_router

# Import all routers
from lib.routers.auth import router as auth_router
from lib.routers.batch_features import router as batch_features_router
from lib.routers.colormaps import router as colormaps_router
from lib.routers.datasources import router as datasources_router
from lib.routers.features import router as features_router
from lib.routers.health import router as health_router
from lib.routers.stats import router as stats_router
from lib.routers.teams import router as teams_router
from lib.routers.tiles import router as tiles_router
from lib.routers.tilesets import router as tilesets_router

# E2E テスト用のルーター（環境変数 E2E_MODE=1 のときだけ登録される）。
# 本番には絶対に出してはいけない。詳細は lib/routers/test_helpers.py を参照。
if os.getenv("E2E_MODE") == "1":
    from lib.routers.test_helpers import router as test_helpers_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield
    close_pool()


app = FastAPI(
    title="geo-base Tile Server",
    description="Geospatial tile server API for vector and raster data distribution",
    version="0.4.6",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    TwoTierCORSMiddleware,
    strict_origins=settings.cors_origins,
)

# Include Routers
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(tilesets_router)
app.include_router(features_router)
app.include_router(batch_features_router)
app.include_router(datasources_router)
app.include_router(colormaps_router)
app.include_router(stats_router)
app.include_router(tiles_router)
app.include_router(teams_router)
app.include_router(api_keys_router)

if os.getenv("E2E_MODE") == "1":
    app.include_router(test_helpers_router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """`raise api_error(...)` (lib.errors) で envelope `detail` を持つ
    HTTPException を発生させた場合、body をそのまま展開して
    `{error: {code, message, details?}}` を返す。

    旧来の `raise HTTPException(detail="...")` は default の `{detail: "..."}`
    にフォールバックする (Phase 2b 期間中の混在を許す)。
    """
    if is_envelope_detail(exc.detail):
        # exc.detail は {"error": {...}} 形式なのでそのまま body にする
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers=getattr(exc, "headers", None),
        )
    # Default behaviour (Starlette / FastAPI 互換): body = {"detail": exc.detail}
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


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
        body { margin: 0; padding: 20px; font-family: system-ui, sans-serif; background: #f8fafc; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #1e293b; margin-bottom: 8px; }
        .version { color: #64748b; font-size: 14px; margin-bottom: 24px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h2 { margin: 0 0 12px 0; font-size: 16px; color: #334155; }
        .links { display: flex; gap: 16px; }
        .links a { color: #3b82f6; text-decoration: none; }
        .links a:hover { text-decoration: underline; }
        .endpoint-group { margin-bottom: 16px; }
        .endpoint-group h3 { font-size: 14px; color: #64748b; margin: 0 0 8px 0; }
        .endpoint { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 13px; }
        .method { display: inline-block; width: 50px; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; text-align: center; }
        .get { background: #dbeafe; color: #1d4ed8; }
        .post { background: #dcfce7; color: #15803d; }
        .put { background: #fef3c7; color: #b45309; }
        .delete { background: #fee2e2; color: #dc2626; }
        code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        .new { background: #f0fdf4; border-left: 3px solid #22c55e; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🗺️ geo-base Tile Server</h1>
        <p class="version">Version 0.4.6 | <a href="/docs">API Docs</a> | <a href="/redoc">ReDoc</a></p>

        <div class="card">
            <h2>Core Endpoints</h2>
            <div class="endpoint-group">
                <div class="endpoint"><span class="method get">GET</span> <code>/api/health</code></div>
                <div class="endpoint"><span class="method get">GET</span> <code>/api/tilesets</code></div>
                <div class="endpoint"><span class="method get">GET</span> <code>/api/features</code></div>
            </div>
        </div>

        <div class="card new">
            <h2>🆕 Team Management (v0.4.5+)</h2>
            <div class="endpoint-group">
                <div class="endpoint"><span class="method get">GET</span> <code>/api/teams</code> - List teams</div>
                <div class="endpoint"><span class="method post">POST</span> <code>/api/teams</code> - Create team</div>
                <div class="endpoint"><span class="method get">GET</span> <code>/api/teams/{id}/members</code> - List members</div>
                <div class="endpoint"><span class="method post">POST</span> <code>/api/teams/{id}/invitations</code> - Invite member</div>
            </div>
        </div>

        <div class="card new">
            <h2>🔑 API Key Management (v0.4.6+)</h2>
            <div class="endpoint-group">
                <div class="endpoint"><span class="method get">GET</span> <code>/api/api-keys</code> - List API keys</div>
                <div class="endpoint"><span class="method post">POST</span> <code>/api/api-keys</code> - Create API key</div>
                <div class="endpoint"><span class="method get">GET</span> <code>/api/api-keys/{id}/usage</code> - Usage stats</div>
                <div class="endpoint"><span class="method post">POST</span> <code>/api/api-keys/{id}/revoke</code> - Revoke key</div>
            </div>
        </div>

        <div class="card">
            <h2>Tile Endpoints</h2>
            <div class="endpoint-group">
                <div class="endpoint"><span class="method get">GET</span> <code>/api/tiles/dynamic/{tileset_id}/{z}/{x}/{y}.{format}</code></div>
                <div class="endpoint"><span class="method get">GET</span> <code>/api/tiles/pmtiles/{tileset_id}/{z}/{x}/{y}.pbf</code></div>
                <div class="endpoint"><span class="method get">GET</span> <code>/api/tiles/raster/{tileset_id}/{z}/{x}/{y}.{format}</code></div>
            </div>
        </div>
    </div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def preview_page():
    return PREVIEW_HTML
