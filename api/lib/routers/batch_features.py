"""
Batch operations endpoints for features.

Provides endpoints for:
- Bulk export (GeoJSON, CSV)
- Batch update
- Batch delete

These endpoints are separate from the main features router for clarity.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from lib.database import get_connection
from lib.auth import User, require_auth
from lib.cache import invalidate_tileset_cache
from lib.batch import (
    export_features_geojson,
    export_features_geojson_streaming,
    export_features_csv,
    batch_update_features,
    batch_update_by_filter,
    batch_delete_features,
    batch_delete_by_filter,
    BatchResult,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/features", tags=["features-batch"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ExportRequest(BaseModel):
    """Request model for export endpoint."""
    tileset_id: str = Field(..., description="Tileset UUID to export")
    layer_name: Optional[str] = Field(None, description="Filter by layer name")
    bbox: Optional[List[float]] = Field(
        None,
        description="Bounding box [minx, miny, maxx, maxy]",
        min_length=4,
        max_length=4,
    )
    properties_filter: Optional[Dict[str, Any]] = Field(
        None,
        description="Property key-value filters"
    )
    limit: Optional[int] = Field(None, ge=1, le=100000, description="Maximum features")
    format: str = Field("geojson", description="Export format: geojson or csv")
    include_metadata: bool = Field(True, description="Include export metadata")


class BatchUpdateRequest(BaseModel):
    """Request model for batch update."""
    feature_ids: Optional[List[str]] = Field(
        None,
        description="List of feature UUIDs to update (max 10000)",
        max_length=10000,
    )
    tileset_id: Optional[str] = Field(
        None,
        description="Tileset UUID for filter-based update"
    )
    filter: Optional[Dict[str, Any]] = Field(
        None,
        description="Filter conditions (layer_name, bbox, properties)"
    )
    updates: Dict[str, Any] = Field(
        ...,
        description="Fields to update (layer_name, properties, geometry)"
    )
    merge_properties: bool = Field(
        True,
        description="Merge properties instead of replacing"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=100000,
        description="Maximum features to update (filter mode only)"
    )


class BatchDeleteRequest(BaseModel):
    """Request model for batch delete."""
    feature_ids: Optional[List[str]] = Field(
        None,
        description="List of feature UUIDs to delete (max 10000)",
        max_length=10000,
    )
    tileset_id: Optional[str] = Field(
        None,
        description="Tileset UUID for filter-based delete"
    )
    filter: Optional[Dict[str, Any]] = Field(
        None,
        description="Filter conditions (layer_name, bbox, properties)"
    )
    limit: Optional[int] = Field(
        None,
        ge=1,
        le=100000,
        description="Maximum features to delete (filter mode only)"
    )
    dry_run: bool = Field(
        False,
        description="Preview delete without executing"
    )


class BatchOperationResponse(BaseModel):
    """Response model for batch operations."""
    success_count: int = Field(..., description="Number of successful operations")
    failed_count: int = Field(..., description="Number of failed operations")
    total_count: int = Field(..., description="Total items processed")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    status: str = Field(..., description="Operation status")
    duration_seconds: Optional[float] = Field(None, description="Operation duration")


# =============================================================================
# Helper Functions
# =============================================================================


def _check_tileset_ownership(cur, tileset_id: str, user_id: str) -> bool:
    """Check if user owns the tileset."""
    cur.execute(
        "SELECT user_id FROM tilesets WHERE id = %s",
        (tileset_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tileset not found")
    
    if str(row[0]) != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to modify this tileset"
        )
    
    return True


def _get_tileset_ids_for_features(cur, feature_ids: List[str]) -> set:
    """Get unique tileset IDs for given features."""
    cur.execute(
        "SELECT DISTINCT tileset_id FROM features WHERE id = ANY(%s)",
        (feature_ids,),
    )
    return {str(row[0]) for row in cur.fetchall()}


# =============================================================================
# Export Endpoints
# =============================================================================


@router.post("/export")
def export_features(
    request: ExportRequest,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Export features from a tileset.
    
    Supports GeoJSON and CSV formats.
    Requires authentication and ownership of the tileset.
    """
    try:
        with conn.cursor() as cur:
            # Check ownership
            _check_tileset_ownership(cur, request.tileset_id, user.id)
        
        # Parse bbox if provided
        bbox = None
        if request.bbox:
            bbox = tuple(request.bbox)
        
        if request.format.lower() == "csv":
            # Export as CSV
            csv_content = export_features_csv(
                conn,
                tileset_id=request.tileset_id,
                layer_name=request.layer_name,
                bbox=bbox,
            )
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={request.tileset_id}.csv"
                },
            )
        
        else:
            # Export as GeoJSON
            geojson = export_features_geojson(
                conn,
                tileset_id=request.tileset_id,
                layer_name=request.layer_name,
                bbox=bbox,
                properties_filter=request.properties_filter,
                limit=request.limit,
                include_metadata=request.include_metadata,
            )
            
            return geojson
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/{tileset_id}")
def export_features_get(
    tileset_id: str,
    format: str = Query("geojson", description="Export format"),
    layer: Optional[str] = Query(None, description="Filter by layer"),
    bbox: Optional[str] = Query(None, description="Bounding box (minx,miny,maxx,maxy)"),
    limit: Optional[int] = Query(None, ge=1, le=100000, description="Maximum features"),
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Export features from a tileset (GET method).
    
    Alternative to POST for simple exports.
    """
    try:
        with conn.cursor() as cur:
            _check_tileset_ownership(cur, tileset_id, user.id)
        
        # Parse bbox
        bbox_tuple = None
        if bbox:
            try:
                bbox_tuple = tuple(float(x) for x in bbox.split(","))
                if len(bbox_tuple) != 4:
                    raise ValueError("bbox must have 4 values")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid bbox: {e}")
        
        if format.lower() == "csv":
            csv_content = export_features_csv(
                conn,
                tileset_id=tileset_id,
                layer_name=layer,
                bbox=bbox_tuple,
            )
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={tileset_id}.csv"
                },
            )
        
        else:
            geojson = export_features_geojson(
                conn,
                tileset_id=tileset_id,
                layer_name=layer,
                bbox=bbox_tuple,
                limit=limit,
            )
            
            return geojson
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/{tileset_id}/stream")
def export_features_streaming(
    tileset_id: str,
    layer: Optional[str] = Query(None, description="Filter by layer"),
    bbox: Optional[str] = Query(None, description="Bounding box (minx,miny,maxx,maxy)"),
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Export features as streaming GeoJSON.
    
    Use this for large exports to avoid memory issues.
    Returns a streaming response with chunked transfer encoding.
    """
    try:
        with conn.cursor() as cur:
            _check_tileset_ownership(cur, tileset_id, user.id)
        
        # Parse bbox
        bbox_tuple = None
        if bbox:
            try:
                bbox_tuple = tuple(float(x) for x in bbox.split(","))
                if len(bbox_tuple) != 4:
                    raise ValueError("bbox must have 4 values")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid bbox: {e}")
        
        def generate():
            for chunk in export_features_geojson_streaming(
                conn,
                tileset_id=tileset_id,
                layer_name=layer,
                bbox=bbox_tuple,
            ):
                yield chunk
        
        return StreamingResponse(
            generate(),
            media_type="application/geo+json",
            headers={
                "Content-Disposition": f"attachment; filename={tileset_id}.geojson"
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming export error: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# =============================================================================
# Batch Update Endpoints
# =============================================================================


@router.post("/bulk/update", response_model=BatchOperationResponse)
def batch_update(
    request: BatchUpdateRequest,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Update multiple features at once.
    
    Two modes:
    1. By feature IDs: Provide feature_ids list
    2. By filter: Provide tileset_id and filter conditions
    
    Requires authentication and ownership of affected tilesets.
    """
    try:
        with conn.cursor() as cur:
            result: BatchResult
            affected_tilesets = set()
            
            if request.feature_ids:
                # Mode 1: Update by feature IDs
                
                # Check ownership of all affected tilesets
                tileset_ids = _get_tileset_ids_for_features(cur, request.feature_ids)
                
                for tid in tileset_ids:
                    _check_tileset_ownership(cur, tid, user.id)
                
                affected_tilesets = tileset_ids
                
                result = batch_update_features(
                    conn,
                    feature_ids=request.feature_ids,
                    updates=request.updates,
                    merge_properties=request.merge_properties,
                )
                
            elif request.tileset_id:
                # Mode 2: Update by filter
                _check_tileset_ownership(cur, request.tileset_id, user.id)
                
                affected_tilesets.add(request.tileset_id)
                
                result = batch_update_by_filter(
                    conn,
                    tileset_id=request.tileset_id,
                    filter_conditions=request.filter or {},
                    updates=request.updates,
                    merge_properties=request.merge_properties,
                    limit=request.limit,
                )
                
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either feature_ids or tileset_id must be provided"
                )
            
            # Invalidate cache for affected tilesets
            for tid in affected_tilesets:
                invalidate_tileset_cache(f"vector:{tid}")
            
            return BatchOperationResponse(
                success_count=result.success_count,
                failed_count=result.failed_count,
                total_count=result.total_count,
                errors=result.errors,
                warnings=result.warnings,
                status=result.status.value,
                duration_seconds=result.duration_seconds,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch update error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


# =============================================================================
# Batch Delete Endpoints
# =============================================================================


@router.post("/bulk/delete", response_model=BatchOperationResponse)
def batch_delete(
    request: BatchDeleteRequest,
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete multiple features at once.
    
    Two modes:
    1. By feature IDs: Provide feature_ids list
    2. By filter: Provide tileset_id and filter conditions
    
    Use dry_run=true to preview without deleting.
    Requires authentication and ownership of affected tilesets.
    """
    try:
        with conn.cursor() as cur:
            result: BatchResult
            affected_tilesets = set()
            
            if request.feature_ids:
                # Mode 1: Delete by feature IDs
                
                # Check ownership of all affected tilesets
                tileset_ids = _get_tileset_ids_for_features(cur, request.feature_ids)
                
                for tid in tileset_ids:
                    _check_tileset_ownership(cur, tid, user.id)
                
                affected_tilesets = tileset_ids
                
                if request.dry_run:
                    # Dry run - just count
                    result = BatchResult(
                        total_count=len(request.feature_ids),
                        success_count=0,
                        failed_count=0,
                    )
                    result.warnings.append(
                        f"Dry run: would delete {len(request.feature_ids)} features"
                    )
                else:
                    result = batch_delete_features(
                        conn,
                        feature_ids=request.feature_ids,
                    )
                
            elif request.tileset_id:
                # Mode 2: Delete by filter
                _check_tileset_ownership(cur, request.tileset_id, user.id)
                
                affected_tilesets.add(request.tileset_id)
                
                result = batch_delete_by_filter(
                    conn,
                    tileset_id=request.tileset_id,
                    filter_conditions=request.filter or {},
                    limit=request.limit,
                    dry_run=request.dry_run,
                )
                
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Either feature_ids or tileset_id must be provided"
                )
            
            # Invalidate cache for affected tilesets (only if not dry run)
            if not request.dry_run:
                for tid in affected_tilesets:
                    invalidate_tileset_cache(f"vector:{tid}")
            
            return BatchOperationResponse(
                success_count=result.success_count,
                failed_count=result.failed_count,
                total_count=result.total_count,
                errors=result.errors,
                warnings=result.warnings,
                status=result.status.value,
                duration_seconds=result.duration_seconds,
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch delete error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/bulk")
def batch_delete_simple(
    feature_ids: List[str] = Query(..., description="Feature UUIDs to delete"),
    user: User = Depends(require_auth),
    conn=Depends(get_connection),
):
    """
    Delete multiple features (simple DELETE method).
    
    Alternative to POST for simple batch deletes.
    """
    if len(feature_ids) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10000 features per request"
        )
    
    try:
        with conn.cursor() as cur:
            # Check ownership
            tileset_ids = _get_tileset_ids_for_features(cur, feature_ids)
            
            for tid in tileset_ids:
                _check_tileset_ownership(cur, tid, user.id)
            
            result = batch_delete_features(conn, feature_ids)
            
            # Invalidate cache
            for tid in tileset_ids:
                invalidate_tileset_cache(f"vector:{tid}")
            
            return {
                "success_count": result.success_count,
                "failed_count": result.failed_count,
                "errors": result.errors,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch delete error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")
