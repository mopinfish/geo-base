"""
Dynamic vector tile serving endpoints (PostGIS-backed).
"""

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from lib.auth import AuthContext, check_tileset_access_v2, get_auth_context_optional
from lib.database import get_connection
from lib.errors import ErrorCode, api_error
from lib.tiles import (
    VECTOR_TILE_MEDIA_TYPE,
    generate_features_mvt,
    generate_mvt_from_postgis,
    get_cache_headers,
)

router = APIRouter(tags=["tiles"])


def get_base_url(request: Request) -> str:
    """
    Get base URL from request headers.

    Handles various proxy configurations including Fly.io and Vercel.
    Always uses HTTPS in production (non-localhost).
    """
    # Get protocol - prefer x-forwarded-proto, also check fly-forwarded-proto
    forwarded_proto = (
        request.headers.get("x-forwarded-proto") or
        request.headers.get("fly-forwarded-proto") or
        "http"
    )

    # Get host - prefer x-forwarded-host, fallback to host header
    forwarded_host = (
        request.headers.get("x-forwarded-host") or
        request.headers.get("host")
    )

    if forwarded_host:
        # Force HTTPS for non-localhost hosts
        if "localhost" not in forwarded_host and "127.0.0.1" not in forwarded_host:
            forwarded_proto = "https"
        return f"{forwarded_proto}://{forwarded_host}"

    # Fallback to request.base_url
    base_url = str(request.base_url).rstrip("/")

    # Force HTTPS for production URLs
    if base_url.startswith("http://") and "localhost" not in base_url and "127.0.0.1" not in base_url:
        base_url = base_url.replace("http://", "https://", 1)

    return base_url


# ============================================================================
# Dynamic Vector Tiles (from PostGIS table)
# ============================================================================


@router.get("/dynamic/{layer_name}/{z}/{x}/{y}.pbf")
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
        raise api_error(
            500,
            ErrorCode.TILE_RENDER_FAILED,
            f"Error generating tile: {str(e)}",
            details={"layer": layer_name, "z": z, "x": x, "y": y},
        )

    # Get optimized cache headers based on zoom level
    headers = get_cache_headers(z, is_static=False)

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


@router.get("/dynamic/{layer_name}/tilejson.json")
def get_dynamic_tilejson(layer_name: str, request: Request):
    """
    Get TileJSON for a dynamic layer.

    Args:
        layer_name: Name of the database table/layer
    """
    from lib.tiles import generate_tilejson

    base_url = get_base_url(request)

    tilejson = generate_tilejson(
        tileset_id=f"dynamic/{layer_name}",
        name=layer_name,
        base_url=base_url,
        tile_format="pbf",
        description=f"Dynamic vector tiles from {layer_name} table",
    )

    return tilejson


# ============================================================================
# Features Vector Tiles (from features table)
# ============================================================================


@router.get("/features/{z}/{x}/{y}.pbf")
def get_features_vector_tile(
    z: int,
    x: int,
    y: int,
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    filter: str = Query(None, description="Attribute filter (e.g., 'properties.type=station')"),
    simplify: bool = Query(True, description="Apply zoom-based simplification"),
    conn=Depends(get_connection),
    auth: Optional[AuthContext] = Depends(get_auth_context_optional),
):
    """
    Generate a vector tile from the features table.

    Features:
    - Filter by tileset_id and layer name
    - Attribute filtering with expressions
    - Automatic zoom-based geometry simplification
    - Optimized caching based on zoom level
    - Access control for private tilesets

    Args:
        z: Zoom level (0-22)
        x: X tile coordinate
        y: Y tile coordinate
        tileset_id: Optional tileset ID filter
        layer: Optional layer name filter
        filter: Attribute filter expression
        simplify: Whether to apply zoom-based geometry simplification (default: true)
    """
    # If tileset_id is specified, check access
    if tileset_id:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, is_public, user_id FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()

        if row:
            tileset = {
                "id": row[0],
                "is_public": row[1],
                "user_id": str(row[2]) if row[2] else None,
            }

            if not check_tileset_access_v2(conn, tileset, auth):
                if auth is None:
                    # NOTE: Phase 2b では envelope 化を見送り。
                    # api_error() は headers= を受けないため、
                    # WWW-Authenticate を維持するために HTTPException を直書きしている (#106)。
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required to access this tileset",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                raise api_error(
                    403,
                    ErrorCode.TILESET_FORBIDDEN,
                    "You do not have permission to access this tileset",
                    details={"tileset_id": tileset_id},
                )

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
        raise api_error(
            500,
            ErrorCode.TILE_RENDER_FAILED,
            f"Error generating tile: {str(e)}",
            details={"z": z, "x": x, "y": y, "tileset_id": tileset_id},
        )

    # Get optimized cache headers based on zoom level
    headers = get_cache_headers(z, is_static=False)

    return Response(content=tile_data, media_type=VECTOR_TILE_MEDIA_TYPE, headers=headers)


@router.get("/features/tilejson.json")
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
