"""
Database connection management for geo-base API.
"""

from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool

from lib.config import get_settings

# Connection pool (initialized lazily)
_pool: psycopg2.pool.SimpleConnectionPool | None = None


def get_pool() -> psycopg2.pool.SimpleConnectionPool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = psycopg2.pool.SimpleConnectionPool(
            dsn=settings.database_url,
            minconn=2,
            maxconn=10,
        )
    return _pool


def get_connection() -> Generator:
    """
    Dependency for getting a database connection.

    Usage:
        @app.get("/endpoint")
        def endpoint(conn=Depends(get_connection)):
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
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
    except Exception:
        return False


def check_postgis_extension() -> bool:
    """Check if PostGIS extension is available."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT PostGIS_Version()")
                return cur.fetchone() is not None
    except Exception:
        return False
