"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends

from lib.auth import User, is_auth_configured, require_auth
from lib.cache import clear_all_caches, get_cache_stats
from lib.config import get_settings
from lib.database import check_database_connection, check_postgis_extension
from lib.pmtiles import is_pmtiles_available
from lib.raster_tiles import is_rasterio_available
from lib.redis_client import check_redis_health

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


@router.get("/api/health/redis")
def health_check_redis():
    """Redis connection health endpoint (Issue #119).

    `redis_client.check_redis_health()` を expose して、本番 Redis の稼働状況を
    外部から確認できるようにする。`/api/health/cache` は in-memory cache のみを
    返すため、Redis 自体の到達性は本エンドポイントで確認する。

    Returns one of:
    - status=healthy: Redis 接続成功 + INFO 取得済み
    - status=unavailable: REDIS_ENABLED=true だが接続失敗
    - status=disabled: REDIS_ENABLED=false で意図的に無効化されている
    - status=error: 接続後の INFO 取得で例外発生
    """
    return check_redis_health()


@router.post("/api/admin/cache/clear")
def clear_cache(user: User = Depends(require_auth)):
    """
    Clear all caches.

    Requires authentication. In production, this should be restricted to admins.
    """
    clear_all_caches()
    return {"status": "ok", "message": "All caches cleared"}
