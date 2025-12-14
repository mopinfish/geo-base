"""
Simple in-memory TTL cache for geo-base API.

This module provides a thread-safe, TTL-based cache to reduce database
access for frequently requested data like tileset information.
"""

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, TypeVar, Generic

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """A cache entry with value and expiration time."""
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """
    A simple thread-safe TTL (Time-To-Live) cache.
    
    Features:
    - Automatic expiration of entries
    - Thread-safe operations
    - Optional size limit with LRU eviction
    - Lazy cleanup of expired entries
    
    Usage:
        cache = TTLCache[dict](ttl=60, max_size=1000)
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")  # Returns cached value or None
    """
    
    def __init__(self, ttl: float = 60.0, max_size: int = 1000):
        """
        Initialize the cache.
        
        Args:
            ttl: Time-to-live in seconds for cache entries (default: 60)
            max_size: Maximum number of entries (default: 1000)
        """
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._lock = threading.RLock()
        self._access_order: list[str] = []  # For LRU eviction
    
    def get(self, key: str) -> Optional[T]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            # Check if expired
            if time.time() > entry.expires_at:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return None
            
            # Update access order for LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
    def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL for this entry (defaults to cache TTL)
        """
        with self._lock:
            # Evict if at max size
            while len(self._cache) >= self._max_size and self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
            
            entry_ttl = ttl if ttl is not None else self._ttl
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + entry_ttl
            )
            
            # Update access order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if the key was found and deleted, False otherwise
        """
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
    
    def cleanup(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            return len(expired_keys)
    
    def size(self) -> int:
        """Return the current number of entries in the cache."""
        with self._lock:
            return len(self._cache)
    
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


# =============================================================================
# Global cache instances for different data types
# =============================================================================

# Cache for tileset information (COG URL, access permissions, etc.)
# TTL: 60 seconds - tileset info doesn't change frequently
tileset_cache: TTLCache[dict] = TTLCache(ttl=60.0, max_size=500)

# Cache for PMTiles metadata
# TTL: 300 seconds (5 minutes) - PMTiles metadata is static
pmtiles_metadata_cache: TTLCache[dict] = TTLCache(ttl=300.0, max_size=100)


def get_cached_tileset_info(tileset_id: str) -> Optional[dict]:
    """
    Get cached tileset information.
    
    Args:
        tileset_id: Tileset ID
        
    Returns:
        Cached tileset info dict or None
    """
    return tileset_cache.get(tileset_id)


def cache_tileset_info(tileset_id: str, info: dict) -> None:
    """
    Cache tileset information.
    
    Args:
        tileset_id: Tileset ID
        info: Tileset info dict to cache
    """
    tileset_cache.set(tileset_id, info)


def invalidate_tileset_cache(tileset_id: str) -> None:
    """
    Invalidate cached tileset information.
    
    Call this when a tileset is updated or deleted.
    
    Args:
        tileset_id: Tileset ID to invalidate
    """
    tileset_cache.delete(tileset_id)


def get_cached_pmtiles_metadata(url: str) -> Optional[dict]:
    """
    Get cached PMTiles metadata.
    
    Args:
        url: PMTiles URL
        
    Returns:
        Cached metadata dict or None
    """
    return pmtiles_metadata_cache.get(url)


def cache_pmtiles_metadata(url: str, metadata: dict) -> None:
    """
    Cache PMTiles metadata.
    
    Args:
        url: PMTiles URL
        metadata: Metadata dict to cache
    """
    pmtiles_metadata_cache.set(url, metadata)


def get_cache_stats() -> dict:
    """
    Get statistics for all caches.
    
    Returns:
        Dict with stats for each cache
    """
    return {
        "tileset_cache": tileset_cache.stats(),
        "pmtiles_metadata_cache": pmtiles_metadata_cache.stats(),
    }


def clear_all_caches() -> None:
    """Clear all caches."""
    tileset_cache.clear()
    pmtiles_metadata_cache.clear()
