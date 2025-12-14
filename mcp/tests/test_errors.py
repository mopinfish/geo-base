"""
Tests for error handling utilities.

This module tests:
- Custom exception classes
- Error response formatting
- Error code handling
"""

import pytest
import httpx
from unittest.mock import Mock

from errors import (
    MCPError,
    ValidationError,
    APIError,
    AuthenticationError,
    NotFoundError,
    NetworkError,
    ErrorCode,
    handle_api_error,
    create_error_response,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""

    def test_error_codes_are_strings(self):
        """Error codes should be string values."""
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.TIMEOUT.value == "TIMEOUT"

    def test_all_error_codes_defined(self):
        """All expected error codes should be defined."""
        expected_codes = [
            "VALIDATION_ERROR",
            "AUTH_REQUIRED",
            "FORBIDDEN",
            "NOT_FOUND",
            "NETWORK_ERROR",
            "TIMEOUT",
            "SERVER_ERROR",
            "UNKNOWN_ERROR",
        ]
        for code in expected_codes:
            assert hasattr(ErrorCode, code)


class TestMCPError:
    """Tests for base MCPError exception."""

    def test_basic_creation(self):
        """MCPError should be created with message."""
        error = MCPError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.code == ErrorCode.UNKNOWN_ERROR

    def test_with_code(self):
        """MCPError should accept custom error code."""
        error = MCPError("Test", code=ErrorCode.VALIDATION_ERROR)
        assert error.code == ErrorCode.VALIDATION_ERROR

    def test_with_details(self):
        """MCPError should accept details dictionary."""
        error = MCPError("Test", details={"field": "name"})
        assert error.details == {"field": "name"}

    def test_to_dict(self):
        """to_dict should return standardized format."""
        error = MCPError(
            "Test error",
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": "bbox"},
        )
        result = error.to_dict()

        assert result["error"] == "Test error"
        assert result["code"] == "VALIDATION_ERROR"
        assert result["details"] == {"field": "bbox"}

    def test_to_dict_without_details(self):
        """to_dict should not include details if empty."""
        error = MCPError("Test error")
        result = error.to_dict()

        assert "error" in result
        assert "code" in result
        assert "details" not in result


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_basic_creation(self):
        """ValidationError should set correct code."""
        error = ValidationError("Invalid input")
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Invalid input"

    def test_with_field(self):
        """ValidationError should include field in details."""
        error = ValidationError("Invalid format", field="bbox")
        assert error.field == "bbox"
        assert error.details["field"] == "bbox"

    def test_to_dict(self):
        """ValidationError to_dict should include field."""
        error = ValidationError("Invalid", field="limit")
        result = error.to_dict()

        assert result["code"] == "VALIDATION_ERROR"
        assert result["details"]["field"] == "limit"


class TestAPIError:
    """Tests for APIError exception."""

    def test_basic_creation(self):
        """APIError should be created with message."""
        error = APIError("Server error")
        assert error.message == "Server error"
        assert error.status_code is None

    def test_with_status_code(self):
        """APIError should store status code."""
        error = APIError("Not found", status_code=404)
        assert error.status_code == 404
        assert error.code == ErrorCode.NOT_FOUND

    def test_status_code_mapping(self):
        """APIError should map status codes to error codes."""
        assert APIError("", status_code=401).code == ErrorCode.AUTH_REQUIRED
        assert APIError("", status_code=403).code == ErrorCode.FORBIDDEN
        assert APIError("", status_code=404).code == ErrorCode.NOT_FOUND
        assert APIError("", status_code=500).code == ErrorCode.SERVER_ERROR
        assert APIError("", status_code=400).code == ErrorCode.HTTP_ERROR

    def test_with_response_text(self):
        """APIError should store response text."""
        error = APIError("Error", status_code=400, response_text="Bad request")
        assert error.response_text == "Bad request"
        assert error.details["response"] == "Bad request"

    def test_response_text_truncation(self):
        """APIError should truncate long response text."""
        long_text = "x" * 1000
        error = APIError("Error", response_text=long_text)
        assert len(error.details["response"]) == 500


class TestAuthenticationError:
    """Tests for AuthenticationError exception."""

    def test_default_message(self):
        """AuthenticationError should have default message."""
        error = AuthenticationError()
        assert error.message == "Authentication required"
        assert error.code == ErrorCode.AUTH_REQUIRED

    def test_custom_message(self):
        """AuthenticationError should accept custom message."""
        error = AuthenticationError("Invalid token")
        assert error.message == "Invalid token"


class TestNotFoundError:
    """Tests for NotFoundError exception."""

    def test_creation(self):
        """NotFoundError should format message from resource info."""
        error = NotFoundError("Tileset", "abc123")
        assert error.message == "Tileset not found: abc123"
        assert error.code == ErrorCode.NOT_FOUND
        assert error.resource_type == "Tileset"
        assert error.resource_id == "abc123"

    def test_details_include_resource_info(self):
        """NotFoundError should include resource info in details."""
        error = NotFoundError("Feature", "xyz789")
        assert error.details["resource_type"] == "Feature"
        assert error.details["resource_id"] == "xyz789"


class TestNetworkError:
    """Tests for NetworkError exception."""

    def test_default_not_timeout(self):
        """NetworkError should default to not being a timeout."""
        error = NetworkError("Connection failed")
        assert error.code == ErrorCode.NETWORK_ERROR
        assert error.is_timeout is False

    def test_timeout_flag(self):
        """NetworkError should handle timeout flag."""
        error = NetworkError("Request timed out", is_timeout=True)
        assert error.code == ErrorCode.TIMEOUT
        assert error.is_timeout is True


class TestHandleApiError:
    """Tests for handle_api_error function."""

    def test_handles_mcp_error(self):
        """handle_api_error should convert MCPError to dict."""
        error = ValidationError("Invalid input", field="bbox")
        result = handle_api_error(error)

        assert result["error"] == "Invalid input"
        assert result["code"] == "VALIDATION_ERROR"
        assert result["details"]["field"] == "bbox"

    def test_handles_mcp_error_with_context(self):
        """handle_api_error should merge context into MCPError."""
        error = NotFoundError("Tileset", "abc")
        result = handle_api_error(error, {"operation": "get"})

        assert "operation" in result["details"]
        assert result["details"]["operation"] == "get"

    def test_handles_http_status_error_401(self):
        """handle_api_error should handle 401 errors."""
        response = Mock()
        response.status_code = 401
        response.text = "Unauthorized"
        error = httpx.HTTPStatusError("", request=Mock(), response=response)

        result = handle_api_error(error)

        assert result["code"] == "AUTH_REQUIRED"
        assert "認証" in result["error"]

    def test_handles_http_status_error_403(self):
        """handle_api_error should handle 403 errors."""
        response = Mock()
        response.status_code = 403
        response.text = "Forbidden"
        error = httpx.HTTPStatusError("", request=Mock(), response=response)

        result = handle_api_error(error)

        assert result["code"] == "FORBIDDEN"
        assert "権限" in result["error"]

    def test_handles_http_status_error_404(self):
        """handle_api_error should handle 404 errors."""
        response = Mock()
        response.status_code = 404
        response.text = "Not found"
        error = httpx.HTTPStatusError("", request=Mock(), response=response)

        result = handle_api_error(error)

        assert result["code"] == "NOT_FOUND"

    def test_handles_http_status_error_500(self):
        """handle_api_error should handle 500 errors."""
        response = Mock()
        response.status_code = 500
        response.text = "Internal server error"
        error = httpx.HTTPStatusError("", request=Mock(), response=response)

        result = handle_api_error(error)

        assert result["code"] == "SERVER_ERROR"
        assert result["status_code"] == 500

    def test_handles_timeout_exception(self):
        """handle_api_error should handle timeout errors."""
        error = httpx.TimeoutException("Request timed out")
        result = handle_api_error(error)

        assert result["code"] == "TIMEOUT"
        assert "タイムアウト" in result["error"]

    def test_handles_network_error(self):
        """handle_api_error should handle network errors."""
        error = httpx.NetworkError("Connection failed")
        result = handle_api_error(error)

        assert result["code"] == "NETWORK_ERROR"
        assert "ネットワーク" in result["error"]

    def test_handles_unknown_exception(self):
        """handle_api_error should handle unknown exceptions."""
        error = ValueError("Something went wrong")
        result = handle_api_error(error)

        assert result["code"] == "UNKNOWN_ERROR"
        assert result["exception_type"] == "ValueError"

    def test_includes_context(self):
        """handle_api_error should include context in result."""
        error = httpx.TimeoutException("Timeout")
        result = handle_api_error(error, {"url": "https://example.com"})

        assert result["url"] == "https://example.com"


class TestCreateErrorResponse:
    """Tests for create_error_response function."""

    def test_basic_response(self):
        """create_error_response should create basic error dict."""
        result = create_error_response("Something went wrong")

        assert result["error"] == "Something went wrong"
        assert result["code"] == "UNKNOWN_ERROR"

    def test_with_error_code_enum(self):
        """create_error_response should accept ErrorCode enum."""
        result = create_error_response(
            "Validation failed",
            ErrorCode.VALIDATION_ERROR,
        )

        assert result["code"] == "VALIDATION_ERROR"

    def test_with_string_code(self):
        """create_error_response should accept string code."""
        result = create_error_response("Error", "CUSTOM_ERROR")
        assert result["code"] == "CUSTOM_ERROR"

    def test_with_extra_kwargs(self):
        """create_error_response should include extra kwargs."""
        result = create_error_response(
            "Not found",
            ErrorCode.NOT_FOUND,
            tileset_id="abc123",
            hint="Check the ID",
        )

        assert result["tileset_id"] == "abc123"
        assert result["hint"] == "Check the ID"
