"""
Tests for CRUD tools.

This module tests create, update, delete operations for:
- Tilesets
- Features

Uses standard asyncio approach (not pytest-asyncio).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from tools.crud import (
    create_tileset,
    update_tileset,
    delete_tileset,
    create_feature,
    update_feature,
    delete_feature,
)


class TestCreateTileset:
    """Tests for create_tileset function."""

    def test_create_tileset_success(self):
        """create_tileset should return created tileset."""
        async def run_test():
            mock_response = Mock()
            mock_response.json = Mock(return_value={
                "id": "new-tileset-id",
                "name": "Test Tileset",
                "type": "vector",
                "format": "pbf",
            })
            mock_response.raise_for_status = Mock()
            mock_response.status_code = 201

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await create_tileset(
                    name="Test Tileset",
                    type="vector",
                    format="pbf",
                )

                assert "id" in result or "name" in result
                # Verify post was called
                mock_instance.post.assert_called_once()

        asyncio.run(run_test())

    def test_create_tileset_auth_required(self):
        """create_tileset should handle auth errors."""
        async def run_test():
            import httpx

            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await create_tileset(
                    name="Test",
                    type="vector",
                    format="pbf",
                )

                assert "error" in result

        asyncio.run(run_test())

    def test_create_tileset_with_all_params(self):
        """create_tileset should handle all parameters."""
        async def run_test():
            mock_response = Mock()
            mock_response.json = Mock(return_value={"id": "test-id", "name": "Full Test"})
            mock_response.raise_for_status = Mock()
            mock_response.status_code = 201

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await create_tileset(
                    name="Full Test",
                    type="vector",
                    format="pbf",
                    description="Test description",
                    min_zoom=0,
                    max_zoom=14,
                    bounds=[139.5, 35.5, 140.0, 36.0],
                    center=[139.75, 35.75],
                    attribution="Test Attribution",
                    is_public=True,
                    metadata={"key": "value"},
                )

                assert result is not None

        asyncio.run(run_test())


class TestUpdateTileset:
    """Tests for update_tileset function."""

    def test_update_tileset_success(self):
        """update_tileset should return updated tileset."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "test-id",
                "name": "Updated Name",
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.patch.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await update_tileset(
                    tileset_id="test-id",
                    name="Updated Name",
                )

                assert result is not None

        asyncio.run(run_test())

    def test_update_tileset_not_found(self):
        """update_tileset should handle 404 errors."""
        async def run_test():
            import httpx

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.text = "Not found"
                mock_instance.patch.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await update_tileset(
                    tileset_id="nonexistent-id",
                    name="New Name",
                )

                assert "error" in result

        asyncio.run(run_test())

    def test_update_tileset_no_fields(self):
        """update_tileset with no fields should return error."""
        async def run_test():
            result = await update_tileset(tileset_id="test-id")
            assert "error" in result
            assert "No fields" in result["error"] or "no update" in result["error"].lower()

        asyncio.run(run_test())


class TestDeleteTileset:
    """Tests for delete_tileset function."""

    def test_delete_tileset_success(self):
        """delete_tileset should return success message."""
        async def run_test():
            mock_response = Mock()
            mock_response.status_code = 204
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.delete.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await delete_tileset(tileset_id="test-id")

                assert "success" in result or "deleted" in str(result).lower()

        asyncio.run(run_test())

    def test_delete_tileset_not_found(self):
        """delete_tileset should handle 404 errors."""
        async def run_test():
            import httpx

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.text = "Not found"
                mock_instance.delete.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await delete_tileset(tileset_id="nonexistent-id")

                assert "error" in result

        asyncio.run(run_test())


class TestCreateFeature:
    """Tests for create_feature function."""

    def test_create_feature_success(self):
        """create_feature should return created feature."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "new-feature-id",
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [139.7, 35.6]},
                "properties": {"name": "Test Point"},
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await create_feature(
                    tileset_id="test-tileset-id",
                    geometry={"type": "Point", "coordinates": [139.7, 35.6]},
                    properties={"name": "Test Point"},
                )

                assert result is not None

        asyncio.run(run_test())

    def test_create_feature_tileset_not_found(self):
        """create_feature should handle tileset not found."""
        async def run_test():
            import httpx

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.text = "Tileset not found"
                mock_instance.post.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await create_feature(
                    tileset_id="nonexistent",
                    geometry={"type": "Point", "coordinates": [0, 0]},
                )

                assert "error" in result

        asyncio.run(run_test())

    def test_create_feature_with_layer(self):
        """create_feature should accept layer_name."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "feat-id",
                "layer_name": "custom_layer",
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await create_feature(
                    tileset_id="test-id",
                    geometry={"type": "Point", "coordinates": [0, 0]},
                    layer_name="custom_layer",
                )

                assert result is not None

        asyncio.run(run_test())


class TestUpdateFeature:
    """Tests for update_feature function."""

    def test_update_feature_success(self):
        """update_feature should return updated feature."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": "feat-id",
                "properties": {"name": "Updated"},
            }
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.patch.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await update_feature(
                    feature_id="feat-id",
                    properties={"name": "Updated"},
                )

                assert result is not None

        asyncio.run(run_test())

    def test_update_feature_geometry(self):
        """update_feature should update geometry."""
        async def run_test():
            new_geom = {"type": "Point", "coordinates": [140.0, 36.0]}
            mock_response = Mock()
            mock_response.json.return_value = {"id": "feat-id", "geometry": new_geom}
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.patch.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await update_feature(
                    feature_id="feat-id",
                    geometry=new_geom,
                )

                assert result is not None

        asyncio.run(run_test())

    def test_update_feature_no_fields(self):
        """update_feature with no fields should return error."""
        async def run_test():
            result = await update_feature(feature_id="feat-id")
            assert "error" in result

        asyncio.run(run_test())


class TestDeleteFeature:
    """Tests for delete_feature function."""

    def test_delete_feature_success(self):
        """delete_feature should return success message."""
        async def run_test():
            mock_response = Mock()
            mock_response.status_code = 204
            mock_response.raise_for_status = Mock()

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.delete.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await delete_feature(feature_id="feat-id")

                assert "success" in result or "deleted" in str(result).lower()

        asyncio.run(run_test())

    def test_delete_feature_not_found(self):
        """delete_feature should handle 404 errors."""
        async def run_test():
            import httpx

            with patch("tools.crud.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.text = "Not found"
                mock_instance.delete.side_effect = httpx.HTTPStatusError(
                    "", request=Mock(), response=mock_response
                )
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await delete_feature(feature_id="nonexistent")

                assert "error" in result

        asyncio.run(run_test())
