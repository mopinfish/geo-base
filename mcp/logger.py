"""
Logging configuration for geo-base MCP Server.

Provides structured logging with configurable log levels
and formatted output for debugging and monitoring.

Usage:
    from logger import get_logger

    logger = get_logger(__name__)
    logger.info("Tool called", extra={"tool": "list_tilesets"})
"""

import logging
import os
import sys
from functools import lru_cache
from typing import Any


class MCPFormatter(logging.Formatter):
    """
    Custom formatter for MCP server logs.
    
    Formats logs with timestamp, level, logger name, and message.
    Includes extra fields if provided.
    """

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        # Add extra fields to message if present
        base_message = super().format(record)
        
        # Check for extra fields (exclude standard LogRecord attributes)
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'taskName', 'message', 'asctime',
        }
        
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith('_')
        }
        
        if extra_fields:
            extra_str = " | " + " ".join(f"{k}={v}" for k, v in extra_fields.items())
            return base_message + extra_str
        
        return base_message


class ToolCallLogger:
    """
    Context manager for logging tool calls with timing and result tracking.
    
    Usage:
        async def my_tool(param: str) -> dict:
            with ToolCallLogger(logger, "my_tool", param=param) as log:
                result = await process(param)
                log.set_result(result)
                return result
    """

    def __init__(
        self,
        logger: logging.Logger,
        tool_name: str,
        **params: Any,
    ):
        self.logger = logger
        self.tool_name = tool_name
        self.params = params
        self.result: Any = None
        self.error: Exception | None = None
        self._start_time: float = 0

    def __enter__(self) -> "ToolCallLogger":
        import time
        self._start_time = time.time()
        
        # Log tool call start
        self.logger.info(
            f"Tool '{self.tool_name}' called",
            extra={"tool": self.tool_name, "params": str(self.params)},
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        import time
        elapsed_ms = (time.time() - self._start_time) * 1000

        if exc_val is not None:
            # Log error
            self.logger.error(
                f"Tool '{self.tool_name}' failed: {exc_val}",
                extra={
                    "tool": self.tool_name,
                    "elapsed_ms": f"{elapsed_ms:.2f}",
                    "error": str(exc_val),
                },
                exc_info=True,
            )
            return False  # Re-raise exception

        # Log success
        result_summary = self._summarize_result(self.result)
        self.logger.info(
            f"Tool '{self.tool_name}' completed",
            extra={
                "tool": self.tool_name,
                "elapsed_ms": f"{elapsed_ms:.2f}",
                "result": result_summary,
            },
        )
        return False

    def set_result(self, result: Any) -> None:
        """Set the result for logging."""
        self.result = result

    def _summarize_result(self, result: Any) -> str:
        """Create a brief summary of the result for logging."""
        if result is None:
            return "None"
        
        if isinstance(result, dict):
            if "error" in result:
                return f"error: {result['error']}"
            if "count" in result:
                return f"count={result['count']}"
            if "tilesets" in result:
                return f"tilesets={len(result['tilesets'])}"
            if "features" in result:
                return f"features={len(result['features'])}"
            if "results" in result:
                return f"results={len(result['results'])}"
            if "id" in result:
                return f"id={result['id']}"
            return f"dict with {len(result)} keys"
        
        if isinstance(result, list):
            return f"list with {len(result)} items"
        
        if isinstance(result, str):
            if len(result) > 50:
                return f"str({len(result)} chars)"
            return f"'{result}'"
        
        return str(type(result).__name__)


def get_log_level() -> int:
    """
    Get log level from environment variable.
    
    Supports: DEBUG, INFO, WARNING, ERROR, CRITICAL
    Default: INFO
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    return level_map.get(level_name, logging.INFO)


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Loggers are cached to avoid duplicate handlers.
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        Configured logging.Logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("Starting operation")
        logger.debug("Debug details", extra={"key": "value"})
        logger.error("Something went wrong", exc_info=True)
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(get_log_level())
        
        # Create console handler
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(get_log_level())
        handler.setFormatter(MCPFormatter())
        
        logger.addHandler(handler)
        
        # Prevent propagation to avoid duplicate logs
        logger.propagate = False
    
    return logger


def log_tool_call(logger: logging.Logger, tool_name: str, **params: Any):
    """
    Decorator factory for logging tool calls.
    
    Usage:
        @log_tool_call(logger, "my_tool")
        async def my_tool(param: str) -> dict:
            return await process(param)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with ToolCallLogger(logger, tool_name, **params, **kwargs) as log:
                result = await func(*args, **kwargs)
                log.set_result(result)
                return result
        return wrapper
    return decorator


# Create a default logger for the MCP server
mcp_logger = get_logger("geo-base-mcp")
