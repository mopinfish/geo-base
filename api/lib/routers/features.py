"""
Features CRUD endpoints.

Provides endpoints for creating, reading, updating, and deleting
geographic features within tilesets.

Key features:
- Single and bulk feature creation
- Automatic bounds/center calculation after bulk import
- Geometry validation before import
- Access control via tileset ownership
"""

import json
import logging
from typing import Optional, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from lib.database import get_connection
from lib.models.feature import (
    FeatureCreate,
    FeatureUpdate,
    BulkFeatureCreate,
    BulkFeatureResponse,
)
from lib.auth import User, get_current_user, require_auth, check_tileset_access
from lib.validators import (
    validate_feature,
    validate_geometry,
    ValidationResult,
)
from lib.cache import invalidate_tileset_cache


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/features", tags=["features"])


# ============================================================================
# Helper Functions
# ============================================================================


def _update_tileset_bounds(tileset_id: str, conn) -> Tuple[bool, Optional[List[float]], Optional[List[float]]]:
    """
    Calculate and update tileset bounds from its features.
    
    Args:
        tileset_id: The tileset ID to update
        conn: Database connection
        
    Returns:
        Tuple of (success, bounds, center)
        - success: Whether bounds were successfully updated
        - bounds: [west, south, east, north] or None
        - center: [longitude, latitude] or None
    """
    try:
        with conn.cursor() as cur:
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
                logger.info(f"No features found for tileset {tileset_id}, skipping bounds update")
                return False, None, None
            
            xmin, ymin, xmax, ymax, center_x, center_y, feature_count = result
            
            # Update tileset with calculated bounds and center
            cur.execute(
                """
                UPDATE tilesets
                SET bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                    center = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (xmin, ymin, xmax, ymax, center_x, center_y, tileset_id),
            )
            
            logger.info(
                f"Updated bounds for tileset {tileset_id}: "
                f"bounds=[{xmin}, {ymin}, {xmax}, {ymax}], "
                f"center=[{center_x}, {center_y}], "
                f"features={feature_count}"
            )
            
            return True, [xmin, ymin, xmax, ymax], [center_x, center_y]
            
    except Exception as e:
        logger.error(f"Error updating tileset bounds: {str(e)}")
        return False, None, None


def _validate_features_for_import(
    features: List[dict],
    validate_geometry_flag: bool = True,
    max_errors: int = 100
) -> Tuple[List[dict], List[str], List[str]]:
    """
    Validate features before import.
    
    Args:
        features: List of GeoJSON feature objects
        validate_geometry_flag: Whether to perform geometry validation
        max_errors: Maximum number of errors to collect
        
    Returns:
        Tuple of (valid_features, errors, warnings)
    """
    valid_features = []
    errors = []
    warnings = []
    
    for idx, feature in enumerate(features):
        try:
            # Basic structure validation
            if not isinstance(feature, dict):
                errors.append(f"Feature #{idx + 1}: Must be an object")
                continue
            
            geometry = feature.get("geometry")
            if not geometry:
                errors.append(f"Feature #{idx + 1}: Missing geometry")
                continue
            
            # Validate geometry if flag is set
            if validate_geometry_flag:
                result = validate_geometry(geometry, f"Feature #{idx + 1}", check_coordinates=True)
                if not result.valid:
                    errors.append(result.error or f"Feature #{idx + 1}: Invalid geometry")
                    if len(errors) >= max_errors:
                        errors.append(f"... stopped after {max_errors} errors")
                        break
                    continue
                
                # Collect warnings
                for warning in result.warnings:
                    warnings.append(f"Feature #{idx + 1}: {warning}")
            
            # Ensure properties is a dict
            properties = feature.get("properties", {})
            if properties is None:
                properties = {}
            
            valid_features.append({
                "geometry": json.dumps(geometry),
                "properties": json.dumps(properties),
            })
            
        except Exception as e:
            errors.append(f"Feature #{idx + 1}: {str(e)}")
            if len(errors) >= max_errors:
                errors.append(f"... stopped after {max_errors} errors")
                break
    
    return valid_features, errors, warnings


# ============================================================================
# Create Feature
# ============================================================================


@router.post("", status_code=201)
def create_feature(
    feature: FeatureCreate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Create a new feature in a tileset.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id FROM tilesets WHERE id = %s",
                (feature.tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to add features to this tileset")
            
            # Validate geometry
            geom_result = validate_geometry(feature.geometry, "geometry", check_coordinates=True)
            if not geom_result.valid:
                raise HTTPException(status_code=400, detail=f"Invalid geometry: {geom_result.error}")
            
            # Convert GeoJSON geometry to JSON string
            geometry_json = json.dumps(feature.geometry)
            properties_json = json.dumps(feature.properties) if feature.properties else "{}"
            
            cur.execute(
                """
                INSERT INTO features (tileset_id, layer_name, geom, properties)
                VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s)
                RETURNING id, layer_name, ST_AsGeoJSON(geom)::json as geometry, properties,
                          created_at, updated_at
                """,
                (
                    feature.tileset_id,
                    feature.layer_name,
                    geometry_json,
                    properties_json,
                ),
            )
            
            row = cur.fetchone()
            conn.commit()
            
            # Invalidate cache
            invalidate_tileset_cache(f"vector:{feature.tileset_id}")
            
            return {
                "id": str(row[0]),
                "type": "Feature",
                "geometry": row[2],
                "properties": {
                    **(row[3] if row[3] else {}),
                    "layer_name": row[1],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating feature: {str(e)}")


# ============================================================================
# Bulk Create Features
# ============================================================================


@router.post("/bulk", status_code=201, response_model=BulkFeatureResponse)
def create_features_bulk(
    data: BulkFeatureCreate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Create multiple features in a tileset at once.
    
    This endpoint is optimized for bulk imports and uses batch INSERT
    for significantly better performance compared to individual inserts.
    
    Features:
    - Maximum 10,000 features per request
    - Optional geometry validation before import
    - Automatic bounds/center calculation after successful import
    
    Requires authentication and ownership of the parent tileset.
    """
    from psycopg2.extras import execute_values
    
    try:
        with conn.cursor() as cur:
            # Check if tileset exists and user owns it
            cur.execute(
                "SELECT id, user_id, type FROM tilesets WHERE id = %s",
                (data.tileset_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Tileset not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(
                    status_code=403, 
                    detail="Not authorized to add features to this tileset"
                )
            
            tileset_type = row[2]
            
            # Warn if adding features to non-vector tileset
            if tileset_type != "vector":
                logger.warning(
                    f"Adding features to non-vector tileset {data.tileset_id} (type: {tileset_type})"
                )
            
            # Validate and prepare features
            valid_features, validation_errors, validation_warnings = _validate_features_for_import(
                data.features,
                validate_geometry_flag=data.validate_geometry,
            )
            
            if not valid_features:
                return BulkFeatureResponse(
                    success_count=0,
                    failed_count=len(data.features),
                    feature_ids=[],
                    errors=validation_errors[:100],
                    warnings=validation_warnings[:50],
                    bounds_updated=False,
                )
            
            # Prepare for bulk insert
            success_count = 0
            failed_count = len(validation_errors)  # Already failed validation
            feature_ids = []
            errors = validation_errors.copy()
            
            # Batch insert using execute_values for performance
            insert_query = """
                INSERT INTO features (tileset_id, layer_name, geom, properties)
                VALUES %s
                RETURNING id
            """
            
            # Prepare values template
            values_template = f"('{data.tileset_id}', '{data.layer_name}', ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s)"
            
            # Convert to list of tuples for execute_values
            values_list = [(f["geometry"], f["properties"]) for f in valid_features]
            
            try:
                # Use execute_values for efficient bulk insert
                result = execute_values(
                    cur,
                    insert_query,
                    values_list,
                    template=values_template,
                    fetch=True,
                )
                
                # Collect created feature IDs
                for row in result:
                    feature_ids.append(str(row[0]))
                    success_count += 1
                
                # Update bounds if requested and we have successful inserts
                bounds_updated = False
                bounds = None
                center = None
                
                if data.update_bounds and success_count > 0:
                    bounds_updated, bounds, center = _update_tileset_bounds(data.tileset_id, conn)
                
                conn.commit()
                
                # Invalidate cache
                invalidate_tileset_cache(f"vector:{data.tileset_id}")
                
                logger.info(
                    f"Bulk import completed: {success_count} succeeded, {failed_count} failed, "
                    f"bounds_updated={bounds_updated}"
                )
                
                return BulkFeatureResponse(
                    success_count=success_count,
                    failed_count=failed_count,
                    feature_ids=feature_ids,
                    errors=errors[:100],
                    warnings=validation_warnings[:50],
                    bounds_updated=bounds_updated,
                    bounds=bounds,
                    center=center,
                )
                
            except Exception as e:
                conn.rollback()
                logger.warning(f"Batch insert failed, falling back to individual inserts: {str(e)}")
                
                # If batch insert fails, try one by one to identify problematic features
                for idx, values in enumerate(values_list):
                    try:
                        cur.execute(
                            """
                            INSERT INTO features (tileset_id, layer_name, geom, properties)
                            VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s)
                            RETURNING id
                            """,
                            (data.tileset_id, data.layer_name, values[0], values[1]),
                        )
                        row = cur.fetchone()
                        if row:
                            feature_ids.append(str(row[0]))
                            success_count += 1
                        conn.commit()
                    except Exception as inner_e:
                        conn.rollback()
                        failed_count += 1
                        errors.append(f"Feature #{idx + 1}: {str(inner_e)}")
                
                # Update bounds after fallback inserts
                bounds_updated = False
                bounds = None
                center = None
                
                if data.update_bounds and success_count > 0:
                    bounds_updated, bounds, center = _update_tileset_bounds(data.tileset_id, conn)
                    conn.commit()
                
                # Invalidate cache
                if success_count > 0:
                    invalidate_tileset_cache(f"vector:{data.tileset_id}")
                
                return BulkFeatureResponse(
                    success_count=success_count,
                    failed_count=failed_count,
                    feature_ids=feature_ids,
                    errors=errors[:100],
                    warnings=validation_warnings[:50],
                    bounds_updated=bounds_updated,
                    bounds=bounds,
                    center=center,
                )
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in bulk feature creation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error creating features: {str(e)}"
        )


# ============================================================================
# List Features
# ============================================================================


@router.get("")
def list_features(
    tileset_id: str = Query(None, description="Filter by tileset ID"),
    layer: str = Query(None, description="Filter by layer name"),
    bbox: str = Query(None, description="Bounding box filter (minx,miny,maxx,maxy)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of features"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """
    List features with optional filters.
    
    Returns GeoJSON FeatureCollection.
    """
    try:
        with conn.cursor() as cur:
            # Build query
            conditions = []
            params = []
            
            if tileset_id:
                # Check access to tileset
                cur.execute(
                    "SELECT is_public, user_id FROM tilesets WHERE id = %s",
                    (tileset_id,),
                )
                row = cur.fetchone()
                
                if row:
                    is_public, owner_user_id = row
                    owner_user_id = str(owner_user_id) if owner_user_id else None
                    
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
                
                conditions.append("f.tileset_id = %s")
                params.append(tileset_id)
            else:
                # Only return features from public tilesets if no tileset_id specified
                conditions.append("t.is_public = true")
            
            if layer:
                conditions.append("f.layer_name = %s")
                params.append(layer)
            
            if bbox:
                try:
                    minx, miny, maxx, maxy = [float(x) for x in bbox.split(",")]
                    conditions.append(
                        "ST_Intersects(f.geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                    )
                    params.extend([minx, miny, maxx, maxy])
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid bbox format")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Get total count
            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE {where_clause}
                """,
                params,
            )
            total_count = cur.fetchone()[0]
            
            # Get features
            cur.execute(
                f"""
                SELECT f.id, f.layer_name, ST_AsGeoJSON(f.geom)::json as geometry,
                       f.properties, f.tileset_id, f.created_at, f.updated_at
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE {where_clause}
                ORDER BY f.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            rows = cur.fetchall()
            
            features = []
            for row in rows:
                features.append({
                    "id": str(row[0]),
                    "type": "Feature",
                    "geometry": row[2],
                    "properties": {
                        **(row[3] if row[3] else {}),
                        "layer_name": row[1],
                        "tileset_id": str(row[4]),
                        "created_at": row[5].isoformat() if row[5] else None,
                        "updated_at": row[6].isoformat() if row[6] else None,
                    },
                })
            
            return {
                "type": "FeatureCollection",
                "features": features,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing features: {str(e)}")


# ============================================================================
# Get Feature
# ============================================================================


@router.get("/{feature_id}")
def get_feature(
    feature_id: str,
    conn=Depends(get_connection),
    user: Optional[User] = Depends(get_current_user),
):
    """Get a specific feature by ID."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.id, f.layer_name, ST_AsGeoJSON(f.geom)::json as geometry,
                       f.properties, f.tileset_id, f.created_at, f.updated_at,
                       t.is_public, t.user_id
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE f.id = %s
                """,
                (feature_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            is_public = row[7]
            owner_user_id = str(row[8]) if row[8] else None
            
            # Check access
            if not check_tileset_access(str(row[4]), is_public, owner_user_id, user):
                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Authentication required to access this feature",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                raise HTTPException(
                    status_code=403,
                    detail="You do not have permission to access this feature"
                )
            
            return {
                "id": str(row[0]),
                "type": "Feature",
                "geometry": row[2],
                "properties": {
                    **(row[3] if row[3] else {}),
                    "layer_name": row[1],
                    "tileset_id": str(row[4]),
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feature: {str(e)}")


# ============================================================================
# Update Feature
# ============================================================================


@router.patch("/{feature_id}")
def update_feature(
    feature_id: str,
    feature: FeatureUpdate,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Update an existing feature.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if feature exists and user owns the parent tileset
            cur.execute(
                """
                SELECT f.id, t.user_id, f.tileset_id
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE f.id = %s
                """,
                (feature_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to update this feature")
            
            tileset_id = str(row[2])
            
            # Build update query dynamically
            updates = []
            params = []
            
            if feature.layer_name is not None:
                updates.append("layer_name = %s")
                params.append(feature.layer_name)
            
            if feature.geometry is not None:
                # Validate geometry
                geom_result = validate_geometry(feature.geometry, "geometry", check_coordinates=True)
                if not geom_result.valid:
                    raise HTTPException(status_code=400, detail=f"Invalid geometry: {geom_result.error}")
                
                updates.append("geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)")
                params.append(json.dumps(feature.geometry))
            
            if feature.properties is not None:
                updates.append("properties = %s")
                params.append(json.dumps(feature.properties))
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            updates.append("updated_at = NOW()")
            params.append(feature_id)
            
            cur.execute(
                f"""
                UPDATE features
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, layer_name, ST_AsGeoJSON(geom)::json as geometry, properties,
                          tileset_id, created_at, updated_at
                """,
                params,
            )
            
            row = cur.fetchone()
            conn.commit()
            
            # Invalidate cache
            invalidate_tileset_cache(f"vector:{tileset_id}")
            
            return {
                "id": str(row[0]),
                "type": "Feature",
                "geometry": row[2],
                "properties": {
                    **(row[3] if row[3] else {}),
                    "layer_name": row[1],
                    "tileset_id": str(row[4]),
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                },
            }
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating feature: {str(e)}")


# ============================================================================
# Delete Feature
# ============================================================================


@router.delete("/{feature_id}", status_code=204)
def delete_feature(
    feature_id: str,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete a feature.
    
    Requires authentication and ownership of the parent tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check if feature exists and user owns the parent tileset
            cur.execute(
                """
                SELECT f.id, t.user_id, f.tileset_id
                FROM features f
                JOIN tilesets t ON f.tileset_id = t.id
                WHERE f.id = %s
                """,
                (feature_id,),
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Feature not found")
            
            if str(row[1]) != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this feature")
            
            tileset_id = str(row[2])
            
            # Delete feature
            cur.execute("DELETE FROM features WHERE id = %s", (feature_id,))
            conn.commit()
            
            # Invalidate cache
            invalidate_tileset_cache(f"vector:{tileset_id}")
            
            return Response(status_code=204)
            
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting feature: {str(e)}")
