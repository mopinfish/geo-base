"""
Cache health check helpers for geo-base API.

This module provides helper functions to be used by the main API
for cache-related health checks and statistics.

Usage in main.py:
    from lib.cache_health import get_full_cache_stats, clear_all_caches_with_redis

    @app.get("/api/health/cache")
    def health_check_cache():
        return get_full_cache_stats()

    @app.post("/api/admin/cache/clear")
    def clear_cache():
        clear_all_caches_with_redis()
        return {"status": "ok"}
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_full_cache_stats() -> Dict[str, Any]:
    """
    Get comprehensive cache statistics including Redis and memory caches.
    
    Returns:
        Dict containing status and statistics from all cache layers
    """
    stats: Dict[str, Any] = {
        "status": "ok",
    }
    
    # Get Redis stats
    try:
        from lib.redis_client import check_redis_health, get_redis_stats
        
        redis_health = check_redis_health()
        stats["redis"] = {
            "health": redis_health,
            "stats": get_redis_stats() if redis_health.get("status") == "healthy" else None,
        }
    except ImportError:
        stats["redis"] = {"status": "not_installed"}
    except Exception as e:
        logger.warning(f"Error getting Redis stats: {e}")
        stats["redis"] = {"status": "error", "message": str(e)}
    
    # Get tile cache stats
    try:
        from lib.tile_cache import get_tile_cache_stats
        
        stats["tile_cache"] = get_tile_cache_stats()
    except ImportError:
        stats["tile_cache"] = {"status": "not_installed"}
    except Exception as e:
        logger.warning(f"Error getting tile cache stats: {e}")
        stats["tile_cache"] = {"status": "error", "message": str(e)}
    
    # Get legacy in-memory cache stats (from lib/cache.py)
    try:
        from lib.cache import get_cache_stats
        
        stats["memory_cache"] = get_cache_stats()
    except ImportError:
        pass  # OK if not available
    except Exception as e:
        logger.warning(f"Error getting memory cache stats: {e}")
        stats["memory_cache"] = {"status": "error", "message": str(e)}
    
    return stats


def clear_all_caches_with_redis() -> Dict[str, Any]:
    """
    Clear all caches including Redis and memory caches.
    
    Returns:
        Dict with status of each cache clear operation
    """
    results: Dict[str, Any] = {}
    
    # Clear tile cache (Redis + memory)
    try:
        from lib.tile_cache import clear_all_tile_caches
        
        clear_all_tile_caches()
        results["tile_cache"] = "cleared"
    except ImportError:
        results["tile_cache"] = "not_installed"
    except Exception as e:
        logger.warning(f"Error clearing tile cache: {e}")
        results["tile_cache"] = f"error: {e}"
    
    # Clear legacy in-memory cache
    try:
        from lib.cache import clear_all_caches
        
        clear_all_caches()
        results["memory_cache"] = "cleared"
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Error clearing memory cache: {e}")
        results["memory_cache"] = f"error: {e}"
    
    return {
        "status": "ok",
        "message": "All caches cleared",
        "details": results,
    }


def get_cache_health_summary() -> Dict[str, Any]:
    """
    Get a summary of cache health status.
    
    Returns:
        Dict with overall health status
    """
    try:
        from lib.redis_client import redis_available, check_redis_health
        
        redis_ok = redis_available()
        redis_health = check_redis_health()
        
        return {
            "status": "healthy" if redis_ok else "degraded",
            "redis_available": redis_ok,
            "redis_status": redis_health.get("status"),
            "fallback_enabled": True,  # Memory cache is always available
        }
    except ImportError:
        return {
            "status": "degraded",
            "redis_available": False,
            "redis_status": "not_installed",
            "fallback_enabled": True,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


__all__ = [
    "get_full_cache_stats",
    "clear_all_caches_with_redis",
    "get_cache_health_summary",
]
