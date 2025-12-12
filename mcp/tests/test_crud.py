"""
Tests for CRUD tools.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tools.crud import (
    create_tileset,
    update_tileset,
    delete_tileset,
    create_feature,
    update_feature,
    delete_feature,
)


def create_mock_response(status_code: int, json_data: dict | None = None):
    """Create a mock HTTP response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data or {}
    mock_response.text = str(json_data) if json_data else ""
    # raise_for_status should not raise for success codes
    if 200 <= status_code < 300:
        mock_response.raise_for_status = MagicMock()
    else:
        from httpx import HTTPStatusError
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )
    return mock_response


class TestCreateTileset:
    """Tests for create_tileset function."""

    @pytest.mark.asyncio
    async def test_create_tileset_success(self):
        """Test successful tileset creation."""
        mock_response_data = {
            "id": "test-uuid-123",
            "name": "Test Tileset",
            "description": "Test description",
            "type": "vector",
            "format": "pbf",
            "min_zoom": 0,
            "max_zoom": 14,
            "is_public": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = create_mock_response(201, mock_response_data)

            result = await create_tileset(
                name="Test Tileset",
                type="vector",
                format="pbf",
                description="Test description",
            )

            assert result["id"] == "test-uuid-123"
            assert result["name"] == "Test Tileset"

    @pytest.mark.asyncio
    async def test_create_tileset_auth_required(self):
        """Test tileset creation without auth."""
        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = create_mock_response(401)

            result = await create_tileset(
                name="Test",
                type="vector",
                format="pbf",
            )

            assert "error" in result
            assert "Authentication" in result["error"]


class TestUpdateTileset:
    """Tests for update_tileset function."""

    @pytest.mark.asyncio
    async def test_update_tileset_success(self):
        """Test successful tileset update."""
        mock_response_data = {
            "id": "test-uuid-123",
            "name": "Updated Name",
            "description": "Updated description",
            "type": "vector",
            "format": "pbf",
        }

        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.patch.return_value = create_mock_response(200, mock_response_data)

            result = await update_tileset(
                tileset_id="test-uuid-123",
                name="Updated Name",
            )

            assert result["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_tileset_not_found(self):
        """Test update non-existent tileset."""
        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.patch.return_value = create_mock_response(404)

            result = await update_tileset(
                tileset_id="non-existent",
                name="New Name",
            )

            assert "error" in result
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_update_tileset_no_fields(self):
        """Test update with no fields."""
        result = await update_tileset(tileset_id="test-uuid-123")

        assert "error" in result
        assert "No fields" in result["error"]


class TestDeleteTileset:
    """Tests for delete_tileset function."""

    @pytest.mark.asyncio
    async def test_delete_tileset_success(self):
        """Test successful tileset deletion."""
        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.delete.return_value = create_mock_response(204)

            result = await delete_tileset(tileset_id="test-uuid-123")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_tileset_not_found(self):
        """Test delete non-existent tileset."""
        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.delete.return_value = create_mock_response(404)

            result = await delete_tileset(tileset_id="non-existent")

            assert "error" in result


class TestCreateFeature:
    """Tests for create_feature function."""

    @pytest.mark.asyncio
    async def test_create_feature_success(self):
        """Test successful feature creation."""
        mock_response_data = {
            "id": "feature-uuid-123",
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [139.7671, 35.6812],
            },
            "properties": {
                "name": "Tokyo Station",
                "layer_name": "stations",
            },
        }

        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = create_mock_response(201, mock_response_data)

            result = await create_feature(
                tileset_id="tileset-uuid-123",
                geometry={
                    "type": "Point",
                    "coordinates": [139.7671, 35.6812],
                },
                properties={"name": "Tokyo Station"},
                layer_name="stations",
            )

            assert result["id"] == "feature-uuid-123"
            assert result["geometry"]["type"] == "Point"

    @pytest.mark.asyncio
    async def test_create_feature_tileset_not_found(self):
        """Test create feature in non-existent tileset."""
        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.post.return_value = create_mock_response(404)

            result = await create_feature(
                tileset_id="non-existent",
                geometry={"type": "Point", "coordinates": [0, 0]},
            )

            assert "error" in result


class TestUpdateFeature:
    """Tests for update_feature function."""

    @pytest.mark.asyncio
    async def test_update_feature_success(self):
        """Test successful feature update."""
        mock_response_data = {
            "id": "feature-uuid-123",
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [139.77, 35.68],
            },
            "properties": {
                "name": "Updated Name",
            },
        }

        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.patch.return_value = create_mock_response(200, mock_response_data)

            result = await update_feature(
                feature_id="feature-uuid-123",
                properties={"name": "Updated Name"},
            )

            assert result["properties"]["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_feature_no_fields(self):
        """Test update with no fields."""
        result = await update_feature(feature_id="feature-uuid-123")

        assert "error" in result
        assert "No fields" in result["error"]


class TestDeleteFeature:
    """Tests for delete_feature function."""

    @pytest.mark.asyncio
    async def test_delete_feature_success(self):
        """Test successful feature deletion."""
        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.delete.return_value = create_mock_response(204)

            result = await delete_feature(feature_id="feature-uuid-123")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delete_feature_not_found(self):
        """Test delete non-existent feature."""
        with patch("tools.crud.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.delete.return_value = create_mock_response(404)

            result = await delete_feature(feature_id="non-existent")

            assert "error" in result
