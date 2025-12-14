"""
Tests for spatial analysis tools.

This module tests:
- analyze_area
- calculate_distance
- find_nearest_features
- get_buffer_zone_features
- Helper functions
"""

import asyncio
import math
import pytest
from unittest.mock import AsyncMock, Mock, patch

from tools.analysis import (
    analyze_area,
    calculate_distance,
    find_nearest_features,
    get_buffer_zone_features,
    _haversine_distance,
    _get_feature_centroid,
    _expand_bbox,
    _bearing_to_direction,
)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_haversine_distance_same_point(self):
        """Distance between same points should be 0."""
        result = _haversine_distance(35.6812, 139.7671, 35.6812, 139.7671)
        assert result == 0.0

    def test_haversine_distance_tokyo_to_osaka(self):
        """Distance from Tokyo to Osaka should be roughly 400km."""
        # Tokyo Station: 35.6812, 139.7671
        # Osaka Station: 34.7024, 135.4959
        result = _haversine_distance(35.6812, 139.7671, 34.7024, 135.4959)
        assert 390 < result < 410  # Approximately 400km

    def test_haversine_distance_short(self):
        """Short distance should be accurate."""
        # About 1km apart in Tokyo
        result = _haversine_distance(35.6812, 139.7671, 35.6902, 139.7671)
        assert 0.9 < result < 1.1  # Approximately 1km

    def test_get_feature_centroid_point(self):
        """Centroid of Point should return its coordinates."""
        feature = {
            "geometry": {
                "type": "Point",
                "coordinates": [139.7671, 35.6812]
            }
        }
        result = _get_feature_centroid(feature)
        assert result == (35.6812, 139.7671)

    def test_get_feature_centroid_polygon(self):
        """Centroid of Polygon should return average of ring coordinates."""
        feature = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
            }
        }
        result = _get_feature_centroid(feature)
        assert result is not None
        lat, lng = result
        # Average of 0, 0, 10, 10, 0 = 20/5 = 4.0
        assert 3.9 <= lat <= 4.1
        assert 3.9 <= lng <= 4.1

    def test_get_feature_centroid_empty(self):
        """Empty feature should return None."""
        feature = {}
        result = _get_feature_centroid(feature)
        assert result is None

    def test_expand_bbox(self):
        """expand_bbox should expand by buffer distance."""
        result = _expand_bbox(139.7, 35.6, 139.8, 35.7, 10)
        min_lng, min_lat, max_lng, max_lat = result
        
        # Should be expanded
        assert min_lng < 139.7
        assert min_lat < 35.6
        assert max_lng > 139.8
        assert max_lat > 35.7

    def test_bearing_to_direction_north(self):
        """0 degrees should be North."""
        assert _bearing_to_direction(0) == "N"

    def test_bearing_to_direction_east(self):
        """90 degrees should be East."""
        assert _bearing_to_direction(90) == "E"

    def test_bearing_to_direction_south(self):
        """180 degrees should be South."""
        assert _bearing_to_direction(180) == "S"

    def test_bearing_to_direction_west(self):
        """270 degrees should be West."""
        assert _bearing_to_direction(270) == "W"


class TestAnalyzeArea:
    """Tests for analyze_area function."""

    def test_successful_analysis(self):
        """analyze_area should return comprehensive analysis."""
        async def run_test():
            features_data = {
                "features": [
                    {
                        "id": "f1",
                        "geometry": {"type": "Point", "coordinates": [139.76, 35.68]},
                        "layer_name": "points",
                    },
                    {
                        "id": "f2",
                        "geometry": {"type": "Point", "coordinates": [139.77, 35.69]},
                        "layer_name": "points",
                    },
                ]
            }

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.analysis.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await analyze_area("139.5,35.5,140.0,36.0")

                assert "bbox" in result
                assert "area_km2" in result
                assert result["features"]["count"] == 2
                assert "density" in result
                assert "clustering" in result

        asyncio.run(run_test())

    def test_invalid_bbox(self):
        """analyze_area should return error for invalid bbox."""
        async def run_test():
            result = await analyze_area("invalid")
            assert "error" in result

        asyncio.run(run_test())

    def test_without_density(self):
        """analyze_area should skip density when disabled."""
        async def run_test():
            features_data = {"features": []}

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.analysis.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await analyze_area(
                    "139.5,35.5,140.0,36.0",
                    include_density=False,
                )

                assert "density" not in result

        asyncio.run(run_test())

    def test_without_clustering(self):
        """analyze_area should skip clustering when disabled."""
        async def run_test():
            features_data = {"features": []}

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.analysis.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await analyze_area(
                    "139.5,35.5,140.0,36.0",
                    include_clustering=False,
                )

                assert "clustering" not in result

        asyncio.run(run_test())


class TestCalculateDistance:
    """Tests for calculate_distance function."""

    def test_same_point_distance(self):
        """Distance between same points should be 0."""
        async def run_test():
            result = await calculate_distance(35.6812, 139.7671, 35.6812, 139.7671)

            assert result["distance_km"] == 0
            assert result["distance_m"] == 0

        asyncio.run(run_test())

    def test_distance_with_bearing(self):
        """Should return distance and bearing."""
        async def run_test():
            # North of Tokyo Station
            result = await calculate_distance(35.6812, 139.7671, 35.7812, 139.7671)

            assert result["distance_km"] > 0
            assert "bearing" in result
            assert "bearing_direction" in result
            # Should be roughly North
            assert result["bearing_direction"] == "N"

        asyncio.run(run_test())

    def test_invalid_latitude(self):
        """Should return error for invalid latitude."""
        async def run_test():
            result = await calculate_distance(91, 139.7671, 35.6812, 139.7671)
            assert "error" in result

        asyncio.run(run_test())

    def test_invalid_longitude(self):
        """Should return error for invalid longitude."""
        async def run_test():
            result = await calculate_distance(35.6812, 181, 35.6812, 139.7671)
            assert "error" in result

        asyncio.run(run_test())

    def test_distance_units(self):
        """Should return distance in multiple units."""
        async def run_test():
            result = await calculate_distance(35.6812, 139.7671, 35.7812, 139.7671)

            assert "distance_km" in result
            assert "distance_m" in result
            assert "distance_miles" in result
            # Verify conversion
            assert abs(result["distance_m"] - result["distance_km"] * 1000) < 1

        asyncio.run(run_test())


class TestFindNearestFeatures:
    """Tests for find_nearest_features function."""

    def test_successful_search(self):
        """find_nearest_features should return sorted features."""
        async def run_test():
            features_data = {
                "features": [
                    {
                        "id": "f1",
                        "geometry": {"type": "Point", "coordinates": [139.767, 35.681]},
                        "layer_name": "poi",
                        "properties": {"name": "Near"},
                    },
                    {
                        "id": "f2",
                        "geometry": {"type": "Point", "coordinates": [139.770, 35.685]},
                        "layer_name": "poi",
                        "properties": {"name": "Far"},
                    },
                ]
            }

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.analysis.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await find_nearest_features(
                    lat=35.6812, lng=139.7671, radius_km=1.0
                )

                assert "features" in result
                assert "count" in result
                # Should be sorted by distance
                if len(result["features"]) >= 2:
                    assert result["features"][0]["distance_km"] <= result["features"][1]["distance_km"]

        asyncio.run(run_test())

    def test_invalid_coordinates(self):
        """Should return error for invalid coordinates."""
        async def run_test():
            result = await find_nearest_features(lat=91, lng=139.7671)
            assert "error" in result

        asyncio.run(run_test())

    def test_with_tileset_filter(self):
        """Should pass tileset_id to query."""
        async def run_test():
            features_data = {"features": []}

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.analysis.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await find_nearest_features(
                    lat=35.6812, lng=139.7671, tileset_id="test-123"
                )

                assert result["query"]["tileset_id"] == "test-123"

        asyncio.run(run_test())


class TestGetBufferZoneFeatures:
    """Tests for get_buffer_zone_features function."""

    def test_successful_buffer_search(self):
        """get_buffer_zone_features should return features in ring."""
        async def run_test():
            features_data = {
                "features": [
                    {
                        "id": "f1",
                        "geometry": {"type": "Point", "coordinates": [139.78, 35.69]},
                        "layer_name": "poi",
                    },
                ]
            }

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.analysis.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_buffer_zone_features(
                    lat=35.6812, lng=139.7671,
                    inner_radius_km=0.5, outer_radius_km=2.0
                )

                assert "ring_area_km2" in result
                assert result["inner_radius_km"] == 0.5
                assert result["outer_radius_km"] == 2.0

        asyncio.run(run_test())

    def test_invalid_radius_order(self):
        """Should return error when inner >= outer."""
        async def run_test():
            result = await get_buffer_zone_features(
                lat=35.6812, lng=139.7671,
                inner_radius_km=2.0, outer_radius_km=1.0
            )
            assert "error" in result

        asyncio.run(run_test())

    def test_ring_area_calculation(self):
        """Should calculate ring area correctly."""
        async def run_test():
            features_data = {"features": []}

            mock_response = Mock()
            mock_response.json.return_value = features_data
            mock_response.raise_for_status = Mock()

            with patch("tools.analysis.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await get_buffer_zone_features(
                    lat=35.6812, lng=139.7671,
                    inner_radius_km=1.0, outer_radius_km=2.0
                )

                # Ring area should be pi * (2^2 - 1^2) = 3*pi ≈ 9.42 km²
                expected_area = math.pi * (4 - 1)
                assert abs(result["ring_area_km2"] - expected_area) < 0.1

        asyncio.run(run_test())
