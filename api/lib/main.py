"""
FastAPI Tile Server for geo-base.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from lib.config import get_settings
from lib.database import (
    check_database_connection,
    check_postgis_extension,
    close_pool,
    get_connection,
)
from lib.tiles import (
    FORMAT_MEDIA_TYPES,
    VECTOR_TILE_MEDIA_TYPE,
    generate_features_mvt,
    generate_mvt_from_postgis,
    generate_tilejson,
    get_cache_headers,
    get_mbtiles_metadata,
    get_tile_from_mbtiles,
)


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
    description="地理空間タイル配信API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_base_url(request: Request) -> str:
    """Get base URL from request headers."""
    # Check for forwarded headers (used by proxies/Vercel)
    forwarded_proto = request.headers.get("x-forwarded-proto", "http")
    forwarded_host = request.headers.get("x-forwarded-host")
    
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    
    # Fallback to request URL
    return str(request.base_url).rstrip("/")


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/api/health")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/api/health/db")
def health_check_db():
    """Database health check endpoint with detailed error info."""
    db_result = check_database_connection()
    db_connected = db_result.get("connected", False)
    
    postgis_result = check_postgis_extension() if db_connected else {"available": False}
    postgis_available = postgis_result.get("available", False)

    status = "ok" if db_connected and postgis_available else "error"

    response = {
        "status": status,
        "database": "connected" if db_connected else "disconnected",
        "postgis": "available" if postgis_available else "unavailable",
        "environment": settings.environment,
    }
    
    # Add error details if present
    if not db_connected and db_result.get("error"):
        response["db_error"] = db_result["error"]
    
    if db_connected and postgis_result.get("version"):
        response["postgis_version"] = postgis_result["version"]
    elif not postgis_available and postgis_result.get("error"):
        response["postgis_error"] = postgis_result["error"]
    
    return response



# ============================================================================
# Tile Endpoints - Static (MBTiles) - For Local Development
# ============================================================================


@app.get("/api/tiles/mbtiles/{tileset_name}/{z}/{x}/{y}.{tile_format}")
def get_mbtiles_tile(
    tileset_name: str,
    z: int,
    x: int,
    y: int,
    tile_format: str,
):
    """
    Get a tile from an MBTiles file.
    
    Note: This endpoint is primarily for local development.
    In production (Vercel), use database-backed tiles instead.

    Args:
        tileset_name: Name of the MBTiles file (without extension)
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
        tile_format: Tile format (pbf, png, jpg)
    """
    # Validate format
    media_type = FORMAT_MEDIA_TYPES.get(tile_format.lower())
    if not media_type:
        raise HTTPException(status_code=400, detail=f"Unsupported tile format: {tile_format}")

    # Build path to MBTiles file
    mbtiles_path = Path(f"data/{tileset_name}.mbtiles")

    if not mbtiles_path.exists():
        raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_name}")

    # Get tile data
    tile_data = get_tile_from_mbtiles(mbtiles_path, z, x, y)

    if tile_data is None:
        raise HTTPException(status_code=404, detail="Tile not found")

    # Get optimized cache headers (static tiles = longer cache)
    headers = get_cache_headers(z, is_static=True)

    # Add content-encoding for gzipped vector tiles
    if tile_format.lower() in ("pbf", "mvt"):
        headers["Content-Encoding"] = "gzip"

    return Response(content=tile_data, media_type=media_type, headers=headers)


@app.get("/api/tiles/mbtiles/{tileset_name}/metadata.json")
def get_mbtiles_tileset_metadata(tileset_name: str):
    """
    Get metadata for an MBTiles tileset.

    Args:
        tileset_name: Name of the MBTiles file (without extension)
    """
    mbtiles_path = Path(f"data/{tileset_name}.mbtiles")

    if not mbtiles_path.exists():
        raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_name}")

    metadata = get_mbtiles_metadata(mbtiles_path)
    return metadata


# ============================================================================
# Tile Endpoints - Dynamic (PostGIS)
# ============================================================================


@app.get("/api/tiles/dynamic/{layer_name}/{z}/{x}/{y}.pbf")
def get_dynamic_vector_tile(
    layer_name: str,
    z: int,
    x: int,
    y: int,
    simplify: bool = Query(True, description="Apply zoom-based simplification"),
    conn=Depends(get_connection),
):
    """
    Generate a vector tile dynamically from PostGIS table.
    
    Features:
    - Automatic zoom-based geometry simplification
    - Optimized caching based on zoom level

    Args:
        layer_name: Name of the database table/layer
        z: Zoom level (0-22)
        x: X tile coordinate
        y: Y tile coordinate
        simplify: Whether to apply zoom-based geometry simplification (default: true)
    """
    try:
        tile_data = generate_mvt_from_postgis(
            conn=conn,
            table_name=layer_name,
            z=z,
            x=x,
            y=y,
            layer_name=layer_name,
            simplify=simplify,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")

    # Get optimized cache headers based on zoom level
    headers = get_cache_headers(z, is_static=False)

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


@app.get("/api/tiles/features/{z}/{x}/{y}.pbf")
def get_features_vector_tile(
    z: int,
    x: int,
    y: int,
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    filter: str = Query(None, description="Attribute filter (e.g., 'properties.type=station')"),
    simplify: bool = Query(True, description="Apply zoom-based simplification"),
    conn=Depends(get_connection),
):
    """
    Generate a vector tile from the features table.
    
    Features:
    - Filter by tileset_id and layer name
    - Attribute filtering with expressions
    - Automatic zoom-based geometry simplification
    - Optimized caching based on zoom level

    Args:
        z: Zoom level (0-22)
        x: X tile coordinate
        y: Y tile coordinate
        tileset_id: Optional tileset ID filter
        layer: Optional layer name filter
        filter: Attribute filter expression
            - Simple: "properties.type=station"
            - Multiple values: "properties.type=station,landmark"
            - Pattern match: "properties.name~Tokyo"
            - Multiple conditions: "properties.type=station;properties.name~Tokyo"
        simplify: Whether to apply zoom-based geometry simplification (default: true)
    """
    try:
        tile_data = generate_features_mvt(
            conn=conn,
            z=z,
            x=x,
            y=y,
            tileset_id=tileset_id,
            layer_name=layer,
            filter_expr=filter,
            simplify=simplify,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")

    # Get optimized cache headers based on zoom level
    headers = get_cache_headers(z, is_static=False)

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


# ============================================================================
# TileJSON Endpoints
# ============================================================================


@app.get("/api/tiles/dynamic/{layer_name}/tilejson.json")
def get_dynamic_tilejson(layer_name: str, request: Request):
    """
    Get TileJSON for a dynamic layer.

    Args:
        layer_name: Name of the database table/layer
    """
    base_url = get_base_url(request)

    tilejson = generate_tilejson(
        tileset_id=f"dynamic/{layer_name}",
        name=layer_name,
        base_url=base_url,
        tile_format="pbf",
        description=f"Dynamic vector tiles from {layer_name} table",
    )

    return tilejson


@app.get("/api/tiles/features/tilejson.json")
def get_features_tilejson(
    request: Request,
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    filter: str = Query(None, description="Attribute filter expression"),
):
    """
    Get TileJSON for the features layer.
    
    Query parameters are passed through to the tile URLs.
    """
    base_url = get_base_url(request)
    
    # Build tile URL with query params
    tile_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf"
    query_params = []
    if tileset_id:
        query_params.append(f"tileset_id={tileset_id}")
    if layer:
        query_params.append(f"layer={layer}")
    if filter:
        # URL encode the filter parameter
        from urllib.parse import quote
        query_params.append(f"filter={quote(filter)}")
    if query_params:
        tile_url += "?" + "&".join(query_params)

    return {
        "tilejson": "3.0.0",
        "name": "features",
        "tiles": [tile_url],
        "minzoom": 0,
        "maxzoom": 22,
        "bounds": [-180, -85.051129, 180, 85.051129],
        "center": [139.7, 35.7, 10],
    }


# ============================================================================
# Tilesets API (CRUD)
# ============================================================================


@app.get("/api/tilesets")
def list_tilesets(conn=Depends(get_connection)):
    """List all tilesets."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, type, format, min_zoom, max_zoom,
                       is_public, created_at, updated_at
                FROM tilesets
                ORDER BY created_at DESC
                """
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        tilesets = [dict(zip(columns, row)) for row in rows]

        # Convert datetime and UUID to string
        for tileset in tilesets:
            if tileset.get("id"):
                tileset["id"] = str(tileset["id"])
            if tileset.get("created_at"):
                tileset["created_at"] = tileset["created_at"].isoformat()
            if tileset.get("updated_at"):
                tileset["updated_at"] = tileset["updated_at"].isoformat()

        return {"tilesets": tilesets, "count": len(tilesets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tilesets: {str(e)}")


@app.get("/api/tilesets/{tileset_id}")
def get_tileset(tileset_id: str, conn=Depends(get_connection)):
    """Get a specific tileset by ID."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, type, format, min_zoom, max_zoom,
                       ST_AsGeoJSON(bounds) as bounds, ST_AsGeoJSON(center) as center,
                       attribution, is_public, metadata, created_at, updated_at
                FROM tilesets
                WHERE id = %s
                """,
                (tileset_id,),
            )
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_id}")

        tileset = dict(zip(columns, row))

        # Convert datetime and UUID to string
        if tileset.get("id"):
            tileset["id"] = str(tileset["id"])
        if tileset.get("created_at"):
            tileset["created_at"] = tileset["created_at"].isoformat()
        if tileset.get("updated_at"):
            tileset["updated_at"] = tileset["updated_at"].isoformat()

        return tileset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tileset: {str(e)}")


@app.get("/api/tilesets/{tileset_id}/tilejson.json")
def get_tileset_tilejson(tileset_id: str, request: Request, conn=Depends(get_connection)):
    """Get TileJSON for a specific tileset."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name, description, type, format, min_zoom, max_zoom, attribution
                FROM tilesets
                WHERE id = %s
                """,
                (tileset_id,),
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_id}")

        name, description, tile_type, tile_format, min_zoom, max_zoom, attribution = row
        base_url = get_base_url(request)

        # For vector tilesets, use features endpoint
        if tile_type == "vector":
            tile_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}"
        else:
            # For raster, would need different endpoint
            tile_url = f"{base_url}/api/tiles/raster/{tileset_id}/{{z}}/{{x}}/{{y}}.{tile_format}"

        return {
            "tilejson": "3.0.0",
            "name": name,
            "description": description,
            "tiles": [tile_url],
            "minzoom": min_zoom or 0,
            "maxzoom": max_zoom or 22,
            "attribution": attribution,
            "bounds": [-180, -85.051129, 180, 85.051129],
            "center": [139.7, 35.7, 10],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TileJSON: {str(e)}")


# ============================================================================
# Preview Page
# ============================================================================


PREVIEW_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>geo-base Tile Preview</title>
    <script src="https://unpkg.com/maplibre-gl@^4.0/dist/maplibre-gl.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@^4.0/dist/maplibre-gl.css" />
    <style>
        body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        .info-panel {
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 1;
            max-width: 300px;
        }
        .info-panel h3 { margin: 0 0 10px 0; font-size: 18px; }
        .info-panel p { margin: 5px 0; font-size: 14px; color: #666; }
        .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
        .status.ok { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.loading { background: #fff3cd; color: #856404; }
        .endpoints { margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; }
        .endpoints h4 { margin: 0 0 8px 0; font-size: 14px; }
        .endpoints a { display: block; font-size: 12px; color: #007bff; margin: 4px 0; text-decoration: none; }
        .endpoints a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="info-panel">
        <h3>🗺️ geo-base Tile Server</h3>
        <p>API: <span id="api-status" class="status loading">checking...</span></p>
        <p>DB: <span id="db-status" class="status loading">checking...</span></p>
        <div class="endpoints">
            <h4>API Endpoints</h4>
            <a href="/api/health" target="_blank">/api/health</a>
            <a href="/api/health/db" target="_blank">/api/health/db</a>
            <a href="/api/tilesets" target="_blank">/api/tilesets</a>
            <a href="/api/tiles/features/tilejson.json" target="_blank">/api/tiles/features/tilejson.json</a>
        </div>
    </div>
    <div id="map"></div>
    <script>
        // Check API health
        fetch('/api/health')
            .then(res => res.json())
            .then(data => {
                const el = document.getElementById('api-status');
                el.textContent = data.status === 'ok' ? '✓ OK' : '✗ Error';
                el.className = 'status ' + (data.status === 'ok' ? 'ok' : 'error');
            })
            .catch(() => {
                const el = document.getElementById('api-status');
                el.textContent = '✗ Error';
                el.className = 'status error';
            });

        // Check DB health
        fetch('/api/health/db')
            .then(res => res.json())
            .then(data => {
                const el = document.getElementById('db-status');
                el.textContent = data.status === 'ok' ? '✓ Connected' : '✗ ' + data.database;
                el.className = 'status ' + (data.status === 'ok' ? 'ok' : 'error');
            })
            .catch(() => {
                const el = document.getElementById('db-status');
                el.textContent = '✗ Error';
                el.className = 'status error';
            });

        // Initialize map
        const map = new maplibregl.Map({
            hash: true,
            container: 'map',
            style: {
                version: 8,
                sources: {
                    osm: {
                        type: 'raster',
                        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                        tileSize: 256,
                        attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
                    },
                    features: {
                        type: 'vector',
                        tiles: [window.location.origin + '/api/tiles/features/{z}/{x}/{y}.pbf'],
                        minzoom: 0,
                        maxzoom: 22,
                    },
                },
                layers: [
                    {
                        id: 'osm',
                        type: 'raster',
                        source: 'osm',
                    },
                    {
                        id: 'features-circle',
                        type: 'circle',
                        source: 'features',
                        'source-layer': 'features',
                        paint: {
                            'circle-radius': 8,
                            'circle-color': '#e74c3c',
                            'circle-stroke-width': 2,
                            'circle-stroke-color': '#ffffff',
                        },
                    },
                ],
            },
            center: [139.7, 35.68],
            zoom: 11,
        });

        map.addControl(new maplibregl.NavigationControl());

        // Popup on click
        map.on('click', 'features-circle', (e) => {
            const props = e.features[0].properties;
            let content = '<strong>' + (props.name || 'Feature') + '</strong>';
            if (props.properties) {
                try {
                    const p = JSON.parse(props.properties);
                    if (p.name_en) content += '<br>' + p.name_en;
                    if (p.type) content += '<br>Type: ' + p.type;
                } catch(e) {}
            }
            new maplibregl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(content)
                .addTo(map);
        });

        map.on('mouseenter', 'features-circle', () => {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'features-circle', () => {
            map.getCanvas().style.cursor = '';
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def preview_page():
    """Tile preview page with MapLibre GL JS."""
    return PREVIEW_HTML
