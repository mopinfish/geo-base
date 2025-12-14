"""
Tests for the logging module.
"""

import logging
import os
import pytest
from unittest.mock import patch

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import (
    get_logger,
    get_log_level,
    MCPFormatter,
    ToolCallLogger,
)


class TestGetLogLevel:
    """Tests for get_log_level function."""

    def test_default_log_level(self):
        """Default log level should be INFO."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear LOG_LEVEL if it exists
            os.environ.pop("LOG_LEVEL", None)
            level = get_log_level()
            assert level == logging.INFO

    def test_debug_log_level(self):
        """LOG_LEVEL=DEBUG should return DEBUG level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            level = get_log_level()
            assert level == logging.DEBUG

    def test_warning_log_level(self):
        """LOG_LEVEL=WARNING should return WARNING level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            level = get_log_level()
            assert level == logging.WARNING

    def test_error_log_level(self):
        """LOG_LEVEL=ERROR should return ERROR level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            level = get_log_level()
            assert level == logging.ERROR

    def test_case_insensitive(self):
        """LOG_LEVEL should be case insensitive."""
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            level = get_log_level()
            assert level == logging.DEBUG

    def test_invalid_log_level_defaults_to_info(self):
        """Invalid LOG_LEVEL should default to INFO."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            level = get_log_level()
            assert level == logging.INFO


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self):
        """get_logger should return a Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self):
        """Logger should have the correct name."""
        logger = get_logger("my_test_module")
        assert logger.name == "my_test_module"

    def test_logger_has_handler(self):
        """Logger should have at least one handler."""
        logger = get_logger("handler_test_module")
        assert len(logger.handlers) >= 1

    def test_logger_uses_mcp_formatter(self):
        """Logger handler should use MCPFormatter."""
        logger = get_logger("formatter_test_module")
        for handler in logger.handlers:
            assert isinstance(handler.formatter, MCPFormatter)

    def test_cached_logger(self):
        """Same name should return the same logger instance."""
        logger1 = get_logger("cached_test")
        logger2 = get_logger("cached_test")
        assert logger1 is logger2


class TestMCPFormatter:
    """Tests for MCPFormatter class."""

    def test_basic_format(self):
        """Formatter should include timestamp, name, level, and message."""
        formatter = MCPFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        
        assert "test" in formatted
        assert "INFO" in formatted
        assert "Test message" in formatted

    def test_extra_fields(self):
        """Formatter should include extra fields."""
        formatter = MCPFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.tool = "my_tool"
        record.elapsed_ms = "123.45"
        
        formatted = formatter.format(record)
        
        assert "tool=my_tool" in formatted
        assert "elapsed_ms=123.45" in formatted


class TestToolCallLogger:
    """Tests for ToolCallLogger context manager."""

    def test_context_manager_basic(self):
        """ToolCallLogger should work as context manager."""
        logger = get_logger("tool_call_test")
        
        with ToolCallLogger(logger, "test_tool", param="value") as log:
            log.set_result({"success": True})
        
        # No exception means success

    def test_result_summarization_dict_with_error(self):
        """Result summarization should handle error in dict."""
        logger = get_logger("summary_test_1")
        
        with ToolCallLogger(logger, "test_tool") as log:
            result = {"error": "Something went wrong"}
            log.set_result(result)
            summary = log._summarize_result(result)
            assert "error" in summary

    def test_result_summarization_dict_with_count(self):
        """Result summarization should handle count in dict."""
        logger = get_logger("summary_test_2")
        
        with ToolCallLogger(logger, "test_tool") as log:
            result = {"count": 5, "items": []}
            log.set_result(result)
            summary = log._summarize_result(result)
            assert "count=5" in summary

    def test_result_summarization_list(self):
        """Result summarization should handle list."""
        logger = get_logger("summary_test_3")
        
        with ToolCallLogger(logger, "test_tool") as log:
            result = [1, 2, 3, 4, 5]
            log.set_result(result)
            summary = log._summarize_result(result)
            assert "5 items" in summary

    def test_result_summarization_none(self):
        """Result summarization should handle None."""
        logger = get_logger("summary_test_4")
        
        with ToolCallLogger(logger, "test_tool") as log:
            log.set_result(None)
            summary = log._summarize_result(None)
            assert summary == "None"

    def test_exception_handling(self):
        """ToolCallLogger should log exceptions and re-raise them."""
        logger = get_logger("exception_test")
        
        with pytest.raises(ValueError):
            with ToolCallLogger(logger, "failing_tool"):
                raise ValueError("Test error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
