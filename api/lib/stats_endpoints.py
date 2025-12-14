# ============================================================================
# Statistics Endpoints
# ============================================================================
# このコードは api/lib/main.py の「Preview Page」セクションの前に追加してください
# （@app.post("/api/datasources/{datasource_id}/test") の後）


import uuid  # ファイル上部のimport文に追加が必要


@app.get("/api/stats")
def get_system_stats():
    """
    Get overall system statistics.
    
    Returns:
        - Total tilesets count (by type)
        - Total features count
        - Public/private tileset counts
        - Geometry type distribution
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # タイルセット統計
                cur.execute("""
                    SELECT 
                        type,
                        COUNT(*) as count,
                        COUNT(*) FILTER (WHERE is_public = true) as public_count,
                        COUNT(*) FILTER (WHERE is_public = false) as private_count
                    FROM tilesets
                    GROUP BY type
                """)
                tileset_rows = cur.fetchall()
                
                tileset_stats = {
                    "total": 0,
                    "by_type": {},
                    "public": 0,
                    "private": 0
                }
                for row in tileset_rows:
                    tileset_stats["by_type"][row[0]] = row[1]
                    tileset_stats["total"] += row[1]
                    tileset_stats["public"] += row[2]
                    tileset_stats["private"] += row[3]
                
                # フィーチャー統計
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE ST_GeometryType(geom) LIKE '%Point%') as points,
                        COUNT(*) FILTER (WHERE ST_GeometryType(geom) LIKE '%LineString%') as lines,
                        COUNT(*) FILTER (WHERE ST_GeometryType(geom) LIKE '%Polygon%') as polygons
                    FROM features
                """)
                feature_row = cur.fetchone()
                
                feature_stats = {
                    "total": feature_row[0] if feature_row else 0,
                    "by_geometry_type": {
                        "Point": feature_row[1] if feature_row else 0,
                        "LineString": feature_row[2] if feature_row else 0,
                        "Polygon": feature_row[3] if feature_row else 0
                    }
                }
                
                # タイルセット別フィーチャー数（上位10件）
                cur.execute("""
                    SELECT 
                        t.id,
                        t.name,
                        t.type,
                        COUNT(f.id) as feature_count
                    FROM tilesets t
                    LEFT JOIN features f ON t.id = f.tileset_id
                    WHERE t.type = 'vector'
                    GROUP BY t.id, t.name, t.type
                    ORDER BY feature_count DESC
                    LIMIT 10
                """)
                top_tilesets = cur.fetchall()
                
                tileset_feature_stats = [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "type": row[2],
                        "feature_count": row[3]
                    }
                    for row in top_tilesets
                ]
                
                # データソース統計
                cur.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM pmtiles_sources) as pmtiles_count,
                        (SELECT COUNT(*) FROM raster_sources) as raster_count
                """)
                datasource_row = cur.fetchone()
                
                datasource_stats = {
                    "pmtiles": datasource_row[0] if datasource_row else 0,
                    "raster": datasource_row[1] if datasource_row else 0,
                    "total": (datasource_row[0] or 0) + (datasource_row[1] or 0) if datasource_row else 0
                }
                
                return {
                    "tilesets": tileset_stats,
                    "features": feature_stats,
                    "datasources": datasource_stats,
                    "top_tilesets_by_features": tileset_feature_stats
                }
                
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@app.get("/api/tilesets/{tileset_id}/stats")
def get_tileset_stats(
    tileset_id: str,
    user: Optional[User] = Depends(get_current_user)
):
    """
    Get statistics for a specific tileset.
    
    Returns:
        - Feature count
        - Geometry type distribution
        - Bounds (calculated from features)
        - Latest update timestamp
    """
    try:
        # Validate UUID
        try:
            uuid_obj = uuid.UUID(tileset_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tileset ID format")
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # タイルセット存在確認とアクセス権チェック
                cur.execute("""
                    SELECT id, name, type, is_public, user_id
                    FROM tilesets
                    WHERE id = %s
                """, (str(uuid_obj),))
                tileset = cur.fetchone()
                
                if not tileset:
                    raise HTTPException(status_code=404, detail="Tileset not found")
                
                # 非公開タイルセットの場合はオーナーチェック
                if not tileset[3]:  # is_public
                    if not user:
                        raise HTTPException(status_code=401, detail="Authentication required")
                    if tileset[4] and str(tileset[4]) != user.id:  # user_id
                        raise HTTPException(status_code=403, detail="Access denied")
                
                # vectorタイプのみフィーチャー統計を返す
                if tileset[2] != "vector":  # type
                    return {
                        "tileset_id": tileset_id,
                        "tileset_name": tileset[1],
                        "tileset_type": tileset[2],
                        "feature_count": 0,
                        "geometry_types": {},
                        "bounds": None,
                        "latest_update": None,
                        "message": "Feature statistics are only available for vector tilesets"
                    }
                
                # フィーチャー統計
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE ST_GeometryType(geom) LIKE '%%Point%%') as points,
                        COUNT(*) FILTER (WHERE ST_GeometryType(geom) LIKE '%%LineString%%') as lines,
                        COUNT(*) FILTER (WHERE ST_GeometryType(geom) LIKE '%%Polygon%%') as polygons,
                        MAX(updated_at) as latest_update
                    FROM features
                    WHERE tileset_id = %s
                """, (str(uuid_obj),))
                stats_row = cur.fetchone()
                
                # Bounds計算
                cur.execute("""
                    SELECT 
                        ST_XMin(ST_Extent(geom)) as min_x,
                        ST_YMin(ST_Extent(geom)) as min_y,
                        ST_XMax(ST_Extent(geom)) as max_x,
                        ST_YMax(ST_Extent(geom)) as max_y
                    FROM features
                    WHERE tileset_id = %s
                """, (str(uuid_obj),))
                bounds_row = cur.fetchone()
                
                bounds = None
                if bounds_row and bounds_row[0] is not None:
                    bounds = [
                        bounds_row[0],  # min_x
                        bounds_row[1],  # min_y
                        bounds_row[2],  # max_x
                        bounds_row[3]   # max_y
                    ]
                
                return {
                    "tileset_id": tileset_id,
                    "tileset_name": tileset[1],
                    "tileset_type": tileset[2],
                    "feature_count": stats_row[0] if stats_row else 0,
                    "geometry_types": {
                        "Point": stats_row[1] if stats_row else 0,
                        "LineString": stats_row[2] if stats_row else 0,
                        "Polygon": stats_row[3] if stats_row else 0
                    },
                    "bounds": bounds,
                    "latest_update": stats_row[4].isoformat() if stats_row and stats_row[4] else None
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tileset statistics: {str(e)}"
        )
