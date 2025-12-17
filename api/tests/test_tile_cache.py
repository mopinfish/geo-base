"""
Tests for tile cache module.

Tests cover:
- TileCacheConfig configuration
- Tile caching (get/set)
- TileJSON caching
- Tileset info caching
- Cache invalidation
- Statistics
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def tile_cache_config():
    """Create test configuration."""
    from lib.tile_cache import TileCacheConfig
    
    return TileCacheConfig(
        tile_ttl=60,
        tilejson_ttl=30,
        tileset_info_ttl=10,
        memory_cache_max_size=100,
        memory_cache_enabled=True,
        cache_vector_tiles=True,
        cache_raster_tiles=True,
        cache_pmtiles=True,
        cache_tilejson=True,
    )


@pytest.fixture
def sample_tile_data():
    """Sample tile data for testing."""
    return b"\x1a\x03MVT\x00\x00\x00\x00\x00"


@pytest.fixture
def sample_tilejson():
    """Sample TileJSON for testing."""
    return {
        "tilejson": "3.0.0",
        "name": "Test Tileset",
        "tiles": ["https://example.com/tiles/{z}/{x}/{y}.pbf"],
        "minzoom": 0,
        "maxzoom": 22,
        "bounds": [-180, -90, 180, 90],
    }


@pytest.fixture
def sample_tileset_info():
    """Sample tileset info for testing."""
    return {
        "id": "test-uuid",
        "name": "Test Tileset",
        "type": "vector",
        "format": "pbf",
        "min_zoom": 0,
        "max_zoom": 22,
    }


@pytest.fixture
def reset_tile_cache():
    """Reset tile cache state before and after test."""
    from lib import tile_cache
    
    # Reset config
    tile_cache._config = None
    
    # Reset memory caches
    tile_cache._tile_memory_cache = None
    tile_cache._tilejson_memory_cache = None
    tile_cache._tileset_memory_cache = None
    
    yield
    
    # Cleanup
    tile_cache._config = None
    tile_cache._tile_memory_cache = None
    tile_cache._tilejson_memory_cache = None
    tile_cache._tileset_memory_cache = None


# =============================================================================
# Test TileCacheConfig
# =============================================================================


class TestTileCacheConfig:
    """Tests for TileCacheConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        from lib.tile_cache import TileCacheConfig
        
        config = TileCacheConfig()
        
        assert config.tile_ttl == 3600
        assert config.tilejson_ttl == 300
        assert config.tileset_info_ttl == 60
        assert config.memory_cache_enabled is True
        assert config.cache_vector_tiles is True
        assert config.cache_raster_tiles is True
    
    def test_from_environment(self):
        """Test configuration from environment variables."""
        env = {
            "TILE_CACHE_TTL": "7200",
            "TILEJSON_CACHE_TTL": "600",
            "TILESET_INFO_CACHE_TTL": "120",
            "MEMORY_CACHE_ENABLED": "false",
            "CACHE_VECTOR_TILES": "false",
        }
        
        with patch.dict("os.environ", env, clear=True):
            from lib.tile_cache import TileCacheConfig
            
            config = TileCacheConfig.from_env()
            
            assert config.tile_ttl == 7200
            assert config.tilejson_ttl == 600
            assert config.tileset_info_ttl == 120
            assert config.memory_cache_enabled is False
            assert config.cache_vector_tiles is False


# =============================================================================
# Test Cache Key Generation
# =============================================================================


class TestCacheKeyGeneration:
    """Tests for cache key generation."""
    
    def test_tile_key_basic(self):
        """Test basic tile key generation."""
        from lib.tile_cache import _make_tile_key
        
        key = _make_tile_key(
            tileset_id="test-uuid",
            z=10,
            x=100,
            y=200,
            tile_type="vector",
        )
        
        assert "tile:vector" in key
        assert "test-uuid" in key
        assert "10" in key
        assert "100" in key
        assert "200" in key
    
    def test_tile_key_with_layer(self):
        """Test tile key with layer."""
        from lib.tile_cache import _make_tile_key
        
        key = _make_tile_key(
            tileset_id="test-uuid",
            z=10,
            x=100,
            y=200,
            tile_type="vector",
            layer="buildings",
        )
        
        assert "layer:buildings" in key
    
    def test_tile_key_with_raster_options(self):
        """Test tile key with raster-specific options."""
        from lib.tile_cache import _make_tile_key
        
        key = _make_tile_key(
            tileset_id="test-uuid",
            z=10,
            x=100,
            y=200,
            tile_type="raster",
            colormap="viridis",
            bands="1,2,3",
        )
        
        assert "tile:raster" in key
        assert "cmap:viridis" in key
        assert "bands:1,2,3" in key
    
    def test_tilejson_key(self):
        """Test TileJSON key generation."""
        from lib.tile_cache import _make_tilejson_key
        
        key = _make_tilejson_key("test-uuid", "vector")
        
        assert key == "tilejson:vector:test-uuid"
    
    def test_tileset_key(self):
        """Test tileset info key generation."""
        from lib.tile_cache import _make_tileset_key
        
        key = _make_tileset_key("test-uuid")
        
        assert key == "tileset:test-uuid"


# =============================================================================
# Test Tile Caching (Memory Only)
# =============================================================================


class TestTileCachingMemoryOnly:
    """Tests for tile caching with memory cache only."""
    
    def test_cache_and_get_tile(self, reset_tile_cache, sample_tile_data):
        """Test caching and retrieving a tile."""
        # Disable Redis for this test
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import cache_tile, get_cached_tile
            
            # Cache tile
            result = cache_tile(
                tileset_id="test-uuid",
                z=10, x=100, y=200,
                data=sample_tile_data,
                tile_type="vector",
            )
            
            assert result is True
            
            # Retrieve tile
            cached = get_cached_tile(
                tileset_id="test-uuid",
                z=10, x=100, y=200,
                tile_type="vector",
            )
            
            assert cached == sample_tile_data
    
    def test_cache_miss_returns_none(self, reset_tile_cache):
        """Test that cache miss returns None."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import get_cached_tile
            
            cached = get_cached_tile(
                tileset_id="nonexistent",
                z=10, x=100, y=200,
                tile_type="vector",
            )
            
            assert cached is None
    
    def test_caching_respects_tile_type_config(self, reset_tile_cache, sample_tile_data):
        """Test that caching respects tile type configuration."""
        env = {"CACHE_VECTOR_TILES": "false"}
        
        with patch.dict("os.environ", env):
            with patch("lib.tile_cache.redis_available", return_value=False):
                from lib.tile_cache import cache_tile, get_tile_cache_config
                
                # Reset config
                import lib.tile_cache
                lib.tile_cache._config = None
                
                # Try to cache
                result = cache_tile(
                    tileset_id="test-uuid",
                    z=10, x=100, y=200,
                    data=sample_tile_data,
                    tile_type="vector",
                )
                
                assert result is False


# =============================================================================
# Test TileJSON Caching
# =============================================================================


class TestTileJsonCaching:
    """Tests for TileJSON caching."""
    
    def test_cache_and_get_tilejson(self, reset_tile_cache, sample_tilejson):
        """Test caching and retrieving TileJSON."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import cache_tilejson, get_cached_tilejson
            
            # Cache TileJSON
            result = cache_tilejson(
                tileset_id="test-uuid",
                tilejson=sample_tilejson,
                tile_type="vector",
            )
            
            assert result is True
            
            # Retrieve TileJSON
            cached = get_cached_tilejson(
                tileset_id="test-uuid",
                tile_type="vector",
            )
            
            assert cached == sample_tilejson
    
    def test_tilejson_cache_miss(self, reset_tile_cache):
        """Test TileJSON cache miss."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import get_cached_tilejson
            
            cached = get_cached_tilejson(
                tileset_id="nonexistent",
                tile_type="vector",
            )
            
            assert cached is None


# =============================================================================
# Test Tileset Info Caching
# =============================================================================


class TestTilesetInfoCaching:
    """Tests for tileset info caching."""
    
    def test_cache_and_get_tileset_info(self, reset_tile_cache, sample_tileset_info):
        """Test caching and retrieving tileset info."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import cache_tileset_info, get_cached_tileset_info
            
            # Cache info
            result = cache_tileset_info(
                tileset_id="test-uuid",
                info=sample_tileset_info,
            )
            
            assert result is True
            
            # Retrieve info
            cached = get_cached_tileset_info("test-uuid")
            
            assert cached == sample_tileset_info
    
    def test_tileset_info_cache_miss(self, reset_tile_cache):
        """Test tileset info cache miss."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import get_cached_tileset_info
            
            cached = get_cached_tileset_info("nonexistent")
            
            assert cached is None


# =============================================================================
# Test Cache Invalidation
# =============================================================================


class TestCacheInvalidation:
    """Tests for cache invalidation."""
    
    def test_invalidate_tileset(self, reset_tile_cache, sample_tile_data, sample_tilejson):
        """Test invalidating all cache for a tileset."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import (
                cache_tile,
                cache_tilejson,
                cache_tileset_info,
                get_cached_tile,
                get_cached_tilejson,
                get_cached_tileset_info,
                invalidate_tileset,
            )
            
            tileset_id = "test-uuid"
            
            # Cache some data
            cache_tile(tileset_id, 10, 100, 200, sample_tile_data, "vector")
            cache_tilejson(tileset_id, sample_tilejson, "vector")
            cache_tileset_info(tileset_id, {"id": tileset_id})
            
            # Verify cached
            assert get_cached_tile(tileset_id, 10, 100, 200, "vector") is not None
            assert get_cached_tilejson(tileset_id, "vector") is not None
            assert get_cached_tileset_info(tileset_id) is not None
            
            # Invalidate
            count = invalidate_tileset(tileset_id)
            
            # Note: Memory cache doesn't support pattern deletion for tiles
            # So only tilejson and tileset_info are invalidated
            assert count >= 2
            
            # TileJSON and tileset info should be gone
            assert get_cached_tilejson(tileset_id, "vector") is None
            assert get_cached_tileset_info(tileset_id) is None
    
    def test_invalidate_single_tile(self, reset_tile_cache, sample_tile_data):
        """Test invalidating a single tile."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import (
                cache_tile,
                get_cached_tile,
                invalidate_tile,
            )
            
            tileset_id = "test-uuid"
            
            # Cache tile
            cache_tile(tileset_id, 10, 100, 200, sample_tile_data, "vector")
            
            # Verify cached
            assert get_cached_tile(tileset_id, 10, 100, 200, "vector") is not None
            
            # Invalidate
            result = invalidate_tile(tileset_id, 10, 100, 200, "vector")
            
            assert result is True
            
            # Should be gone
            assert get_cached_tile(tileset_id, 10, 100, 200, "vector") is None
    
    def test_clear_all_caches(self, reset_tile_cache, sample_tile_data):
        """Test clearing all caches."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            from lib.tile_cache import (
                cache_tile,
                cache_tilejson,
                get_cached_tile,
                get_cached_tilejson,
                clear_all_tile_caches,
            )
            
            # Cache some data
            cache_tile("uuid1", 10, 100, 200, sample_tile_data, "vector")
            cache_tilejson("uuid1", {"name": "test"}, "vector")
            
            # Clear all
            clear_all_tile_caches()
            
            # Everything should be gone
            assert get_cached_tile("uuid1", 10, 100, 200, "vector") is None
            assert get_cached_tilejson("uuid1", "vector") is None


# =============================================================================
# Test Statistics
# =============================================================================


class TestStatistics:
    """Tests for cache statistics."""
    
    def test_get_tile_cache_stats(self, reset_tile_cache):
        """Test getting cache statistics."""
        with patch("lib.tile_cache.redis_available", return_value=False):
            with patch("lib.tile_cache.get_redis_stats", return_value={"available": False}):
                from lib.tile_cache import get_tile_cache_stats
                
                stats = get_tile_cache_stats()
                
                assert "config" in stats
                assert "redis" in stats
                assert "memory" in stats
                
                # Check config section
                assert "tile_ttl" in stats["config"]
                assert "cache_vector_tiles" in stats["config"]
                
                # Check memory section
                assert "tiles" in stats["memory"]
                assert "tilejson" in stats["memory"]
                assert "tileset_info" in stats["memory"]


# =============================================================================
# Test Redis Integration (Mocked)
# =============================================================================


class TestRedisIntegration:
    """Tests for Redis integration."""
    
    def test_cache_tile_uses_redis_when_available(
        self, reset_tile_cache, sample_tile_data
    ):
        """Test that tile caching uses Redis when available."""
        with patch("lib.tile_cache.redis_available", return_value=True):
            with patch("lib.tile_cache.redis_set_binary", return_value=True) as mock_set:
                from lib.tile_cache import cache_tile
                
                result = cache_tile(
                    tileset_id="test-uuid",
                    z=10, x=100, y=200,
                    data=sample_tile_data,
                    tile_type="vector",
                )
                
                assert result is True
                mock_set.assert_called_once()
    
    def test_get_cached_tile_uses_redis_when_available(
        self, reset_tile_cache, sample_tile_data
    ):
        """Test that tile retrieval uses Redis when available."""
        with patch("lib.tile_cache.redis_available", return_value=True):
            with patch(
                "lib.tile_cache.redis_get_binary",
                return_value=sample_tile_data
            ) as mock_get:
                from lib.tile_cache import get_cached_tile
                
                result = get_cached_tile(
                    tileset_id="test-uuid",
                    z=10, x=100, y=200,
                    tile_type="vector",
                )
                
                assert result == sample_tile_data
                mock_get.assert_called_once()
    
    def test_invalidate_tileset_clears_redis(self, reset_tile_cache):
        """Test that tileset invalidation clears Redis."""
        with patch("lib.tile_cache.redis_available", return_value=True):
            with patch(
                "lib.tile_cache.safe_redis_delete_pattern",
                return_value=5
            ) as mock_delete:
                from lib.tile_cache import invalidate_tileset
                
                count = invalidate_tileset("test-uuid")
                
                # Should call delete pattern for tiles, tilejson, tileset
                assert mock_delete.call_count >= 3
                assert count >= 5
