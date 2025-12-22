"""
Datasources CRUD endpoints.
"""

import json
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File
from pydantic import BaseModel

from lib.database import get_connection
from lib.models.datasource import DatasourceType, StorageProvider, DatasourceCreate
from lib.auth import User, get_current_user, require_auth, check_tileset_access
from lib.pmtiles import is_pmtiles_available, get_pmtiles_metadata
from lib.raster_tiles import is_rasterio_available, get_cog_info
from lib.storage import get_storage_client, validate_cog_file


router = APIRouter(prefix="/api/datasources", tags=["datasources"])


# ============================================================================
# Helper Functions
# ============================================================================


def safe_json_parse(value: Any) -> Any:
    """
    Safely parse a value that might be JSON string or already a Python object.
    
    PostgreSQL JSONB columns are automatically deserialized by psycopg2 to Python
    objects. This function handles both cases:
    - If value is a string, parse it as JSON
    - If value is already a Python object (list/dict), return as-is
    - If value is None, return None
    
    Args:
        value: The value to parse (string, list, dict, or None)
        
    Returns:
        Parsed Python object or None
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    # Already a Python object (list, dict, etc.)
    return value


# ============================================================================
# Response Models
# ============================================================================


class COGUploadResponse(BaseModel):
    """Response model for COG upload."""
    id: str
    tileset_id: str
    type: str = "cog"
    url: str
    storage_provider: str
    band_count: Optional[int] = None
    band_descriptions: Optional[List[str]] = None
    native_crs: Optional[str] = None
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None
    bounds: Optional[List[float]] = None
    center: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


# ============================================================================
# List Datasources
# ============================================================================


@router.get("")
def list_datasources(
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
    type: Optional[str] = Query(None, description="Filter by type (pmtiles or cog)"),
    include_private: bool = Query(False, description="Include private datasources (requires auth)"),
):
    """
    List all accessible datasources (PMTiles and COG sources combined).
    
    By default, only datasources from public tilesets are returned.
    With authentication and include_private=true, also returns user's private datasources.
    """
    try:
        datasources = []
        
        with conn.cursor() as cur:
            # Build conditions for both queries
            if include_private and user:
                access_condition = "(t.is_public = true OR t.user_id = %s)"
                access_params = [user.id]
            else:
                access_condition = "t.is_public = true"
                access_params = []
            
            # Get PMTiles sources
            if type is None or type == "pmtiles":
                cur.execute(
                    f"""
                    SELECT ps.id, ps.tileset_id, ps.pmtiles_url, ps.storage_provider,
                           ps.tile_type, ps.tile_compression, ps.min_zoom, ps.max_zoom,
                           ps.bounds, ps.center, ps.metadata, ps.created_at, ps.updated_at,
                           t.name as tileset_name, t.is_public, t.user_id
                    FROM pmtiles_sources ps
                    JOIN tilesets t ON ps.tileset_id = t.id
                    WHERE {access_condition}
                    ORDER BY ps.created_at DESC
                    """,
                    access_params,
                )
                
                for row in cur.fetchall():
                    datasources.append({
                        "id": str(row[0]),
                        "tileset_id": str(row[1]),
                        "type": "pmtiles",
                        "url": row[2],
                        "storage_provider": row[3],
                        "tile_type": row[4],
                        "compression": row[5],
                        "min_zoom": row[6],
                        "max_zoom": row[7],
                        "bounds": safe_json_parse(row[8]),
                        "center": safe_json_parse(row[9]),
                        "metadata": safe_json_parse(row[10]),
                        "created_at": row[11].isoformat() if row[11] else None,
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "tileset_name": row[13],
                        "is_public": row[14],
                        "user_id": str(row[15]) if row[15] else None,
                    })
            
            # Get COG sources
            if type is None or type == "cog":
                cur.execute(
                    f"""
                    SELECT rs.id, rs.tileset_id, rs.cog_url, rs.storage_provider,
                           rs.band_count, rs.native_crs, rs.recommended_min_zoom, rs.recommended_max_zoom,
                           rs.metadata, rs.created_at, rs.updated_at,
                           t.name as tileset_name, t.is_public, t.user_id
                    FROM raster_sources rs
                    JOIN tilesets t ON rs.tileset_id = t.id
                    WHERE {access_condition}
                    ORDER BY rs.created_at DESC
                    """,
                    access_params,
                )
                
                for row in cur.fetchall():
                    datasources.append({
                        "id": str(row[0]),
                        "tileset_id": str(row[1]),
                        "type": "cog",
                        "url": row[2],
                        "storage_provider": row[3],
                        "band_count": row[4],
                        "native_crs": row[5],
                        "min_zoom": row[6],
                        "max_zoom": row[7],
                        "metadata": safe_json_parse(row[8]),
                        "created_at": row[9].isoformat() if row[9] else None,
                        "updated_at": row[10].isoformat() if row[10] else None,
                        "tileset_name": row[11],
                        "is_public": row[12],
                        "user_id": str(row[13]) if row[13] else None,
                    })
        
        # Sort by created_at descending
        datasources.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        
        return {"datasources": datasources, "count": len(datasources)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing datasources: {str(e)}")


# ============================================================================
# Get Datasource
# ============================================================================


@router.get("/{datasource_id}")
def get_datasource(
    datasource_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific datasource by ID."""
    try:
        with conn.cursor() as cur:
            # Try PMTiles first
            cur.execute(
                """
                SELECT ps.id, ps.tileset_id, ps.pmtiles_url, ps.storage_provider,
                       ps.tile_type, ps.tile_compression, ps.min_zoom, ps.max_zoom,
                       ps.bounds, ps.center, ps.layers, ps.metadata, ps.created_at, ps.updated_at,
                       t.name as tileset_name, t.is_public, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE ps.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                is_public = row[15]
                owner_user_id = str(row[16]) if row[16] else None
                
                # Check access
                if not check_tileset_access(str(row[1]), is_public, owner_user_id, user):
                    if not user:
                        raise HTTPException(
                            status_code=401,
                            detail="Authentication required to access this datasource",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have permission to access this datasource"
                    )
                
                return {
                    "id": str(row[0]),
                    "tileset_id": str(row[1]),
                    "type": "pmtiles",
                    "url": row[2],
                    "storage_provider": row[3],
                    "tile_type": row[4],
                    "compression": row[5],
                    "min_zoom": row[6],
                    "max_zoom": row[7],
                    "bounds": safe_json_parse(row[8]),
                    "center": safe_json_parse(row[9]),
                    "layers": safe_json_parse(row[10]),
                    "metadata": safe_json_parse(row[11]),
                    "created_at": row[12].isoformat() if row[12] else None,
                    "updated_at": row[13].isoformat() if row[13] else None,
                    "tileset_name": row[14],
                    "is_public": row[15],
                    "user_id": owner_user_id,
                }
            
            # Try COG
            cur.execute(
                """
                SELECT rs.id, rs.tileset_id, rs.cog_url, rs.storage_provider,
                       rs.band_count, rs.band_descriptions, rs.native_crs, rs.native_resolution,
                       rs.recommended_min_zoom, rs.recommended_max_zoom,
                       rs.metadata, rs.created_at, rs.updated_at,
                       t.name as tileset_name, t.is_public, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE rs.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                is_public = row[14]
                owner_user_id = str(row[15]) if row[15] else None
                
                # Check access
                if not check_tileset_access(str(row[1]), is_public, owner_user_id, user):
                    if not user:
                        raise HTTPException(
                            status_code=401,
                            detail="Authentication required to access this datasource",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have permission to access this datasource"
                    )
                
                return {
                    "id": str(row[0]),
                    "tileset_id": str(row[1]),
                    "type": "cog",
                    "url": row[2],
                    "storage_provider": row[3],
                    "band_count": row[4],
                    "band_descriptions": safe_json_parse(row[5]),
                    "native_crs": row[6],
                    "native_resolution": row[7],
                    "min_zoom": row[8],
                    "max_zoom": row[9],
                    "metadata": safe_json_parse(row[10]),
                    "created_at": row[11].isoformat() if row[11] else None,
                    "updated_at": row[12].isoformat() if row[12] else None,
                    "tileset_name": row[13],
                    "is_public": row[14],
                    "user_id": owner_user_id,
                }
            
            raise HTTPException(status_code=404, detail="Datasource not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching datasource: {str(e)}")


# ============================================================================
# Create Datasource
# ============================================================================


@router.post("", status_code=201)
async def create_datasource(
    datasource: DatasourceCreate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Create a new datasource.
    
    Requires authentication and ownership of the parent tileset.
    Automatically fetches metadata (bounds, center, zoom levels) from the data source
    and updates both the datasource record and the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id, type FROM tilesets WHERE id = %s",
                (datasource.tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to add datasource to this tileset")
            
            tileset_type = row[2]
            
            # Validate type matches tileset type
            if datasource.type == DatasourceType.pmtiles and tileset_type != "pmtiles":
                raise HTTPException(
                    status_code=400,
                    detail="PMTiles datasource can only be added to pmtiles type tileset"
                )
            if datasource.type == DatasourceType.cog and tileset_type != "raster":
                raise HTTPException(
                    status_code=400,
                    detail="COG datasource can only be added to raster type tileset"
                )
            
            metadata_json = json.dumps(datasource.metadata) if datasource.metadata else None
            
            if datasource.type == DatasourceType.pmtiles:
                return await _create_pmtiles_datasource(datasource, metadata_json, conn, cur)
            else:
                return await _create_cog_datasource(datasource, metadata_json, conn, cur)
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating datasource: {str(e)}")


async def _create_pmtiles_datasource(datasource: DatasourceCreate, metadata_json, conn, cur):
    """Create a PMTiles datasource."""
    # Check if datasource already exists for this tileset
    cur.execute(
        "SELECT id FROM pmtiles_sources WHERE tileset_id = %s",
        (datasource.tileset_id,),
    )
    if cur.fetchone():
        raise HTTPException(
            status_code=400,
            detail="Datasource already exists for this tileset"
        )
    
    # Fetch PMTiles metadata
    source_bounds = None
    source_center = None
    source_min_zoom = None
    source_max_zoom = None
    tile_type = None
    tile_compression = None
    layers_json = None
    
    if is_pmtiles_available():
        try:
            pmtiles_meta = await get_pmtiles_metadata(datasource.url)
            if pmtiles_meta:
                source_bounds = pmtiles_meta.get("bounds")
                source_center = pmtiles_meta.get("center")
                source_min_zoom = pmtiles_meta.get("min_zoom")
                source_max_zoom = pmtiles_meta.get("max_zoom")
                tile_type = pmtiles_meta.get("tile_type")
                tile_compression = pmtiles_meta.get("tile_compression")
                layers = pmtiles_meta.get("layers", [])
                if layers:
                    layers_json = json.dumps(layers)
        except Exception as meta_error:
            print(f"Warning: Could not fetch PMTiles metadata: {meta_error}")
    
    # Insert with metadata
    cur.execute(
        """
        INSERT INTO pmtiles_sources (
            tileset_id, pmtiles_url, storage_provider, metadata,
            tile_type, tile_compression, min_zoom, max_zoom,
            bounds, center, layers
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, tileset_id, pmtiles_url, storage_provider, metadata,
                  created_at, updated_at, tile_type, tile_compression,
                  min_zoom, max_zoom, bounds, center, layers
        """,
        (
            datasource.tileset_id,
            datasource.url,
            datasource.storage_provider.value,
            metadata_json,
            tile_type,
            tile_compression,
            source_min_zoom,
            source_max_zoom,
            json.dumps(source_bounds) if source_bounds else None,
            json.dumps(source_center) if source_center else None,
            layers_json,
        ),
    )
    
    row = cur.fetchone()
    
    # Update parent tileset with bounds/center/zoom if available
    _update_tileset_from_metadata(
        cur, datasource.tileset_id,
        source_bounds, source_center, source_min_zoom, source_max_zoom
    )
    
    conn.commit()
    
    return {
        "id": str(row[0]),
        "tileset_id": str(row[1]),
        "type": "pmtiles",
        "url": row[2],
        "storage_provider": row[3],
        "metadata": safe_json_parse(row[4]),
        "created_at": row[5].isoformat() if row[5] else None,
        "updated_at": row[6].isoformat() if row[6] else None,
        "tile_type": row[7],
        "tile_compression": row[8],
        "min_zoom": row[9],
        "max_zoom": row[10],
        "bounds": safe_json_parse(row[11]),
        "center": safe_json_parse(row[12]),
        "layers": safe_json_parse(row[13]),
    }


async def _create_cog_datasource(datasource: DatasourceCreate, metadata_json, conn, cur):
    """Create a COG datasource."""
    # Check if datasource already exists for this tileset
    cur.execute(
        "SELECT id FROM raster_sources WHERE tileset_id = %s",
        (datasource.tileset_id,),
    )
    if cur.fetchone():
        raise HTTPException(
            status_code=400,
            detail="Datasource already exists for this tileset"
        )
    
    # Fetch COG metadata
    source_bounds = None
    source_center = None
    source_min_zoom = None
    source_max_zoom = None
    band_count = None
    band_descriptions_json = None
    native_crs = None
    
    if is_rasterio_available():
        try:
            cog_info = get_cog_info(datasource.url)
            if cog_info:
                cog_bounds = cog_info.get("bounds")
                if cog_bounds:
                    source_bounds = list(cog_bounds)
                    source_center = [
                        (cog_bounds[0] + cog_bounds[2]) / 2,
                        (cog_bounds[1] + cog_bounds[3]) / 2,
                        10
                    ]
                source_min_zoom = cog_info.get("minzoom")
                source_max_zoom = cog_info.get("maxzoom")
                band_count = cog_info.get("count")
                band_descriptions = cog_info.get("band_descriptions", [])
                if band_descriptions:
                    band_descriptions_json = json.dumps(band_descriptions)
                native_crs = cog_info.get("crs")
        except Exception as meta_error:
            print(f"Warning: Could not fetch COG info: {meta_error}")
    
    # Insert with metadata
    cur.execute(
        """
        INSERT INTO raster_sources (
            tileset_id, cog_url, storage_provider, metadata,
            band_count, band_descriptions, native_crs,
            recommended_min_zoom, recommended_max_zoom,
            bounds, center
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, tileset_id, cog_url, storage_provider, metadata,
                  created_at, updated_at, band_count, band_descriptions,
                  native_crs, recommended_min_zoom, recommended_max_zoom,
                  bounds, center
        """,
        (
            datasource.tileset_id,
            datasource.url,
            datasource.storage_provider.value,
            metadata_json,
            band_count,
            band_descriptions_json,
            native_crs,
            source_min_zoom,
            source_max_zoom,
            json.dumps(source_bounds) if source_bounds else None,
            json.dumps(source_center) if source_center else None,
        ),
    )
    
    row = cur.fetchone()
    
    # Update parent tileset with bounds/center/zoom if available
    _update_tileset_from_metadata(
        cur, datasource.tileset_id,
        source_bounds, source_center, source_min_zoom, source_max_zoom
    )
    
    conn.commit()
    
    return {
        "id": str(row[0]),
        "tileset_id": str(row[1]),
        "type": "cog",
        "url": row[2],
        "storage_provider": row[3],
        "metadata": safe_json_parse(row[4]),
        "created_at": row[5].isoformat() if row[5] else None,
        "updated_at": row[6].isoformat() if row[6] else None,
        "band_count": row[7],
        "band_descriptions": safe_json_parse(row[8]),
        "native_crs": row[9],
        "min_zoom": row[10],
        "max_zoom": row[11],
        "bounds": safe_json_parse(row[12]),
        "center": safe_json_parse(row[13]),
    }


def _update_tileset_from_metadata(cur, tileset_id, source_bounds, source_center, source_min_zoom, source_max_zoom):
    """Update parent tileset with metadata from datasource."""
    if source_bounds or source_center or source_min_zoom is not None or source_max_zoom is not None:
        update_parts = []
        update_values = []
        
        if source_bounds and len(source_bounds) == 4:
            # Convert [west, south, east, north] to PostGIS Polygon
            west, south, east, north = source_bounds
            update_parts.append("bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
            update_values.extend([west, south, east, north])
        
        if source_center and len(source_center) >= 2:
            # Convert [lon, lat, ...] to PostGIS Point
            lon, lat = source_center[0], source_center[1]
            update_parts.append("center = ST_SetSRID(ST_MakePoint(%s, %s), 4326)")
            update_values.extend([lon, lat])
        
        if source_min_zoom is not None:
            update_parts.append("min_zoom = %s")
            update_values.append(source_min_zoom)
        
        if source_max_zoom is not None:
            update_parts.append("max_zoom = %s")
            update_values.append(source_max_zoom)
        
        if update_parts:
            update_values.append(tileset_id)
            cur.execute(
                f"UPDATE tilesets SET {', '.join(update_parts)} WHERE id = %s",
                update_values,
            )


# ============================================================================
# COG Upload
# ============================================================================


@router.post("/cog/upload", status_code=201, response_model=COGUploadResponse)
async def upload_cog(
    tileset_id: str = Query(..., description="Parent tileset ID"),
    file: UploadFile = File(..., description="COG file to upload"),
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Upload a COG file to Supabase Storage and create a datasource.
    
    The file will be validated as a valid Cloud Optimized GeoTIFF,
    uploaded to Supabase Storage, and a new datasource record will be created
    linked to the specified tileset.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        # Check if tileset exists and user owns it
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, type FROM tilesets WHERE id = %s",
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to add datasource to this tileset")
            
            if row[2] != "raster":
                raise HTTPException(
                    status_code=400,
                    detail="COG datasource can only be added to raster type tileset"
                )
            
            # Check if datasource already exists for this tileset
            cur.execute(
                "SELECT id FROM raster_sources WHERE tileset_id = %s",
                (tileset_id,),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Datasource already exists for this tileset"
                )
        
        # Read file content
        file_content = await file.read()
        
        # Validate it's a valid COG
        is_valid, validation_message = validate_cog_file(file_content)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid COG file: {validation_message}"
            )
        
        # Upload to Supabase Storage
        storage = get_storage_client()
        if not storage:
            raise HTTPException(
                status_code=500,
                detail="Storage service is not available"
            )
        
        # Generate storage path
        filename = file.filename or "upload.tif"
        storage_path = f"cog/{tileset_id}/{filename}"
        
        # Upload file
        cog_url = storage.upload_file(storage_path, file_content, "image/tiff")
        if not cog_url:
            raise HTTPException(
                status_code=500,
                detail="Failed to upload file to storage"
            )
        
        # Get COG metadata
        source_bounds = None
        source_center = None
        source_min_zoom = None
        source_max_zoom = None
        band_count = None
        band_descriptions_json = None
        native_crs = None
        
        if is_rasterio_available():
            try:
                cog_info = get_cog_info(cog_url)
                if cog_info:
                    cog_bounds = cog_info.get("bounds")
                    if cog_bounds:
                        source_bounds = list(cog_bounds)
                        source_center = [
                            (cog_bounds[0] + cog_bounds[2]) / 2,
                            (cog_bounds[1] + cog_bounds[3]) / 2,
                            10
                        ]
                    source_min_zoom = cog_info.get("minzoom")
                    source_max_zoom = cog_info.get("maxzoom")
                    band_count = cog_info.get("count")
                    band_descriptions = cog_info.get("band_descriptions", [])
                    if band_descriptions:
                        band_descriptions_json = json.dumps(band_descriptions)
                    native_crs = cog_info.get("crs")
            except Exception as meta_error:
                print(f"Warning: Could not fetch COG info: {meta_error}")
        
        # Insert datasource record
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raster_sources (
                    tileset_id, cog_url, storage_provider, metadata,
                    band_count, band_descriptions, native_crs,
                    recommended_min_zoom, recommended_max_zoom,
                    bounds, center
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, tileset_id, cog_url, storage_provider,
                          created_at, updated_at, band_count, band_descriptions,
                          native_crs, recommended_min_zoom, recommended_max_zoom,
                          bounds, center
                """,
                (
                    tileset_id,
                    cog_url,
                    "supabase",
                    None,
                    band_count,
                    band_descriptions_json,
                    native_crs,
                    source_min_zoom,
                    source_max_zoom,
                    json.dumps(source_bounds) if source_bounds else None,
                    json.dumps(source_center) if source_center else None,
                ),
            )
            
            row = cur.fetchone()
            
            # Update parent tileset with bounds/center/zoom
            _update_tileset_from_metadata(
                cur, tileset_id,
                source_bounds, source_center, source_min_zoom, source_max_zoom
            )
            
            conn.commit()
            
            # Parse band descriptions from JSON - use safe_json_parse
            band_desc_list = safe_json_parse(row[7])
            
            return COGUploadResponse(
                id=str(row[0]),
                tileset_id=str(row[1]),
                type="cog",
                url=row[2],
                storage_provider=row[3],
                created_at=row[4].isoformat() if row[4] else None,
                band_count=row[6],
                band_descriptions=band_desc_list,
                native_crs=row[8],
                min_zoom=row[9],
                max_zoom=row[10],
                bounds=safe_json_parse(row[11]),
                center=safe_json_parse(row[12]),
            )
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading COG: {str(e)}")


# ============================================================================
# Delete Datasource
# ============================================================================


@router.delete("/{datasource_id}", status_code=204)
def delete_datasource(
    datasource_id: str,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete a datasource.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Try PMTiles first
            cur.execute(
                """
                SELECT ps.id, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE ps.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[1]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to delete this datasource")
                
                cur.execute("DELETE FROM pmtiles_sources WHERE id = %s", (datasource_id,))
                conn.commit()
                return Response(status_code=204)
            
            # Try COG
            cur.execute(
                """
                SELECT rs.id, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE rs.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[1]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to delete this datasource")
                
                cur.execute("DELETE FROM raster_sources WHERE id = %s", (datasource_id,))
                conn.commit()
                return Response(status_code=204)
            
            raise HTTPException(status_code=404, detail="Datasource not found")
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting datasource: {str(e)}")


# ============================================================================
# Test Datasource Connection
# ============================================================================


@router.post("/{datasource_id}/test")
async def test_datasource_connection(
    datasource_id: str,
    conn=Depends(get_connection),
    user: User = Depends(require_auth),
):
    """
    Test connection to a datasource.
    
    For PMTiles: Attempts to read metadata from the file.
    For COG: Attempts to read info from the file.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Try PMTiles first
            cur.execute(
                """
                SELECT ps.id, ps.pmtiles_url, t.user_id
                FROM pmtiles_sources ps
                JOIN tilesets t ON ps.tileset_id = t.id
                WHERE ps.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[2]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to test this datasource")
                
                pmtiles_url = row[1]
                
                if not is_pmtiles_available():
                    return {
                        "status": "error",
                        "type": "pmtiles",
                        "message": "PMTiles service is not available",
                    }
                
                try:
                    metadata = await get_pmtiles_metadata(pmtiles_url)
                    return {
                        "status": "success",
                        "type": "pmtiles",
                        "message": "Successfully connected to PMTiles file",
                        "metadata": metadata,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "type": "pmtiles",
                        "message": f"Failed to connect: {str(e)}",
                    }
            
            # Try COG
            cur.execute(
                """
                SELECT rs.id, rs.cog_url, t.user_id
                FROM raster_sources rs
                JOIN tilesets t ON rs.tileset_id = t.id
                WHERE rs.id = %s
                """,
                (datasource_id,),
            )
            row = cur.fetchone()
            
            if row:
                if str(row[2]) != user.id:
                    raise HTTPException(status_code=403, detail="Not authorized to test this datasource")
                
                cog_url = row[1]
                
                if not is_rasterio_available():
                    return {
                        "status": "error",
                        "type": "cog",
                        "message": "Rasterio is not available",
                    }
                
                try:
                    cog_info = get_cog_info(cog_url)
                    return {
                        "status": "success",
                        "type": "cog",
                        "message": "Successfully connected to COG file",
                        "info": cog_info,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "type": "cog",
                        "message": f"Failed to connect: {str(e)}",
                    }
            
            raise HTTPException(status_code=404, detail="Datasource not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing datasource: {str(e)}")
