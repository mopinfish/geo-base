"""
Redis client for geo-base API.

This module provides Redis connection management with support for
multiple deployment environments:
- Local development: Docker Redis
- Production (Fly.io): Fly.io Redis or Upstash

Features:
- Connection pooling
- Automatic reconnection on connection loss
- Graceful degradation when Redis is unavailable
- Support for both sync and async operations

Configuration via environment variables:
- REDIS_URL: Full Redis URL (redis://host:port/db)
- REDIS_HOST: Redis host (default: localhost)
- REDIS_PORT: Redis port (default: 6379)
- REDIS_PASSWORD: Redis password (optional)
- REDIS_DB: Redis database number (default: 0)
- REDIS_SSL: Use SSL/TLS (default: false)
- REDIS_ENABLED: Enable/disable Redis cache (default: true)

Usage:
    from lib.redis_client import get_redis, redis_available

    # Check if Redis is available
    if redis_available():
        client = get_redis()
        client.set("key", "value", ex=60)
        value = client.get("key")

    # Or use the safe wrapper
    from lib.redis_client import safe_redis_get, safe_redis_set

    safe_redis_set("key", "value", ttl=60)
    value = safe_redis_get("key")  # Returns None if Redis unavailable
"""

import logging
import os
from functools import lru_cache
from typing import Any, Optional, Union
import json

logger = logging.getLogger(__name__)

# Redis client (lazy initialized)
_redis_client: Optional[Any] = None
_redis_available: Optional[bool] = None


# =============================================================================
# Configuration
# =============================================================================


class RedisConfig:
    """Redis configuration loaded from environment variables."""
    
    def __init__(self):
        # Check if Redis is enabled
        self.enabled = os.environ.get("REDIS_ENABLED", "true").lower() == "true"
        
        # Get Redis URL (takes precedence over individual settings)
        self.url = os.environ.get("REDIS_URL")
        
        # Individual settings (used if REDIS_URL not set)
        self.host = os.environ.get("REDIS_HOST", "localhost")
        self.port = int(os.environ.get("REDIS_PORT", "6379"))
        self.password = os.environ.get("REDIS_PASSWORD")
        self.db = int(os.environ.get("REDIS_DB", "0"))
        self.ssl = os.environ.get("REDIS_SSL", "false").lower() == "true"
        
        # Connection pool settings
        self.max_connections = int(os.environ.get("REDIS_MAX_CONNECTIONS", "10"))
        self.socket_timeout = float(os.environ.get("REDIS_SOCKET_TIMEOUT", "5.0"))
        self.socket_connect_timeout = float(
            os.environ.get("REDIS_CONNECT_TIMEOUT", "5.0")
        )
        
        # Retry settings
        self.retry_on_timeout = os.environ.get(
            "REDIS_RETRY_ON_TIMEOUT", "true"
        ).lower() == "true"
        
        # Key prefix for namespacing
        self.key_prefix = os.environ.get("REDIS_KEY_PREFIX", "geo-base:")
    
    def get_connection_url(self) -> str:
        """Get the full Redis connection URL."""
        if self.url:
            return self.url
        
        # Build URL from individual settings
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"
    
    def __repr__(self) -> str:
        """Return string representation (without password)."""
        return (
            f"RedisConfig(enabled={self.enabled}, host={self.host}, "
            f"port={self.port}, db={self.db}, ssl={self.ssl})"
        )


@lru_cache
def get_redis_config() -> RedisConfig:
    """Get cached Redis configuration."""
    return RedisConfig()


# =============================================================================
# Client Management
# =============================================================================


def _create_redis_client():
    """
    Create a Redis client with connection pooling.
    
    Returns:
        Redis client instance or None if creation fails
    """
    try:
        import redis
    except ImportError:
        logger.warning(
            "Redis package not installed. Install with: pip install redis"
        )
        return None
    
    config = get_redis_config()
    
    if not config.enabled:
        logger.info("Redis is disabled by configuration")
        return None
    
    try:
        # Create connection pool
        pool = redis.ConnectionPool.from_url(
            config.get_connection_url(),
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            retry_on_timeout=config.retry_on_timeout,
            decode_responses=True,  # Return strings instead of bytes
        )
        
        # Create client with pool
        client = redis.Redis(connection_pool=pool)
        
        # Test connection
        client.ping()
        
        logger.info(
            f"Redis connected: {config.host}:{config.port}/{config.db} "
            f"(SSL: {config.ssl})"
        )
        
        return client
        
    except redis.ConnectionError as e:
        logger.warning(f"Failed to connect to Redis: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error creating Redis client: {e}")
        return None


def get_redis():
    """
    Get the Redis client instance.
    
    Returns lazily initialized client, or None if Redis is unavailable.
    
    Returns:
        Redis client or None
    """
    global _redis_client, _redis_available
    
    if _redis_client is None and _redis_available is not False:
        _redis_client = _create_redis_client()
        _redis_available = _redis_client is not None
    
    return _redis_client


def redis_available() -> bool:
    """
    Check if Redis is available.
    
    Returns:
        True if Redis is connected and responding
    """
    global _redis_available
    
    if _redis_available is None:
        get_redis()  # Triggers initialization
    
    return _redis_available or False


def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client, _redis_available
    
    if _redis_client is not None:
        try:
            _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None
            _redis_available = None


def reset_redis() -> None:
    """
    Reset the Redis client (for reconnection after errors).
    
    Call this if you suspect the connection is broken.
    """
    global _redis_client, _redis_available
    _redis_client = None
    _redis_available = None


# =============================================================================
# Safe Operations (with fallback to None)
# =============================================================================


def _make_key(key: str) -> str:
    """Add prefix to key for namespacing."""
    config = get_redis_config()
    return f"{config.key_prefix}{key}"


def safe_redis_get(key: str) -> Optional[str]:
    """
    Safely get a value from Redis.
    
    Returns None if Redis is unavailable or on error.
    
    Args:
        key: Cache key (prefix will be added automatically)
        
    Returns:
        Cached value or None
    """
    client = get_redis()
    if client is None:
        return None
    
    try:
        return client.get(_make_key(key))
    except Exception as e:
        logger.warning(f"Redis GET error for key '{key}': {e}")
        return None


def safe_redis_set(
    key: str,
    value: str,
    ttl: Optional[int] = None,
) -> bool:
    """
    Safely set a value in Redis.
    
    Returns False if Redis is unavailable or on error.
    
    Args:
        key: Cache key (prefix will be added automatically)
        value: Value to cache
        ttl: Time-to-live in seconds (optional)
        
    Returns:
        True if successful, False otherwise
    """
    client = get_redis()
    if client is None:
        return False
    
    try:
        if ttl is not None:
            client.set(_make_key(key), value, ex=ttl)
        else:
            client.set(_make_key(key), value)
        return True
    except Exception as e:
        logger.warning(f"Redis SET error for key '{key}': {e}")
        return False


def safe_redis_delete(key: str) -> bool:
    """
    Safely delete a value from Redis.
    
    Returns False if Redis is unavailable or on error.
    
    Args:
        key: Cache key (prefix will be added automatically)
        
    Returns:
        True if key was deleted, False otherwise
    """
    client = get_redis()
    if client is None:
        return False
    
    try:
        return client.delete(_make_key(key)) > 0
    except Exception as e:
        logger.warning(f"Redis DELETE error for key '{key}': {e}")
        return False


def safe_redis_delete_pattern(pattern: str) -> int:
    """
    Safely delete all keys matching a pattern.
    
    Args:
        pattern: Key pattern with wildcards (e.g., "tileset:*")
        
    Returns:
        Number of keys deleted
    """
    client = get_redis()
    if client is None:
        return 0
    
    try:
        full_pattern = _make_key(pattern)
        keys = client.keys(full_pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Redis DELETE pattern error for '{pattern}': {e}")
        return 0


def safe_redis_exists(key: str) -> bool:
    """
    Safely check if a key exists in Redis.
    
    Args:
        key: Cache key (prefix will be added automatically)
        
    Returns:
        True if key exists, False otherwise
    """
    client = get_redis()
    if client is None:
        return False
    
    try:
        return client.exists(_make_key(key)) > 0
    except Exception as e:
        logger.warning(f"Redis EXISTS error for key '{key}': {e}")
        return False


# =============================================================================
# JSON Operations (for structured data)
# =============================================================================


def redis_get_json(key: str) -> Optional[Any]:
    """
    Get a JSON value from Redis.
    
    Args:
        key: Cache key
        
    Returns:
        Parsed JSON value or None
    """
    value = safe_redis_get(key)
    if value is None:
        return None
    
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON for key '{key}': {e}")
        return None


def redis_set_json(
    key: str,
    value: Any,
    ttl: Optional[int] = None,
) -> bool:
    """
    Set a JSON value in Redis.
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        json_str = json.dumps(value)
        return safe_redis_set(key, json_str, ttl=ttl)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize value for key '{key}': {e}")
        return False


# =============================================================================
# Binary Operations (for tiles)
# =============================================================================


def redis_get_binary(key: str) -> Optional[bytes]:
    """
    Get a binary value from Redis.
    
    Args:
        key: Cache key
        
    Returns:
        Binary data or None
    """
    client = get_redis()
    if client is None:
        return None
    
    try:
        # Need to get raw client for binary data
        import redis
        config = get_redis_config()
        
        # Create a client without decode_responses for binary data
        binary_client = redis.Redis.from_url(
            config.get_connection_url(),
            decode_responses=False,
        )
        return binary_client.get(_make_key(key))
    except Exception as e:
        logger.warning(f"Redis GET binary error for key '{key}': {e}")
        return None


def redis_set_binary(
    key: str,
    value: bytes,
    ttl: Optional[int] = None,
) -> bool:
    """
    Set a binary value in Redis.
    
    Args:
        key: Cache key
        value: Binary data to cache
        ttl: Time-to-live in seconds (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import redis
        config = get_redis_config()
        
        # Create a client without decode_responses for binary data
        binary_client = redis.Redis.from_url(
            config.get_connection_url(),
            decode_responses=False,
        )
        
        if ttl is not None:
            binary_client.set(_make_key(key), value, ex=ttl)
        else:
            binary_client.set(_make_key(key), value)
        return True
    except Exception as e:
        logger.warning(f"Redis SET binary error for key '{key}': {e}")
        return False


# =============================================================================
# Health Check
# =============================================================================


def check_redis_health() -> dict:
    """
    Check Redis health and return status info.
    
    Returns:
        Dict with health status
    """
    config = get_redis_config()
    
    if not config.enabled:
        return {
            "status": "disabled",
            "enabled": False,
            "message": "Redis is disabled by configuration",
        }
    
    client = get_redis()
    
    if client is None:
        return {
            "status": "unavailable",
            "enabled": True,
            "message": "Unable to connect to Redis",
            "host": config.host,
            "port": config.port,
        }
    
    try:
        # Get server info
        info = client.info("server")
        memory = client.info("memory")
        
        return {
            "status": "healthy",
            "enabled": True,
            "connected": True,
            "host": config.host,
            "port": config.port,
            "redis_version": info.get("redis_version"),
            "used_memory_human": memory.get("used_memory_human"),
            "connected_clients": client.info("clients").get("connected_clients"),
        }
    except Exception as e:
        return {
            "status": "error",
            "enabled": True,
            "message": str(e),
            "host": config.host,
            "port": config.port,
        }


# =============================================================================
# Cache Statistics
# =============================================================================


def get_redis_stats() -> dict:
    """
    Get Redis cache statistics.
    
    Returns:
        Dict with cache statistics
    """
    client = get_redis()
    config = get_redis_config()
    
    if client is None:
        return {
            "available": False,
            "enabled": config.enabled,
        }
    
    try:
        info = client.info()
        
        # Count keys with our prefix
        pattern = f"{config.key_prefix}*"
        key_count = len(client.keys(pattern))
        
        return {
            "available": True,
            "enabled": True,
            "key_count": key_count,
            "key_prefix": config.key_prefix,
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "hit_rate": _calculate_hit_rate(
                info.get("keyspace_hits", 0),
                info.get("keyspace_misses", 0),
            ),
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }


def _calculate_hit_rate(hits: int, misses: int) -> Optional[float]:
    """Calculate cache hit rate percentage."""
    total = hits + misses
    if total == 0:
        return None
    return round((hits / total) * 100, 2)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Configuration
    "RedisConfig",
    "get_redis_config",
    # Client management
    "get_redis",
    "redis_available",
    "close_redis",
    "reset_redis",
    # Safe operations
    "safe_redis_get",
    "safe_redis_set",
    "safe_redis_delete",
    "safe_redis_delete_pattern",
    "safe_redis_exists",
    # JSON operations
    "redis_get_json",
    "redis_set_json",
    # Binary operations
    "redis_get_binary",
    "redis_set_binary",
    # Health check
    "check_redis_health",
    "get_redis_stats",
]
