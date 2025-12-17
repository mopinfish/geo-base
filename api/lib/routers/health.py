"""
Health check and authentication endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends

from lib.config import get_settings
from lib.database import check_database_connection, check_postgis_extension
from lib.raster_tiles import is_rasterio_available
from lib.pmtiles import is_pmtiles_available
from lib.cache import get_cache_stats, clear_all_caches
from lib.auth import User, get_current_user, require_auth, is_auth_configured


router = APIRouter(tags=["health"])
settings = get_settings()


# ============================================================================
# Health Check Endpoints
# ============================================================================


@router.get("/api/health")
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "version": "0.4.0",
        "environment": settings.environment,
        "rasterio_available": is_rasterio_available(),
        "pmtiles_available": is_pmtiles_available(),
        "auth_configured": is_auth_configured(),
    }


@router.get("/api/health/db")
def health_check_db():
    """Database health check endpoint with detailed error info."""
    db_result = check_database_connection()
    db_connected = db_result.get("connected", False)
    
    postgis_result = check_postgis_extension() if db_connected else {"available": False}
    postgis_available = postgis_result.get("available", False)

    status = "ok" if db_connected and postgis_available else "error"

    response = {
        "status": status,
        "database": "connected" if db_connected else "disconnected",
        "postgis": "available" if postgis_available else "unavailable",
        "environment": settings.environment,
    }
    
    # Add error details if present
    if not db_connected and db_result.get("error"):
        response["db_error"] = db_result["error"]
    
    if db_connected and postgis_result.get("version"):
        response["postgis_version"] = postgis_result["version"]
    elif not postgis_available and postgis_result.get("error"):
        response["postgis_error"] = postgis_result["error"]
    
    return response


@router.get("/api/health/cache")
def health_check_cache():
    """Cache statistics endpoint."""
    return {
        "status": "ok",
        "cache": get_cache_stats(),
    }


@router.post("/api/admin/cache/clear")
def clear_cache(user: User = Depends(require_auth)):
    """
    Clear all caches.
    
    Requires authentication. In production, this should be restricted to admins.
    """
    clear_all_caches()
    return {"status": "ok", "message": "All caches cleared"}


# ============================================================================
# Auth Test Endpoints
# ============================================================================


@router.get("/api/auth/me")
def get_current_user_info(user: User = Depends(require_auth)):
    """
    Get current authenticated user information.
    
    Requires authentication.
    """
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
    }


@router.get("/api/auth/status")
def get_auth_status(user: Optional[User] = Depends(get_current_user)):
    """
    Get authentication status.
    
    Returns authentication status without requiring authentication.
    """
    return {
        "authenticated": user is not None,
        "user_id": user.id if user else None,
        "email": user.email if user else None,
    }
