"""
Tests for tileset and feature tools.

This module tests:
- list_tilesets
- get_tileset
- get_tileset_tilejson
- search_features
- get_feature
- get_features_in_tile

Uses standard asyncio approach (not pytest-asyncio).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from tools.tilesets import (
    list_tilesets,
    get_tileset,
    get_tileset_tilejson,
)
from tools.features import (
    search_features,
    get_feature,
    get_features_in_tile,
)


class TestListTilesets:
    """Tests for list_tilesets function."""

    def test_list_tilesets_returns_dict(self):
        """list_tilesets should return a dictionary with tilesets."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = [
                {"id": "id1", "name": "Tileset 1", "type": "vector"},
                {"id": "id2", "name": "Tileset 2", "type": "raster"},
            ]
            mock_response.raise_for_status = Mock()

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await list_tilesets()

                assert "tilesets" in result
                assert result["count"] == 2

        asyncio.run(run_test())

    def test_list_tilesets_with_type_filter(self):
        """list_tilesets should filter by type."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = [
                {"id": "id1", "name": "Vector Tileset", "type": "vector"},
            ]
            mock_response.raise_for_status = Mock()

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await list_tilesets(type="vector")

                assert result is not None

        asyncio.run(run_test())

    def test_list_tilesets_empty(self):
        """list_tilesets should handle empty result."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status = Mock()

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await list_tilesets()

                assert result["count"] == 0
                assert result["tilesets"] == []

        asyncio.run(run_test())

    def test_list_tilesets_network_error(self):
        """list_tilesets should handle network errors."""
        async def run_test():
            import httpx

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = httpx.RequestError("Connection failed")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await list_tilesets()

                assert "error" in result

        asyncio.run(run_test())


class TestGetTileset:
    """Tests for get_tileset function."""

    def test_get_tileset_returns_dict(self):
        """get_tileset should return tileset details."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "550e8400-e29b-41d4-a716-446655440099",
                "name": "Test Tileset",
                "type": "vector",
                "format": "pbf",
                "min_zoom": 0,
                "max_zoom": 14,
                "bounds": [139.5, 35.5, 140.0, 36.0],
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_tileset("550e8400-e29b-41d4-a716-446655440099")

                assert result["id"] == "550e8400-e29b-41d4-a716-446655440099"
                assert result["name"] == "Test Tileset"

        asyncio.run(run_test())

    def test_get_tileset_not_found(self):
        """get_tileset should handle 404 errors."""
        async def run_test():
            import httpx

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.text = "Not found"
                mock_instance.get.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_tileset("nonexistent-id")

                assert "error" in result

        asyncio.run(run_test())


class TestGetTilesetTilejson:
    """Tests for get_tileset_tilejson function."""

    def test_get_tileset_tilejson_returns_dict(self):
        """get_tileset_tilejson should return TileJSON."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "tilejson": "2.2.0",
                "tiles": ["https://example.com/tiles/{z}/{x}/{y}.pbf"],
                "bounds": [139.5, 35.5, 140.0, 36.0],
                "minzoom": 0,
                "maxzoom": 14,
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_tileset_tilejson("550e8400-e29b-41d4-a716-446655440099")

                assert "tiles" in result or "tilejson" in result

        asyncio.run(run_test())


class TestSearchFeatures:
    """Tests for search_features function."""

    def test_search_features_returns_dict(self):
        """search_features should return features."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "features": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440004",
                        "geometry": {"type": "Point", "coordinates": [139.7, 35.6]},
                        "properties": {"name": "Point 1"},
                    },
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440005",
                        "geometry": {"type": "Point", "coordinates": [139.8, 35.7]},
                        "properties": {"name": "Point 2"},
                    },
                ]
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features()

                assert "features" in result
                assert result["count"] == 2

        asyncio.run(run_test())

    def test_search_features_with_bbox(self):
        """search_features should accept bbox parameter."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features(bbox="139.5,35.5,140.0,36.0")

                assert result is not None
                assert result["query"]["bbox"] == "139.5,35.5,140.0,36.0"

        asyncio.run(run_test())

    def test_search_features_with_tileset_filter(self):
        """search_features should filter by tileset_id."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features(tileset_id="550e8400-e29b-41d4-a716-446655440097")

                assert result["query"]["tileset_id"] == "550e8400-e29b-41d4-a716-446655440097"

        asyncio.run(run_test())

    def test_search_features_with_layer_filter(self):
        """search_features should filter by layer."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features(layer="roads")

                assert result["query"]["layer"] == "roads"

        asyncio.run(run_test())

    def test_search_features_with_property_filter(self):
        """search_features should accept property filter."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features(filter="type=station")

                assert result["query"]["filter"] == "type=station"

        asyncio.run(run_test())

    def test_search_features_with_limit(self):
        """search_features should respect limit parameter."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"features": [{"id": "1"}] * 50}
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features(limit=50)

                assert result["query"]["limit"] == 50

        asyncio.run(run_test())


class TestGetFeature:
    """Tests for get_feature function."""

    def test_get_feature_returns_dict(self):
        """get_feature should return feature details."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "550e8400-e29b-41d4-a716-446655440098",
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [139.7, 35.6]},
                "properties": {"name": "Test Point"},
                "layer_name": "points",
                "tileset_id": "tileset-id",
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_feature("550e8400-e29b-41d4-a716-446655440098")

                assert result["id"] == "550e8400-e29b-41d4-a716-446655440098"
                assert "geometry" in result
                assert "properties" in result

        asyncio.run(run_test())

    def test_get_feature_not_found(self):
        """get_feature should handle 404 errors."""
        async def run_test():
            import httpx

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.text = "Not found"
                mock_instance.get.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_feature("nonexistent")

                assert "error" in result

        asyncio.run(run_test())


class TestGetFeaturesInTile:
    """Tests for get_features_in_tile function."""

    def test_get_features_in_tile(self):
        """get_features_in_tile should return features in tile extent."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "features": [
                    {"id": "550e8400-e29b-41d4-a716-446655440004", "geometry": {"type": "Point", "coordinates": [139.76, 35.68]}},
                ]
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_features_in_tile(
                    tileset_id="550e8400-e29b-41d4-a716-446655440097",
                    z=14,
                    x=14546,
                    y=6454,
                )

                assert "features" in result
                assert "tile" in result
                assert result["tile"]["z"] == 14
                assert result["tile"]["x"] == 14546
                assert result["tile"]["y"] == 6454

        asyncio.run(run_test())

    def test_get_features_in_tile_with_layer(self):
        """get_features_in_tile should filter by layer."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_features_in_tile(
                    tileset_id="550e8400-e29b-41d4-a716-446655440097",
                    z=10,
                    x=906,
                    y=404,
                    layer="buildings",
                )

                assert result is not None

        asyncio.run(run_test())


class TestErrorHandling:
    """Tests for error handling in tools."""

    def test_invalid_tileset_id_handled(self):
        """Invalid tileset ID should be handled gracefully."""
        async def run_test():
            import httpx

            with patch("tools.tilesets.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.text = "Invalid UUID"
                mock_instance.get.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_tileset("not-a-valid-uuid")

                assert "error" in result

        asyncio.run(run_test())

    def test_invalid_bbox_handled(self):
        """Invalid bbox should be handled gracefully."""
        async def run_test():
            import httpx

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.text = "Invalid bbox"
                mock_instance.get.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features(bbox="invalid")

                assert "error" in result

        asyncio.run(run_test())


class TestIntegration:
    """Integration tests combining multiple tools."""

    @pytest.mark.skip(reason="Complex async mock setup needs refactoring")
    def test_full_workflow(self):
        """Test listing tilesets, getting details, and searching features."""
        async def run_test():
            # Mock responses - use Mock for response objects with json() as Mock
            list_response = Mock()
            list_response.json = Mock(return_value=[
                {"id": "tileset-1", "name": "Test Tileset", "type": "vector"}
            ])
            list_response.raise_for_status = Mock()

            detail_response = Mock()
            detail_response.json = Mock(return_value={
                "id": "tileset-1",
                "name": "Test Tileset",
                "type": "vector",
                "bounds": [139.5, 35.5, 140.0, 36.0],
            })
            detail_response.raise_for_status = Mock()

            features_response = Mock()
            features_response.json = Mock(return_value={
                "features": [
                    {"id": "550e8400-e29b-41d4-a716-446655440004", "geometry": {"type": "Point", "coordinates": [139.7, 35.6]}}
                ]
            })
            features_response.raise_for_status = Mock()

            with patch("tools.tilesets.httpx.AsyncClient") as mock_tilesets, \
                 patch("tools.features.httpx.AsyncClient") as mock_features:

                # Setup tileset mocks - AsyncMock for get with side_effect
                mock_ts_instance = AsyncMock()
                mock_ts_instance.get = AsyncMock(side_effect=[list_response, detail_response])
                mock_ts_instance.__aenter__.return_value = mock_ts_instance
                mock_ts_instance.__aexit__.return_value = None
                mock_tilesets.return_value = mock_ts_instance

                # Setup features mock
                mock_feat_instance = AsyncMock()
                mock_feat_instance.get = AsyncMock(return_value=features_response)
                mock_feat_instance.__aenter__.return_value = mock_feat_instance
                mock_feat_instance.__aexit__.return_value = None
                mock_features.return_value = mock_feat_instance

                # Step 1: List tilesets
                tilesets = await list_tilesets()
                assert tilesets["count"] >= 1

                # Step 2: Get tileset details
                tileset_id = tilesets["tilesets"][0]["id"]
                details = await get_tileset(tileset_id)
                assert details["id"] == tileset_id

                # Step 3: Search features in that tileset
                features = await search_features(tileset_id=tileset_id)
                assert "features" in features

        asyncio.run(run_test())
