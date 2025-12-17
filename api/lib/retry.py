"""
Retry utilities for geo-base API Server.

This module provides retry functionality for database operations and general functions
using tenacity. It implements exponential backoff with configurable retry conditions.

Features:
- Automatic retry for transient database errors
- Exponential backoff with jitter
- Configurable retry count and delays
- Detailed logging of retry attempts
- Support for both sync and async operations
- Database operation-specific retry logic

Usage:
    from lib.retry import with_db_retry, retry_on_error, RetryConfig

    # Using decorator with defaults
    @with_db_retry()
    def get_tilesets(conn):
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tilesets")
            return cur.fetchall()

    # Using decorator with custom config
    @with_db_retry(max_attempts=5, base_delay=2.0)
    def important_operation(conn):
        # ...

    # Using execute_with_retry for one-off operations
    result = execute_with_retry(
        lambda: risky_operation(),
        config=RetryConfig(max_attempts=3),
    )

Configuration:
    Retry behavior can be customized via environment variables:
    - RETRY_MAX_ATTEMPTS: Maximum retry attempts (default: 3)
    - RETRY_BASE_DELAY: Base delay between retries in seconds (default: 0.5)
    - RETRY_MAX_DELAY: Maximum delay between retries in seconds (default: 10)
"""

import functools
import logging
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

import psycopg2

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for generic return types
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 0.5)
        max_delay: Maximum delay between retries in seconds (default: 10)
        exponential_base: Base for exponential backoff (default: 2)
        jitter: Whether to add random jitter to delays (default: True)
        jitter_range: Range for jitter as fraction of delay (default: 0.1)
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called on each retry
    """
    max_attempts: int = field(
        default_factory=lambda: int(os.environ.get("RETRY_MAX_ATTEMPTS", "3"))
    )
    base_delay: float = field(
        default_factory=lambda: float(os.environ.get("RETRY_BASE_DELAY", "0.5"))
    )
    max_delay: float = field(
        default_factory=lambda: float(os.environ.get("RETRY_MAX_DELAY", "10"))
    )
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    retryable_exceptions: tuple = field(default_factory=tuple)
    on_retry: Optional[Callable[[Exception, int, float], None]] = None


# Default configuration for database operations
DEFAULT_DB_CONFIG = RetryConfig(
    retryable_exceptions=(
        psycopg2.OperationalError,
        psycopg2.InterfaceError,
        psycopg2.InternalError,
    )
)


# =============================================================================
# Helper Functions
# =============================================================================


# Common retryable error patterns for database operations
RETRYABLE_ERROR_PATTERNS: List[str] = [
    "ssl connection has been closed unexpectedly",
    "connection reset by peer",
    "connection timed out",
    "server closed the connection unexpectedly",
    "could not receive data from server",
    "network is unreachable",
    "connection refused",
    "could not connect to server",
    "the database system is starting up",
    "connection already closed",
    "cursor already closed",
    "no connection to the server",
    "connection terminated",
    "connection lost",
    "deadlock detected",
    "could not serialize access",
    "statement timeout",
]


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable (transient issues).
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error is retryable, False otherwise
    """
    # Check exception type first
    if isinstance(error, (
        psycopg2.OperationalError,
        psycopg2.InterfaceError,
    )):
        error_msg = str(error).lower()
        return any(pattern in error_msg for pattern in RETRYABLE_ERROR_PATTERNS)
    
    # Deadlock is retryable
    if isinstance(error, psycopg2.extensions.TransactionRollbackError):
        return True
    
    return False


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """
    Calculate delay for the next retry attempt using exponential backoff.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    # Calculate exponential delay
    delay = config.base_delay * (config.exponential_base ** attempt)
    
    # Cap at max_delay
    delay = min(delay, config.max_delay)
    
    # Add jitter if enabled
    if config.jitter:
        jitter_amount = delay * config.jitter_range
        delay = delay + random.uniform(-jitter_amount, jitter_amount)
    
    return max(0, delay)


def default_retry_callback(
    error: Exception,
    attempt: int,
    delay: float,
) -> None:
    """
    Default callback function for retry events.
    
    Args:
        error: The exception that triggered the retry
        attempt: Current attempt number (1-indexed)
        delay: Delay before next retry
    """
    logger.warning(
        f"Retry attempt {attempt} after error: {type(error).__name__}: {error}. "
        f"Waiting {delay:.2f}s before next attempt."
    )


# =============================================================================
# Retry Decorators
# =============================================================================


def with_retry(
    config: Optional[RetryConfig] = None,
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    retryable_exceptions: Optional[tuple] = None,
) -> Callable[[F], F]:
    """
    Decorator for retrying functions on transient errors.
    
    Can be used with or without parentheses:
        @with_retry
        def my_function(): ...
        
        @with_retry(max_attempts=5)
        def my_function(): ...
    
    Args:
        config: RetryConfig instance (overrides other parameters)
        max_attempts: Maximum retry attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Build configuration
            retry_config = config or RetryConfig()
            
            # Override with explicit parameters
            if max_attempts is not None:
                retry_config = RetryConfig(
                    max_attempts=max_attempts,
                    base_delay=retry_config.base_delay,
                    max_delay=retry_config.max_delay,
                    exponential_base=retry_config.exponential_base,
                    jitter=retry_config.jitter,
                    jitter_range=retry_config.jitter_range,
                    retryable_exceptions=retry_config.retryable_exceptions,
                    on_retry=retry_config.on_retry,
                )
            if base_delay is not None:
                retry_config = RetryConfig(
                    max_attempts=retry_config.max_attempts,
                    base_delay=base_delay,
                    max_delay=retry_config.max_delay,
                    exponential_base=retry_config.exponential_base,
                    jitter=retry_config.jitter,
                    jitter_range=retry_config.jitter_range,
                    retryable_exceptions=retry_config.retryable_exceptions,
                    on_retry=retry_config.on_retry,
                )
            if max_delay is not None:
                retry_config = RetryConfig(
                    max_attempts=retry_config.max_attempts,
                    base_delay=retry_config.base_delay,
                    max_delay=max_delay,
                    exponential_base=retry_config.exponential_base,
                    jitter=retry_config.jitter,
                    jitter_range=retry_config.jitter_range,
                    retryable_exceptions=retry_config.retryable_exceptions,
                    on_retry=retry_config.on_retry,
                )
            if retryable_exceptions is not None:
                retry_config = RetryConfig(
                    max_attempts=retry_config.max_attempts,
                    base_delay=retry_config.base_delay,
                    max_delay=retry_config.max_delay,
                    exponential_base=retry_config.exponential_base,
                    jitter=retry_config.jitter,
                    jitter_range=retry_config.jitter_range,
                    retryable_exceptions=retryable_exceptions,
                    on_retry=retry_config.on_retry,
                )
            
            return execute_with_retry(
                lambda: func(*args, **kwargs),
                config=retry_config,
            )
        
        return wrapper  # type: ignore
    
    return decorator


def with_db_retry(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
) -> Callable[[F], F]:
    """
    Decorator for retrying database operations on transient errors.
    
    This is a specialized version of with_retry that uses database-specific
    default configuration and error detection.
    
    Args:
        max_attempts: Maximum retry attempts (default: 3)
        base_delay: Initial delay between retries (default: 0.5)
        max_delay: Maximum delay between retries (default: 10)
        
    Returns:
        Decorated function with database retry logic
        
    Example:
        @with_db_retry()
        def get_tilesets(conn):
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tilesets")
                return cur.fetchall()
                
        @with_db_retry(max_attempts=5)
        def important_query(conn, tileset_id):
            # ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Build configuration with DB defaults
            config = RetryConfig(
                max_attempts=max_attempts or DEFAULT_DB_CONFIG.max_attempts,
                base_delay=base_delay or DEFAULT_DB_CONFIG.base_delay,
                max_delay=max_delay or DEFAULT_DB_CONFIG.max_delay,
                retryable_exceptions=DEFAULT_DB_CONFIG.retryable_exceptions,
                on_retry=default_retry_callback,
            )
            
            return execute_db_operation(
                lambda: func(*args, **kwargs),
                config=config,
            )
        
        return wrapper  # type: ignore
    
    return decorator


# =============================================================================
# Execution Functions
# =============================================================================


def execute_with_retry(
    operation: Callable[[], T],
    config: Optional[RetryConfig] = None,
) -> T:
    """
    Execute a function with retry logic.
    
    Args:
        operation: Function to execute (no arguments)
        config: Retry configuration
        
    Returns:
        Result of the operation
        
    Raises:
        The last exception if all retries fail
        
    Example:
        result = execute_with_retry(
            lambda: risky_operation(),
            config=RetryConfig(max_attempts=5),
        )
    """
    retry_config = config or RetryConfig()
    last_error: Optional[Exception] = None
    
    for attempt in range(retry_config.max_attempts):
        try:
            return operation()
            
        except Exception as e:
            last_error = e
            
            # Check if error is retryable
            should_retry = False
            
            if retry_config.retryable_exceptions:
                should_retry = isinstance(e, retry_config.retryable_exceptions)
            else:
                # Default: retry on common transient errors
                should_retry = is_retryable_error(e)
            
            if not should_retry or attempt >= retry_config.max_attempts - 1:
                # Not retryable or last attempt - raise
                logger.error(
                    f"Operation failed after {attempt + 1} attempt(s): "
                    f"{type(e).__name__}: {e}"
                )
                raise
            
            # Calculate delay and wait
            delay = calculate_delay(attempt, retry_config)
            
            # Call retry callback if configured
            if retry_config.on_retry:
                retry_config.on_retry(e, attempt + 1, delay)
            else:
                default_retry_callback(e, attempt + 1, delay)
            
            time.sleep(delay)
    
    # Should not reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state: retry exhausted without exception")


def execute_db_operation(
    operation: Callable[[], T],
    config: Optional[RetryConfig] = None,
) -> T:
    """
    Execute a database operation with retry logic specific to DB errors.
    
    This function uses database-specific error detection to determine
    if an error is retryable.
    
    Args:
        operation: Function to execute (no arguments)
        config: Retry configuration
        
    Returns:
        Result of the operation
        
    Raises:
        The last exception if all retries fail
        
    Example:
        def my_query():
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tilesets")
                return cur.fetchall()
                
        result = execute_db_operation(my_query)
    """
    retry_config = config or DEFAULT_DB_CONFIG
    last_error: Optional[Exception] = None
    
    for attempt in range(retry_config.max_attempts):
        try:
            return operation()
            
        except Exception as e:
            last_error = e
            
            # Check if error is retryable using DB-specific logic
            if not is_retryable_error(e):
                logger.error(
                    f"Non-retryable database error: {type(e).__name__}: {e}"
                )
                raise
            
            if attempt >= retry_config.max_attempts - 1:
                logger.error(
                    f"Database operation failed after {attempt + 1} attempts: "
                    f"{type(e).__name__}: {e}"
                )
                raise
            
            # Calculate delay and wait
            delay = calculate_delay(attempt, retry_config)
            
            # Call retry callback
            if retry_config.on_retry:
                retry_config.on_retry(e, attempt + 1, delay)
            else:
                default_retry_callback(e, attempt + 1, delay)
            
            time.sleep(delay)
    
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state: retry exhausted without exception")


# =============================================================================
# Context Managers
# =============================================================================


class RetryContext:
    """
    Context manager for retry logic.
    
    Provides a convenient way to wrap code blocks with retry behavior.
    
    Example:
        with RetryContext(max_attempts=3) as ctx:
            while ctx.should_retry():
                try:
                    result = risky_operation()
                    break
                except TransientError as e:
                    ctx.record_failure(e)
        
        if ctx.last_error:
            raise ctx.last_error
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
    ):
        self.config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
        )
        self.attempt = 0
        self.last_error: Optional[Exception] = None
        self._entered = False
    
    def __enter__(self) -> "RetryContext":
        self._entered = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # Don't suppress exceptions
        return False
    
    def should_retry(self) -> bool:
        """Check if more retry attempts are available."""
        return self.attempt < self.config.max_attempts
    
    def record_failure(self, error: Exception) -> None:
        """
        Record a failure and wait before next attempt.
        
        Args:
            error: The exception that occurred
        """
        self.last_error = error
        self.attempt += 1
        
        if self.should_retry():
            delay = calculate_delay(self.attempt - 1, self.config)
            logger.warning(
                f"Retry context: attempt {self.attempt}/{self.config.max_attempts} "
                f"failed with {type(error).__name__}. Waiting {delay:.2f}s."
            )
            time.sleep(delay)
    
    @property
    def succeeded(self) -> bool:
        """Check if the operation succeeded (no errors recorded on last attempt)."""
        return self.last_error is None or (
            self.attempt < self.config.max_attempts and 
            not self.should_retry()
        )


# =============================================================================
# Utility Classes
# =============================================================================


class RetryableOperation:
    """
    Class for creating retryable operations with state.
    
    Useful when you need to maintain state across retry attempts
    or perform cleanup on failures.
    
    Example:
        class MyOperation(RetryableOperation):
            def execute(self):
                return expensive_operation()
            
            def on_failure(self, error):
                cleanup_resources()
        
        op = MyOperation(max_attempts=3)
        result = op.run()
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 10.0,
    ):
        self.config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
        )
        self.attempt = 0
        self.last_error: Optional[Exception] = None
    
    def execute(self) -> Any:
        """
        Execute the operation. Override this method in subclasses.
        """
        raise NotImplementedError("Subclasses must implement execute()")
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if the error should trigger a retry.
        Override this method to customize retry logic.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the operation should be retried
        """
        return is_retryable_error(error)
    
    def on_failure(self, error: Exception) -> None:
        """
        Called when an attempt fails. Override to add cleanup logic.
        
        Args:
            error: The exception that occurred
        """
        pass
    
    def on_success(self, result: Any) -> None:
        """
        Called when the operation succeeds. Override to add post-processing.
        
        Args:
            result: The result of the successful operation
        """
        pass
    
    def run(self) -> Any:
        """
        Run the operation with retry logic.
        
        Returns:
            Result of the operation
            
        Raises:
            The last exception if all retries fail
        """
        for attempt in range(self.config.max_attempts):
            self.attempt = attempt + 1
            
            try:
                result = self.execute()
                self.on_success(result)
                return result
                
            except Exception as e:
                self.last_error = e
                self.on_failure(e)
                
                if not self.should_retry(e) or attempt >= self.config.max_attempts - 1:
                    logger.error(
                        f"Operation failed after {attempt + 1} attempts: "
                        f"{type(e).__name__}: {e}"
                    )
                    raise
                
                delay = calculate_delay(attempt, self.config)
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{self.config.max_attempts}), "
                    f"retrying in {delay:.2f}s: {type(e).__name__}: {e}"
                )
                time.sleep(delay)
        
        if self.last_error:
            raise self.last_error
        raise RuntimeError("Unexpected state: retry exhausted without exception")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Configuration
    "RetryConfig",
    "DEFAULT_DB_CONFIG",
    # Helper functions
    "is_retryable_error",
    "calculate_delay",
    "RETRYABLE_ERROR_PATTERNS",
    # Decorators
    "with_retry",
    "with_db_retry",
    # Execution functions
    "execute_with_retry",
    "execute_db_operation",
    # Context manager
    "RetryContext",
    # Classes
    "RetryableOperation",
]
