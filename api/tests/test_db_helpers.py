"""
Tests for database operation helpers.

Tests cover:
- execute_query with retry
- execute_query_with_columns
- execute_query_as_dicts
- execute_transaction
- execute_insert, execute_update, execute_delete
- Convenience functions
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import psycopg2

from lib.db_helpers import (
    execute_query,
    execute_query_with_columns,
    execute_query_as_dicts,
    execute_transaction,
    execute_insert,
    execute_update,
    execute_delete,
    get_tileset_by_id,
    check_tileset_owner,
    count_features,
    DEFAULT_QUERY_CONFIG,
)
from lib.retry import RetryConfig


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_conn():
    """Create a mock database connection."""
    conn = Mock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = Mock(return_value=cursor)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)
    return conn, cursor


@pytest.fixture
def test_config():
    """Test retry configuration with short delays."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.001,
        max_delay=0.01,
        jitter=False,
    )


# =============================================================================
# Test execute_query
# =============================================================================


class TestExecuteQuery:
    """Tests for execute_query function."""
    
    def test_fetch_all_rows(self, mock_conn, test_config):
        """Test fetching all rows."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [
            (1, "Tileset 1"),
            (2, "Tileset 2"),
        ]
        
        result = execute_query(
            conn,
            "SELECT id, name FROM tilesets",
            config=test_config,
        )
        
        assert result == [(1, "Tileset 1"), (2, "Tileset 2")]
        cursor.execute.assert_called_once_with("SELECT id, name FROM tilesets", None)
        cursor.fetchall.assert_called_once()
    
    def test_fetch_one_row(self, mock_conn, test_config):
        """Test fetching single row."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (1, "Tileset 1")
        
        result = execute_query(
            conn,
            "SELECT id, name FROM tilesets WHERE id = %s",
            (1,),
            config=test_config,
            fetch_one=True,
        )
        
        assert result == (1, "Tileset 1")
        cursor.execute.assert_called_once_with(
            "SELECT id, name FROM tilesets WHERE id = %s",
            (1,),
        )
        cursor.fetchone.assert_called_once()
    
    def test_no_fetch(self, mock_conn, test_config):
        """Test execution without fetch."""
        conn, cursor = mock_conn
        
        result = execute_query(
            conn,
            "UPDATE tilesets SET name = %s WHERE id = %s",
            ("New Name", 1),
            config=test_config,
            fetch_all=False,
        )
        
        assert result is None
        cursor.execute.assert_called_once()
    
    def test_retry_on_connection_error(self, mock_conn, test_config):
        """Test retry on transient connection error."""
        conn, cursor = mock_conn
        
        # First call raises error, second succeeds
        cursor.execute.side_effect = [
            psycopg2.OperationalError("connection reset by peer"),
            None,  # Success
        ]
        cursor.fetchall.return_value = [(1,)]
        
        result = execute_query(
            conn,
            "SELECT 1",
            config=test_config,
        )
        
        assert result == [(1,)]
        assert cursor.execute.call_count == 2
    
    def test_no_retry_on_syntax_error(self, mock_conn, test_config):
        """Test no retry on SQL syntax error."""
        conn, cursor = mock_conn
        cursor.execute.side_effect = psycopg2.ProgrammingError("syntax error")
        
        with pytest.raises(psycopg2.ProgrammingError):
            execute_query(conn, "INVALID SQL", config=test_config)
        
        assert cursor.execute.call_count == 1


# =============================================================================
# Test execute_query_with_columns
# =============================================================================


class TestExecuteQueryWithColumns:
    """Tests for execute_query_with_columns function."""
    
    def test_returns_columns_and_rows(self, mock_conn, test_config):
        """Test that columns and rows are returned."""
        conn, cursor = mock_conn
        cursor.description = [("id",), ("name",), ("type",)]
        cursor.fetchall.return_value = [
            (1, "Tileset 1", "vector"),
            (2, "Tileset 2", "raster"),
        ]
        
        columns, rows = execute_query_with_columns(
            conn,
            "SELECT id, name, type FROM tilesets",
            config=test_config,
        )
        
        assert columns == ["id", "name", "type"]
        assert rows == [
            (1, "Tileset 1", "vector"),
            (2, "Tileset 2", "raster"),
        ]
    
    def test_fetch_one(self, mock_conn, test_config):
        """Test fetching single row with columns."""
        conn, cursor = mock_conn
        cursor.description = [("id",), ("name",)]
        cursor.fetchone.return_value = (1, "Tileset 1")
        
        columns, rows = execute_query_with_columns(
            conn,
            "SELECT id, name FROM tilesets WHERE id = %s",
            (1,),
            config=test_config,
            fetch_one=True,
        )
        
        assert columns == ["id", "name"]
        assert rows == [(1, "Tileset 1")]
    
    def test_no_results(self, mock_conn, test_config):
        """Test when no results found."""
        conn, cursor = mock_conn
        cursor.description = [("id",)]
        cursor.fetchone.return_value = None
        
        columns, rows = execute_query_with_columns(
            conn,
            "SELECT id FROM tilesets WHERE id = %s",
            ("nonexistent",),
            config=test_config,
            fetch_one=True,
        )
        
        assert columns == ["id"]
        assert rows == []


# =============================================================================
# Test execute_query_as_dicts
# =============================================================================


class TestExecuteQueryAsDicts:
    """Tests for execute_query_as_dicts function."""
    
    def test_returns_list_of_dicts(self, mock_conn, test_config):
        """Test that results are returned as dictionaries."""
        conn, cursor = mock_conn
        cursor.description = [("id",), ("name",), ("type",)]
        cursor.fetchall.return_value = [
            (1, "Tileset 1", "vector"),
            (2, "Tileset 2", "raster"),
        ]
        
        result = execute_query_as_dicts(
            conn,
            "SELECT id, name, type FROM tilesets",
            config=test_config,
        )
        
        assert result == [
            {"id": 1, "name": "Tileset 1", "type": "vector"},
            {"id": 2, "name": "Tileset 2", "type": "raster"},
        ]
    
    def test_empty_results(self, mock_conn, test_config):
        """Test empty results return empty list."""
        conn, cursor = mock_conn
        cursor.description = [("id",)]
        cursor.fetchall.return_value = []
        
        result = execute_query_as_dicts(
            conn,
            "SELECT id FROM tilesets WHERE 1=0",
            config=test_config,
        )
        
        assert result == []


# =============================================================================
# Test execute_transaction
# =============================================================================


class TestExecuteTransaction:
    """Tests for execute_transaction function."""
    
    def test_successful_transaction_commits(self, mock_conn, test_config):
        """Test that successful transaction is committed."""
        conn, cursor = mock_conn
        
        def transaction(c):
            return "success"
        
        result = execute_transaction(conn, transaction, config=test_config)
        
        assert result == "success"
        conn.commit.assert_called_once()
    
    def test_failed_transaction_rollbacks(self, mock_conn, test_config):
        """Test that failed transaction is rolled back."""
        conn, cursor = mock_conn
        
        def transaction(c):
            raise psycopg2.ProgrammingError("error")
        
        with pytest.raises(psycopg2.ProgrammingError):
            execute_transaction(conn, transaction, config=test_config)
        
        conn.rollback.assert_called()
    
    def test_retryable_error_retries(self, mock_conn, test_config):
        """Test that retryable errors trigger retry."""
        conn, cursor = mock_conn
        
        call_count = 0
        
        def transaction(c):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise psycopg2.OperationalError("connection reset by peer")
            return "success"
        
        result = execute_transaction(conn, transaction, config=test_config)
        
        assert result == "success"
        assert call_count == 2
    
    def test_auto_commit_disabled(self, mock_conn, test_config):
        """Test that auto_commit can be disabled."""
        conn, cursor = mock_conn
        
        def transaction(c):
            return "success"
        
        result = execute_transaction(
            conn,
            transaction,
            config=test_config,
            auto_commit=False,
        )
        
        assert result == "success"
        conn.commit.assert_not_called()


# =============================================================================
# Test execute_insert/update/delete
# =============================================================================


class TestExecuteInsert:
    """Tests for execute_insert function."""
    
    def test_insert_with_returning(self, mock_conn, test_config):
        """Test INSERT with RETURNING clause."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("uuid-123",)
        
        result = execute_insert(
            conn,
            "INSERT INTO tilesets (name) VALUES (%s) RETURNING id",
            ("Test",),
            config=test_config,
        )
        
        assert result == ("uuid-123",)
        conn.commit.assert_called_once()
    
    def test_insert_without_returning(self, mock_conn, test_config):
        """Test INSERT without RETURNING."""
        conn, cursor = mock_conn
        
        result = execute_insert(
            conn,
            "INSERT INTO tilesets (name) VALUES (%s)",
            ("Test",),
            config=test_config,
            returning=False,
        )
        
        assert result is None
        conn.commit.assert_called_once()


class TestExecuteUpdate:
    """Tests for execute_update function."""
    
    def test_update_returns_count(self, mock_conn, test_config):
        """Test UPDATE returns row count."""
        conn, cursor = mock_conn
        cursor.rowcount = 5
        
        result = execute_update(
            conn,
            "UPDATE tilesets SET name = %s WHERE type = %s",
            ("New Name", "vector"),
            config=test_config,
        )
        
        assert result == 5
        conn.commit.assert_called_once()
    
    def test_update_with_returning(self, mock_conn, test_config):
        """Test UPDATE with RETURNING clause."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("uuid-123", "Updated Name")
        
        result = execute_update(
            conn,
            "UPDATE tilesets SET name = %s WHERE id = %s RETURNING id, name",
            ("Updated Name", "uuid-123"),
            config=test_config,
            returning=True,
        )
        
        assert result == ("uuid-123", "Updated Name")


class TestExecuteDelete:
    """Tests for execute_delete function."""
    
    def test_delete_returns_count(self, mock_conn, test_config):
        """Test DELETE returns row count."""
        conn, cursor = mock_conn
        cursor.rowcount = 3
        
        result = execute_delete(
            conn,
            "DELETE FROM features WHERE tileset_id = %s",
            ("uuid-123",),
            config=test_config,
        )
        
        assert result == 3
        conn.commit.assert_called_once()


# =============================================================================
# Test Convenience Functions
# =============================================================================


class TestGetTilesetById:
    """Tests for get_tileset_by_id function."""
    
    def test_returns_tileset_dict(self, mock_conn, test_config):
        """Test that tileset is returned as dictionary."""
        conn, cursor = mock_conn
        cursor.description = [
            ("id",), ("name",), ("description",), ("type",), ("format",),
            ("min_zoom",), ("max_zoom",), ("bounds",), ("center",),
            ("attribution",), ("is_public",), ("user_id",),
            ("metadata",), ("created_at",), ("updated_at",),
        ]
        cursor.fetchone.return_value = (
            "uuid-123", "Test Tileset", "Description", "vector", "pbf",
            0, 22, None, None,
            "Attribution", True, "user-uuid",
            None, "2024-01-01", "2024-01-02",
        )
        
        result = get_tileset_by_id(conn, "uuid-123", config=test_config)
        
        assert result is not None
        assert result["id"] == "uuid-123"
        assert result["name"] == "Test Tileset"
        assert result["type"] == "vector"
    
    def test_returns_none_if_not_found(self, mock_conn, test_config):
        """Test that None is returned if tileset not found."""
        conn, cursor = mock_conn
        cursor.description = [("id",)]
        cursor.fetchone.return_value = None
        
        result = get_tileset_by_id(conn, "nonexistent", config=test_config)
        
        assert result is None


class TestCheckTilesetOwner:
    """Tests for check_tileset_owner function."""
    
    def test_returns_exists_and_owner(self, mock_conn, test_config):
        """Test that exists and owner_id are returned."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("uuid-123", "user-uuid")
        
        exists, owner_id = check_tileset_owner(
            conn, "uuid-123", "user-uuid", config=test_config
        )
        
        assert exists is True
        assert owner_id == "user-uuid"
    
    def test_returns_false_if_not_found(self, mock_conn, test_config):
        """Test that False is returned if tileset not found."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        
        exists, owner_id = check_tileset_owner(
            conn, "nonexistent", "user-uuid", config=test_config
        )
        
        assert exists is False
        assert owner_id is None


class TestCountFeatures:
    """Tests for count_features function."""
    
    def test_counts_all_features(self, mock_conn, test_config):
        """Test counting all features in tileset."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (42,)
        
        result = count_features(conn, "uuid-123", config=test_config)
        
        assert result == 42
    
    def test_counts_features_by_layer(self, mock_conn, test_config):
        """Test counting features filtered by layer."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (10,)
        
        result = count_features(
            conn, "uuid-123", layer_name="layer1", config=test_config
        )
        
        assert result == 10
        # Verify query includes layer filter
        call_args = cursor.execute.call_args
        assert "layer_name" in call_args[0][0]
    
    def test_returns_zero_if_no_features(self, mock_conn, test_config):
        """Test that 0 is returned if no features."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (0,)
        
        result = count_features(conn, "uuid-123", config=test_config)
        
        assert result == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestDbHelpersIntegration:
    """Integration tests for database helpers."""
    
    def test_execute_query_with_params(self, mock_conn, test_config):
        """Test query execution with parameters."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [(1, "Test")]
        
        result = execute_query(
            conn,
            "SELECT id, name FROM tilesets WHERE type = %s AND is_public = %s",
            ("vector", True),
            config=test_config,
        )
        
        cursor.execute.assert_called_once_with(
            "SELECT id, name FROM tilesets WHERE type = %s AND is_public = %s",
            ("vector", True),
        )
    
    def test_transaction_with_multiple_operations(self, mock_conn, test_config):
        """Test transaction with multiple database operations."""
        conn, cursor = mock_conn
        
        def multi_op_transaction(c):
            with c.cursor() as cur:
                cur.execute("INSERT INTO table1 VALUES (%s)", (1,))
                cur.execute("INSERT INTO table2 VALUES (%s)", (2,))
            return "done"
        
        result = execute_transaction(conn, multi_op_transaction, config=test_config)
        
        assert result == "done"
        conn.commit.assert_called_once()
    
    def test_retry_preserves_function_result(self, mock_conn, test_config):
        """Test that retry preserves the function result."""
        conn, cursor = mock_conn
        
        call_count = 0
        
        # Mock cursor to fail first, succeed second
        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise psycopg2.OperationalError("connection lost")
        
        cursor.execute.side_effect = execute_side_effect
        cursor.fetchall.return_value = [(1,), (2,), (3,)]
        
        result = execute_query(conn, "SELECT id FROM items", config=test_config)
        
        assert result == [(1,), (2,), (3,)]
        assert call_count == 2
