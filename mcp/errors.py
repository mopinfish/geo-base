"""
Custom exceptions and error handling utilities for geo-base MCP Server.

This module provides:
- Custom exception classes for different error types
- Standardized error response formatting
- Error code constants for consistent error handling

Usage:
    from errors import (
        MCPError,
        ValidationError,
        APIError,
        handle_api_error,
        ErrorCode,
    )

    # Raise custom exceptions
    raise ValidationError("Invalid bbox format")
    raise APIError("Server error", status_code=500)

    # Handle API errors
    try:
        response = await client.get(url)
        response.raise_for_status()
    except Exception as e:
        return handle_api_error(e)
"""

from enum import Enum
from typing import Any

import httpx


class ErrorCode(str, Enum):
    """Standardized error codes for MCP responses."""

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"

    # Authentication errors
    AUTH_REQUIRED = "AUTH_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Network errors
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"

    # Server errors
    SERVER_ERROR = "SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Generic errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    HTTP_ERROR = "HTTP_ERROR"


class MCPError(Exception):
    """Base exception for MCP Server errors.

    All custom exceptions should inherit from this class.

    Attributes:
        message: Human-readable error message
        code: ErrorCode for programmatic handling
        details: Additional error context
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a standardized error response dict."""
        result = {
            "error": self.message,
            "code": self.code.value,
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(MCPError):
    """Raised when input validation fails.

    Examples:
        - Invalid bbox format
        - Missing required parameter
        - Value out of range
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            details=details,
        )
        self.field = field


class APIError(MCPError):
    """Raised when an external API call fails.

    Attributes:
        status_code: HTTP status code (if applicable)
        response_text: Raw response text (if available)
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if status_code:
            details["status_code"] = status_code
        if response_text:
            # Truncate long response text
            details["response"] = response_text[:500] if len(response_text) > 500 else response_text

        # Determine error code based on status code
        if status_code:
            if status_code == 401:
                code = ErrorCode.AUTH_REQUIRED
            elif status_code == 403:
                code = ErrorCode.FORBIDDEN
            elif status_code == 404:
                code = ErrorCode.NOT_FOUND
            elif status_code >= 500:
                code = ErrorCode.SERVER_ERROR
            else:
                code = ErrorCode.HTTP_ERROR
        else:
            code = ErrorCode.HTTP_ERROR

        super().__init__(message=message, code=code, details=details)
        self.status_code = status_code
        self.response_text = response_text


class AuthenticationError(MCPError):
    """Raised when authentication fails or is required."""

    def __init__(
        self,
        message: str = "Authentication required",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_REQUIRED,
            details=details,
        )


class NotFoundError(MCPError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            code=ErrorCode.NOT_FOUND,
            details=details,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class NetworkError(MCPError):
    """Raised when a network-related error occurs."""

    def __init__(
        self,
        message: str = "Network error occurred",
        is_timeout: bool = False,
        details: dict[str, Any] | None = None,
    ):
        code = ErrorCode.TIMEOUT if is_timeout else ErrorCode.NETWORK_ERROR
        super().__init__(message=message, code=code, details=details)
        self.is_timeout = is_timeout


def handle_api_error(
    e: Exception,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert an exception to a standardized error response dict.

    This function handles various exception types and returns a
    consistent error response format that can be returned from tools.

    Args:
        e: The exception to handle
        context: Additional context to include in the error response
            (e.g., {"feature_id": "abc123", "operation": "get"})

    Returns:
        A dictionary with standardized error information:
        {
            "error": "Human-readable message",
            "code": "ERROR_CODE",
            "details": {...}  # Optional
        }

    Examples:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except Exception as e:
            return handle_api_error(e, {"url": url})
    """
    context = context or {}

    # Handle our custom exceptions
    if isinstance(e, MCPError):
        result = e.to_dict()
        if context:
            result.setdefault("details", {}).update(context)
        return result

    # Handle httpx HTTP status errors
    if isinstance(e, httpx.HTTPStatusError):
        status_code = e.response.status_code
        response_text = e.response.text

        if status_code == 401:
            result = {
                "error": "認証が必要です",
                "code": ErrorCode.AUTH_REQUIRED.value,
                "hint": "API_TOKEN環境変数を設定してください",
            }
        elif status_code == 403:
            result = {
                "error": "アクセス権限がありません",
                "code": ErrorCode.FORBIDDEN.value,
            }
        elif status_code == 404:
            result = {
                "error": "リソースが見つかりません",
                "code": ErrorCode.NOT_FOUND.value,
            }
        elif status_code >= 500:
            result = {
                "error": "サーバーエラーが発生しました",
                "code": ErrorCode.SERVER_ERROR.value,
                "status_code": status_code,
            }
        else:
            result = {
                "error": f"HTTPエラー: {status_code}",
                "code": ErrorCode.HTTP_ERROR.value,
                "status_code": status_code,
            }

        # Add response text if available and not too long
        if response_text and len(response_text) < 500:
            result["response"] = response_text

        if context:
            result.update(context)
        return result

    # Handle httpx timeout errors
    if isinstance(e, httpx.TimeoutException):
        result = {
            "error": "リクエストがタイムアウトしました",
            "code": ErrorCode.TIMEOUT.value,
        }
        if context:
            result.update(context)
        return result

    # Handle httpx network errors
    if isinstance(e, (httpx.NetworkError, httpx.ConnectError)):
        result = {
            "error": "ネットワークエラーが発生しました",
            "code": ErrorCode.NETWORK_ERROR.value,
            "detail": str(e),
        }
        if context:
            result.update(context)
        return result

    # Handle generic httpx errors
    if isinstance(e, httpx.HTTPError):
        result = {
            "error": f"HTTPエラー: {str(e)}",
            "code": ErrorCode.HTTP_ERROR.value,
        }
        if context:
            result.update(context)
        return result

    # Handle unknown errors
    result = {
        "error": f"予期しないエラー: {str(e)}",
        "code": ErrorCode.UNKNOWN_ERROR.value,
        "exception_type": type(e).__name__,
    }
    if context:
        result.update(context)
    return result


def create_error_response(
    message: str,
    code: ErrorCode | str = ErrorCode.UNKNOWN_ERROR,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a standardized error response dict.

    A convenience function for creating error responses without
    raising exceptions.

    Args:
        message: Human-readable error message
        code: Error code (ErrorCode enum or string)
        **kwargs: Additional fields to include in the response

    Returns:
        Standardized error response dict

    Examples:
        return create_error_response(
            "Invalid tileset ID",
            ErrorCode.VALIDATION_ERROR,
            tileset_id=tileset_id,
        )
    """
    result: dict[str, Any] = {
        "error": message,
        "code": code.value if isinstance(code, ErrorCode) else code,
    }
    result.update(kwargs)
    return result
