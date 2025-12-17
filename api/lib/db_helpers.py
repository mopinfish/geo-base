"""
Database operation helpers with retry support.

This module provides helper functions for database operations that
automatically handle transient connection errors with retry logic.

Features:
- Execute queries with automatic retry on connection errors
- Transaction support with retry
- Batch operations with configurable retry behavior
- Integration with FastAPI dependency injection

Usage:
    from lib.db_helpers import execute_query, execute_transaction

    # Simple query with retry
    result = execute_query(conn, "SELECT * FROM tilesets WHERE id = %s", (tileset_id,))

    # Transaction with retry
    def my_transaction(conn):
        with conn.cursor() as cur:
            cur.execute("INSERT INTO ...")
            cur.execute("UPDATE ...")
        return result

    result = execute_transaction(conn, my_transaction)
"""

import functools
import logging
from typing import Any, Callable, List, Optional, Tuple, TypeVar

import psycopg2

from lib.retry import (
    RetryConfig,
    execute_db_operation,
    is_retryable_error,
    calculate_delay,
)

# Configure logging
logger = logging.getLogger(__name__)

# Type variables
T = TypeVar("T")


# =============================================================================
# Configuration
# =============================================================================


# Default configuration for database helpers
DEFAULT_QUERY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.1,
    max_delay=2.0,
    jitter=True,
)


# =============================================================================
# Query Execution Helpers
# =============================================================================


def execute_query(
    conn,
    query: str,
    params: Optional[Tuple] = None,
    config: Optional[RetryConfig] = None,
    fetch_one: bool = False,
    fetch_all: bool = True,
) -> Optional[Any]:
    """
    Execute a SQL query with automatic retry on transient errors.

    This function is designed for read operations (SELECT queries).
    For write operations that modify data, use execute_transaction instead.

    Args:
        conn: Database connection
        query: SQL query string
        params: Query parameters as a tuple
        config: Retry configuration (uses defaults if not provided)
        fetch_one: If True, fetch only one row
        fetch_all: If True, fetch all rows (default)

    Returns:
        Query results (single row, list of rows, or None)

    Raises:
        psycopg2.Error: If all retry attempts fail

    Example:
        # Fetch all rows
        rows = execute_query(conn, "SELECT * FROM tilesets WHERE type = %s", ("vector",))

        # Fetch single row
        row = execute_query(
            conn,
            "SELECT * FROM tilesets WHERE id = %s",
            (tileset_id,),
            fetch_one=True
        )
    """
    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch_one:
                return cur.fetchone()
            elif fetch_all:
                return cur.fetchall()
            return None

    return execute_db_operation(operation, config=retry_config)


def execute_query_with_columns(
    conn,
    query: str,
    params: Optional[Tuple] = None,
    config: Optional[RetryConfig] = None,
    fetch_one: bool = False,
) -> Tuple[List[str], List[Any]]:
    """
    Execute a SQL query and return results with column names.

    Useful for converting results to dictionaries.

    Args:
        conn: Database connection
        query: SQL query string
        params: Query parameters
        config: Retry configuration
        fetch_one: If True, fetch only one row

    Returns:
        Tuple of (column_names, rows)

    Example:
        columns, rows = execute_query_with_columns(
            conn,
            "SELECT id, name FROM tilesets"
        )
        results = [dict(zip(columns, row)) for row in rows]
    """
    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            if fetch_one:
                row = cur.fetchone()
                rows = [row] if row else []
            else:
                rows = cur.fetchall()
            return columns, rows

    return execute_db_operation(operation, config=retry_config)


def execute_query_as_dicts(
    conn,
    query: str,
    params: Optional[Tuple] = None,
    config: Optional[RetryConfig] = None,
) -> List[dict]:
    """
    Execute a SQL query and return results as list of dictionaries.

    Args:
        conn: Database connection
        query: SQL query string
        params: Query parameters
        config: Retry configuration

    Returns:
        List of dictionaries with column names as keys

    Example:
        tilesets = execute_query_as_dicts(
            conn,
            "SELECT id, name, type FROM tilesets"
        )
        # [{"id": "uuid1", "name": "Tileset 1", "type": "vector"}, ...]
    """
    columns, rows = execute_query_with_columns(conn, query, params, config)
    return [dict(zip(columns, row)) for row in rows]


# =============================================================================
# Transaction Helpers
# =============================================================================


def execute_transaction(
    conn,
    transaction_func: Callable[[Any], T],
    config: Optional[RetryConfig] = None,
    auto_commit: bool = True,
    rollback_on_error: bool = True,
) -> T:
    """
    Execute a function within a database transaction with retry support.

    The function will be retried if a transient connection error occurs.
    Note: Retries start from the beginning of the transaction.

    Args:
        conn: Database connection
        transaction_func: Function that performs database operations
                         Should take conn as argument and return result
        config: Retry configuration
        auto_commit: If True, commit on success
        rollback_on_error: If True, rollback on error

    Returns:
        Result from transaction_func

    Raises:
        psycopg2.Error: If all retry attempts fail

    Example:
        def create_tileset_with_features(conn):
            with conn.cursor() as cur:
                cur.execute("INSERT INTO tilesets (...) VALUES (...) RETURNING id")
                tileset_id = cur.fetchone()[0]
                cur.execute("INSERT INTO features (...) VALUES (...)")
            return tileset_id

        tileset_id = execute_transaction(conn, create_tileset_with_features)
    """
    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        try:
            result = transaction_func(conn)
            if auto_commit:
                conn.commit()
            return result
        except Exception as e:
            if rollback_on_error:
                try:
                    conn.rollback()
                except Exception:
                    pass  # Ignore rollback errors
            raise

    return execute_db_operation(operation, config=retry_config)


def execute_insert(
    conn,
    query: str,
    params: Optional[Tuple] = None,
    config: Optional[RetryConfig] = None,
    returning: bool = True,
) -> Optional[Any]:
    """
    Execute an INSERT query with automatic retry and commit.

    Args:
        conn: Database connection
        query: INSERT SQL query (should include RETURNING if returning=True)
        params: Query parameters
        config: Retry configuration
        returning: If True, fetch and return the RETURNING result

    Returns:
        RETURNING result if returning=True, else None

    Example:
        result = execute_insert(
            conn,
            "INSERT INTO tilesets (name, type) VALUES (%s, %s) RETURNING id",
            ("My Tileset", "vector")
        )
        tileset_id = result[0]
    """
    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchone() if returning else None
        conn.commit()
        return result

    return execute_db_operation(operation, config=retry_config)


def execute_update(
    conn,
    query: str,
    params: Optional[Tuple] = None,
    config: Optional[RetryConfig] = None,
    returning: bool = False,
) -> Optional[Any]:
    """
    Execute an UPDATE query with automatic retry and commit.

    Args:
        conn: Database connection
        query: UPDATE SQL query
        params: Query parameters
        config: Retry configuration
        returning: If True and query has RETURNING, fetch the result

    Returns:
        RETURNING result if returning=True, else row count

    Example:
        count = execute_update(
            conn,
            "UPDATE tilesets SET name = %s WHERE id = %s",
            ("New Name", tileset_id)
        )
    """
    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        with conn.cursor() as cur:
            cur.execute(query, params)
            if returning:
                result = cur.fetchone()
            else:
                result = cur.rowcount
        conn.commit()
        return result

    return execute_db_operation(operation, config=retry_config)


def execute_delete(
    conn,
    query: str,
    params: Optional[Tuple] = None,
    config: Optional[RetryConfig] = None,
) -> int:
    """
    Execute a DELETE query with automatic retry and commit.

    Args:
        conn: Database connection
        query: DELETE SQL query
        params: Query parameters
        config: Retry configuration

    Returns:
        Number of rows deleted

    Example:
        count = execute_delete(
            conn,
            "DELETE FROM features WHERE tileset_id = %s",
            (tileset_id,)
        )
    """
    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        with conn.cursor() as cur:
            cur.execute(query, params)
            count = cur.rowcount
        conn.commit()
        return count

    return execute_db_operation(operation, config=retry_config)


# =============================================================================
# Batch Operations
# =============================================================================


def execute_batch(
    conn,
    query: str,
    params_list: List[Tuple],
    config: Optional[RetryConfig] = None,
    page_size: int = 1000,
) -> int:
    """
    Execute a batch of queries using executemany with retry support.

    Args:
        conn: Database connection
        query: SQL query with placeholders
        params_list: List of parameter tuples
        config: Retry configuration
        page_size: Number of rows per batch (for progress tracking)

    Returns:
        Total number of rows affected

    Example:
        features = [
            (tileset_id, "layer1", geom1, props1),
            (tileset_id, "layer1", geom2, props2),
        ]
        count = execute_batch(
            conn,
            "INSERT INTO features (tileset_id, layer_name, geom, properties) VALUES (%s, %s, %s, %s)",
            features
        )
    """
    from psycopg2.extras import execute_batch as pg_execute_batch

    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        with conn.cursor() as cur:
            pg_execute_batch(cur, query, params_list, page_size=page_size)
            count = cur.rowcount
        conn.commit()
        return count

    return execute_db_operation(operation, config=retry_config)


def execute_values(
    conn,
    query: str,
    params_list: List[Tuple],
    template: Optional[str] = None,
    config: Optional[RetryConfig] = None,
    page_size: int = 1000,
    fetch: bool = False,
) -> Any:
    """
    Execute a batch INSERT using execute_values for better performance.

    This is typically faster than execute_batch for INSERT operations.

    Args:
        conn: Database connection
        query: SQL query with %s placeholder for VALUES
        params_list: List of parameter tuples
        template: Optional template for values (e.g., "(%s, %s, ST_GeomFromGeoJSON(%s))")
        config: Retry configuration
        page_size: Number of rows per batch
        fetch: If True, return the inserted rows (query must have RETURNING)

    Returns:
        Inserted rows if fetch=True, else number of rows affected

    Example:
        features = [
            (tileset_id, "layer1", geom_json1),
            (tileset_id, "layer1", geom_json2),
        ]
        count = execute_values(
            conn,
            "INSERT INTO features (tileset_id, layer_name, geom) VALUES %s",
            features,
            template="(%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"
        )
    """
    from psycopg2.extras import execute_values as pg_execute_values

    retry_config = config or DEFAULT_QUERY_CONFIG

    def operation():
        with conn.cursor() as cur:
            result = pg_execute_values(
                cur,
                query,
                params_list,
                template=template,
                page_size=page_size,
                fetch=fetch,
            )
            if fetch:
                return result
            count = cur.rowcount
        conn.commit()
        return count if not fetch else result

    return execute_db_operation(operation, config=retry_config)


# =============================================================================
# Convenience Functions
# =============================================================================


def get_tileset_by_id(conn, tileset_id: str, config: Optional[RetryConfig] = None) -> Optional[dict]:
    """
    Get a tileset by ID with retry support.

    Args:
        conn: Database connection
        tileset_id: UUID of the tileset
        config: Retry configuration

    Returns:
        Tileset as dictionary or None if not found
    """
    columns, rows = execute_query_with_columns(
        conn,
        """
        SELECT id, name, description, type, format, min_zoom, max_zoom,
               ST_AsGeoJSON(bounds) as bounds, ST_AsGeoJSON(center) as center,
               attribution, is_public, user_id, metadata, created_at, updated_at
        FROM tilesets
        WHERE id = %s
        """,
        (tileset_id,),
        config=config,
        fetch_one=True,
    )
    
    if not rows:
        return None
    
    return dict(zip(columns, rows[0]))


def check_tileset_owner(
    conn,
    tileset_id: str,
    user_id: str,
    config: Optional[RetryConfig] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Check if a user owns a tileset with retry support.

    Args:
        conn: Database connection
        tileset_id: UUID of the tileset
        user_id: UUID of the user
        config: Retry configuration

    Returns:
        Tuple of (exists, owner_id)
        - exists: True if tileset exists
        - owner_id: UUID of the owner or None if not found
    """
    result = execute_query(
        conn,
        "SELECT id, user_id FROM tilesets WHERE id = %s",
        (tileset_id,),
        config=config,
        fetch_one=True,
    )
    
    if not result:
        return False, None
    
    return True, str(result[1]) if result[1] else None


def count_features(
    conn,
    tileset_id: str,
    layer_name: Optional[str] = None,
    config: Optional[RetryConfig] = None,
) -> int:
    """
    Count features in a tileset with retry support.

    Args:
        conn: Database connection
        tileset_id: UUID of the tileset
        layer_name: Optional layer name filter
        config: Retry configuration

    Returns:
        Number of features
    """
    if layer_name:
        query = "SELECT COUNT(*) FROM features WHERE tileset_id = %s AND layer_name = %s"
        params = (tileset_id, layer_name)
    else:
        query = "SELECT COUNT(*) FROM features WHERE tileset_id = %s"
        params = (tileset_id,)
    
    result = execute_query(conn, query, params, config=config, fetch_one=True)
    return result[0] if result else 0


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Query helpers
    "execute_query",
    "execute_query_with_columns",
    "execute_query_as_dicts",
    # Transaction helpers
    "execute_transaction",
    "execute_insert",
    "execute_update",
    "execute_delete",
    # Batch helpers
    "execute_batch",
    "execute_values",
    # Convenience functions
    "get_tileset_by_id",
    "check_tileset_owner",
    "count_features",
    # Configuration
    "DEFAULT_QUERY_CONFIG",
]
