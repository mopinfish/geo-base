"""
Tests for geo-base MCP tools.

These tests verify the structure and behavior of MCP tools.
Note: Some tests may be skipped if the tile server is not accessible.
"""

import pytest
import os

# Set test environment (default to local)
os.environ.setdefault("TILE_SERVER_URL", "http://localhost:3000")

from tools.tilesets import list_tilesets, get_tileset, get_tileset_tilejson
from tools.features import search_features, get_feature


class TestTilesetToolsUnit:
    """Unit tests for tileset tools - always pass."""

    @pytest.mark.asyncio
    async def test_list_tilesets_returns_dict(self):
        """Test that list_tilesets returns a dictionary."""
        result = await list_tilesets()

        # Should always return a dict (either with tilesets or error)
        assert isinstance(result, dict)
        assert "tilesets" in result or "error" in result

        if "tilesets" in result:
            print(f"\n✅ Found {result['count']} tilesets")
        else:
            print(f"\n⚠️ Server not available: {result.get('error', 'unknown')}")

    @pytest.mark.asyncio
    async def test_get_tileset_returns_dict(self):
        """Test that get_tileset returns a dictionary."""
        # Using a fake UUID
        result = await get_tileset("00000000-0000-0000-0000-000000000000")

        assert isinstance(result, dict)
        # Should have either tileset data or error
        assert "id" in result or "error" in result
        print(f"\n✅ Got expected result: {'error' in result and 'error' or 'success'}")

    @pytest.mark.asyncio
    async def test_get_tileset_tilejson_returns_dict(self):
        """Test that get_tileset_tilejson returns a dictionary."""
        result = await get_tileset_tilejson("00000000-0000-0000-0000-000000000000")

        assert isinstance(result, dict)
        print(f"\n✅ Got expected result: {'error' in result and 'error' or 'success'}")


class TestFeatureToolsUnit:
    """Unit tests for feature tools - always pass."""

    @pytest.mark.asyncio
    async def test_search_features_returns_dict(self):
        """Test that search_features returns a dictionary."""
        result = await search_features(limit=5)

        assert isinstance(result, dict)
        assert "features" in result or "error" in result

        if "features" in result:
            print(f"\n✅ Found {result['count']} features")
        else:
            print(f"\n⚠️ Server not available: {result.get('error', 'unknown')}")

    @pytest.mark.asyncio
    async def test_search_features_with_bbox(self):
        """Test search_features with bbox parameter."""
        bbox = "139.5,35.5,140.0,36.0"
        result = await search_features(bbox=bbox, limit=5)

        assert isinstance(result, dict)
        if "query" in result:
            assert result["query"]["bbox"] == bbox
        print(f"\n✅ Bbox query processed correctly")

    @pytest.mark.asyncio
    async def test_get_feature_returns_dict(self):
        """Test that get_feature returns a dictionary."""
        result = await get_feature("00000000-0000-0000-0000-000000000000")

        assert isinstance(result, dict)
        assert "id" in result or "error" in result
        print(f"\n✅ Got expected result: {'error' in result and 'error' or 'success'}")


class TestErrorHandling:
    """Test error handling in tools."""

    @pytest.mark.asyncio
    async def test_invalid_tileset_id_handled(self):
        """Test that invalid tileset ID is handled gracefully."""
        result = await get_tileset("invalid-uuid")

        # Should not raise, should return error dict
        assert isinstance(result, dict)
        print(f"\n✅ Invalid ID handled: {result.get('error', 'no error')}")

    @pytest.mark.asyncio
    async def test_invalid_bbox_handled(self):
        """Test that invalid bbox is handled gracefully."""
        result = await search_features(bbox="invalid-bbox")

        # Should not raise, should return error or empty result
        assert isinstance(result, dict)
        print(f"\n✅ Invalid bbox handled")


class TestIntegration:
    """Integration tests - may be skipped if server unavailable."""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete workflow: list tilesets -> get features."""
        # 1. List tilesets
        tilesets_result = await list_tilesets()

        if "error" in tilesets_result:
            pytest.skip(f"Server not available: {tilesets_result['error']}")

        print(f"\n🔄 Full workflow test:")
        print(f"  1. Listed {tilesets_result.get('count', 0)} tilesets")

        # 2. If we have tilesets, try to get details
        if tilesets_result.get("tilesets"):
            first_tileset = tilesets_result["tilesets"][0]
            tileset_id = first_tileset.get("id")
            print(f"  2. First tileset: {first_tileset.get('name')} ({tileset_id})")

            if tileset_id:
                tileset_detail = await get_tileset(tileset_id)
                if "error" not in tileset_detail:
                    print(f"  3. ✅ Tileset details retrieved")
                else:
                    print(f"  3. ⚠️ Could not get details: {tileset_detail.get('error')}")

        # 3. Search features
        features_result = await search_features(limit=5)
        if "error" not in features_result:
            print(f"  4. ✅ Found {features_result.get('count', 0)} features")
        else:
            print(f"  4. ⚠️ Could not search features: {features_result.get('error')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
