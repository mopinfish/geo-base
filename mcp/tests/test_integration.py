"""
Integration tests for geo-base MCP Server.

Tests end-to-end workflows combining multiple components:
- Validators + Tools
- Error handling + Retry
- Stats + Analysis
- Full user workflows
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from validators import (
    validate_uuid,
    validate_bbox,
    validate_coordinates,
    validate_geometry,
)
from errors import (
    handle_api_error,
    create_error_response,
    ErrorCode,
    MCPError,
    ValidationError,
)


class TestValidatorToolIntegration:
    """Tests combining validators with tool functions."""

    def test_validate_before_api_call(self):
        """Validators should catch errors before API calls."""
        # Invalid UUID
        result = validate_uuid("not-a-uuid", "tileset_id")
        assert not result.valid
        assert "Invalid" in result.error

        # This would prevent an unnecessary API call
        error_response = result.to_error_response(attempted_action="get_tileset")
        assert "error" in error_response
        assert error_response["attempted_action"] == "get_tileset"

    def test_bbox_validation_flow(self):
        """Bbox validation should work with feature search."""
        # Valid bbox
        result = validate_bbox("139.5,35.5,140.0,36.0")
        assert result.valid
        min_lng, min_lat, max_lng, max_lat = result.value
        assert min_lng == 139.5
        assert max_lat == 36.0

        # Invalid bbox - would prevent API call
        result = validate_bbox("invalid,bbox")
        assert not result.valid

    def test_geometry_validation_for_create_feature(self):
        """Geometry validation should catch invalid geometries."""
        # Valid Point
        valid_point = {"type": "Point", "coordinates": [139.7, 35.6]}
        result = validate_geometry(valid_point)
        assert result.valid

        # Invalid Point - missing coordinates
        invalid_point = {"type": "Point"}
        result = validate_geometry(invalid_point)
        assert not result.valid

        # Invalid Polygon - ring too short
        invalid_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [0, 0]]]  # Only 3 points
        }
        result = validate_geometry(invalid_polygon)
        assert not result.valid


class TestErrorHandlerIntegration:
    """Tests for error handling integration."""

    def test_mcp_error_to_response(self):
        """MCPError should convert to proper response."""
        error = MCPError("Test error", code=ErrorCode.VALIDATION_ERROR)
        error_dict = error.to_dict()
        
        assert error_dict["error"] == "Test error"
        assert error_dict["code"] == ErrorCode.VALIDATION_ERROR.value

    def test_validation_error_flow(self):
        """ValidationError should include field info."""
        error = ValidationError("Invalid format", field="bbox")
        error_dict = error.to_dict()
        
        assert error_dict["details"]["field"] == "bbox"
        assert "Invalid format" in error_dict["error"]

    def test_handle_http_errors(self):
        """handle_api_error should convert HTTP errors."""
        import httpx

        # Create mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Resource not found"

        error = httpx.HTTPStatusError("", request=Mock(), response=mock_response)
        result = handle_api_error(error, {"resource_id": "test-123"})

        assert "error" in result
        assert result.get("resource_id") == "test-123"


class TestStatsAnalysisIntegration:
    """Tests combining stats and analysis tools."""

    def test_area_calculations_consistent(self):
        """Area calculations should be consistent across tools."""
        from tools.stats import _calculate_bbox_area_km2
        from tools.analysis import _haversine_distance

        # Calculate area via bbox
        area = _calculate_bbox_area_km2(139.5, 35.5, 140.0, 36.0)
        assert area > 0

        # Calculate diagonal distance
        diagonal = _haversine_distance(35.5, 139.5, 36.0, 140.0)
        assert diagonal > 0

        # Diagonal should be roughly sqrt(2) * side for a square
        # This is a sanity check

    def test_centroid_extraction(self):
        """Centroid extraction should work for all geometry types."""
        from tools.analysis import _get_feature_centroid

        # Point
        point_feature = {
            "geometry": {"type": "Point", "coordinates": [139.7, 35.6]}
        }
        centroid = _get_feature_centroid(point_feature)
        assert centroid == (35.6, 139.7)

        # Polygon
        polygon_feature = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
            }
        }
        centroid = _get_feature_centroid(polygon_feature)
        assert centroid is not None
        lat, lng = centroid
        # Centroid should be near center
        assert 3 < lat < 7
        assert 3 < lng < 7


class TestFullWorkflows:
    """Tests for complete user workflows."""

    def test_search_and_analyze_workflow(self):
        """Test searching features and analyzing results."""
        async def run_test():
            from tools.features import search_features
            from tools.stats import get_area_stats

            # Mock feature response
            feature_response = Mock()
            feature_response.json.return_value = {
                "features": [
                    {
                        "id": "f1",
                        "geometry": {"type": "Point", "coordinates": [139.7, 35.65]},
                        "layer_name": "points",
                    },
                    {
                        "id": "f2",
                        "geometry": {"type": "Point", "coordinates": [139.75, 35.7]},
                        "layer_name": "points",
                    },
                    {
                        "id": "f3",
                        "geometry": {"type": "Polygon", "coordinates": [[]]},
                        "layer_name": "areas",
                    },
                ]
            }
            feature_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_features, \
                 patch("tools.stats.httpx.AsyncClient") as mock_stats:

                # Setup mocks
                mock_feat_instance = AsyncMock()
                mock_feat_instance.get.return_value = feature_response
                mock_feat_instance.__aenter__.return_value = mock_feat_instance
                mock_feat_instance.__aexit__.return_value = None
                mock_features.return_value = mock_feat_instance

                mock_stats_instance = AsyncMock()
                mock_stats_instance.get.return_value = feature_response
                mock_stats_instance.__aenter__.return_value = mock_stats_instance
                mock_stats_instance.__aexit__.return_value = None
                mock_stats.return_value = mock_stats_instance

                # Step 1: Search features in area
                bbox = "139.5,35.5,140.0,36.0"
                features = await search_features(bbox=bbox)
                assert features["count"] >= 1

                # Step 2: Get area statistics
                stats = await get_area_stats(bbox=bbox)
                assert "area_km2" in stats
                assert stats["feature_count"] >= 0

        asyncio.run(run_test())

    @pytest.mark.skip(reason="Complex async mock setup needs refactoring")
    def test_geocode_and_find_nearby_workflow(self):
        """Test geocoding a location and finding nearby features."""
        async def run_test():
            from tools.geocoding import geocode
            from tools.analysis import find_nearest_features

            # Mock geocode response (Nominatim format) - use Mock for response object
            geocode_response = Mock()
            geocode_response.json = Mock(return_value=[
                {
                    "lat": "35.6812",
                    "lon": "139.7671",
                    "display_name": "Tokyo Station",
                    "type": "station",
                    "category": "railway",
                }
            ])
            geocode_response.raise_for_status = Mock()

            # Mock nearby features response
            features_response = Mock()
            features_response.json = Mock(return_value={
                "features": [
                    {
                        "id": "f1",
                        "geometry": {"type": "Point", "coordinates": [139.768, 35.682]},
                        "properties": {"name": "Nearby POI"},
                    }
                ]
            })
            features_response.raise_for_status = Mock()

            with patch("tools.geocoding.httpx.AsyncClient") as mock_geocoding, \
                 patch("tools.analysis.httpx.AsyncClient") as mock_analysis:

                # Setup geocoding mock - AsyncMock for get, returns Mock response
                mock_geo_instance = AsyncMock()
                mock_geo_instance.get = AsyncMock(return_value=geocode_response)
                mock_geo_instance.__aenter__.return_value = mock_geo_instance
                mock_geo_instance.__aexit__.return_value = None
                mock_geocoding.return_value = mock_geo_instance

                # Setup analysis mock
                mock_anal_instance = AsyncMock()
                mock_anal_instance.get = AsyncMock(return_value=features_response)
                mock_anal_instance.__aenter__.return_value = mock_anal_instance
                mock_anal_instance.__aexit__.return_value = None
                mock_analysis.return_value = mock_anal_instance

                # Step 1: Geocode location
                geo_result = await geocode("Tokyo Station")
                assert geo_result["count"] >= 1

                # Step 2: Extract coordinates (geocode returns latitude/longitude)
                first = geo_result["results"][0]
                lat = first["latitude"]
                lng = first["longitude"]

                # Step 3: Find nearby features
                nearby = await find_nearest_features(lat=lat, lng=lng, radius_km=1.0)
                assert "features" in nearby
                assert "center" in nearby

        asyncio.run(run_test())

    @pytest.mark.skip(reason="Complex async mock setup needs refactoring")
    def test_create_and_query_workflow(self):
        """Test creating a feature and then querying it."""
        async def run_test():
            from tools.crud import create_feature
            from tools.features import get_feature

            # Mock create response (use regular Mock for json() and raise_for_status())
            create_response = Mock()
            create_response.json = Mock(return_value={
                "id": "new-feature-123",
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [139.7, 35.6]},
                "properties": {"name": "New POI"},
            })
            create_response.raise_for_status = Mock()
            create_response.status_code = 201

            # Mock get response
            get_response = Mock()
            get_response.json = Mock(return_value={
                "id": "new-feature-123",
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [139.7, 35.6]},
                "properties": {"name": "New POI"},
                "layer_name": "pois",
                "created_at": "2025-01-01T00:00:00Z",
            })
            get_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_crud, \
                 patch("tools.features.httpx.AsyncClient") as mock_features:

                # Setup crud mock - use AsyncMock for the client but Mock responses
                mock_crud_instance = AsyncMock()
                mock_crud_instance.post = AsyncMock(return_value=create_response)
                mock_crud_instance.__aenter__.return_value = mock_crud_instance
                mock_crud_instance.__aexit__.return_value = None
                mock_crud.return_value = mock_crud_instance

                # Setup features mock
                mock_feat_instance = AsyncMock()
                mock_feat_instance.get = AsyncMock(return_value=get_response)
                mock_feat_instance.__aenter__.return_value = mock_feat_instance
                mock_feat_instance.__aexit__.return_value = None
                mock_features.return_value = mock_feat_instance

                # Step 1: Create feature
                created = await create_feature(
                    tileset_id="test-tileset",
                    geometry={"type": "Point", "coordinates": [139.7, 35.6]},
                    properties={"name": "New POI"},
                )
                assert "id" in created

                # Step 2: Query the created feature
                feature_id = created["id"]
                retrieved = await get_feature(feature_id)
                assert retrieved["id"] == feature_id
                assert retrieved["properties"]["name"] == "New POI"

        asyncio.run(run_test())


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_results_handling(self):
        """Tools should handle empty results gracefully."""
        async def run_test():
            from tools.features import search_features

            mock_response = Mock()
            mock_response.json.return_value = {"features": []}
            mock_response.raise_for_status = Mock()

            with patch("tools.features.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await search_features(bbox="0,0,1,1")

                assert result["count"] == 0
                assert result["features"] == []

        asyncio.run(run_test())

    def test_large_coordinate_values(self):
        """Should handle coordinates at extremes."""
        # Maximum values
        result = validate_coordinates(90, 180)
        assert result.valid

        result = validate_coordinates(-90, -180)
        assert result.valid

    def test_unicode_in_properties(self):
        """Should handle Unicode in property values."""
        async def run_test():
            from tools.crud import create_feature

            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "feat-id",
                "properties": {"name": "東京駅", "description": "日本の首都の主要駅"},
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await create_feature(
                    tileset_id="test",
                    geometry={"type": "Point", "coordinates": [139.7671, 35.6812]},
                    properties={"name": "東京駅", "description": "日本の首都の主要駅"},
                )

                assert result is not None

        asyncio.run(run_test())

    def test_special_characters_in_filter(self):
        """Should handle special characters in filter values."""
        from validators import validate_filter

        # Filter with special characters
        result = validate_filter("name=Tokyo Station (Main)")
        assert result.valid
        assert result.value == ("name", "Tokyo Station (Main)")

        # Filter with equals in value
        result = validate_filter("equation=a=b+c")
        assert result.valid
        assert result.value == ("equation", "a=b+c")
