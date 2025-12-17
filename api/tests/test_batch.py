"""
Tests for batch operations module.

Tests cover:
- BatchResult dataclass
- Export functions (GeoJSON, CSV)
- Batch update functions
- Batch delete functions
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from lib.batch import (
    BatchStatus,
    BatchResult,
    export_features_geojson,
    export_features_csv,
    batch_update_features,
    batch_update_by_filter,
    batch_delete_features,
    batch_delete_by_filter,
)


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
def sample_feature_rows():
    """Sample feature rows from database."""
    return [
        (
            "uuid-1",
            "layer1",
            {"type": "Point", "coordinates": [139.7, 35.6]},
            {"name": "Feature 1", "type": "point"},
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 2, 12, 0, 0),
        ),
        (
            "uuid-2",
            "layer1",
            {"type": "Point", "coordinates": [139.8, 35.7]},
            {"name": "Feature 2", "type": "point"},
            datetime(2024, 1, 1, 13, 0, 0),
            datetime(2024, 1, 2, 13, 0, 0),
        ),
    ]


# =============================================================================
# Test BatchResult
# =============================================================================


class TestBatchResult:
    """Tests for BatchResult dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        result = BatchResult()
        
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.total_count == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.status == BatchStatus.COMPLETED
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        result = BatchResult(
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 0, 10),
        )
        
        assert result.duration_seconds == 10.0
    
    def test_duration_none_when_incomplete(self):
        """Test duration is None when timestamps missing."""
        result = BatchResult(started_at=datetime.now())
        
        assert result.duration_seconds is None
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = BatchResult(
            success_count=5,
            failed_count=2,
            total_count=7,
            errors=["Error 1"],
            warnings=["Warning 1"],
            status=BatchStatus.COMPLETED,
        )
        
        data = result.to_dict()
        
        assert data["success_count"] == 5
        assert data["failed_count"] == 2
        assert data["total_count"] == 7
        assert data["status"] == "completed"
    
    def test_to_dict_limits_errors(self):
        """Test that to_dict limits errors to 100."""
        result = BatchResult(
            errors=[f"Error {i}" for i in range(150)],
        )
        
        data = result.to_dict()
        
        assert len(data["errors"]) == 100


# =============================================================================
# Test Export Functions
# =============================================================================


class TestExportFeaturesGeojson:
    """Tests for export_features_geojson function."""
    
    def test_basic_export(self, mock_conn, sample_feature_rows):
        """Test basic GeoJSON export."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (2,)  # Total count
        cursor.fetchall.return_value = sample_feature_rows
        
        result = export_features_geojson(conn, "tileset-uuid")
        
        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 2
        assert "metadata" in result
    
    def test_export_with_layer_filter(self, mock_conn, sample_feature_rows):
        """Test export with layer filter."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (1,)
        cursor.fetchall.return_value = [sample_feature_rows[0]]
        
        result = export_features_geojson(
            conn,
            "tileset-uuid",
            layer_name="layer1",
        )
        
        # Verify layer filter was used in query
        call_args = cursor.execute.call_args_list
        assert any("layer_name" in str(args) for args in call_args)
    
    def test_export_with_bbox(self, mock_conn, sample_feature_rows):
        """Test export with bounding box filter."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (1,)
        cursor.fetchall.return_value = [sample_feature_rows[0]]
        
        result = export_features_geojson(
            conn,
            "tileset-uuid",
            bbox=(139.0, 35.0, 140.0, 36.0),
        )
        
        # Verify bbox filter was used
        call_args = cursor.execute.call_args_list
        assert any("ST_Intersects" in str(args) for args in call_args)
    
    def test_export_without_metadata(self, mock_conn, sample_feature_rows):
        """Test export without metadata."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (2,)
        cursor.fetchall.return_value = sample_feature_rows
        
        result = export_features_geojson(
            conn,
            "tileset-uuid",
            include_metadata=False,
        )
        
        assert "metadata" not in result
    
    def test_export_with_limit(self, mock_conn, sample_feature_rows):
        """Test export with limit."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (10,)  # Total is 10
        cursor.fetchall.return_value = [sample_feature_rows[0]]  # But only 1 returned
        
        result = export_features_geojson(
            conn,
            "tileset-uuid",
            limit=1,
        )
        
        # Verify LIMIT was used
        call_args = cursor.execute.call_args_list
        assert any("LIMIT" in str(args) for args in call_args)


class TestExportFeaturesCsv:
    """Tests for export_features_csv function."""
    
    def test_basic_csv_export(self, mock_conn):
        """Test basic CSV export."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [
            ("uuid-1", "layer1", 139.7, 35.6, "POINT(139.7 35.6)", {"name": "Test"}),
        ]
        
        result = export_features_csv(conn, "tileset-uuid")
        
        assert "id,layer_name,longitude,latitude" in result
        assert "uuid-1" in result
        assert "layer1" in result
    
    def test_csv_without_wkt(self, mock_conn):
        """Test CSV export without WKT column."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [
            ("uuid-1", "layer1", 139.7, 35.6, None, {"name": "Test"}),
        ]
        
        result = export_features_csv(conn, "tileset-uuid", include_wkt=False)
        
        assert "wkt" not in result.split("\n")[0]


# =============================================================================
# Test Batch Update Functions
# =============================================================================


class TestBatchUpdateFeatures:
    """Tests for batch_update_features function."""
    
    def test_update_by_ids(self, mock_conn):
        """Test updating features by IDs."""
        conn, cursor = mock_conn
        cursor.fetchone.side_effect = [("uuid-1",), ("uuid-2",)]
        
        result = batch_update_features(
            conn,
            feature_ids=["uuid-1", "uuid-2"],
            updates={"properties": {"status": "updated"}},
        )
        
        assert result.success_count == 2
        assert result.failed_count == 0
        assert result.status == BatchStatus.COMPLETED
    
    def test_update_with_layer_name(self, mock_conn):
        """Test updating layer name."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = ("uuid-1",)
        
        result = batch_update_features(
            conn,
            feature_ids=["uuid-1"],
            updates={"layer_name": "new_layer"},
        )
        
        assert result.success_count == 1
        # Verify layer_name was in the update
        call_args = cursor.execute.call_args_list
        assert any("layer_name" in str(args) for args in call_args)
    
    def test_update_not_found(self, mock_conn):
        """Test updating non-existent feature."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None  # Not found
        
        result = batch_update_features(
            conn,
            feature_ids=["nonexistent"],
            updates={"properties": {"status": "updated"}},
        )
        
        assert result.success_count == 0
        assert result.failed_count == 1
        assert "Not found" in result.errors[0]
    
    def test_update_empty_list(self, mock_conn):
        """Test updating with empty feature list."""
        conn, cursor = mock_conn
        
        result = batch_update_features(
            conn,
            feature_ids=[],
            updates={"properties": {}},
        )
        
        assert result.total_count == 0
        assert result.status == BatchStatus.COMPLETED


class TestBatchUpdateByFilter:
    """Tests for batch_update_by_filter function."""
    
    def test_update_by_layer(self, mock_conn):
        """Test updating by layer filter."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (5,)  # 5 matching features
        cursor.rowcount = 5
        
        result = batch_update_by_filter(
            conn,
            tileset_id="tileset-uuid",
            filter_conditions={"layer_name": "old_layer"},
            updates={"layer_name": "new_layer"},
        )
        
        assert result.success_count == 5
    
    def test_update_no_matches(self, mock_conn):
        """Test updating with no matching features."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (0,)  # No matches
        
        result = batch_update_by_filter(
            conn,
            tileset_id="tileset-uuid",
            filter_conditions={"layer_name": "nonexistent"},
            updates={"properties": {}},
        )
        
        assert result.total_count == 0
        assert "No features matched" in result.warnings[0]


# =============================================================================
# Test Batch Delete Functions
# =============================================================================


class TestBatchDeleteFeatures:
    """Tests for batch_delete_features function."""
    
    def test_delete_by_ids(self, mock_conn):
        """Test deleting features by IDs."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [("uuid-1",), ("uuid-2",)]
        
        result = batch_delete_features(
            conn,
            feature_ids=["uuid-1", "uuid-2"],
        )
        
        assert result.success_count == 2
        assert result.failed_count == 0
    
    def test_delete_partial_success(self, mock_conn):
        """Test deleting with some features not found."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [("uuid-1",)]  # Only 1 deleted
        
        result = batch_delete_features(
            conn,
            feature_ids=["uuid-1", "uuid-2"],
        )
        
        assert result.success_count == 1
        assert result.failed_count == 1
        assert "Not found" in result.errors[0]
    
    def test_delete_empty_list(self, mock_conn):
        """Test deleting with empty feature list."""
        conn, cursor = mock_conn
        
        result = batch_delete_features(
            conn,
            feature_ids=[],
        )
        
        assert result.total_count == 0
        assert result.status == BatchStatus.COMPLETED


class TestBatchDeleteByFilter:
    """Tests for batch_delete_by_filter function."""
    
    def test_delete_by_layer(self, mock_conn):
        """Test deleting by layer filter."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (10,)  # 10 matching features
        cursor.rowcount = 10
        
        result = batch_delete_by_filter(
            conn,
            tileset_id="tileset-uuid",
            filter_conditions={"layer_name": "temp_layer"},
        )
        
        assert result.success_count == 10
    
    def test_delete_dry_run(self, mock_conn):
        """Test delete with dry_run flag."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (5,)  # 5 matching features
        
        result = batch_delete_by_filter(
            conn,
            tileset_id="tileset-uuid",
            filter_conditions={"layer_name": "temp_layer"},
            dry_run=True,
        )
        
        assert result.total_count == 5
        assert result.success_count == 0  # Nothing actually deleted
        assert "Dry run" in result.warnings[0]
        conn.commit.assert_not_called()
    
    def test_delete_with_limit(self, mock_conn):
        """Test delete with limit."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (100,)  # 100 matching features
        cursor.rowcount = 10  # But only 10 deleted due to limit
        
        result = batch_delete_by_filter(
            conn,
            tileset_id="tileset-uuid",
            filter_conditions={},
            limit=10,
        )
        
        assert result.success_count == 10
    
    def test_delete_no_matches(self, mock_conn):
        """Test deleting with no matching features."""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = (0,)  # No matches
        
        result = batch_delete_by_filter(
            conn,
            tileset_id="tileset-uuid",
            filter_conditions={"layer_name": "nonexistent"},
        )
        
        assert result.total_count == 0
        assert "No features matched" in result.warnings[0]


# =============================================================================
# Integration Tests
# =============================================================================


class TestBatchIntegration:
    """Integration tests for batch operations."""
    
    def test_result_duration_tracking(self, mock_conn):
        """Test that duration is tracked correctly."""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [("uuid-1",)]
        
        result = batch_delete_features(conn, ["uuid-1"])
        
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0
    
    def test_error_collection(self, mock_conn):
        """Test that errors are collected properly."""
        conn, cursor = mock_conn
        
        # Simulate error on execute
        cursor.fetchone.side_effect = Exception("Database error")
        
        result = batch_update_features(
            conn,
            feature_ids=["uuid-1"],
            updates={"properties": {}},
        )
        
        assert result.failed_count >= 1
        assert len(result.errors) >= 1
