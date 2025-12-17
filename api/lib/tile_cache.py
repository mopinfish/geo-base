"""
Tile caching module for geo-base API.

This module provides a unified caching layer for tile data with support for:
- In-memory cache (fallback when Redis unavailable)
- Redis cache (preferred for production)
- Automatic fallback between backends

Cache Key Patterns:
- Vector tiles: "tile:vector:{tileset_id}:{z}:{x}:{y}:{layer}"
- Raster tiles: "tile:raster:{tileset_id}:{z}:{x}:{y}:{colormap}:{bands}"
- PMTiles tiles: "tile:pmtiles:{tileset_id}:{z}:{x}:{y}"
- TileJSON: "tilejson:{tileset_type}:{tileset_id}"
- Tileset info: "tileset:{tileset_id}"

TTL Settings (configurable via environment):
- TILE_CACHE_TTL: TTL for tile data (default: 3600 = 1 hour)
- TILEJSON_CACHE_TTL: TTL for TileJSON (default: 300 = 5 minutes)
- TILESET_INFO_CACHE_TTL: TTL for tileset info (default: 60 = 1 minute)

Usage:
    from lib.tile_cache import (
        get_cached_tile,
        cache_tile,
        get_cached_tilejson,
        cache_tilejson,
        invalidate_tileset,
    )

    # Cache a tile
    cache_tile(
        tileset_id="uuid",
        z=10, x=100, y=200,
        tile_type="vector",
        data=mvt_bytes,
    )

    # Get cached tile
    data = get_cached_tile(tileset_id="uuid", z=10, x=100, y=200, tile_type="vector")

    # Invalidate all cache for a tileset
    invalidate_tileset("uuid")
"""

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional, Union

import threading
import time
from dataclasses import dataclass as dc_dataclass
from typing import Generic, TypeVar, Dict

from lib.redis_client import (
    redis_available,
    redis_get_binary,
    redis_set_binary,
    redis_get_json,
    redis_set_json,
    safe_redis_delete_pattern,
    safe_redis_exists,
    get_redis_stats,
)

# Type variable for TTLCache
CacheT = TypeVar('CacheT')


@dc_dataclass
class CacheEntry(Generic[CacheT]):
    """A cache entry with value and expiration time."""
    value: CacheT
    expires_at: float


class TTLCache(Generic[CacheT]):
    """
    A simple thread-safe TTL (Time-To-Live) cache.
    
    This is a local copy to avoid import issues.
    For full implementation, see lib/cache.py
    """
    
    def __init__(self, ttl: float = 60.0, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry[CacheT]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = threading.RLock()
        self._access_order: list = []
    
    def get(self, key: str) -> Optional[CacheT]:
        """Get a value from the cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if time.time() > entry.expires_at:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return None
            
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
    def set(self, key: str, value: CacheT, ttl: Optional[float] = None) -> None:
        """Set a value in the cache."""
        with self._lock:
            while len(self._cache) >= self._max_size and self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
            
            entry_ttl = ttl if ttl is not None else self._ttl
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + entry_ttl
            )
            
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            now = time.time()
            expired_count = sum(
                1 for entry in self._cache.values()
                if now > entry.expires_at
            )
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl": self._ttl,
                "expired_pending": expired_count,
            }

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class TileCacheConfig:
    """Tile cache configuration."""
    
    # TTL settings (in seconds)
    tile_ttl: int = 3600  # 1 hour for tiles
    tilejson_ttl: int = 300  # 5 minutes for TileJSON
    tileset_info_ttl: int = 60  # 1 minute for tileset info
    
    # Memory cache settings (fallback)
    memory_cache_max_size: int = 1000  # Max entries in memory cache
    memory_cache_enabled: bool = True  # Enable memory cache as fallback
    
    # Feature flags
    cache_vector_tiles: bool = True
    cache_raster_tiles: bool = True
    cache_pmtiles: bool = True
    cache_tilejson: bool = True
    
    @classmethod
    def from_env(cls) -> "TileCacheConfig":
        """Load configuration from environment variables."""
        return cls(
            tile_ttl=int(os.environ.get("TILE_CACHE_TTL", "3600")),
            tilejson_ttl=int(os.environ.get("TILEJSON_CACHE_TTL", "300")),
            tileset_info_ttl=int(os.environ.get("TILESET_INFO_CACHE_TTL", "60")),
            memory_cache_max_size=int(os.environ.get("MEMORY_CACHE_MAX_SIZE", "1000")),
            memory_cache_enabled=os.environ.get(
                "MEMORY_CACHE_ENABLED", "true"
            ).lower() == "true",
            cache_vector_tiles=os.environ.get(
                "CACHE_VECTOR_TILES", "true"
            ).lower() == "true",
            cache_raster_tiles=os.environ.get(
                "CACHE_RASTER_TILES", "true"
            ).lower() == "true",
            cache_pmtiles=os.environ.get(
                "CACHE_PMTILES", "true"
            ).lower() == "true",
            cache_tilejson=os.environ.get(
                "CACHE_TILEJSON", "true"
            ).lower() == "true",
        )


# Global configuration
_config: Optional[TileCacheConfig] = None


def get_tile_cache_config() -> TileCacheConfig:
    """Get tile cache configuration."""
    global _config
    if _config is None:
        _config = TileCacheConfig.from_env()
    return _config


# =============================================================================
# Memory Cache (Fallback)
# =============================================================================

# In-memory fallback caches
_tile_memory_cache: Optional[TTLCache] = None
_tilejson_memory_cache: Optional[TTLCache] = None
_tileset_memory_cache: Optional[TTLCache] = None


def _get_memory_caches():
    """Initialize and return memory caches."""
    global _tile_memory_cache, _tilejson_memory_cache, _tileset_memory_cache
    
    config = get_tile_cache_config()
    
    if _tile_memory_cache is None:
        _tile_memory_cache = TTLCache(
            ttl=config.tile_ttl,
            max_size=config.memory_cache_max_size,
        )
    
    if _tilejson_memory_cache is None:
        _tilejson_memory_cache = TTLCache(
            ttl=config.tilejson_ttl,
            max_size=100,
        )
    
    if _tileset_memory_cache is None:
        _tileset_memory_cache = TTLCache(
            ttl=config.tileset_info_ttl,
            max_size=500,
        )
    
    return _tile_memory_cache, _tilejson_memory_cache, _tileset_memory_cache


# =============================================================================
# Cache Key Generation
# =============================================================================


def _make_tile_key(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    tile_type: str = "vector",
    layer: Optional[str] = None,
    colormap: Optional[str] = None,
    bands: Optional[str] = None,
) -> str:
    """
    Generate a cache key for a tile.
    
    Args:
        tileset_id: Tileset UUID
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        tile_type: Type of tile (vector, raster, pmtiles)
        layer: Optional layer name (for vector tiles)
        colormap: Optional colormap (for raster tiles)
        bands: Optional band selection (for raster tiles)
        
    Returns:
        Cache key string
    """
    key_parts = [f"tile:{tile_type}", tileset_id, str(z), str(x), str(y)]
    
    if layer:
        key_parts.append(f"layer:{layer}")
    
    if colormap:
        key_parts.append(f"cmap:{colormap}")
    
    if bands:
        key_parts.append(f"bands:{bands}")
    
    return ":".join(key_parts)


def _make_tilejson_key(tileset_id: str, tile_type: str = "vector") -> str:
    """Generate a cache key for TileJSON."""
    return f"tilejson:{tile_type}:{tileset_id}"


def _make_tileset_key(tileset_id: str) -> str:
    """Generate a cache key for tileset info."""
    return f"tileset:{tileset_id}"


# =============================================================================
# Tile Caching
# =============================================================================


def get_cached_tile(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    tile_type: str = "vector",
    layer: Optional[str] = None,
    colormap: Optional[str] = None,
    bands: Optional[str] = None,
) -> Optional[bytes]:
    """
    Get a cached tile.
    
    Tries Redis first, falls back to memory cache.
    
    Args:
        tileset_id: Tileset UUID
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        tile_type: Type of tile (vector, raster, pmtiles)
        layer: Optional layer name (for vector tiles)
        colormap: Optional colormap (for raster tiles)
        bands: Optional band selection (for raster tiles)
        
    Returns:
        Cached tile data or None if not found
    """
    config = get_tile_cache_config()
    
    # Check if caching is enabled for this tile type
    if tile_type == "vector" and not config.cache_vector_tiles:
        return None
    if tile_type == "raster" and not config.cache_raster_tiles:
        return None
    if tile_type == "pmtiles" and not config.cache_pmtiles:
        return None
    
    key = _make_tile_key(
        tileset_id, z, x, y, tile_type, layer, colormap, bands
    )
    
    # Try Redis first
    if redis_available():
        data = redis_get_binary(key)
        if data is not None:
            logger.debug(f"Redis cache hit: {key}")
            return data
    
    # Fall back to memory cache
    if config.memory_cache_enabled:
        tile_cache, _, _ = _get_memory_caches()
        data = tile_cache.get(key)
        if data is not None:
            logger.debug(f"Memory cache hit: {key}")
            return data
    
    logger.debug(f"Cache miss: {key}")
    return None


def cache_tile(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    data: bytes,
    tile_type: str = "vector",
    layer: Optional[str] = None,
    colormap: Optional[str] = None,
    bands: Optional[str] = None,
    ttl: Optional[int] = None,
) -> bool:
    """
    Cache a tile.
    
    Stores in both Redis and memory cache for optimal performance.
    
    Args:
        tileset_id: Tileset UUID
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        data: Tile data (binary)
        tile_type: Type of tile (vector, raster, pmtiles)
        layer: Optional layer name (for vector tiles)
        colormap: Optional colormap (for raster tiles)
        bands: Optional band selection (for raster tiles)
        ttl: Custom TTL in seconds (optional)
        
    Returns:
        True if cached successfully
    """
    config = get_tile_cache_config()
    
    # Check if caching is enabled for this tile type
    if tile_type == "vector" and not config.cache_vector_tiles:
        return False
    if tile_type == "raster" and not config.cache_raster_tiles:
        return False
    if tile_type == "pmtiles" and not config.cache_pmtiles:
        return False
    
    key = _make_tile_key(
        tileset_id, z, x, y, tile_type, layer, colormap, bands
    )
    cache_ttl = ttl or config.tile_ttl
    
    success = False
    
    # Store in Redis
    if redis_available():
        if redis_set_binary(key, data, ttl=cache_ttl):
            logger.debug(f"Cached in Redis: {key}")
            success = True
    
    # Also store in memory cache for fast access
    if config.memory_cache_enabled:
        tile_cache, _, _ = _get_memory_caches()
        tile_cache.set(key, data, ttl=cache_ttl)
        logger.debug(f"Cached in memory: {key}")
        success = True
    
    return success


# =============================================================================
# TileJSON Caching
# =============================================================================


def get_cached_tilejson(
    tileset_id: str,
    tile_type: str = "vector",
) -> Optional[dict]:
    """
    Get cached TileJSON.
    
    Args:
        tileset_id: Tileset UUID
        tile_type: Type of tileset
        
    Returns:
        Cached TileJSON dict or None
    """
    config = get_tile_cache_config()
    
    if not config.cache_tilejson:
        return None
    
    key = _make_tilejson_key(tileset_id, tile_type)
    
    # Try Redis first
    if redis_available():
        data = redis_get_json(key)
        if data is not None:
            logger.debug(f"Redis TileJSON cache hit: {key}")
            return data
    
    # Fall back to memory cache
    if config.memory_cache_enabled:
        _, tilejson_cache, _ = _get_memory_caches()
        data = tilejson_cache.get(key)
        if data is not None:
            logger.debug(f"Memory TileJSON cache hit: {key}")
            return data
    
    return None


def cache_tilejson(
    tileset_id: str,
    tilejson: dict,
    tile_type: str = "vector",
    ttl: Optional[int] = None,
) -> bool:
    """
    Cache TileJSON.
    
    Args:
        tileset_id: Tileset UUID
        tilejson: TileJSON dict
        tile_type: Type of tileset
        ttl: Custom TTL in seconds (optional)
        
    Returns:
        True if cached successfully
    """
    config = get_tile_cache_config()
    
    if not config.cache_tilejson:
        return False
    
    key = _make_tilejson_key(tileset_id, tile_type)
    cache_ttl = ttl or config.tilejson_ttl
    
    success = False
    
    # Store in Redis
    if redis_available():
        if redis_set_json(key, tilejson, ttl=cache_ttl):
            success = True
    
    # Also store in memory cache
    if config.memory_cache_enabled:
        _, tilejson_cache, _ = _get_memory_caches()
        tilejson_cache.set(key, tilejson, ttl=cache_ttl)
        success = True
    
    return success


# =============================================================================
# Tileset Info Caching
# =============================================================================


def get_cached_tileset_info(tileset_id: str) -> Optional[dict]:
    """
    Get cached tileset information.
    
    Args:
        tileset_id: Tileset UUID
        
    Returns:
        Cached tileset info dict or None
    """
    config = get_tile_cache_config()
    key = _make_tileset_key(tileset_id)
    
    # Try Redis first
    if redis_available():
        data = redis_get_json(key)
        if data is not None:
            return data
    
    # Fall back to memory cache
    if config.memory_cache_enabled:
        _, _, tileset_cache = _get_memory_caches()
        return tileset_cache.get(key)
    
    return None


def cache_tileset_info(
    tileset_id: str,
    info: dict,
    ttl: Optional[int] = None,
) -> bool:
    """
    Cache tileset information.
    
    Args:
        tileset_id: Tileset UUID
        info: Tileset info dict
        ttl: Custom TTL in seconds (optional)
        
    Returns:
        True if cached successfully
    """
    config = get_tile_cache_config()
    key = _make_tileset_key(tileset_id)
    cache_ttl = ttl or config.tileset_info_ttl
    
    success = False
    
    # Store in Redis
    if redis_available():
        if redis_set_json(key, info, ttl=cache_ttl):
            success = True
    
    # Also store in memory cache
    if config.memory_cache_enabled:
        _, _, tileset_cache = _get_memory_caches()
        tileset_cache.set(key, info, ttl=cache_ttl)
        success = True
    
    return success


# =============================================================================
# Cache Invalidation
# =============================================================================


def invalidate_tileset(tileset_id: str) -> int:
    """
    Invalidate all cache entries for a tileset.
    
    This removes:
    - All tile cache entries for this tileset
    - TileJSON cache entries
    - Tileset info cache
    
    Args:
        tileset_id: Tileset UUID
        
    Returns:
        Number of cache entries invalidated
    """
    count = 0
    config = get_tile_cache_config()
    
    # Patterns to invalidate
    patterns = [
        f"tile:*:{tileset_id}:*",  # All tiles
        f"tilejson:*:{tileset_id}",  # All TileJSON
        f"tileset:{tileset_id}",  # Tileset info
    ]
    
    # Invalidate in Redis
    if redis_available():
        for pattern in patterns:
            count += safe_redis_delete_pattern(pattern)
    
    # Invalidate in memory caches
    if config.memory_cache_enabled:
        tile_cache, tilejson_cache, tileset_cache = _get_memory_caches()
        
        # Clear tileset info
        if tileset_cache.delete(_make_tileset_key(tileset_id)):
            count += 1
        
        # Clear TileJSON (check all types)
        for tile_type in ["vector", "raster", "pmtiles"]:
            if tilejson_cache.delete(_make_tilejson_key(tileset_id, tile_type)):
                count += 1
        
        # Note: Memory cache doesn't support pattern-based deletion
        # for tiles, so we can't efficiently clear all tiles.
        # This is one reason why Redis is preferred.
    
    logger.info(f"Invalidated {count} cache entries for tileset {tileset_id}")
    return count


def invalidate_tile(
    tileset_id: str,
    z: int,
    x: int,
    y: int,
    tile_type: str = "vector",
    layer: Optional[str] = None,
) -> bool:
    """
    Invalidate a specific tile cache entry.
    
    Args:
        tileset_id: Tileset UUID
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        tile_type: Type of tile
        layer: Optional layer name
        
    Returns:
        True if entry was invalidated
    """
    key = _make_tile_key(tileset_id, z, x, y, tile_type, layer)
    config = get_tile_cache_config()
    
    invalidated = False
    
    # Remove from Redis
    if redis_available():
        from lib.redis_client import safe_redis_delete
        if safe_redis_delete(key):
            invalidated = True
    
    # Remove from memory cache
    if config.memory_cache_enabled:
        tile_cache, _, _ = _get_memory_caches()
        if tile_cache.delete(key):
            invalidated = True
    
    return invalidated


def clear_all_tile_caches() -> None:
    """Clear all tile caches (Redis and memory)."""
    config = get_tile_cache_config()
    
    # Clear Redis
    if redis_available():
        safe_redis_delete_pattern("tile:*")
        safe_redis_delete_pattern("tilejson:*")
        safe_redis_delete_pattern("tileset:*")
    
    # Clear memory caches
    if config.memory_cache_enabled:
        tile_cache, tilejson_cache, tileset_cache = _get_memory_caches()
        tile_cache.clear()
        tilejson_cache.clear()
        tileset_cache.clear()
    
    logger.info("Cleared all tile caches")


# =============================================================================
# Statistics
# =============================================================================


def get_tile_cache_stats() -> dict:
    """
    Get tile cache statistics.
    
    Returns:
        Dict with cache statistics from both Redis and memory caches
    """
    config = get_tile_cache_config()
    stats = {
        "config": {
            "tile_ttl": config.tile_ttl,
            "tilejson_ttl": config.tilejson_ttl,
            "tileset_info_ttl": config.tileset_info_ttl,
            "cache_vector_tiles": config.cache_vector_tiles,
            "cache_raster_tiles": config.cache_raster_tiles,
            "cache_pmtiles": config.cache_pmtiles,
            "cache_tilejson": config.cache_tilejson,
        },
        "redis": get_redis_stats(),
    }
    
    # Memory cache stats
    if config.memory_cache_enabled:
        tile_cache, tilejson_cache, tileset_cache = _get_memory_caches()
        stats["memory"] = {
            "tiles": tile_cache.stats(),
            "tilejson": tilejson_cache.stats(),
            "tileset_info": tileset_cache.stats(),
        }
    
    return stats


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Configuration
    "TileCacheConfig",
    "get_tile_cache_config",
    # Tile caching
    "get_cached_tile",
    "cache_tile",
    # TileJSON caching
    "get_cached_tilejson",
    "cache_tilejson",
    # Tileset info caching
    "get_cached_tileset_info",
    "cache_tileset_info",
    # Invalidation
    "invalidate_tileset",
    "invalidate_tile",
    "clear_all_tile_caches",
    # Statistics
    "get_tile_cache_stats",
]
