"""
Database connection management for geo-base API.

Supports both local development (connection pool) and
serverless environments (simple connections).
"""

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool

from lib.config import get_settings

# Connection pool (initialized lazily, used in development)
_pool: psycopg2.pool.SimpleConnectionPool | None = None


def _is_serverless() -> bool:
    """Check if running in a serverless environment."""
    # Vercel sets VERCEL=1 in serverless functions
    # AWS Lambda sets AWS_LAMBDA_FUNCTION_NAME
    return os.environ.get("VERCEL") == "1" or "AWS_LAMBDA_FUNCTION_NAME" in os.environ


def _get_connection_params() -> dict:
    """Get database connection parameters."""
    settings = get_settings()
    
    params = {
        "dsn": settings.database_url,
    }
    
    # For Supabase/production, SSL is typically required
    if settings.environment == "production" or "supabase" in settings.database_url.lower():
        params["sslmode"] = "require"
    
    return params


def get_pool() -> psycopg2.pool.SimpleConnectionPool:
    """
    Get or create the connection pool.
    
    Used in development/non-serverless environments.
    """
    global _pool
    if _pool is None:
        params = _get_connection_params()
        _pool = psycopg2.pool.SimpleConnectionPool(
            dsn=params["dsn"],
            minconn=1,
            maxconn=5,
        )
    return _pool


def get_connection() -> Generator:
    """
    Dependency for getting a database connection.

    In serverless environments, creates a new connection per request.
    In development, uses a connection pool.

    Usage:
        @app.get("/endpoint")
        def endpoint(conn=Depends(get_connection)):
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    if _is_serverless():
        # Serverless: create new connection per request
        params = _get_connection_params()
        conn = psycopg2.connect(**params)
        try:
            yield conn
        finally:
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

    Usage:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    if _is_serverless():
        params = _get_connection_params()
        conn = psycopg2.connect(**params)
        try:
            yield conn
        finally:
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


def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone()[0] == 1
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


def check_postgis_extension() -> bool:
    """Check if PostGIS extension is available."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT PostGIS_Version()")
                return cur.fetchone() is not None
    except Exception as e:
        print(f"PostGIS check error: {e}")
        return False
