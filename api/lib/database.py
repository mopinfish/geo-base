"""
Database connection management for geo-base API.

Supports both local development (connection pool) and
serverless environments (simple connections with SSL).
"""

import os
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import psycopg2
import psycopg2.pool

from lib.config import get_settings

# Connection pool (initialized lazily, used in development)
_pool: psycopg2.pool.SimpleConnectionPool | None = None


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
            minconn=1,
            maxconn=5,
        )
    return _pool


def get_connection() -> Generator:
    """
    Dependency for getting a database connection.

    In serverless environments, creates a new connection per request.
    In development, uses a connection pool.
    """
    settings = get_settings()
    
    if _is_serverless():
        # Serverless: create new connection per request with SSL
        dsn = _prepare_connection_string(settings.database_url)
        conn = None
        try:
            conn = psycopg2.connect(dsn)
            yield conn
        finally:
            if conn is not None:
                conn.close()
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
    """
    settings = get_settings()
    
    if _is_serverless():
        dsn = _prepare_connection_string(settings.database_url)
        conn = None
        try:
            conn = psycopg2.connect(dsn)
            yield conn
        finally:
            if conn is not None:
                conn.close()
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
            conn = psycopg2.connect(dsn, connect_timeout=10)
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
