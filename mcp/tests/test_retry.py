"""
Tests for retry utilities.

This module tests:
- Retry configuration
- fetch_with_retry function
- post_with_retry function
- RetryableClient class
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from retry import (
    fetch_with_retry,
    post_with_retry,
    put_with_retry,
    delete_with_retry,
    RetryableClient,
    RETRY_MAX_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT,
    RETRYABLE_EXCEPTIONS,
    _create_retry_config,
)


class TestRetryConfiguration:
    """Tests for retry configuration."""

    def test_default_retry_attempts(self):
        """Default retry attempts should be 3."""
        assert RETRY_MAX_ATTEMPTS == 3

    def test_default_min_wait(self):
        """Default minimum wait should be 1 second."""
        assert RETRY_MIN_WAIT == 1

    def test_default_max_wait(self):
        """Default maximum wait should be 10 seconds."""
        assert RETRY_MAX_WAIT == 10

    def test_retryable_exceptions(self):
        """Retryable exceptions should include network errors."""
        assert httpx.TimeoutException in RETRYABLE_EXCEPTIONS
        assert httpx.NetworkError in RETRYABLE_EXCEPTIONS
        assert httpx.ConnectError in RETRYABLE_EXCEPTIONS

    def test_create_retry_config_defaults(self):
        """_create_retry_config should use defaults."""
        config = _create_retry_config()
        assert config["reraise"] is True

    def test_create_retry_config_custom(self):
        """_create_retry_config should accept custom values."""
        config = _create_retry_config(
            max_attempts=5,
            min_wait=2.0,
            max_wait=20.0,
        )
        assert config is not None


class TestFetchWithRetry:
    """Tests for fetch_with_retry function."""

    def test_successful_fetch(self):
        """fetch_with_retry should return data on success."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await fetch_with_retry("https://example.com/api")

                assert result == {"data": "test"}
                mock_instance.get.assert_called_once()

        asyncio.run(run_test())

    def test_fetch_with_params(self):
        """fetch_with_retry should pass params to request."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await fetch_with_retry(
                    "https://example.com/api",
                    params={"key": "value"},
                )

                call_args = mock_instance.get.call_args
                assert call_args[1]["params"] == {"key": "value"}

        asyncio.run(run_test())

    def test_fetch_with_headers(self):
        """fetch_with_retry should pass headers to request."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await fetch_with_retry(
                    "https://example.com/api",
                    headers={"Authorization": "Bearer token"},
                )

                call_args = mock_instance.get.call_args
                assert call_args[1]["headers"] == {"Authorization": "Bearer token"}

        asyncio.run(run_test())

    def test_fetch_retries_on_timeout(self):
        """fetch_with_retry should retry on timeout."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = Mock()

            call_count = 0

            async def mock_get(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise httpx.TimeoutException("Timeout")
                return mock_response

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = mock_get
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                # Reduce wait time for faster tests
                with patch("retry.RETRY_MIN_WAIT", 0.01), patch("retry.RETRY_MAX_WAIT", 0.02):
                    result = await fetch_with_retry(
                        "https://example.com/api",
                        max_attempts=3,
                    )

                assert result == {"data": "test"}
                assert call_count == 2

        asyncio.run(run_test())

    def test_fetch_raises_after_max_retries(self):
        """fetch_with_retry should raise after max retries."""
        async def run_test():
            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.side_effect = httpx.TimeoutException("Timeout")
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                with patch("retry.RETRY_MIN_WAIT", 0.01), patch("retry.RETRY_MAX_WAIT", 0.02):
                    with pytest.raises(httpx.TimeoutException):
                        await fetch_with_retry(
                            "https://example.com/api",
                            max_attempts=2,
                        )

        asyncio.run(run_test())


class TestPostWithRetry:
    """Tests for post_with_retry function."""

    def test_successful_post(self):
        """post_with_retry should return data on success."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"id": "123"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await post_with_retry(
                    "https://example.com/api",
                    json={"name": "test"},
                )

                assert result == {"id": "123"}
                mock_instance.post.assert_called_once()

        asyncio.run(run_test())

    def test_post_with_json(self):
        """post_with_retry should pass json to request."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"id": "123"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                await post_with_retry(
                    "https://example.com/api",
                    json={"name": "test"},
                )

                call_args = mock_instance.post.call_args
                assert call_args[1]["json"] == {"name": "test"}

        asyncio.run(run_test())


class TestPutWithRetry:
    """Tests for put_with_retry function."""

    def test_successful_put(self):
        """put_with_retry should return data on success."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"updated": True}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.put.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await put_with_retry(
                    "https://example.com/api/123",
                    json={"name": "updated"},
                )

                assert result == {"updated": True}

        asyncio.run(run_test())


class TestDeleteWithRetry:
    """Tests for delete_with_retry function."""

    def test_successful_delete(self):
        """delete_with_retry should return data on success."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"deleted": True}
            mock_response.status_code = 200
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.delete.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await delete_with_retry("https://example.com/api/123")

                assert result == {"deleted": True}

        asyncio.run(run_test())

    def test_delete_no_content(self):
        """delete_with_retry should handle 204 No Content."""
        async def run_test():
            mock_response = Mock()
            mock_response.status_code = 204
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.delete.return_value = mock_response
                mock_instance.__aenter__.return_value = mock_instance
                mock_instance.__aexit__.return_value = None
                mock_client.return_value = mock_instance

                result = await delete_with_retry("https://example.com/api/123")

                assert result["success"] is True

        asyncio.run(run_test())


class TestRetryableClient:
    """Tests for RetryableClient class."""

    def test_client_context_manager(self):
        """RetryableClient should work as context manager."""
        async def run_test():
            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_client.return_value = mock_instance

                async with RetryableClient() as client:
                    assert client._client is not None

        asyncio.run(run_test())

    def test_client_get(self):
        """RetryableClient.get should make GET request."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_client.return_value = mock_instance

                async with RetryableClient() as client:
                    result = await client.get("https://example.com/api")

                assert result == {"data": "test"}

        asyncio.run(run_test())

    def test_client_post(self):
        """RetryableClient.post should make POST request."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"id": "123"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_client.return_value = mock_instance

                async with RetryableClient() as client:
                    result = await client.post(
                        "https://example.com/api",
                        json={"name": "test"},
                    )

                assert result == {"id": "123"}

        asyncio.run(run_test())

    def test_client_not_initialized_error(self):
        """RetryableClient should raise error when not in context."""
        async def run_test():
            client = RetryableClient()

            with pytest.raises(RuntimeError, match="not initialized"):
                await client.get("https://example.com/api")

        asyncio.run(run_test())

    def test_client_with_default_headers(self):
        """RetryableClient should use default headers."""
        async def run_test():
            mock_response = Mock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.raise_for_status = Mock()

            with patch("retry.httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get.return_value = mock_response
                mock_client.return_value = mock_instance

                async with RetryableClient(
                    headers={"Authorization": "Bearer token"}
                ) as client:
                    await client.get("https://example.com/api")

                # Check that AsyncClient was called with headers
                call_kwargs = mock_client.call_args[1]
                assert call_kwargs["headers"] == {"Authorization": "Bearer token"}

        asyncio.run(run_test())
