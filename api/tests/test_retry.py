"""
Tests for retry utilities.

Tests cover:
- RetryConfig configuration
- is_retryable_error detection
- calculate_delay with exponential backoff
- with_retry and with_db_retry decorators
- execute_with_retry and execute_db_operation functions
- RetryContext context manager
- RetryableOperation class
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import psycopg2

from lib.retry import (
    RetryConfig,
    DEFAULT_DB_CONFIG,
    is_retryable_error,
    calculate_delay,
    RETRYABLE_ERROR_PATTERNS,
    with_retry,
    with_db_retry,
    execute_with_retry,
    execute_db_operation,
    RetryContext,
    RetryableOperation,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def basic_config():
    """Basic retry configuration for testing."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.01,  # Short delays for testing
        max_delay=0.1,
        jitter=False,  # Disable jitter for predictable tests
    )


@pytest.fixture
def db_config():
    """Database retry configuration for testing."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.01,
        max_delay=0.1,
        jitter=False,
        retryable_exceptions=(
            psycopg2.OperationalError,
            psycopg2.InterfaceError,
        ),
    )


@pytest.fixture
def mock_operation():
    """Mock operation that can be configured to fail/succeed."""
    return Mock()


# =============================================================================
# Test RetryConfig
# =============================================================================


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        
        assert config.max_attempts >= 1
        assert config.base_delay >= 0
        assert config.max_delay >= config.base_delay
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert 0 <= config.jitter_range <= 1
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
            jitter_range=0.2,
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.jitter_range == 0.2
    
    def test_with_callback(self):
        """Test configuration with retry callback."""
        callback = Mock()
        config = RetryConfig(
            max_attempts=3,
            on_retry=callback,
        )
        
        assert config.on_retry is callback
    
    def test_with_retryable_exceptions(self):
        """Test configuration with custom retryable exceptions."""
        config = RetryConfig(
            retryable_exceptions=(ValueError, TypeError),
        )
        
        assert ValueError in config.retryable_exceptions
        assert TypeError in config.retryable_exceptions
    
    @patch.dict("os.environ", {"RETRY_MAX_ATTEMPTS": "5", "RETRY_BASE_DELAY": "2.0"})
    def test_env_var_defaults(self):
        """Test configuration from environment variables."""
        config = RetryConfig()
        
        assert config.max_attempts == 5
        assert config.base_delay == 2.0


# =============================================================================
# Test is_retryable_error
# =============================================================================


class TestIsRetryableError:
    """Tests for is_retryable_error function."""
    
    def test_operational_error_connection_closed(self):
        """Test OperationalError with connection closed message."""
        error = psycopg2.OperationalError("SSL connection has been closed unexpectedly")
        assert is_retryable_error(error) is True
    
    def test_operational_error_connection_reset(self):
        """Test OperationalError with connection reset message."""
        error = psycopg2.OperationalError("connection reset by peer")
        assert is_retryable_error(error) is True
    
    def test_operational_error_timeout(self):
        """Test OperationalError with timeout message."""
        error = psycopg2.OperationalError("connection timed out")
        assert is_retryable_error(error) is True
    
    def test_operational_error_server_closed(self):
        """Test OperationalError with server closed message."""
        error = psycopg2.OperationalError("server closed the connection unexpectedly")
        assert is_retryable_error(error) is True
    
    def test_interface_error_connection_closed(self):
        """Test InterfaceError with connection closed message."""
        error = psycopg2.InterfaceError("connection already closed")
        assert is_retryable_error(error) is True
    
    def test_non_retryable_operational_error(self):
        """Test OperationalError that should not be retried."""
        error = psycopg2.OperationalError("FATAL: password authentication failed")
        assert is_retryable_error(error) is False
    
    def test_programming_error(self):
        """Test ProgrammingError (should not be retried)."""
        error = psycopg2.ProgrammingError("syntax error")
        assert is_retryable_error(error) is False
    
    def test_data_error(self):
        """Test DataError (should not be retried)."""
        error = psycopg2.DataError("invalid input syntax")
        assert is_retryable_error(error) is False
    
    def test_generic_exception(self):
        """Test generic Exception (should not be retried)."""
        error = Exception("generic error")
        assert is_retryable_error(error) is False
    
    def test_value_error(self):
        """Test ValueError (should not be retried)."""
        error = ValueError("invalid value")
        assert is_retryable_error(error) is False
    
    def test_all_retryable_patterns(self):
        """Test all patterns in RETRYABLE_ERROR_PATTERNS are detected."""
        for pattern in RETRYABLE_ERROR_PATTERNS:
            error = psycopg2.OperationalError(f"Error: {pattern}")
            assert is_retryable_error(error) is True, f"Pattern not detected: {pattern}"


# =============================================================================
# Test calculate_delay
# =============================================================================


class TestCalculateDelay:
    """Tests for calculate_delay function."""
    
    def test_first_attempt_delay(self, basic_config):
        """Test delay for first retry attempt."""
        delay = calculate_delay(0, basic_config)
        assert delay == basic_config.base_delay
    
    def test_exponential_backoff(self, basic_config):
        """Test exponential backoff calculation."""
        delay0 = calculate_delay(0, basic_config)
        delay1 = calculate_delay(1, basic_config)
        delay2 = calculate_delay(2, basic_config)
        
        assert delay1 == delay0 * basic_config.exponential_base
        assert delay2 == delay0 * (basic_config.exponential_base ** 2)
    
    def test_max_delay_cap(self, basic_config):
        """Test that delay is capped at max_delay."""
        delay = calculate_delay(10, basic_config)  # Should hit max
        assert delay <= basic_config.max_delay
    
    def test_jitter_adds_variation(self):
        """Test that jitter adds variation to delay."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=10.0,
            jitter=True,
            jitter_range=0.1,
        )
        
        delays = [calculate_delay(0, config) for _ in range(10)]
        # With jitter, not all delays should be equal
        unique_delays = set(round(d, 6) for d in delays)
        assert len(unique_delays) > 1
    
    def test_no_jitter(self):
        """Test calculation without jitter."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=10.0,
            jitter=False,
        )
        
        delays = [calculate_delay(0, config) for _ in range(10)]
        # Without jitter, all delays should be equal
        assert all(d == delays[0] for d in delays)
    
    def test_delay_never_negative(self, basic_config):
        """Test that delay is never negative."""
        for attempt in range(100):
            delay = calculate_delay(attempt, basic_config)
            assert delay >= 0


# =============================================================================
# Test with_retry Decorator
# =============================================================================


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""
    
    def test_successful_operation_no_retry(self, basic_config):
        """Test that successful operations don't trigger retry."""
        call_count = 0
        
        @with_retry(config=basic_config)
        def successful_op():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_op()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure_then_success(self, basic_config):
        """Test retry when first attempts fail but eventually succeeds."""
        call_count = 0
        
        @with_retry(
            config=basic_config,
            retryable_exceptions=(ValueError,),
        )
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient error")
            return "success"
        
        result = eventually_succeeds()
        
        assert result == "success"
        assert call_count == 2
    
    def test_max_attempts_exceeded(self, basic_config):
        """Test that error is raised after max attempts."""
        call_count = 0
        
        @with_retry(
            config=basic_config,
            retryable_exceptions=(ValueError,),
        )
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")
        
        with pytest.raises(ValueError, match="persistent error"):
            always_fails()
        
        assert call_count == basic_config.max_attempts
    
    def test_non_retryable_error_fails_immediately(self, basic_config):
        """Test that non-retryable errors fail immediately."""
        call_count = 0
        
        @with_retry(
            config=basic_config,
            retryable_exceptions=(ValueError,),
        )
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("non-retryable")
        
        with pytest.raises(TypeError, match="non-retryable"):
            raises_type_error()
        
        assert call_count == 1
    
    def test_custom_max_attempts(self, basic_config):
        """Test custom max_attempts parameter."""
        call_count = 0
        
        @with_retry(max_attempts=5, retryable_exceptions=(ValueError,), base_delay=0.001)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("error")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert call_count == 5


# =============================================================================
# Test with_db_retry Decorator
# =============================================================================


class TestWithDbRetryDecorator:
    """Tests for with_db_retry decorator."""
    
    def test_successful_db_operation(self):
        """Test successful database operation."""
        @with_db_retry(base_delay=0.001)
        def get_data(conn):
            return {"id": 1, "name": "test"}
        
        mock_conn = Mock()
        result = get_data(mock_conn)
        
        assert result == {"id": 1, "name": "test"}
    
    def test_retry_on_operational_error(self):
        """Test retry on OperationalError."""
        call_count = 0
        
        @with_db_retry(max_attempts=3, base_delay=0.001)
        def db_operation(conn):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise psycopg2.OperationalError("connection reset by peer")
            return "success"
        
        mock_conn = Mock()
        result = db_operation(mock_conn)
        
        assert result == "success"
        assert call_count == 2
    
    def test_retry_on_interface_error(self):
        """Test retry on InterfaceError."""
        call_count = 0
        
        @with_db_retry(max_attempts=3, base_delay=0.001)
        def db_operation(conn):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise psycopg2.InterfaceError("connection already closed")
            return "success"
        
        mock_conn = Mock()
        result = db_operation(mock_conn)
        
        assert result == "success"
        assert call_count == 2
    
    def test_no_retry_on_programming_error(self):
        """Test no retry on ProgrammingError."""
        call_count = 0
        
        @with_db_retry(max_attempts=3, base_delay=0.001)
        def bad_sql(conn):
            nonlocal call_count
            call_count += 1
            raise psycopg2.ProgrammingError("syntax error at or near")
        
        mock_conn = Mock()
        
        with pytest.raises(psycopg2.ProgrammingError):
            bad_sql(mock_conn)
        
        assert call_count == 1


# =============================================================================
# Test execute_with_retry
# =============================================================================


class TestExecuteWithRetry:
    """Tests for execute_with_retry function."""
    
    def test_successful_execution(self, basic_config):
        """Test successful execution without retry."""
        result = execute_with_retry(
            lambda: "success",
            config=basic_config,
        )
        
        assert result == "success"
    
    def test_retry_on_configured_exception(self, basic_config):
        """Test retry on configured exception type."""
        call_count = 0
        basic_config = RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            jitter=False,
            retryable_exceptions=(ValueError,),
        )
        
        def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient")
            return "success"
        
        result = execute_with_retry(operation, config=basic_config)
        
        assert result == "success"
        assert call_count == 2
    
    def test_callback_called_on_retry(self, basic_config):
        """Test that callback is called on retry."""
        callback = Mock()
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.001,
            jitter=False,
            retryable_exceptions=(ValueError,),
            on_retry=callback,
        )
        
        call_count = 0
        
        def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient")
            return "success"
        
        result = execute_with_retry(operation, config=config)
        
        assert result == "success"
        callback.assert_called_once()
        # Verify callback arguments
        args, kwargs = callback.call_args
        assert isinstance(args[0], ValueError)  # error
        assert args[1] == 1  # attempt number
        assert args[2] >= 0  # delay


# =============================================================================
# Test execute_db_operation
# =============================================================================


class TestExecuteDbOperation:
    """Tests for execute_db_operation function."""
    
    def test_successful_operation(self):
        """Test successful database operation."""
        config = RetryConfig(max_attempts=3, base_delay=0.001)
        result = execute_db_operation(
            lambda: {"id": 1},
            config=config,
        )
        
        assert result == {"id": 1}
    
    def test_retry_on_connection_error(self):
        """Test retry on connection error."""
        call_count = 0
        config = RetryConfig(max_attempts=3, base_delay=0.001, jitter=False)
        
        def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise psycopg2.OperationalError("SSL connection has been closed unexpectedly")
            return "success"
        
        result = execute_db_operation(operation, config=config)
        
        assert result == "success"
        assert call_count == 2
    
    def test_no_retry_on_constraint_error(self):
        """Test no retry on constraint violation."""
        call_count = 0
        config = RetryConfig(max_attempts=3, base_delay=0.001)
        
        def operation():
            nonlocal call_count
            call_count += 1
            raise psycopg2.IntegrityError("duplicate key value violates unique constraint")
        
        with pytest.raises(psycopg2.IntegrityError):
            execute_db_operation(operation, config=config)
        
        assert call_count == 1


# =============================================================================
# Test RetryContext
# =============================================================================


class TestRetryContext:
    """Tests for RetryContext context manager."""
    
    def test_should_retry_initial(self):
        """Test should_retry returns True initially."""
        with RetryContext(max_attempts=3) as ctx:
            assert ctx.should_retry() is True
    
    def test_should_retry_decrements(self):
        """Test should_retry decrements on record_failure."""
        with RetryContext(max_attempts=3, base_delay=0.001) as ctx:
            assert ctx.should_retry() is True
            ctx.record_failure(ValueError("error"))
            assert ctx.should_retry() is True
            ctx.record_failure(ValueError("error"))
            assert ctx.should_retry() is True
            ctx.record_failure(ValueError("error"))
            assert ctx.should_retry() is False
    
    def test_last_error_recorded(self):
        """Test that last error is recorded."""
        error = ValueError("test error")
        
        with RetryContext(max_attempts=3, base_delay=0.001) as ctx:
            ctx.record_failure(error)
            assert ctx.last_error is error
    
    def test_attempt_counter(self):
        """Test that attempt counter increments."""
        with RetryContext(max_attempts=3, base_delay=0.001) as ctx:
            assert ctx.attempt == 0
            ctx.record_failure(ValueError())
            assert ctx.attempt == 1
            ctx.record_failure(ValueError())
            assert ctx.attempt == 2
    
    def test_practical_usage(self):
        """Test practical retry loop pattern."""
        attempt_count = 0
        result = None
        
        with RetryContext(max_attempts=3, base_delay=0.001) as ctx:
            while ctx.should_retry():
                try:
                    attempt_count += 1
                    if attempt_count < 2:
                        raise ValueError("transient")
                    result = "success"
                    break
                except ValueError as e:
                    ctx.record_failure(e)
        
        assert result == "success"
        assert attempt_count == 2


# =============================================================================
# Test RetryableOperation
# =============================================================================


class TestRetryableOperation:
    """Tests for RetryableOperation class."""
    
    def test_successful_operation(self):
        """Test successful operation."""
        class SuccessOp(RetryableOperation):
            def execute(self):
                return "success"
        
        op = SuccessOp(max_attempts=3, base_delay=0.001)
        result = op.run()
        
        assert result == "success"
        assert op.attempt == 1
        assert op.last_error is None
    
    def test_retry_then_success(self):
        """Test operation that fails then succeeds."""
        class EventualSuccess(RetryableOperation):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.call_count = 0
            
            def execute(self):
                self.call_count += 1
                if self.call_count < 2:
                    raise psycopg2.OperationalError("connection reset by peer")
                return "success"
        
        op = EventualSuccess(max_attempts=3, base_delay=0.001)
        result = op.run()
        
        assert result == "success"
        assert op.call_count == 2
    
    def test_on_failure_callback(self):
        """Test that on_failure is called."""
        failures = []
        
        class FailingOp(RetryableOperation):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.call_count = 0
            
            def execute(self):
                self.call_count += 1
                if self.call_count < 2:
                    raise psycopg2.OperationalError("connection lost")
                return "success"
            
            def on_failure(self, error):
                failures.append(error)
        
        op = FailingOp(max_attempts=3, base_delay=0.001)
        op.run()
        
        assert len(failures) == 1
        assert isinstance(failures[0], psycopg2.OperationalError)
    
    def test_on_success_callback(self):
        """Test that on_success is called."""
        results = []
        
        class SuccessOp(RetryableOperation):
            def execute(self):
                return {"status": "ok"}
            
            def on_success(self, result):
                results.append(result)
        
        op = SuccessOp(max_attempts=3, base_delay=0.001)
        op.run()
        
        assert len(results) == 1
        assert results[0] == {"status": "ok"}
    
    def test_custom_should_retry(self):
        """Test custom should_retry logic."""
        class CustomRetry(RetryableOperation):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.call_count = 0
            
            def execute(self):
                self.call_count += 1
                raise ValueError("test error")
            
            def should_retry(self, error):
                # Only retry on ValueError
                return isinstance(error, ValueError)
        
        op = CustomRetry(max_attempts=3, base_delay=0.001)
        
        with pytest.raises(ValueError):
            op.run()
        
        assert op.call_count == 3
    
    def test_not_implemented_error(self):
        """Test that execute must be implemented."""
        op = RetryableOperation(max_attempts=3)
        
        with pytest.raises(NotImplementedError):
            op.run()


# =============================================================================
# Integration Tests
# =============================================================================


class TestRetryIntegration:
    """Integration tests for retry functionality."""
    
    def test_decorator_with_arguments(self):
        """Test decorator with arguments preserves function."""
        @with_db_retry(max_attempts=2, base_delay=0.001)
        def my_function(x, y, z=None):
            """Docstring for my_function."""
            return x + y + (z or 0)
        
        assert my_function(1, 2) == 3
        assert my_function(1, 2, z=3) == 6
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "Docstring for my_function."
    
    def test_timing_of_retries(self):
        """Test that retries have appropriate delays."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.05,
            max_delay=1.0,
            jitter=False,
            retryable_exceptions=(ValueError,),
        )
        
        times = []
        call_count = 0
        
        def operation():
            nonlocal call_count
            times.append(time.time())
            call_count += 1
            if call_count < 3:
                raise ValueError("error")
            return "success"
        
        start = time.time()
        result = execute_with_retry(operation, config=config)
        total_time = time.time() - start
        
        assert result == "success"
        assert call_count == 3
        
        # Verify delays: first delay should be ~0.05s, second ~0.1s
        # Total should be around 0.15s
        assert 0.1 < total_time < 0.3  # Allow some margin
    
    def test_nested_retry_operations(self):
        """Test nested retry operations."""
        inner_count = 0
        outer_count = 0
        
        @with_retry(max_attempts=2, retryable_exceptions=(ValueError,), base_delay=0.001)
        def inner():
            nonlocal inner_count
            inner_count += 1
            if inner_count < 2:
                raise ValueError("inner error")
            return "inner success"
        
        @with_retry(max_attempts=2, retryable_exceptions=(TypeError,), base_delay=0.001)
        def outer():
            nonlocal outer_count
            outer_count += 1
            return inner()
        
        result = outer()
        
        assert result == "inner success"
        assert inner_count == 2
        assert outer_count == 1
