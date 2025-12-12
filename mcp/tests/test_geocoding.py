"""
Tests for geocoding tools
"""

import pytest
from tools.geocoding import geocode, reverse_geocode


class TestGeocode:
    """Tests for geocode function"""

    @pytest.mark.asyncio
    async def test_geocode_tokyo_station(self):
        """Test geocoding for Tokyo Station"""
        result = await geocode("東京駅", limit=1)
        
        assert "results" in result
        assert "count" in result
        assert "query" in result
        assert result["query"] == "東京駅"
        
        # Should find at least one result
        if result["count"] > 0:
            location = result["results"][0]
            assert "latitude" in location
            assert "longitude" in location
            assert "name" in location
            
            # Tokyo Station should be around these coordinates
            assert 35.5 < location["latitude"] < 35.8
            assert 139.5 < location["longitude"] < 140.0

    @pytest.mark.asyncio
    async def test_geocode_with_country_filter(self):
        """Test geocoding with country filter"""
        result = await geocode("Tokyo", country_codes="jp", limit=3)
        
        assert "results" in result
        assert result["count"] <= 3

    @pytest.mark.asyncio
    async def test_geocode_empty_query(self):
        """Test geocoding with empty query"""
        result = await geocode("", limit=1)
        
        assert "results" in result
        # Empty query may return no results or error

    @pytest.mark.asyncio
    async def test_geocode_nonexistent_place(self):
        """Test geocoding for nonexistent place"""
        result = await geocode("asdfjkl12345nonexistent", limit=1)
        
        assert "results" in result
        assert result["count"] == 0


class TestReverseGeocode:
    """Tests for reverse_geocode function"""

    @pytest.mark.asyncio
    async def test_reverse_geocode_tokyo_station(self):
        """Test reverse geocoding for Tokyo Station coordinates"""
        # Tokyo Station coordinates
        result = await reverse_geocode(
            latitude=35.6812,
            longitude=139.7671,
        )
        
        assert "display_name" in result
        assert "coordinates" in result
        assert result["coordinates"]["latitude"] == 35.6812
        assert result["coordinates"]["longitude"] == 139.7671
        
        # Should return address in Japan
        if result["display_name"]:
            # The result should contain Japanese text or "Japan"
            assert "address" in result or result["display_name"]

    @pytest.mark.asyncio
    async def test_reverse_geocode_with_zoom(self):
        """Test reverse geocoding with different zoom levels"""
        # City level (zoom=10)
        result_city = await reverse_geocode(
            latitude=35.6812,
            longitude=139.7671,
            zoom=10,
        )
        
        # Building level (zoom=18)
        result_building = await reverse_geocode(
            latitude=35.6812,
            longitude=139.7671,
            zoom=18,
        )
        
        assert "display_name" in result_city
        assert "display_name" in result_building

    @pytest.mark.asyncio
    async def test_reverse_geocode_ocean(self):
        """Test reverse geocoding for ocean coordinates"""
        # Middle of Pacific Ocean
        result = await reverse_geocode(
            latitude=0.0,
            longitude=-160.0,
        )
        
        # Should return error or empty result for ocean
        assert "coordinates" in result


class TestGeocodingIntegration:
    """Integration tests for geocoding tools"""

    @pytest.mark.asyncio
    async def test_geocode_then_reverse(self):
        """Test geocoding followed by reverse geocoding"""
        # First, geocode an address
        geocode_result = await geocode("東京タワー", limit=1)
        
        if geocode_result["count"] > 0:
            location = geocode_result["results"][0]
            
            # Then, reverse geocode the coordinates
            reverse_result = await reverse_geocode(
                latitude=location["latitude"],
                longitude=location["longitude"],
            )
            
            assert "display_name" in reverse_result
            # The reverse result should be in Japan
            if reverse_result.get("address"):
                assert reverse_result["address"].get("country_code") == "jp" or \
                       "Japan" in reverse_result.get("display_name", "") or \
                       "日本" in reverse_result.get("display_name", "")
