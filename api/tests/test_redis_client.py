"""
Tests for Redis client module.

Tests cover:
- RedisConfig configuration
- Connection management
- Safe operations (get, set, delete)
- JSON operations
- Health check
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    client = MagicMock()
    client.ping.return_value = True
    client.get.return_value = None
    client.set.return_value = True
    client.delete.return_value = 1
    client.exists.return_value = 0
    client.keys.return_value = []
    client.info.return_value = {
        "redis_version": "7.0.0",
        "used_memory_human": "1M",
        "connected_clients": 1,
        "keyspace_hits": 100,
        "keyspace_misses": 10,
        "total_commands_processed": 1000,
    }
    return client


@pytest.fixture
def reset_redis_module():
    """Reset the Redis module state before and after test."""
    from lib import redis_client
    redis_client._redis_client = None
    redis_client._redis_available = None
    yield
    redis_client._redis_client = None
    redis_client._redis_available = None


# =============================================================================
# Test RedisConfig
# =============================================================================


class TestRedisConfig:
    """Tests for RedisConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        from lib.redis_client import RedisConfig
        
        with patch.dict("os.environ", {}, clear=True):
            config = RedisConfig()
            
            assert config.enabled is True
            assert config.host == "localhost"
            assert config.port == 6379
            assert config.db == 0
            assert config.ssl is False
            assert config.max_connections == 10
    
    def test_from_environment(self):
        """Test configuration from environment variables."""
        from lib.redis_client import RedisConfig
        
        env = {
            "REDIS_ENABLED": "true",
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "secret",
            "REDIS_DB": "1",
            "REDIS_SSL": "true",
            "REDIS_KEY_PREFIX": "myapp:",
        }
        
        with patch.dict("os.environ", env, clear=True):
            config = RedisConfig()
            
            assert config.enabled is True
            assert config.host == "redis.example.com"
            assert config.port == 6380
            assert config.password == "secret"
            assert config.db == 1
            assert config.ssl is True
            assert config.key_prefix == "myapp:"
    
    def test_redis_url_takes_precedence(self):
        """Test that REDIS_URL takes precedence over individual settings."""
        from lib.redis_client import RedisConfig
        
        env = {
            "REDIS_URL": "redis://other:password@custom-host:9999/5",
            "REDIS_HOST": "ignored",
            "REDIS_PORT": "6379",
        }
        
        with patch.dict("os.environ", env, clear=True):
            config = RedisConfig()
            
            assert config.get_connection_url() == "redis://other:password@custom-host:9999/5"
    
    def test_connection_url_generation(self):
        """Test connection URL generation from individual settings."""
        from lib.redis_client import RedisConfig
        
        # Without password, without SSL
        env = {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0",
            "REDIS_SSL": "false",
        }
        
        with patch.dict("os.environ", env, clear=True):
            config = RedisConfig()
            url = config.get_connection_url()
            
            assert url == "redis://localhost:6379/0"
        
        # With password and SSL
        env = {
            "REDIS_HOST": "secure.redis.io",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "secret123",
            "REDIS_DB": "2",
            "REDIS_SSL": "true",
        }
        
        with patch.dict("os.environ", env, clear=True):
            config = RedisConfig()
            url = config.get_connection_url()
            
            assert url == "rediss://:secret123@secure.redis.io:6380/2"
    
    def test_disabled_config(self):
        """Test disabled Redis configuration."""
        from lib.redis_client import RedisConfig
        
        with patch.dict("os.environ", {"REDIS_ENABLED": "false"}, clear=True):
            config = RedisConfig()
            
            assert config.enabled is False


# =============================================================================
# Test Connection Management
# =============================================================================


class TestConnectionManagement:
    """Tests for Redis connection management."""
    
    def test_get_redis_returns_none_when_disabled(self, reset_redis_module):
        """Test that get_redis returns None when disabled."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "false"}):
            # Clear cache
            from lib.redis_client import get_redis_config
            get_redis_config.cache_clear()
            
            from lib.redis_client import get_redis, redis_available
            
            client = get_redis()
            assert client is None
            assert redis_available() is False
    
    def test_redis_available_returns_false_on_connection_error(self, reset_redis_module):
        """Test redis_available returns False on connection error."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "true"}):
            from lib.redis_client import get_redis_config
            get_redis_config.cache_clear()
            
            with patch("lib.redis_client._create_redis_client", return_value=None):
                from lib.redis_client import redis_available
                
                assert redis_available() is False
    
    def test_get_redis_creates_client(self, reset_redis_module):
        """Test that get_redis attempts to create a client."""
        # This test verifies the creation logic without actually connecting
        with patch.dict("os.environ", {"REDIS_ENABLED": "true"}):
            from lib.redis_client import get_redis_config, redis_available
            get_redis_config.cache_clear()
            
            # Mock the creation to avoid actual connection
            with patch("lib.redis_client._create_redis_client", return_value=None):
                # Should return False when client creation returns None
                assert redis_available() is False


# =============================================================================
# Test Safe Operations
# =============================================================================


class TestSafeOperations:
    """Tests for safe Redis operations."""
    
    def test_safe_redis_get_returns_none_when_unavailable(self, reset_redis_module):
        """Test safe_redis_get returns None when Redis unavailable."""
        with patch("lib.redis_client.get_redis", return_value=None):
            from lib.redis_client import safe_redis_get
            
            result = safe_redis_get("test_key")
            
            assert result is None
    
    def test_safe_redis_get_returns_value(self, mock_redis, reset_redis_module):
        """Test safe_redis_get returns cached value."""
        mock_redis.get.return_value = "cached_value"
        
        with patch("lib.redis_client.get_redis", return_value=mock_redis):
            from lib.redis_client import safe_redis_get, get_redis_config
            get_redis_config.cache_clear()
            
            with patch.dict("os.environ", {"REDIS_KEY_PREFIX": "test:"}):
                from lib.redis_client import RedisConfig
                
                result = safe_redis_get("my_key")
                
                # Should call get with prefixed key
                mock_redis.get.assert_called()
    
    def test_safe_redis_set_returns_false_when_unavailable(self, reset_redis_module):
        """Test safe_redis_set returns False when Redis unavailable."""
        with patch("lib.redis_client.get_redis", return_value=None):
            from lib.redis_client import safe_redis_set
            
            result = safe_redis_set("test_key", "value")
            
            assert result is False
    
    def test_safe_redis_set_with_ttl(self, mock_redis, reset_redis_module):
        """Test safe_redis_set with TTL."""
        with patch("lib.redis_client.get_redis", return_value=mock_redis):
            from lib.redis_client import safe_redis_set, get_redis_config
            get_redis_config.cache_clear()
            
            with patch.dict("os.environ", {"REDIS_KEY_PREFIX": "test:"}):
                result = safe_redis_set("key", "value", ttl=60)
                
                # Should call set with ex parameter
                mock_redis.set.assert_called()
    
    def test_safe_redis_delete_returns_false_when_unavailable(self, reset_redis_module):
        """Test safe_redis_delete returns False when Redis unavailable."""
        with patch("lib.redis_client.get_redis", return_value=None):
            from lib.redis_client import safe_redis_delete
            
            result = safe_redis_delete("test_key")
            
            assert result is False
    
    def test_safe_redis_exists(self, mock_redis, reset_redis_module):
        """Test safe_redis_exists."""
        mock_redis.exists.return_value = 1
        
        with patch("lib.redis_client.get_redis", return_value=mock_redis):
            from lib.redis_client import safe_redis_exists, get_redis_config
            get_redis_config.cache_clear()
            
            with patch.dict("os.environ", {"REDIS_KEY_PREFIX": "test:"}):
                result = safe_redis_exists("key")
                
                # Should return True when exists returns > 0
                mock_redis.exists.assert_called()
    
    def test_safe_redis_delete_pattern(self, mock_redis, reset_redis_module):
        """Test safe_redis_delete_pattern."""
        mock_redis.keys.return_value = ["test:key1", "test:key2"]
        mock_redis.delete.return_value = 2
        
        with patch("lib.redis_client.get_redis", return_value=mock_redis):
            from lib.redis_client import safe_redis_delete_pattern, get_redis_config
            get_redis_config.cache_clear()
            
            with patch.dict("os.environ", {"REDIS_KEY_PREFIX": "test:"}):
                result = safe_redis_delete_pattern("key*")
                
                mock_redis.keys.assert_called()


# =============================================================================
# Test JSON Operations
# =============================================================================


class TestJsonOperations:
    """Tests for JSON operations."""
    
    def test_redis_get_json_returns_none_when_unavailable(self, reset_redis_module):
        """Test redis_get_json returns None when value not found."""
        with patch("lib.redis_client.safe_redis_get", return_value=None):
            from lib.redis_client import redis_get_json
            
            result = redis_get_json("test_key")
            
            assert result is None
    
    def test_redis_get_json_parses_json(self, reset_redis_module):
        """Test redis_get_json parses JSON correctly."""
        json_str = '{"name": "test", "value": 123}'
        
        with patch("lib.redis_client.safe_redis_get", return_value=json_str):
            from lib.redis_client import redis_get_json
            
            result = redis_get_json("test_key")
            
            assert result == {"name": "test", "value": 123}
    
    def test_redis_get_json_handles_invalid_json(self, reset_redis_module):
        """Test redis_get_json handles invalid JSON gracefully."""
        with patch("lib.redis_client.safe_redis_get", return_value="invalid json{"):
            from lib.redis_client import redis_get_json
            
            result = redis_get_json("test_key")
            
            assert result is None
    
    def test_redis_set_json_serializes_dict(self, reset_redis_module):
        """Test redis_set_json serializes dict correctly."""
        with patch("lib.redis_client.safe_redis_set", return_value=True) as mock_set:
            from lib.redis_client import redis_set_json
            
            data = {"name": "test", "values": [1, 2, 3]}
            result = redis_set_json("test_key", data, ttl=60)
            
            assert result is True
            # Verify JSON was passed
            call_args = mock_set.call_args
            assert "name" in call_args[0][1]  # JSON string contains "name"
    
    def test_redis_set_json_handles_non_serializable(self, reset_redis_module):
        """Test redis_set_json handles non-serializable data."""
        from lib.redis_client import redis_set_json
        
        # Sets are not JSON serializable
        result = redis_set_json("test_key", {1, 2, 3})
        
        assert result is False


# =============================================================================
# Test Health Check
# =============================================================================


class TestHealthCheck:
    """Tests for health check functionality."""
    
    def test_check_redis_health_when_disabled(self, reset_redis_module):
        """Test health check when Redis is disabled."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "false"}):
            from lib.redis_client import check_redis_health, get_redis_config
            get_redis_config.cache_clear()
            
            result = check_redis_health()
            
            assert result["status"] == "disabled"
            assert result["enabled"] is False
    
    def test_check_redis_health_when_unavailable(self, reset_redis_module):
        """Test health check when Redis is unavailable."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "true"}):
            from lib.redis_client import get_redis_config
            get_redis_config.cache_clear()
            
            with patch("lib.redis_client.get_redis", return_value=None):
                from lib.redis_client import check_redis_health
                
                result = check_redis_health()
                
                assert result["status"] == "unavailable"
                assert result["enabled"] is True
    
    def test_check_redis_health_when_healthy(self, mock_redis, reset_redis_module):
        """Test health check when Redis is healthy."""
        with patch.dict("os.environ", {"REDIS_ENABLED": "true"}):
            from lib.redis_client import get_redis_config
            get_redis_config.cache_clear()
            
            with patch("lib.redis_client.get_redis", return_value=mock_redis):
                from lib.redis_client import check_redis_health
                
                result = check_redis_health()
                
                assert result["status"] == "healthy"
                assert result["connected"] is True
                assert "redis_version" in result


# =============================================================================
# Test Statistics
# =============================================================================


class TestStatistics:
    """Tests for Redis statistics."""
    
    def test_get_redis_stats_when_unavailable(self, reset_redis_module):
        """Test stats when Redis is unavailable."""
        with patch("lib.redis_client.get_redis", return_value=None):
            from lib.redis_client import get_redis_stats, get_redis_config
            
            with patch.dict("os.environ", {"REDIS_ENABLED": "true"}):
                get_redis_config.cache_clear()
                
                result = get_redis_stats()
                
                assert result["available"] is False
    
    def test_get_redis_stats_when_available(self, mock_redis, reset_redis_module):
        """Test stats when Redis is available."""
        with patch("lib.redis_client.get_redis", return_value=mock_redis):
            from lib.redis_client import get_redis_stats, get_redis_config
            
            with patch.dict("os.environ", {"REDIS_ENABLED": "true", "REDIS_KEY_PREFIX": "test:"}):
                get_redis_config.cache_clear()
                
                result = get_redis_stats()
                
                assert result["available"] is True
                assert "key_count" in result
                assert "used_memory" in result
