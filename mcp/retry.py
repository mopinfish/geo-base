"""
Retry utilities for geo-base MCP Server.

This module provides retry functionality for HTTP requests using tenacity.
It implements exponential backoff with configurable retry conditions.

Features:
- Automatic retry for transient network errors
- Exponential backoff with jitter
- Configurable retry count and delays
- Detailed logging of retry attempts
- Support for both GET and POST requests

Usage:
    from retry import fetch_with_retry, post_with_retry

    # Simple GET request with retry
    data = await fetch_with_retry("https://api.example.com/data")

    # POST request with retry
    result = await post_with_retry(
        "https://api.example.com/create",
        json={"name": "test"},
        headers={"Authorization": "Bearer token"},
    )

Configuration:
    Retry behavior can be customized via environment variables:
    - RETRY_MAX_ATTEMPTS: Maximum retry attempts (default: 3)
    - RETRY_MIN_WAIT: Minimum wait between retries in seconds (default: 1)
    - RETRY_MAX_WAIT: Maximum wait between retries in seconds (default: 10)
"""

import os
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)

from config import get_settings
from logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Configuration from environment variables
RETRY_MAX_ATTEMPTS = int(os.environ.get("RETRY_MAX_ATTEMPTS", "3"))
RETRY_MIN_WAIT = float(os.environ.get("RETRY_MIN_WAIT", "1"))
RETRY_MAX_WAIT = float(os.environ.get("RETRY_MAX_WAIT", "10"))

# Exception types that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ConnectTimeout,
)


def _create_retry_config(
    max_attempts: int | None = None,
    min_wait: float | None = None,
    max_wait: float | None = None,
) -> dict[str, Any]:
    """Create retry configuration for tenacity.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Dictionary of tenacity retry parameters
    """
    return {
        "stop": stop_after_attempt(max_attempts or RETRY_MAX_ATTEMPTS),
        "wait": wait_exponential(
            multiplier=1,
            min=min_wait or RETRY_MIN_WAIT,
            max=max_wait or RETRY_MAX_WAIT,
        ),
        "retry": retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        "before_sleep": before_sleep_log(logger, log_level=20),  # INFO level
        "after": after_log(logger, log_level=10),  # DEBUG level
        "reraise": True,
    }


async def fetch_with_retry(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    max_attempts: int | None = None,
) -> dict[str, Any]:
    """Fetch data from a URL with automatic retry on transient failures.

    This function performs an HTTP GET request with automatic retry
    for network-related errors. It uses exponential backoff between
    retry attempts.

    Args:
        url: The URL to fetch
        params: Optional query parameters
        headers: Optional HTTP headers
        timeout: Request timeout in seconds (default: from settings)
        max_attempts: Maximum retry attempts (default: 3)

    Returns:
        Parsed JSON response as a dictionary

    Raises:
        httpx.HTTPStatusError: For HTTP error responses (4xx, 5xx)
        httpx.TimeoutException: If all retries fail due to timeout
        httpx.NetworkError: If all retries fail due to network issues
        RetryError: If all retry attempts are exhausted

    Examples:
        # Basic usage
        data = await fetch_with_retry("https://api.example.com/data")

        # With parameters and headers
        data = await fetch_with_retry(
            "https://api.example.com/search",
            params={"q": "tokyo"},
            headers={"Authorization": "Bearer token"},
        )
    """
    retry_config = _create_retry_config(max_attempts=max_attempts)
    request_timeout = timeout or settings.http_timeout

    async for attempt in AsyncRetrying(**retry_config):
        with attempt:
            logger.debug(
                f"Fetching {url}",
                extra={
                    "attempt": attempt.retry_state.attempt_number,
                    "params": str(params) if params else None,
                },
            )

            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()

    # This should never be reached due to reraise=True
    raise RuntimeError("Unexpected state: retry exhausted without exception")


async def post_with_retry(
    url: str,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    max_attempts: int | None = None,
) -> dict[str, Any]:
    """Send a POST request with automatic retry on transient failures.

    This function performs an HTTP POST request with automatic retry
    for network-related errors. It uses exponential backoff between
    retry attempts.

    Args:
        url: The URL to post to
        json: JSON body to send
        data: Form data to send
        headers: Optional HTTP headers
        timeout: Request timeout in seconds (default: from settings)
        max_attempts: Maximum retry attempts (default: 3)

    Returns:
        Parsed JSON response as a dictionary

    Raises:
        httpx.HTTPStatusError: For HTTP error responses (4xx, 5xx)
        httpx.TimeoutException: If all retries fail due to timeout
        httpx.NetworkError: If all retries fail due to network issues

    Examples:
        # Send JSON data
        result = await post_with_retry(
            "https://api.example.com/create",
            json={"name": "New Item"},
        )

        # With authentication
        result = await post_with_retry(
            "https://api.example.com/create",
            json={"name": "New Item"},
            headers={"Authorization": "Bearer token"},
        )
    """
    retry_config = _create_retry_config(max_attempts=max_attempts)
    request_timeout = timeout or settings.http_timeout

    async for attempt in AsyncRetrying(**retry_config):
        with attempt:
            logger.debug(
                f"Posting to {url}",
                extra={
                    "attempt": attempt.retry_state.attempt_number,
                    "has_json": json is not None,
                    "has_data": data is not None,
                },
            )

            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.post(
                    url,
                    json=json,
                    data=data,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()

    raise RuntimeError("Unexpected state: retry exhausted without exception")


async def put_with_retry(
    url: str,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    max_attempts: int | None = None,
) -> dict[str, Any]:
    """Send a PUT request with automatic retry on transient failures.

    Args:
        url: The URL to put to
        json: JSON body to send
        headers: Optional HTTP headers
        timeout: Request timeout in seconds (default: from settings)
        max_attempts: Maximum retry attempts (default: 3)

    Returns:
        Parsed JSON response as a dictionary
    """
    retry_config = _create_retry_config(max_attempts=max_attempts)
    request_timeout = timeout or settings.http_timeout

    async for attempt in AsyncRetrying(**retry_config):
        with attempt:
            logger.debug(
                f"Putting to {url}",
                extra={
                    "attempt": attempt.retry_state.attempt_number,
                },
            )

            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.put(url, json=json, headers=headers)
                response.raise_for_status()
                return response.json()

    raise RuntimeError("Unexpected state: retry exhausted without exception")


async def delete_with_retry(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    max_attempts: int | None = None,
) -> dict[str, Any]:
    """Send a DELETE request with automatic retry on transient failures.

    Args:
        url: The URL to delete
        headers: Optional HTTP headers
        timeout: Request timeout in seconds (default: from settings)
        max_attempts: Maximum retry attempts (default: 3)

    Returns:
        Parsed JSON response as a dictionary
    """
    retry_config = _create_retry_config(max_attempts=max_attempts)
    request_timeout = timeout or settings.http_timeout

    async for attempt in AsyncRetrying(**retry_config):
        with attempt:
            logger.debug(
                f"Deleting {url}",
                extra={
                    "attempt": attempt.retry_state.attempt_number,
                },
            )

            async with httpx.AsyncClient(timeout=request_timeout) as client:
                response = await client.delete(url, headers=headers)
                response.raise_for_status()

                # Handle empty response (204 No Content)
                if response.status_code == 204:
                    return {"success": True, "message": "Deleted successfully"}

                return response.json()

    raise RuntimeError("Unexpected state: retry exhausted without exception")


class RetryableClient:
    """A context manager that provides an HTTP client with retry capabilities.

    This class wraps httpx.AsyncClient and provides methods with automatic
    retry functionality. It's useful when you need more control over the
    HTTP client lifecycle.

    Usage:
        async with RetryableClient() as client:
            data = await client.get("https://api.example.com/data")
            result = await client.post("https://api.example.com/create", json={...})
    """

    def __init__(
        self,
        timeout: float | None = None,
        max_attempts: int | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Initialize the retryable client.

        Args:
            timeout: Default request timeout in seconds
            max_attempts: Maximum retry attempts for all requests
            headers: Default headers for all requests
        """
        self.timeout = timeout or settings.http_timeout
        self.max_attempts = max_attempts or RETRY_MAX_ATTEMPTS
        self.default_headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "RetryableClient":
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.default_headers,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform a GET request with retry."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        retry_config = _create_retry_config(max_attempts=self.max_attempts)

        async for attempt in AsyncRetrying(**retry_config):
            with attempt:
                response = await self._client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()

        raise RuntimeError("Unexpected state")

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform a POST request with retry."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        retry_config = _create_retry_config(max_attempts=self.max_attempts)

        async for attempt in AsyncRetrying(**retry_config):
            with attempt:
                response = await self._client.post(url, json=json, headers=headers)
                response.raise_for_status()
                return response.json()

        raise RuntimeError("Unexpected state")

    async def put(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform a PUT request with retry."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        retry_config = _create_retry_config(max_attempts=self.max_attempts)

        async for attempt in AsyncRetrying(**retry_config):
            with attempt:
                response = await self._client.put(url, json=json, headers=headers)
                response.raise_for_status()
                return response.json()

        raise RuntimeError("Unexpected state")

    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform a DELETE request with retry."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        retry_config = _create_retry_config(max_attempts=self.max_attempts)

        async for attempt in AsyncRetrying(**retry_config):
            with attempt:
                response = await self._client.delete(url, headers=headers)
                response.raise_for_status()

                if response.status_code == 204:
                    return {"success": True, "message": "Deleted successfully"}

                return response.json()

        raise RuntimeError("Unexpected state")
