"""
FastAPI Tile Server for geo-base.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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
    generate_mvt_from_postgis,
    generate_tilejson,
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


# ============================================================================
# Health Check Endpoints
# ============================================================================


@app.get("/api/health")
def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}


@app.get("/api/health/db")
def health_check_db():
    """Database health check endpoint."""
    db_ok = check_database_connection()
    postgis_ok = check_postgis_extension() if db_ok else False

    status = "ok" if db_ok and postgis_ok else "error"

    return {
        "status": status,
        "database": "connected" if db_ok else "disconnected",
        "postgis": "available" if postgis_ok else "unavailable",
    }


# ============================================================================
# Tile Endpoints - Static (MBTiles)
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

    # Prepare headers
    headers = {
        "Cache-Control": f"public, max-age={settings.default_tile_cache_ttl}",
        "Access-Control-Allow-Origin": "*",
    }

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
    conn=Depends(get_connection),
):
    """
    Generate a vector tile dynamically from PostGIS.

    Args:
        layer_name: Name of the database table/layer
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
    """
    try:
        tile_data = generate_mvt_from_postgis(
            conn=conn,
            table_name=layer_name,
            z=z,
            x=x,
            y=y,
            layer_name=layer_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")

    headers = {
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
    }

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


@app.get("/api/tiles/features/{z}/{x}/{y}.pbf")
def get_features_vector_tile(
    z: int,
    x: int,
    y: int,
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    conn=Depends(get_connection),
):
    """
    Generate a vector tile from the features table.

    Args:
        z: Zoom level
        x: X tile coordinate
        y: Y tile coordinate
        tileset_id: Optional tileset ID filter
        layer: Optional layer name filter
    """
    # Build WHERE clause
    where_conditions = []
    params = {"z": z, "x": x, "y": y, "layer_name": "features"}

    if tileset_id:
        where_conditions.append("tileset_id = %(tileset_id)s")
        params["tileset_id"] = tileset_id

    if layer:
        where_conditions.append("layer_name = %(layer)s")
        params["layer"] = layer

    where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

    # Build query
    query = f"""
        WITH mvtgeom AS (
            SELECT
                ST_AsMVTGeom(
                    ST_Transform(geom, 3857),
                    ST_TileEnvelope(%(z)s, %(x)s, %(y)s)
                ) AS geom,
                id,
                layer_name,
                properties
            FROM features
            WHERE ST_Transform(geom, 3857) && ST_TileEnvelope(%(z)s, %(x)s, %(y)s)
              AND {where_clause}
        )
        SELECT ST_AsMVT(mvtgeom.*, %(layer_name)s)
        FROM mvtgeom;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchone()

        tile_data = result[0].tobytes() if result and result[0] else b""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tile: {str(e)}")

    headers = {
        "Cache-Control": "public, max-age=3600",
        "Access-Control-Allow-Origin": "*",
    }

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


# ============================================================================
# TileJSON Endpoints
# ============================================================================


@app.get("/api/tiles/dynamic/{layer_name}/tilejson.json")
def get_dynamic_tilejson(layer_name: str):
    """
    Get TileJSON for a dynamic layer.

    Args:
        layer_name: Name of the database table/layer
    """
    # Get base URL from settings or request
    base_url = "http://localhost:3000"  # TODO: Get from request

    tilejson = generate_tilejson(
        tileset_id=f"dynamic/{layer_name}",
        name=layer_name,
        base_url=base_url,
        tile_format="pbf",
        description=f"Dynamic vector tiles from {layer_name} table",
    )

    return tilejson


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
        body { margin: 0; padding: 0; }
        #map { position: absolute; top: 0; bottom: 0; width: 100%; }
        .info-panel {
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 10px 15px;
            border-radius: 4px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.2);
            z-index: 1;
            font-family: sans-serif;
            font-size: 14px;
        }
        .info-panel h3 { margin: 0 0 10px 0; }
    </style>
</head>
<body>
    <div class="info-panel">
        <h3>🗺️ geo-base Tile Server</h3>
        <p>Status: <span id="status">Loading...</span></p>
    </div>
    <div id="map"></div>
    <script>
        // Check API health
        fetch('/api/health')
            .then(res => res.json())
            .then(data => {
                document.getElementById('status').textContent = data.status === 'ok' ? '✅ Running' : '❌ Error';
            })
            .catch(() => {
                document.getElementById('status').textContent = '❌ Error';
            });

        // Initialize map with GSI tiles as base
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
                        attribution: '&copy; OpenStreetMap contributors',
                    },
                },
                layers: [
                    {
                        id: 'osm',
                        type: 'raster',
                        source: 'osm',
                    },
                ],
            },
            center: [139.7, 35.7],
            zoom: 10,
        });

        map.addControl(new maplibregl.NavigationControl());
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def preview_page():
    """Tile preview page with MapLibre GL JS."""
    return PREVIEW_HTML


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

        # Convert datetime to string
        for tileset in tilesets:
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

        # Convert datetime to string
        if tileset.get("created_at"):
            tileset["created_at"] = tileset["created_at"].isoformat()
        if tileset.get("updated_at"):
            tileset["updated_at"] = tileset["updated_at"].isoformat()

        return tileset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tileset: {str(e)}")
