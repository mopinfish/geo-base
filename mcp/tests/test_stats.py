"""
Tests for statistics tools.

This module tests:
- get_tileset_stats
- get_feature_distribution
- get_layer_stats
- get_area_stats
- Helper functions
"""

import asyncio
import math
import pytest
from unittest.mock import AsyncMock, Mock, patch

from tools.stats import (
    get_tileset_stats,
    get_feature_distribution,
    get_layer_stats,
    get_area_stats,
    _parse_bbox,
    _calculate_bbox_area_km2,
    _extract_geometry_type,
    _count_coordinates,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_parse_bbox_valid(self):
        """_parse_bbox should parse valid bbox string."""
        result = _parse_bbox("139.5,35.5,140.0,36.0")
        assert result == (139.5, 35.5, 140.0, 36.0)

    def test_parse_bbox_with_spaces(self):
        """_parse_bbox should handle spaces."""
        result = _parse_bbox("139.5, 35.5, 140.0, 36.0")
        assert result == (139.5, 35.5, 140.0, 36.0)

    def test_parse_bbox_invalid(self):
        """_parse_bbox should return None for invalid input."""
        assert _parse_bbox("invalid") is None
        assert _parse_bbox("1,2,3") is None
        assert _parse_bbox("") is None
        assert _parse_bbox(None) is None

    def test_calculate_bbox_area_tokyo(self):
        """_calculate_bbox_area_km2 should calculate reasonable area for Tokyo."""
        # Tokyo station area (roughly 0.5 degree square)
        area = _calculate_bbox_area_km2(139.5, 35.5, 140.0, 36.0)
        # Should be roughly 2000-3000 km²
        assert 2000 < area < 3500

    def test_calculate_bbox_area_small(self):
        """_calculate_bbox_area_km2 should work for small areas."""
        # Very small area (0.01 degree square)
        area = _calculate_bbox_area_km2(139.76, 35.68, 139.77, 35.69)
        # Should be roughly 1 km²
        assert 0.5 < area < 2.0

    def test_extract_geometry_type_point(self):
        """_extract_geometry_type should extract Point type."""
        feature = {"geometry": {"type": "Point", "coordinates": [139.7, 35.6]}}
        assert _extract_geometry_type(feature) == "Point"

    def test_extract_geometry_type_polygon(self):
        """_extract_geometry_type should extract Polygon type."""
        feature = {"geometry": {"type": "Polygon", "coordinates": [[]]}}
        assert _extract_geometry_type(feature) == "Polygon"

    def test_extract_geometry_type_geom_field(self):
        """_extract_geometry_type should handle 'geom' field."""
        feature = {"geom": {"type": "LineString", "coordinates": []}}
        assert _extract_geometry_type(feature) == "LineString"

    def test_extract_geometry_type_missing(self):
        """_extract_geometry_type should return Unknown for missing geometry."""
        feature = {}
        assert _extract_geometry_type(feature) == "Unknown"

    def test_count_coordinates_point(self):
        """_count_coordinates should count 1 for Point."""
        feature = {"geometry": {"type": "Point", "coordinates": [139.7, 35.6]}}
        assert _count_coordinates(feature) == 1

    def test_count_coordinates_linestring(self):
        """_count_coordinates should count LineString coordinates."""
        feature = {
            "geometry": {
                "type": "LineString",
                "coordinates": [[0, 0], [1, 1], [2, 2]]
            }
        }
        assert _count_coordinates(feature) == 3

    def test_count_coordinates_polygon(self):
        """_count_coordinates should count Polygon coordinates."""
        feature = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            }
        }
        assert _count_coordinates(feature) == 5


class TestGetTilesetStats:
    """Tests for get_tileset_stats function."""

    def test_successful_stats(self):
        """get_tileset_stats should return comprehensive statistics."""
        async def run_test():
            tileset_data = {
                "id": "test-id",
                "name": "Test Tileset",
                "type": "vector",
                "min_zoom": 0,
                "max_zoom": 14,
                "bounds": [139.5, 35.5, 140.0, 36.0],
            }

            features_data = {
                "features": [
                    {
                        "id": "f1",
                        "geometry": {"type": "Point", "coordinates": [139.7, 35.6]},
                        "layer_name": "points",
                    },
                    {
                        "id": "f2",
                        "geometry": {"type": "Point", "coordinates": [139.8, 35.7]},
                        "layer_name": "points",
                    },
                    {
                        "id": "f3",
                        "geometry": {"type": "Polygon", "coordinates": [[]]},
                        "layer_name": "areas",
                    },
                ]
            }

            mock_tileset_response = Mock()
            mock_tileset_response.json.return_value = tileset_data
            mock_tileset_response.raise_for_status = Mock()

            mock_features_response = Mock()
            mock_features_response.json.return_value = features_data
            mock_features_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = [
                    mock_tileset_response,
                    mock_features_response,
                ]
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_tileset_stats("test-id")

                assert result["tileset_id"] == "test-id"
                assert result["tileset_name"] == "Test Tileset"
                assert result["feature_count"] == 3
                assert result["geometry_types"]["Point"] == 2
                assert result["geometry_types"]["Polygon"] == 1
                assert "points" in result["layers"]
                assert "areas" in result["layers"]

        asyncio.run(run_test())

    def test_stats_with_error(self):
        """get_tileset_stats should handle errors gracefully."""
        async def run_test():
            import httpx

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
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

                result = await get_tileset_stats("nonexistent-id")

                assert "error" in result

        asyncio.run(run_test())


class TestGetFeatureDistribution:
    """Tests for get_feature_distribution function."""

    def test_distribution_calculation(self):
        """get_feature_distribution should calculate correct percentages."""
        async def run_test():
            features_data = {
                "features": [
                    {"geometry": {"type": "Point"}},
                    {"geometry": {"type": "Point"}},
                    {"geometry": {"type": "Point"}},
                    {"geometry": {"type": "Polygon"}},
                ]
            }

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_feature_distribution()

                assert result["total_features"] == 4
                assert result["geometry_types"]["Point"] == 3
                assert result["geometry_types"]["Polygon"] == 1
                assert result["percentages"]["Point"] == 75.0
                assert result["percentages"]["Polygon"] == 25.0

        asyncio.run(run_test())

    def test_distribution_with_tileset_filter(self):
        """get_feature_distribution should pass tileset_id to API."""
        async def run_test():
            features_data = {"features": []}

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_feature_distribution(tileset_id="test-123")

                # Check that tileset_id was in the query
                assert result["query"]["tileset_id"] == "test-123"

        asyncio.run(run_test())


class TestGetLayerStats:
    """Tests for get_layer_stats function."""

    def test_layer_grouping(self):
        """get_layer_stats should group features by layer."""
        async def run_test():
            features_data = {
                "features": [
                    {"layer_name": "roads", "geometry": {"type": "LineString"}, "properties": {"name": "Main St"}},
                    {"layer_name": "roads", "geometry": {"type": "LineString"}, "properties": {"name": "Oak Ave"}},
                    {"layer_name": "buildings", "geometry": {"type": "Polygon"}, "properties": {"height": 10}},
                ]
            }

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_layer_stats("test-tileset")

                assert result["layer_count"] == 2
                assert result["layers"]["roads"]["feature_count"] == 2
                assert result["layers"]["buildings"]["feature_count"] == 1
                assert "name" in result["layers"]["roads"]["property_keys"]
                assert "height" in result["layers"]["buildings"]["property_keys"]

        asyncio.run(run_test())

    def test_default_layer(self):
        """get_layer_stats should use 'default' for features without layer."""
        async def run_test():
            features_data = {
                "features": [
                    {"geometry": {"type": "Point"}},  # No layer_name
                ]
            }

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_layer_stats("test-tileset")

                assert "default" in result["layers"]

        asyncio.run(run_test())


class TestGetAreaStats:
    """Tests for get_area_stats function."""

    def test_area_calculation(self):
        """get_area_stats should calculate area and density."""
        async def run_test():
            features_data = {
                "features": [
                    {"geometry": {"type": "Point"}, "layer_name": "points"},
                    {"geometry": {"type": "Point"}, "layer_name": "points"},
                ]
            }

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_area_stats("139.5,35.5,140.0,36.0")

                assert "area_km2" in result
                assert result["area_km2"] > 0
                assert result["feature_count"] == 2
                assert "density" in result
                assert "features_per_km2" in result["density"]
                assert "points" in result["layers"]

        asyncio.run(run_test())

    def test_invalid_bbox(self):
        """get_area_stats should return error for invalid bbox."""
        async def run_test():
            result = await get_area_stats("invalid-bbox")

            assert "error" in result
            assert "VALIDATION_ERROR" in result.get("code", "")

        asyncio.run(run_test())

    def test_bbox_parsing(self):
        """get_area_stats should correctly parse bbox."""
        async def run_test():
            features_data = {"features": []}

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_area_stats("139.5,35.5,140.0,36.0")

                assert result["bbox"]["min_lng"] == 139.5
                assert result["bbox"]["min_lat"] == 35.5
                assert result["bbox"]["max_lng"] == 140.0
                assert result["bbox"]["max_lat"] == 36.0

        asyncio.run(run_test())

    def test_with_tileset_filter(self):
        """get_area_stats should filter by tileset_id."""
        async def run_test():
            features_data = {"features": []}

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.stats.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_area_stats(
                    bbox="139.5,35.5,140.0,36.0",
                    tileset_id="test-123",
                )

                assert result["query"]["tileset_id"] == "test-123"

        asyncio.run(run_test())
