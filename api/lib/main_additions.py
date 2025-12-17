# ============================================================================
# 追加import (main.pyの先頭のimport部分に追加)
# ============================================================================

from fastapi import UploadFile, File
from lib.raster_tiles import list_colormaps, validate_cog
from lib.storage import (
    SupabaseStorageClient,
    get_storage_client,
    validate_cog_file,
    extract_cog_metadata,
    MAX_FILE_SIZE,
    COG_EXTENSIONS,
)


# ============================================================================
# Colormap API Endpoints (datasource endpointsの前に追加)
# ============================================================================


@app.get("/api/colormaps")
def get_colormaps():
    """
    List all available colormaps for raster visualization.
    
    Returns a list of colormap names that can be used with raster tiles.
    Preset colormaps include: ndvi, terrain, temperature, precipitation, etc.
    """
    try:
        colormaps = list_colormaps()
        
        # カラーマップの説明
        descriptions = {
            "ndvi": "Normalized Difference Vegetation Index - green to red",
            "terrain": "Elevation/DEM - green to brown to white",
            "elevation": "Alias for terrain colormap",
            "dem": "Alias for terrain colormap",
            "temperature": "Cool to warm - blue to white to red",
            "coolwarm": "Alias for temperature colormap",
            "precipitation": "Rainfall - white to blue to purple",
            "rainfall": "Alias for precipitation colormap",
            "bathymetry": "Ocean depth - deep blue to turquoise",
            "ocean": "Alias for bathymetry colormap",
            "grayscale": "Black to white gradient",
            "hillshade": "Alias for grayscale colormap",
            "viridis": "Perceptually uniform - purple to green to yellow",
        }
        
        return {
            "colormaps": [
                {
                    "name": cm,
                    "description": descriptions.get(cm, ""),
                }
                for cm in colormaps
            ],
            "count": len(colormaps),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing colormaps: {str(e)}")


@app.get("/api/colormaps/{name}")
def get_colormap_info(name: str):
    """
    Get information about a specific colormap.
    
    Args:
        name: Colormap name
        
    Returns:
        Colormap details including color stops
    """
    try:
        from lib.raster_tiles import get_colormap, COLORMAP_PRESETS
        
        cmap = get_colormap(name)
        if not cmap:
            raise HTTPException(status_code=404, detail=f"Colormap '{name}' not found")
        
        # カラーストップを抽出
        color_stops = []
        for value, rgba in sorted(cmap.items()):
            color_stops.append({
                "value": value,
                "color": f"rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3] / 255:.2f})",
                "hex": f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}",
            })
        
        return {
            "name": name,
            "color_stops": color_stops,
            "is_preset": name.lower() in COLORMAP_PRESETS,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting colormap: {str(e)}")


# ============================================================================
# COG Upload Endpoint (datasource endpointsの後に追加)
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


@app.post("/api/datasources/cog/upload", response_model=COGUploadResponse)
async def upload_cog_file(
    tileset_id: str = Query(..., description="Parent tileset UUID"),
    file: UploadFile = File(..., description="COG file to upload"),
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Upload a Cloud Optimized GeoTIFF (COG) file and create a datasource.
    
    This endpoint:
    1. Validates the file (type, size)
    2. Uploads to Supabase Storage
    3. Extracts COG metadata (bounds, bands, CRS)
    4. Creates a raster_sources record
    5. Updates the parent tileset with bounds/center
    
    Requires authentication and ownership of the parent tileset.
    Maximum file size: 500MB
    Supported formats: .tif, .tiff, .geotiff
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        is_valid, error_msg = validate_cog_file(file.filename, file.size or 0)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
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
                raise HTTPException(
                    status_code=403, 
                    detail="Not authorized to upload to this tileset"
                )
            
            if row[2] != "raster":
                raise HTTPException(
                    status_code=400,
                    detail="COG can only be uploaded to raster type tileset"
                )
            
            # Check if datasource already exists
            cur.execute(
                "SELECT id FROM raster_sources WHERE tileset_id = %s",
                (tileset_id,),
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Datasource already exists for this tileset. Delete it first."
                )
        
        # Upload to Supabase Storage
        storage = get_storage_client()
        
        upload_result = await storage.upload_file(
            file=file.file,
            filename=file.filename,
            tileset_id=tileset_id,
            user_id=user.id,
            content_type="image/tiff",
        )
        
        if not upload_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {upload_result.error}"
            )
        
        cog_url = upload_result.url
        
        # Extract COG metadata
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
            if source_bounds or source_center or source_min_zoom is not None or source_max_zoom is not None:
                update_parts = []
                update_values = []
                
                if source_bounds and len(source_bounds) == 4:
                    west, south, east, north = source_bounds
                    update_parts.append("bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
                    update_values.extend([west, south, east, north])
                
                if source_center and len(source_center) >= 2:
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
            
            conn.commit()
            
            # Parse band descriptions from JSON
            band_desc_list = None
            if row[7]:
                try:
                    band_desc_list = json.loads(row[7]) if isinstance(row[7], str) else row[7]
                except:
                    pass
            
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
                bounds=json.loads(row[11]) if row[11] else None,
                center=json.loads(row[12]) if row[12] else None,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading COG: {str(e)}")


# ============================================================================
# Raster Preview Enhancement (既存のraster previewエンドポイントを置き換え)
# ============================================================================


@app.get("/api/tiles/raster/{tileset_id}/preview")
async def get_raster_preview_image(
    tileset_id: str,
    max_size: int = Query(512, ge=64, le=2048, description="Maximum preview size"),
    bands: Optional[str] = Query(None, description="Band indexes (comma-separated)"),
    scale_min: Optional[float] = Query(None, description="Minimum scale value"),
    scale_max: Optional[float] = Query(None, description="Maximum scale value"),
    colormap: Optional[str] = Query(None, description="Colormap name for single-band"),
    format: str = Query("png", description="Output format (png, jpg, webp)"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    Generate a preview image from a raster tileset.
    
    Args:
        tileset_id: Tileset UUID
        max_size: Maximum width/height of preview
        bands: Band indexes (e.g., "1,2,3" for RGB)
        scale_min: Minimum value for rescaling
        scale_max: Maximum value for rescaling
        colormap: Colormap name for single-band visualization
        format: Output image format
        
    Returns:
        Preview image
    """
    if not is_rasterio_available():
        raise HTTPException(
            status_code=503,
            detail="Raster preview service is not available"
        )
    
    try:
        # Validate format
        normalized_format = validate_tile_format(format)
        media_type = get_raster_media_type(normalized_format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    try:
        with conn.cursor() as cur:
            # Get tileset and COG URL
            cur.execute(
                """
                SELECT t.id, t.is_public, t.user_id,
                       rs.cog_url, rs.recommended_min_zoom, rs.recommended_max_zoom
                FROM tilesets t
                LEFT JOIN raster_sources rs ON rs.tileset_id = t.id
                WHERE t.id = %s AND t.type = 'raster'
                """,
                (tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Raster tileset not found")
            
            is_public = row[1]
            owner_id = str(row[2]) if row[2] else None
            cog_url = row[3]
            
            # Check access
            if not check_tileset_access(tileset_id, is_public, owner_id, user):
                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                raise HTTPException(status_code=403, detail="Access denied")
            
            if not cog_url:
                raise HTTPException(
                    status_code=404,
                    detail="No COG datasource configured for this tileset"
                )
        
        # Parse band indexes
        indexes = None
        if bands:
            try:
                indexes = tuple(int(b.strip()) for b in bands.split(","))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid band indexes")
        
        # Use defaults if not specified
        if scale_min is None:
            scale_min = settings.raster_default_scale_min
        if scale_max is None:
            scale_max = settings.raster_default_scale_max
        
        # Import async preview function
        from lib.raster_tiles import get_raster_preview_async
        
        # Generate preview
        preview_data = await get_raster_preview_async(
            cog_url=cog_url,
            max_size=max_size,
            indexes=indexes,
            scale_min=scale_min,
            scale_max=scale_max,
            img_format=normalized_format,
            colormap=colormap,
        )
        
        return Response(
            content=preview_data,
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*",
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")
