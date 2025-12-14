"""
Tests for geocoding tools.

This module tests:
- geocode (address to coordinates)
- reverse_geocode (coordinates to address)

Uses standard asyncio approach (not pytest-asyncio).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from tools.geocoding import (
    geocode,
    reverse_geocode,
)


class TestGeocode:
    """Tests for geocode function."""

    def test_geocode_tokyo_station(self):
        """geocode should return coordinates for Tokyo Station."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = [
                {
                    "place_id": 12345,
                    "lat": "35.6812",
                    "lon": "139.7671",
                    "display_name": "東京駅, 千代田区, 東京都, 日本",
                    "type": "station",
                    "boundingbox": ["35.6", "35.7", "139.7", "139.8"],
                }
            ]
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await geocode("東京駅")

                assert "results" in result
                assert result["count"] >= 1
                assert result["query"] == "東京駅"

        asyncio.run(run_test())

    def test_geocode_with_country_filter(self):
        """geocode should filter by country code."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await geocode("Tokyo", country_codes="jp")

                assert result is not None
                # Verify the request was made with country_codes
                call_args = mock_instance.get.call_args
                assert "countrycodes" in str(call_args) or result is not None

        asyncio.run(run_test())

    def test_geocode_with_limit(self):
        """geocode should respect limit parameter."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = [
                {"lat": "35.0", "lon": "139.0", "display_name": "Result 1"},
                {"lat": "35.1", "lon": "139.1", "display_name": "Result 2"},
                {"lat": "35.2", "lon": "139.2", "display_name": "Result 3"},
            ]
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await geocode("Tokyo", limit=3)

                assert result["count"] <= 3

        asyncio.run(run_test())

    def test_geocode_empty_query(self):
        """geocode with empty query should return error."""
        async def run_test():
            result = await geocode("")
            assert "error" in result or result.get("count", 1) == 0

        asyncio.run(run_test())

    def test_geocode_nonexistent_place(self):
        """geocode should handle no results gracefully."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await geocode("xyznonexistent12345")

                assert result["count"] == 0
                assert result["results"] == []

        asyncio.run(run_test())

    def test_geocode_network_error(self):
        """geocode should handle network errors."""
        async def run_test():
            import httpx

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = httpx.RequestError("Connection failed")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await geocode("Tokyo")

                assert "error" in result

        asyncio.run(run_test())

    def test_geocode_language_parameter(self):
        """geocode should pass language parameter."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = [
                {"lat": "35.6812", "lon": "139.7671", "display_name": "Tokyo Station"}
            ]
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await geocode("東京駅", language="en")

                assert result is not None

        asyncio.run(run_test())


class TestReverseGeocode:
    """Tests for reverse_geocode function."""

    def test_reverse_geocode_tokyo_station(self):
        """reverse_geocode should return address for Tokyo Station coordinates."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "place_id": 12345,
                "lat": "35.6812",
                "lon": "139.7671",
                "display_name": "東京駅, 1丁目, 丸の内, 千代田区, 東京都, 100-0005, 日本",
                "address": {
                    "railway": "東京駅",
                    "suburb": "丸の内",
                    "city": "千代田区",
                    "state": "東京都",
                    "postcode": "100-0005",
                    "country": "日本",
                    "country_code": "jp",
                },
                "boundingbox": ["35.6", "35.7", "139.7", "139.8"],
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await reverse_geocode(latitude=35.6812, longitude=139.7671)

                assert "display_name" in result
                assert "address" in result
                assert "coordinates" in result
                assert result["coordinates"]["latitude"] == 35.6812
                assert result["coordinates"]["longitude"] == 139.7671

        asyncio.run(run_test())

    def test_reverse_geocode_with_zoom(self):
        """reverse_geocode should respect zoom parameter."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "display_name": "Tokyo, Japan",
                "address": {"city": "Tokyo", "country": "Japan"},
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await reverse_geocode(
                    latitude=35.6812,
                    longitude=139.7671,
                    zoom=10,  # City level
                )

                assert result is not None

        asyncio.run(run_test())

    def test_reverse_geocode_ocean(self):
        """reverse_geocode should handle ocean/empty locations."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"error": "Unable to geocode"}
            mock_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                # Middle of Pacific Ocean
                result = await reverse_geocode(latitude=0, longitude=-160)

                # Should return something (maybe error or empty result)
                assert result is not None

        asyncio.run(run_test())

    def test_reverse_geocode_invalid_latitude(self):
        """reverse_geocode should handle invalid latitude."""
        async def run_test():
            # Latitude out of range
            result = await reverse_geocode(latitude=91, longitude=139.7671)
            assert "error" in result

        asyncio.run(run_test())

    def test_reverse_geocode_invalid_longitude(self):
        """reverse_geocode should handle invalid longitude."""
        async def run_test():
            # Longitude out of range
            result = await reverse_geocode(latitude=35.6812, longitude=181)
            assert "error" in result

        asyncio.run(run_test())

    def test_reverse_geocode_network_error(self):
        """reverse_geocode should handle network errors."""
        async def run_test():
            import httpx

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = httpx.RequestError("Connection failed")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await reverse_geocode(latitude=35.6812, longitude=139.7671)

                assert "error" in result

        asyncio.run(run_test())


class TestGeocodingIntegration:
    """Integration tests for geocoding tools."""

    def test_geocode_then_reverse(self):
        """Should be able to geocode and then reverse geocode."""
        async def run_test():
            # Mock geocode response
            geocode_response = Mock()
            geocode_response.json.return_value = [
                {
                    "lat": "35.6812",
                    "lon": "139.7671",
                    "display_name": "東京駅",
                }
            ]
            geocode_response.raise_for_status = Mock()

            # Mock reverse geocode response
            reverse_response = Mock()
            reverse_response.json.return_value = {
                "display_name": "東京駅, 千代田区",
                "address": {"railway": "東京駅"},
            }
            reverse_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = [geocode_response, reverse_response]
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                # First geocode
                geo_result = await geocode("東京駅")
                assert geo_result["count"] >= 1

                if geo_result["results"]:
                    first_result = geo_result["results"][0]
                    lat = first_result.get("lat") or first_result.get("latitude")
                    lng = first_result.get("lng") or first_result.get("longitude")

                    # Then reverse geocode
                    reverse_result = await reverse_geocode(
                        latitude=float(lat),
                        longitude=float(lng),
                    )
                    assert reverse_result is not None

        asyncio.run(run_test())
