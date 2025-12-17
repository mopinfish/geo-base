"""
Batch operations module for geo-base API.

This module provides batch processing utilities for:
- Bulk export (GeoJSON/CSV)
- Batch update
- Batch delete
- Progress tracking

Usage:
    from lib.batch import (
        export_features_geojson,
        batch_update_features,
        batch_delete_features,
    )
"""

import json
import logging
import io
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Batch Operation Status
# =============================================================================


class BatchStatus(str, Enum):
    """Status of a batch operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchResult:
    """Result of a batch operation."""
    success_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: BatchStatus = BatchStatus.COMPLETED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate operation duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "total_count": self.total_count,
            "errors": self.errors[:100],  # Limit errors in response
            "warnings": self.warnings[:50],
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


# =============================================================================
# Export Functions
# =============================================================================


def export_features_geojson(
    conn,
    tileset_id: str,
    layer_name: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    properties_filter: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
    include_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Export features as GeoJSON FeatureCollection.
    
    Args:
        conn: Database connection
        tileset_id: Tileset UUID to export
        layer_name: Filter by layer name (optional)
        bbox: Bounding box filter (minx, miny, maxx, maxy) (optional)
        properties_filter: Filter by properties (key=value) (optional)
        limit: Maximum number of features (optional)
        include_metadata: Include export metadata (default: True)
        
    Returns:
        GeoJSON FeatureCollection dict
    """
    try:
        with conn.cursor() as cur:
            # Build query
            conditions = ["f.tileset_id = %s"]
            params: List[Any] = [tileset_id]
            
            if layer_name:
                conditions.append("f.layer_name = %s")
                params.append(layer_name)
            
            if bbox:
                minx, miny, maxx, maxy = bbox
                conditions.append(
                    "ST_Intersects(f.geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                )
                params.extend([minx, miny, maxx, maxy])
            
            if properties_filter:
                for key, value in properties_filter.items():
                    # Use JSONB containment operator
                    conditions.append("f.properties @> %s::jsonb")
                    params.append(json.dumps({key: value}))
            
            where_clause = " AND ".join(conditions)
            
            # Get total count
            cur.execute(
                f"SELECT COUNT(*) FROM features f WHERE {where_clause}",
                params,
            )
            total_count = cur.fetchone()[0]
            
            # Build main query
            query = f"""
                SELECT 
                    f.id,
                    f.layer_name,
                    ST_AsGeoJSON(f.geom)::json as geometry,
                    f.properties,
                    f.created_at,
                    f.updated_at
                FROM features f
                WHERE {where_clause}
                ORDER BY f.created_at
            """
            
            if limit:
                query += f" LIMIT {int(limit)}"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Build features
            features = []
            for row in rows:
                feature_id, layer, geometry, properties, created_at, updated_at = row
                
                feature_props = properties.copy() if properties else {}
                feature_props["_layer"] = layer
                
                if include_metadata:
                    feature_props["_id"] = str(feature_id)
                    feature_props["_created_at"] = created_at.isoformat() if created_at else None
                    feature_props["_updated_at"] = updated_at.isoformat() if updated_at else None
                
                features.append({
                    "type": "Feature",
                    "id": str(feature_id),
                    "geometry": geometry,
                    "properties": feature_props,
                })
            
            result = {
                "type": "FeatureCollection",
                "features": features,
            }
            
            if include_metadata:
                result["metadata"] = {
                    "tileset_id": tileset_id,
                    "total_count": total_count,
                    "exported_count": len(features),
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "filters": {
                        "layer_name": layer_name,
                        "bbox": list(bbox) if bbox else None,
                        "properties_filter": properties_filter,
                        "limit": limit,
                    },
                }
            
            return result
            
    except Exception as e:
        logger.error(f"Error exporting features: {e}")
        raise


def export_features_geojson_streaming(
    conn,
    tileset_id: str,
    layer_name: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    batch_size: int = 1000,
) -> Generator[str, None, None]:
    """
    Export features as streaming GeoJSON.
    
    Yields JSON strings that can be concatenated to form a valid GeoJSON.
    Useful for large exports to avoid memory issues.
    
    Args:
        conn: Database connection
        tileset_id: Tileset UUID to export
        layer_name: Filter by layer name (optional)
        bbox: Bounding box filter (optional)
        batch_size: Number of features per batch
        
    Yields:
        JSON string chunks
    """
    try:
        with conn.cursor(name="export_cursor") as cur:
            # Build query
            conditions = ["f.tileset_id = %s"]
            params: List[Any] = [tileset_id]
            
            if layer_name:
                conditions.append("f.layer_name = %s")
                params.append(layer_name)
            
            if bbox:
                minx, miny, maxx, maxy = bbox
                conditions.append(
                    "ST_Intersects(f.geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                )
                params.extend([minx, miny, maxx, maxy])
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT 
                    f.id,
                    f.layer_name,
                    ST_AsGeoJSON(f.geom) as geometry,
                    f.properties
                FROM features f
                WHERE {where_clause}
                ORDER BY f.id
            """
            
            cur.execute(query, params)
            
            # Yield opening
            yield '{"type":"FeatureCollection","features":['
            
            first = True
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                
                for row in rows:
                    feature_id, layer, geometry_str, properties = row
                    
                    feature_props = properties.copy() if properties else {}
                    feature_props["_layer"] = layer
                    
                    feature = {
                        "type": "Feature",
                        "id": str(feature_id),
                        "geometry": json.loads(geometry_str),
                        "properties": feature_props,
                    }
                    
                    if first:
                        first = False
                        yield json.dumps(feature)
                    else:
                        yield "," + json.dumps(feature)
            
            # Yield closing
            yield "]}"
            
    except Exception as e:
        logger.error(f"Error in streaming export: {e}")
        raise


def export_features_csv(
    conn,
    tileset_id: str,
    layer_name: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    properties_columns: Optional[List[str]] = None,
    include_wkt: bool = True,
) -> str:
    """
    Export features as CSV.
    
    Args:
        conn: Database connection
        tileset_id: Tileset UUID to export
        layer_name: Filter by layer name (optional)
        bbox: Bounding box filter (optional)
        properties_columns: Specific property columns to include (optional)
        include_wkt: Include WKT geometry column (default: True)
        
    Returns:
        CSV string
    """
    try:
        with conn.cursor() as cur:
            # Build query
            conditions = ["f.tileset_id = %s"]
            params: List[Any] = [tileset_id]
            
            if layer_name:
                conditions.append("f.layer_name = %s")
                params.append(layer_name)
            
            if bbox:
                minx, miny, maxx, maxy = bbox
                conditions.append(
                    "ST_Intersects(f.geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                )
                params.extend([minx, miny, maxx, maxy])
            
            where_clause = " AND ".join(conditions)
            
            # Determine columns
            geom_col = "ST_AsText(f.geom) as wkt" if include_wkt else "NULL as wkt"
            
            query = f"""
                SELECT 
                    f.id,
                    f.layer_name,
                    ST_X(ST_Centroid(f.geom)) as longitude,
                    ST_Y(ST_Centroid(f.geom)) as latitude,
                    {geom_col},
                    f.properties
                FROM features f
                WHERE {where_clause}
                ORDER BY f.id
            """
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Determine property columns
            if properties_columns:
                prop_cols = properties_columns
            else:
                # Auto-detect from first 100 rows
                prop_cols = set()
                for row in rows[:100]:
                    if row[5]:
                        prop_cols.update(row[5].keys())
                prop_cols = sorted(prop_cols)
            
            # Build CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            header = ["id", "layer_name", "longitude", "latitude"]
            if include_wkt:
                header.append("wkt")
            header.extend(prop_cols)
            writer.writerow(header)
            
            # Data rows
            for row in rows:
                feature_id, layer, lon, lat, wkt, properties = row
                
                csv_row = [str(feature_id), layer, lon, lat]
                if include_wkt:
                    csv_row.append(wkt)
                
                # Add property values
                props = properties or {}
                for col in prop_cols:
                    value = props.get(col, "")
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    csv_row.append(value)
                
                writer.writerow(csv_row)
            
            return output.getvalue()
            
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise


# =============================================================================
# Batch Update Functions
# =============================================================================


def batch_update_features(
    conn,
    feature_ids: List[str],
    updates: Dict[str, Any],
    merge_properties: bool = True,
) -> BatchResult:
    """
    Update multiple features at once.
    
    Args:
        conn: Database connection
        feature_ids: List of feature UUIDs to update
        updates: Dictionary of fields to update
            - layer_name: New layer name
            - properties: Properties to set/merge
            - geometry: New GeoJSON geometry
        merge_properties: If True, merge properties; if False, replace
        
    Returns:
        BatchResult with operation details
    """
    result = BatchResult(
        total_count=len(feature_ids),
        started_at=datetime.now(timezone.utc),
    )
    
    if not feature_ids:
        result.status = BatchStatus.COMPLETED
        result.completed_at = datetime.now(timezone.utc)
        return result
    
    try:
        with conn.cursor() as cur:
            for feature_id in feature_ids:
                try:
                    # Build SET clause dynamically
                    set_parts = ["updated_at = NOW()"]
                    params = []
                    
                    if "layer_name" in updates:
                        set_parts.append("layer_name = %s")
                        params.append(updates["layer_name"])
                    
                    if "properties" in updates:
                        if merge_properties:
                            # Merge with existing properties
                            set_parts.append("properties = properties || %s::jsonb")
                        else:
                            # Replace properties
                            set_parts.append("properties = %s::jsonb")
                        params.append(json.dumps(updates["properties"]))
                    
                    if "geometry" in updates:
                        set_parts.append("geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)")
                        params.append(json.dumps(updates["geometry"]))
                    
                    if len(set_parts) == 1:
                        # Only updated_at, nothing to update
                        result.warnings.append(f"Feature {feature_id}: No updates provided")
                        continue
                    
                    # Execute update
                    params.append(feature_id)
                    cur.execute(
                        f"""
                        UPDATE features
                        SET {', '.join(set_parts)}
                        WHERE id = %s
                        RETURNING id
                        """,
                        params,
                    )
                    
                    if cur.fetchone():
                        result.success_count += 1
                    else:
                        result.failed_count += 1
                        result.errors.append(f"Feature {feature_id}: Not found")
                        
                except Exception as e:
                    result.failed_count += 1
                    result.errors.append(f"Feature {feature_id}: {str(e)}")
                    conn.rollback()
            
            conn.commit()
            
    except Exception as e:
        result.status = BatchStatus.FAILED
        result.errors.append(f"Batch update failed: {str(e)}")
        conn.rollback()
    
    result.completed_at = datetime.now(timezone.utc)
    return result


def batch_update_by_filter(
    conn,
    tileset_id: str,
    filter_conditions: Dict[str, Any],
    updates: Dict[str, Any],
    merge_properties: bool = True,
    limit: Optional[int] = None,
) -> BatchResult:
    """
    Update features matching filter conditions.
    
    Args:
        conn: Database connection
        tileset_id: Tileset UUID
        filter_conditions: Conditions to match
            - layer_name: Filter by layer
            - bbox: Bounding box (minx, miny, maxx, maxy)
            - properties: Property key-value filters
        updates: Fields to update (same as batch_update_features)
        merge_properties: If True, merge properties; if False, replace
        limit: Maximum number of features to update
        
    Returns:
        BatchResult with operation details
    """
    result = BatchResult(started_at=datetime.now(timezone.utc))
    
    try:
        with conn.cursor() as cur:
            # Build WHERE clause
            conditions = ["tileset_id = %s"]
            params: List[Any] = [tileset_id]
            
            if "layer_name" in filter_conditions:
                conditions.append("layer_name = %s")
                params.append(filter_conditions["layer_name"])
            
            if "bbox" in filter_conditions:
                bbox = filter_conditions["bbox"]
                conditions.append(
                    "ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                )
                params.extend(bbox)
            
            if "properties" in filter_conditions:
                for key, value in filter_conditions["properties"].items():
                    conditions.append("properties @> %s::jsonb")
                    params.append(json.dumps({key: value}))
            
            where_clause = " AND ".join(conditions)
            
            # Count matching features
            cur.execute(f"SELECT COUNT(*) FROM features WHERE {where_clause}", params)
            result.total_count = cur.fetchone()[0]
            
            if result.total_count == 0:
                result.warnings.append("No features matched the filter")
                result.completed_at = datetime.now(timezone.utc)
                return result
            
            # Build SET clause
            set_parts = ["updated_at = NOW()"]
            update_params = []
            
            if "layer_name" in updates:
                set_parts.append("layer_name = %s")
                update_params.append(updates["layer_name"])
            
            if "properties" in updates:
                if merge_properties:
                    set_parts.append("properties = properties || %s::jsonb")
                else:
                    set_parts.append("properties = %s::jsonb")
                update_params.append(json.dumps(updates["properties"]))
            
            if "geometry" in updates:
                set_parts.append("geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)")
                update_params.append(json.dumps(updates["geometry"]))
            
            # Execute update
            update_query = f"""
                UPDATE features
                SET {', '.join(set_parts)}
                WHERE {where_clause}
            """
            
            if limit:
                # Use subquery for limited update
                update_query = f"""
                    UPDATE features
                    SET {', '.join(set_parts)}
                    WHERE id IN (
                        SELECT id FROM features
                        WHERE {where_clause}
                        LIMIT {int(limit)}
                    )
                """
            
            cur.execute(update_query, update_params + params)
            result.success_count = cur.rowcount
            result.failed_count = result.total_count - result.success_count
            
            conn.commit()
            
    except Exception as e:
        result.status = BatchStatus.FAILED
        result.errors.append(f"Batch update failed: {str(e)}")
        conn.rollback()
    
    result.completed_at = datetime.now(timezone.utc)
    return result


# =============================================================================
# Batch Delete Functions
# =============================================================================


def batch_delete_features(
    conn,
    feature_ids: List[str],
) -> BatchResult:
    """
    Delete multiple features at once.
    
    Args:
        conn: Database connection
        feature_ids: List of feature UUIDs to delete
        
    Returns:
        BatchResult with operation details
    """
    result = BatchResult(
        total_count=len(feature_ids),
        started_at=datetime.now(timezone.utc),
    )
    
    if not feature_ids:
        result.status = BatchStatus.COMPLETED
        result.completed_at = datetime.now(timezone.utc)
        return result
    
    try:
        with conn.cursor() as cur:
            # Use ANY for efficient batch delete
            cur.execute(
                "DELETE FROM features WHERE id = ANY(%s) RETURNING id",
                (feature_ids,),
            )
            
            deleted_ids = [str(row[0]) for row in cur.fetchall()]
            result.success_count = len(deleted_ids)
            result.failed_count = len(feature_ids) - result.success_count
            
            # Identify not found features
            not_found = set(feature_ids) - set(deleted_ids)
            for feature_id in not_found:
                result.errors.append(f"Feature {feature_id}: Not found")
            
            conn.commit()
            
    except Exception as e:
        result.status = BatchStatus.FAILED
        result.errors.append(f"Batch delete failed: {str(e)}")
        conn.rollback()
    
    result.completed_at = datetime.now(timezone.utc)
    return result


def batch_delete_by_filter(
    conn,
    tileset_id: str,
    filter_conditions: Dict[str, Any],
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> BatchResult:
    """
    Delete features matching filter conditions.
    
    Args:
        conn: Database connection
        tileset_id: Tileset UUID
        filter_conditions: Conditions to match
            - layer_name: Filter by layer
            - bbox: Bounding box (minx, miny, maxx, maxy)
            - properties: Property key-value filters
        limit: Maximum number of features to delete
        dry_run: If True, only count without deleting
        
    Returns:
        BatchResult with operation details
    """
    result = BatchResult(started_at=datetime.now(timezone.utc))
    
    try:
        with conn.cursor() as cur:
            # Build WHERE clause
            conditions = ["tileset_id = %s"]
            params: List[Any] = [tileset_id]
            
            if "layer_name" in filter_conditions:
                conditions.append("layer_name = %s")
                params.append(filter_conditions["layer_name"])
            
            if "bbox" in filter_conditions:
                bbox = filter_conditions["bbox"]
                conditions.append(
                    "ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
                )
                params.extend(bbox)
            
            if "properties" in filter_conditions:
                for key, value in filter_conditions["properties"].items():
                    conditions.append("properties @> %s::jsonb")
                    params.append(json.dumps({key: value}))
            
            where_clause = " AND ".join(conditions)
            
            # Count matching features
            cur.execute(f"SELECT COUNT(*) FROM features WHERE {where_clause}", params)
            result.total_count = cur.fetchone()[0]
            
            if result.total_count == 0:
                result.warnings.append("No features matched the filter")
                result.completed_at = datetime.now(timezone.utc)
                return result
            
            if dry_run:
                result.warnings.append(f"Dry run: would delete {result.total_count} features")
                result.completed_at = datetime.now(timezone.utc)
                return result
            
            # Execute delete
            if limit:
                delete_query = f"""
                    DELETE FROM features
                    WHERE id IN (
                        SELECT id FROM features
                        WHERE {where_clause}
                        LIMIT {int(limit)}
                    )
                """
            else:
                delete_query = f"DELETE FROM features WHERE {where_clause}"
            
            cur.execute(delete_query, params)
            result.success_count = cur.rowcount
            result.failed_count = 0
            
            conn.commit()
            
            logger.info(f"Deleted {result.success_count} features from tileset {tileset_id}")
            
    except Exception as e:
        result.status = BatchStatus.FAILED
        result.errors.append(f"Batch delete failed: {str(e)}")
        conn.rollback()
    
    result.completed_at = datetime.now(timezone.utc)
    return result


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Types
    "BatchStatus",
    "BatchResult",
    # Export
    "export_features_geojson",
    "export_features_geojson_streaming",
    "export_features_csv",
    # Update
    "batch_update_features",
    "batch_update_by_filter",
    # Delete
    "batch_delete_features",
    "batch_delete_by_filter",
]
