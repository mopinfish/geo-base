"""
Database connection management for geo-base API.

Supports both local development (connection pool) and
serverless environments (simple connections with SSL).

Includes:
- TCP keepalive settings for stable connections
- Automatic retry logic for transient SSL errors
- Connection health checking
"""

import os
import time
import logging
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import psycopg2
import psycopg2.pool

from lib.config import get_settings

# Logger for connection diagnostics
logger = logging.getLogger(__name__)

# Connection pool (initialized lazily, used in development)
_pool: psycopg2.pool.SimpleConnectionPool | None = None

# Connection settings for serverless environments
CONNECTION_SETTINGS = {
    "connect_timeout": 10,      # Connection timeout in seconds
    "keepalives": 1,            # Enable TCP keepalives
    "keepalives_idle": 30,      # Seconds before sending first keepalive
    "keepalives_interval": 10,  # Seconds between keepalive probes
    "keepalives_count": 5,      # Number of failed probes before disconnect
}

# Retry settings
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5  # Base delay in seconds (exponential backoff)


def _is_serverless() -> bool:
    """Check if running in a serverless environment."""
    return os.environ.get("VERCEL") == "1" or "AWS_LAMBDA_FUNCTION_NAME" in os.environ


def _prepare_connection_string(database_url: str) -> str:
    """
    Prepare database connection string with SSL settings.
    
    For Supabase and production environments, SSL is required.
    """
    settings = get_settings()
    
    # Parse the URL
    parsed = urlparse(database_url)
    
    # Check if SSL params already exist
    query_params = parse_qs(parsed.query)
    
    # Add sslmode if not present and needed
    is_production = settings.is_production
    is_supabase = "supabase" in database_url.lower()
    
    if (is_production or is_supabase) and "sslmode" not in query_params:
        query_params["sslmode"] = ["require"]
    
    # Rebuild query string
    new_query = urlencode(query_params, doseq=True)
    
    # Rebuild URL
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def _is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable (transient connection issues).
    """
    error_msg = str(error).lower()
    retryable_patterns = [
        "ssl connection has been closed unexpectedly",
        "connection reset by peer",
        "connection timed out",
        "server closed the connection unexpectedly",
        "could not receive data from server",
        "network is unreachable",
        "connection refused",
    ]
    return any(pattern in error_msg for pattern in retryable_patterns)


def _create_serverless_connection(dsn: str):
    """
    Create a database connection with keepalive settings for serverless.
    
    Args:
        dsn: Database connection string
        
    Returns:
        psycopg2 connection object
        
    Raises:
        psycopg2.OperationalError: If connection fails after all retries
    """
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            conn = psycopg2.connect(
                dsn,
                **CONNECTION_SETTINGS
            )
            
            # Verify connection is alive
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            
            if attempt > 0:
                logger.info(f"Database connection succeeded on attempt {attempt + 1}")
            
            return conn
            
        except psycopg2.OperationalError as e:
            last_error = e
            
            if not _is_retryable_error(e):
                # Non-retryable error, raise immediately
                logger.error(f"Non-retryable database error: {e}")
                raise
            
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (attempt + 1)
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                    f"retrying in {delay}s: {e}"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Database connection failed after {MAX_RETRIES} attempts: {e}"
                )
    
    raise last_error


def get_pool() -> psycopg2.pool.SimpleConnectionPool:
    """
    Get or create the connection pool.
    
    Used in development/non-serverless environments.
    """
    global _pool
    if _pool is None:
        settings = get_settings()
        dsn = _prepare_connection_string(settings.database_url)
        _pool = psycopg2.pool.SimpleConnectionPool(
            dsn=dsn,
            minconn=2,
            maxconn=20,  # Increased from 5 to handle concurrent tile requests
        )
    return _pool


def get_connection() -> Generator:
    """
    Dependency for getting a database connection.

    In serverless environments, creates a new connection per request
    with keepalive settings and retry logic.
    In development, uses a connection pool.
    """
    settings = get_settings()
    
    if _is_serverless():
        # Serverless: create new connection per request with SSL and keepalive
        dsn = _prepare_connection_string(settings.database_url)
        conn = None
        try:
            conn = _create_serverless_connection(dsn)
            yield conn
        except psycopg2.OperationalError:
            # Re-raise to let FastAPI handle the error
            raise
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass  # Ignore errors during cleanup
    else:
        # Development: use connection pool
        pool = get_pool()
        conn = None
        try:
            conn = pool.getconn()
            yield conn
        finally:
            if conn is not None:
                pool.putconn(conn)


@contextmanager
def get_db_connection():
    """
    Context manager for getting a database connection.
    
    Includes retry logic for serverless environments.
    """
    settings = get_settings()
    
    if _is_serverless():
        dsn = _prepare_connection_string(settings.database_url)
        conn = None
        try:
            conn = _create_serverless_connection(dsn)
            yield conn
        except psycopg2.OperationalError:
            raise
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    else:
        pool = get_pool()
        conn = None
        try:
            conn = pool.getconn()
            yield conn
        finally:
            if conn is not None:
                pool.putconn(conn)


def close_pool():
    """Close all connections in the pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def check_database_connection() -> dict:
    """
    Check if database connection is working.
    
    Returns dict with status and error details.
    """
    settings = get_settings()
    
    try:
        dsn = _prepare_connection_string(settings.database_url)
        
        if _is_serverless():
            conn = psycopg2.connect(dsn, **CONNECTION_SETTINGS)
        else:
            conn = get_pool().getconn()
        
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()[0] == 1
            return {"connected": result, "error": None}
        finally:
            if _is_serverless():
                conn.close()
            else:
                get_pool().putconn(conn)
                
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        # Simplify common error messages
        if "could not connect to server" in error_msg:
            return {"connected": False, "error": "Connection refused - check host/port"}
        elif "password authentication failed" in error_msg:
            return {"connected": False, "error": "Authentication failed - check password"}
        elif "SSL" in error_msg:
            return {"connected": False, "error": f"SSL error: {error_msg}"}
        elif "timeout" in error_msg.lower():
            return {"connected": False, "error": "Connection timeout"}
        else:
            return {"connected": False, "error": error_msg}
    except Exception as e:
        return {"connected": False, "error": str(e)}


def check_postgis_extension() -> dict:
    """
    Check if PostGIS extension is available.
    
    Returns dict with status and version.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT PostGIS_Version()")
                version = cur.fetchone()
                if version:
                    return {"available": True, "version": version[0]}
                return {"available": False, "error": "PostGIS not installed"}
    except Exception as e:
        return {"available": False, "error": str(e)}
