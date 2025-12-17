"""
Statistics endpoints.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from lib.database import get_db_connection
from lib.auth import User, get_current_user


router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
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
                # Tileset statistics
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
                
                # Feature statistics
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
                
                # Feature count by tileset (top 10)
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
                
                # Datasource statistics
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


# Note: /api/tilesets/{tileset_id}/stats is defined in tilesets router
# This router only handles /api/stats endpoint
