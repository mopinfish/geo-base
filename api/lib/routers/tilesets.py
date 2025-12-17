"""
Tilesets CRUD endpoints.
"""

import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from lib.config import get_settings
from lib.database import get_connection
from lib.models.tileset import TilesetCreate, TilesetUpdate
from lib.cache import invalidate_tileset_cache
from lib.auth import User, get_current_user, require_auth, check_tileset_access
from lib.tiles import generate_tilejson
from lib.pmtiles import generate_pmtiles_tilejson
from lib.raster_tiles import generate_raster_tilejson


router = APIRouter(prefix="/api/tilesets", tags=["tilesets"])
settings = get_settings()


def get_base_url(request: Request) -> str:
    """
    Get base URL from request headers.
    
    Handles various proxy configurations including Fly.io and Vercel.
    Priority:
    1. x-forwarded-host + x-forwarded-proto
    2. host header + x-forwarded-proto
    3. request.base_url (fallback)
    
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
# List Tilesets
# ============================================================================


@router.get("")
def list_tilesets(
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
    include_private: bool = Query(False, description="Include private tilesets (requires auth)"),
    type: Optional[str] = Query(None, description="Filter by tileset type (vector, raster, pmtiles)"),
):
    """
    List all accessible tilesets.
    
    By default, only public tilesets are returned.
    With authentication and include_private=true, also returns user's private tilesets.
    Optionally filter by tileset type.
    """
    try:
        # Validate type parameter if provided
        valid_types = {"vector", "raster", "pmtiles"}
        if type is not None and type.lower() not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid type '{type}'. Must be one of: {', '.join(sorted(valid_types))}"
            )
        
        with conn.cursor() as cur:
            # Build query dynamically based on parameters
            base_query = """
                SELECT id, name, description, type, format, min_zoom, max_zoom,
                       is_public, user_id, created_at, updated_at
                FROM tilesets
                WHERE 1=1
            """
            params = []
            
            # Add visibility filter
            if include_private and user:
                base_query += " AND (is_public = true OR user_id = %s)"
                params.append(user.id)
            else:
                base_query += " AND is_public = true"
            
            # Add type filter if provided
            if type is not None:
                base_query += " AND type = %s"
                params.append(type.lower())
            
            # Add ordering
            base_query += " ORDER BY created_at DESC"
            
            # Execute query
            if params:
                cur.execute(base_query, tuple(params))
            else:
                cur.execute(base_query)
            
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        tilesets = [dict(zip(columns, row)) for row in rows]

        # Convert datetime and UUID to string
        for tileset in tilesets:
            if tileset.get("id"):
                tileset["id"] = str(tileset["id"])
            if tileset.get("user_id"):
                tileset["user_id"] = str(tileset["user_id"])
            if tileset.get("created_at"):
                tileset["created_at"] = tileset["created_at"].isoformat()
            if tileset.get("updated_at"):
                tileset["updated_at"] = tileset["updated_at"].isoformat()

        return {"tilesets": tilesets, "count": len(tilesets)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tilesets: {str(e)}")


# ============================================================================
# Get Tileset
# ============================================================================


@router.get("/{tileset_id}")
def get_tileset(
    tileset_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific tileset by ID with access control."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, description, type, format, min_zoom, max_zoom,
                       ST_AsGeoJSON(bounds) as bounds, ST_AsGeoJSON(center) as center,
                       attribution, is_public, user_id, metadata, created_at, updated_at
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
        is_public = tileset.get("is_public", True)
        owner_user_id = str(tileset.get("user_id")) if tileset.get("user_id") else None

        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )

        # Convert types
        if tileset.get("id"):
            tileset["id"] = str(tileset["id"])
        if tileset.get("user_id"):
            tileset["user_id"] = str(tileset["user_id"])
        if tileset.get("bounds"):
            tileset["bounds"] = json.loads(tileset["bounds"])
        if tileset.get("center"):
            tileset["center"] = json.loads(tileset["center"])
        if tileset.get("created_at"):
            tileset["created_at"] = tileset["created_at"].isoformat()
        if tileset.get("updated_at"):
            tileset["updated_at"] = tileset["updated_at"].isoformat()

        return tileset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tileset: {str(e)}")


# ============================================================================
# Get Tileset TileJSON
# ============================================================================


@router.get("/{tileset_id}/tilejson.json")
def get_tileset_tilejson(
    tileset_id: str,
    request: Request,
    layer: Optional[str] = Query(None, description="Filter to specific layer name for QGIS compatibility"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Get TileJSON for a tileset.
    
    Routes to appropriate handler based on tileset type.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT type, is_public, user_id
                FROM tilesets
                WHERE id = %s
                """,
                (tileset_id,),
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Tileset not found: {tileset_id}")

        tileset_type, is_public, owner_user_id = row
        owner_user_id = str(owner_user_id) if owner_user_id else None

        # Check access
        if not check_tileset_access(tileset_id, is_public, owner_user_id, user):
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required to access this tileset",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this tileset"
            )

        base_url = get_base_url(request)

        # Route based on type
        if tileset_type == "vector":
            return _get_vector_tilejson(tileset_id, layer, conn, base_url)
        elif tileset_type == "pmtiles":
            return _get_pmtiles_tilejson(tileset_id, conn, base_url)
        elif tileset_type == "raster":
            return _get_raster_tilejson(tileset_id, conn, base_url)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tileset type: {tileset_type}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating TileJSON: {str(e)}")


def _get_vector_tilejson(tileset_id: str, layer: Optional[str], conn, base_url: str):
    """Generate TileJSON for vector tileset."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT name, description, min_zoom, max_zoom, attribution,
                   ST_XMin(bounds), ST_YMin(bounds), ST_XMax(bounds), ST_YMax(bounds),
                   ST_X(center), ST_Y(center)
            FROM tilesets
            WHERE id = %s
            """,
            (tileset_id,),
        )
        row = cur.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Tileset not found")
    
    (name, description, min_zoom, max_zoom, attribution,
     xmin, ymin, xmax, ymax, center_x, center_y) = row
    
    # Get vector_layers information from features
    vector_layers = []
    
    with conn.cursor() as cur:
        if layer:
            cur.execute(
                """
                SELECT DISTINCT layer_name
                FROM features
                WHERE tileset_id = %s AND layer_name = %s
                ORDER BY layer_name
                """,
                (tileset_id, layer),
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT layer_name
                FROM features
                WHERE tileset_id = %s
                ORDER BY layer_name
                """,
                (tileset_id,),
            )
        db_layer_names = [row[0] for row in cur.fetchall()]
        
        if layer and not db_layer_names:
            raise HTTPException(
                status_code=404, 
                detail=f"Layer '{layer}' not found in tileset"
            )
        
        for db_layer_name in db_layer_names:
            cur.execute(
                """
                SELECT properties
                FROM features
                WHERE tileset_id = %s AND layer_name = %s
                LIMIT 1
                """,
                (tileset_id, db_layer_name),
            )
            props_row = cur.fetchone()
            
            fields = {}
            if props_row and props_row[0]:
                properties = props_row[0]
                for key, value in properties.items():
                    if isinstance(value, bool):
                        fields[key] = "Boolean"
                    elif isinstance(value, int):
                        fields[key] = "Number"
                    elif isinstance(value, float):
                        fields[key] = "Number"
                    else:
                        fields[key] = "String"
            
            vector_layers.append({
                "id": db_layer_name,
                "fields": fields,
                "minzoom": min_zoom or 0,
                "maxzoom": max_zoom or 22,
                "description": ""
            })
    
    if not vector_layers:
        db_layer_names = ["default"]
        vector_layers.append({
            "id": "default",
            "fields": {},
            "minzoom": min_zoom or 0,
            "maxzoom": max_zoom or 22,
            "description": ""
        })
    
    # Build tiles URL
    if layer:
        tiles_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}&layer={layer}"
    else:
        tiles_url = f"{base_url}/api/tiles/features/{{z}}/{{x}}/{{y}}.pbf?tileset_id={tileset_id}"
    
    tilejson = {
        "tilejson": "3.0.0",
        "name": name,
        "tiles": [tiles_url],
        "minzoom": min_zoom or 0,
        "maxzoom": max_zoom or 22,
        "vector_layers": vector_layers,
    }
    
    if xmin is not None and ymin is not None and xmax is not None and ymax is not None:
        tilejson["bounds"] = [xmin, ymin, xmax, ymax]
    
    if center_x is not None and center_y is not None:
        center_zoom = min_zoom if min_zoom else 10
        tilejson["center"] = [center_x, center_y, center_zoom]
    
    if description:
        tilejson["description"] = description
    
    if attribution:
        tilejson["attribution"] = attribution
    
    return tilejson


def _get_pmtiles_tilejson(tileset_id: str, conn, base_url: str):
    """Generate TileJSON for PMTiles tileset."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ps.pmtiles_url, ps.tile_type, ps.min_zoom, ps.max_zoom,
                   ps.bounds, ps.center, ps.layers,
                   t.name, t.description, t.attribution
            FROM pmtiles_sources ps
            JOIN tilesets t ON ps.tileset_id = t.id
            WHERE t.id = %s
            """,
            (tileset_id,),
        )
        row = cur.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="PMTiles source not found")
    
    (pmtiles_url, tile_type, min_zoom, max_zoom, bounds, center, layers,
     name, description, attribution) = row
    
    metadata = {
        "tile_type": tile_type or "mvt",
        "min_zoom": min_zoom or 0,
        "max_zoom": max_zoom or 22,
        "bounds": bounds,
        "center": center,
        "layers": layers or [],
    }
    
    return generate_pmtiles_tilejson(
        tileset_id=tileset_id,
        tileset_name=name,
        metadata=metadata,
        base_url=base_url,
        description=description or "",
        attribution=attribution or "",
    )


def _get_raster_tilejson(tileset_id: str, conn, base_url: str):
    """Generate TileJSON for raster tileset."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.name, t.description, t.format, t.min_zoom, t.max_zoom,
                   t.attribution, rs.cog_url,
                   ST_XMin(t.bounds), ST_YMin(t.bounds), ST_XMax(t.bounds), ST_YMax(t.bounds),
                   ST_X(t.center), ST_Y(t.center)
            FROM tilesets t
            LEFT JOIN raster_sources rs ON rs.tileset_id = t.id
            WHERE t.id = %s
            """,
            (tileset_id,),
        )
        row = cur.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Raster source not found")
    
    (name, description, tile_format, min_zoom, max_zoom, attribution, cog_url,
     xmin, ymin, xmax, ymax, center_x, center_y) = row
    
    bounds = None
    if xmin is not None and ymin is not None and xmax is not None and ymax is not None:
        bounds = [xmin, ymin, xmax, ymax]
    
    center = None
    if center_x is not None and center_y is not None:
        center_zoom = min_zoom if min_zoom else 10
        center = [center_x, center_y, center_zoom]
    
    return generate_raster_tilejson(
        tileset_id=tileset_id,
        name=name,
        base_url=base_url,
        tile_format=tile_format or "png",
        min_zoom=min_zoom or 0,
        max_zoom=max_zoom or 22,
        bounds=bounds,
        center=center,
        description=description,
        attribution=attribution,
    )


# ============================================================================
# Create Tileset
# ============================================================================


@router.post("", status_code=201)
def create_tileset(
    tileset: TilesetCreate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Create a new tileset.
    
    Requires authentication.
    """
    try:
        with conn.cursor() as cur:
            # Build geometry SQL
            bounds_sql = "NULL"
            center_sql = "NULL"
            
            if tileset.bounds and len(tileset.bounds) == 4:
                west, south, east, north = tileset.bounds
                bounds_sql = f"ST_MakeEnvelope({west}, {south}, {east}, {north}, 4326)"
            
            if tileset.center and len(tileset.center) >= 2:
                lon, lat = tileset.center[0], tileset.center[1]
                center_sql = f"ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)"
            
            metadata_json = json.dumps(tileset.metadata) if tileset.metadata else None
            
            cur.execute(
                f"""
                INSERT INTO tilesets (
                    name, description, type, format,
                    min_zoom, max_zoom, bounds, center,
                    attribution, is_public, user_id, metadata
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, {bounds_sql}, {center_sql},
                    %s, %s, %s, %s
                )
                RETURNING id, name, description, type, format,
                          min_zoom, max_zoom, attribution, is_public,
                          created_at, updated_at
                """,
                (
                    tileset.name,
                    tileset.description,
                    tileset.type,
                    tileset.format,
                    tileset.min_zoom,
                    tileset.max_zoom,
                    tileset.attribution,
                    tileset.is_public,
                    user.id,
                    metadata_json,
                ),
            )
            
            row = cur.fetchone()
            conn.commit()
            
            return {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "type": row[3],
                "format": row[4],
                "min_zoom": row[5],
                "max_zoom": row[6],
                "attribution": row[7],
                "is_public": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating tileset: {str(e)}")


# ============================================================================
# Calculate Bounds
# ============================================================================


@router.post("/{tileset_id}/calculate-bounds")
def calculate_tileset_bounds(
    tileset_id: str,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Calculate and update tileset bounds from its features.
    
    This endpoint calculates the bounding box from all features in the tileset
    and updates the tileset's bounds and center fields.
    
    Useful after bulk importing GeoJSON features.
    
    Requires authentication and ownership of the tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id, type FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to update this tileset")
            
            tileset_type = row[2]
            
            # Only calculate bounds for vector tilesets (which have features)
            if tileset_type != "vector":
                raise HTTPException(
                    status_code=400, 
                    detail=f"Bounds calculation is only supported for vector tilesets, not {tileset_type}"
                )
            
            # Calculate bounding box from all features in this tileset
            cur.execute(
                """
                SELECT 
                    ST_XMin(ST_Extent(geom)) as xmin,
                    ST_YMin(ST_Extent(geom)) as ymin,
                    ST_XMax(ST_Extent(geom)) as xmax,
                    ST_YMax(ST_Extent(geom)) as ymax,
                    ST_X(ST_Centroid(ST_Extent(geom))) as center_x,
                    ST_Y(ST_Centroid(ST_Extent(geom))) as center_y,
                    COUNT(*) as feature_count
                FROM features
                WHERE tileset_id = %s
                """,
                (tileset_id,),
            )
            result = cur.fetchone()
            
            if not result or result[0] is None:
                return {
                    "message": "No features found in tileset",
                    "tileset_id": tileset_id,
                    "feature_count": 0,
                    "bounds": None,
                    "center": None,
                }
            
            xmin, ymin, xmax, ymax, center_x, center_y, feature_count = result
            
            # Update tileset with calculated bounds and center
            cur.execute(
                """
                UPDATE tilesets
                SET bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                    center = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (xmin, ymin, xmax, ymax, center_x, center_y, tileset_id),
            )
            conn.commit()
            
            # Invalidate cache for this tileset
            invalidate_tileset_cache(f"vector:{tileset_id}")
            
            return {
                "message": "Bounds calculated and updated successfully",
                "tileset_id": tileset_id,
                "feature_count": feature_count,
                "bounds": [xmin, ymin, xmax, ymax],
                "center": [center_x, center_y],
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error calculating bounds: {str(e)}")


# ============================================================================
# Update Tileset
# ============================================================================


@router.patch("/{tileset_id}")
def update_tileset(
    tileset_id: str,
    tileset: TilesetUpdate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Update an existing tileset.
    
    Requires authentication and ownership of the tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to update this tileset")
            
            # Build update query dynamically
            updates = []
            params = []
            
            if tileset.name is not None:
                updates.append("name = %s")
                params.append(tileset.name)
            
            if tileset.description is not None:
                updates.append("description = %s")
                params.append(tileset.description)
            
            if tileset.min_zoom is not None:
                updates.append("min_zoom = %s")
                params.append(tileset.min_zoom)
            
            if tileset.max_zoom is not None:
                updates.append("max_zoom = %s")
                params.append(tileset.max_zoom)
            
            if tileset.bounds is not None and len(tileset.bounds) == 4:
                west, south, east, north = tileset.bounds
                updates.append(f"bounds = ST_MakeEnvelope({west}, {south}, {east}, {north}, 4326)")
            
            if tileset.center is not None and len(tileset.center) >= 2:
                lon, lat = tileset.center[0], tileset.center[1]
                updates.append(f"center = ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)")
            
            if tileset.attribution is not None:
                updates.append("attribution = %s")
                params.append(tileset.attribution)
            
            if tileset.is_public is not None:
                updates.append("is_public = %s")
                params.append(tileset.is_public)
            
            if tileset.metadata is not None:
                updates.append("metadata = %s")
                params.append(json.dumps(tileset.metadata))
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            updates.append("updated_at = NOW()")
            params.append(tileset_id)
            
            cur.execute(
                f"""
                UPDATE tilesets
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, name, description, type, format,
                          min_zoom, max_zoom, attribution, is_public,
                          created_at, updated_at
                """,
                params,
            )
            
            row = cur.fetchone()
            conn.commit()
            
            # Invalidate cache for this tileset
            invalidate_tileset_cache(f"raster:{tileset_id}")
            invalidate_tileset_cache(f"pmtiles:{tileset_id}")
            invalidate_tileset_cache(f"vector:{tileset_id}")
            
            return {
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "type": row[3],
                "format": row[4],
                "min_zoom": row[5],
                "max_zoom": row[6],
                "attribution": row[7],
                "is_public": row[8],
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating tileset: {str(e)}")


# ============================================================================
# Delete Tileset
# ============================================================================


@router.delete("/{tileset_id}", status_code=204)
def delete_tileset(
    tileset_id: str,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete a tileset and all associated features.
    
    Requires authentication and ownership of the tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this tileset")
            
            # Delete tileset (cascades to features due to FK constraint)
            cur.execute("DELETE FROM tilesets WHERE id = %s", (tileset_id,))
            conn.commit()
            
            # Invalidate cache for this tileset
            invalidate_tileset_cache(f"raster:{tileset_id}")
            invalidate_tileset_cache(f"pmtiles:{tileset_id}")
            invalidate_tileset_cache(f"vector:{tileset_id}")
            
            return Response(status_code=204)
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting tileset: {str(e)}")
