"""
Tests for fix_bounds.py script.

This module tests the validation and data processing functions in scripts/fix_bounds.py.
Note: Database-dependent tests require DATABASE_URL environment variable.
"""

import pytest

from fix_bounds import (
    validate_bounds,
    validate_center,
    is_center_in_bounds,
    BoundsIssue,
    FixResult,
    ScanReport,
)


# ============================================================================
# Bounds Validation Tests
# ============================================================================

class TestValidateBounds:
    """Tests for bounds validation."""
    
    def test_valid_bounds(self, sample_bounds_tokyo):
        """Test valid bounds."""
        is_valid, error = validate_bounds(sample_bounds_tokyo)
        assert is_valid is True
        assert error is None
    
    def test_valid_bounds_world(self, sample_bounds_world):
        """Test world bounds."""
        is_valid, error = validate_bounds(sample_bounds_world)
        assert is_valid is True
    
    def test_none_bounds(self):
        """Test None bounds (valid - just missing)."""
        is_valid, error = validate_bounds(None)
        assert is_valid is True
    
    def test_invalid_bounds_wrong_count(self):
        """Test bounds with wrong number of values."""
        is_valid, error = validate_bounds([139.5, 35.5, 140.0])
        assert is_valid is False
        assert "4 values" in error
    
    def test_invalid_bounds_west_out_of_range(self):
        """Test bounds with west out of range."""
        is_valid, error = validate_bounds([-200, 35.5, 140.0, 36.0])
        assert is_valid is False
        assert "west" in error
    
    def test_invalid_bounds_east_out_of_range(self):
        """Test bounds with east out of range."""
        is_valid, error = validate_bounds([139.5, 35.5, 200, 36.0])
        assert is_valid is False
        assert "east" in error
    
    def test_invalid_bounds_south_out_of_range(self):
        """Test bounds with south out of range."""
        is_valid, error = validate_bounds([139.5, -100, 140.0, 36.0])
        assert is_valid is False
        assert "south" in error
    
    def test_invalid_bounds_north_out_of_range(self):
        """Test bounds with north out of range."""
        is_valid, error = validate_bounds([139.5, 35.5, 140.0, 100])
        assert is_valid is False
        assert "north" in error
    
    def test_invalid_bounds_south_greater_than_north(self, invalid_bounds_south_greater):
        """Test bounds where south > north."""
        is_valid, error = validate_bounds(invalid_bounds_south_greater)
        assert is_valid is False
        assert "south" in error and "north" in error
    
    def test_invalid_bounds_nan(self):
        """Test bounds with NaN."""
        is_valid, error = validate_bounds([float('nan'), 35.5, 140.0, 36.0])
        assert is_valid is False
        assert "NaN" in error
    
    def test_invalid_bounds_infinity(self):
        """Test bounds with infinity."""
        is_valid, error = validate_bounds([float('inf'), 35.5, 140.0, 36.0])
        assert is_valid is False
        assert "infinite" in error


# ============================================================================
# Center Validation Tests
# ============================================================================

class TestValidateCenter:
    """Tests for center validation."""
    
    def test_valid_center(self, sample_center_tokyo):
        """Test valid center."""
        is_valid, error = validate_center(sample_center_tokyo)
        assert is_valid is True
        assert error is None
    
    def test_valid_center_with_zoom(self, sample_center_with_zoom):
        """Test valid center with zoom."""
        is_valid, error = validate_center(sample_center_with_zoom)
        assert is_valid is True
    
    def test_none_center(self):
        """Test None center (valid - just missing)."""
        is_valid, error = validate_center(None)
        assert is_valid is True
    
    def test_invalid_center_too_few_values(self):
        """Test center with too few values."""
        is_valid, error = validate_center([139.7])
        assert is_valid is False
        assert "at least 2" in error
    
    def test_invalid_center_longitude_out_of_range(self, invalid_center_out_of_range):
        """Test center with longitude out of range."""
        is_valid, error = validate_center(invalid_center_out_of_range)
        assert is_valid is False
        assert "longitude" in error
    
    def test_invalid_center_latitude_out_of_range(self):
        """Test center with latitude out of range."""
        is_valid, error = validate_center([139.7, 100])
        assert is_valid is False
        assert "latitude" in error
    
    def test_invalid_center_nan(self):
        """Test center with NaN."""
        is_valid, error = validate_center([float('nan'), 35.7])
        assert is_valid is False
        assert "NaN" in error
    
    def test_invalid_center_infinity(self):
        """Test center with infinity."""
        is_valid, error = validate_center([float('inf'), 35.7])
        assert is_valid is False
        assert "infinite" in error


# ============================================================================
# Center in Bounds Tests
# ============================================================================

class TestIsCenterInBounds:
    """Tests for center-in-bounds check."""
    
    def test_center_in_bounds(self, sample_center_tokyo, sample_bounds_tokyo):
        """Test center within bounds."""
        # Adjust center to be within bounds
        center = [139.75, 35.75]
        in_bounds, warning = is_center_in_bounds(center, sample_bounds_tokyo)
        assert in_bounds is True
        assert warning is None
    
    def test_center_on_bounds_edge(self, sample_bounds_tokyo):
        """Test center on bounds edge."""
        # Southwest corner
        center = [sample_bounds_tokyo[0], sample_bounds_tokyo[1]]
        in_bounds, warning = is_center_in_bounds(center, sample_bounds_tokyo)
        assert in_bounds is True
    
    def test_center_outside_bounds(self, sample_bounds_tokyo):
        """Test center outside bounds."""
        center = [141.0, 35.75]  # East of bounds
        in_bounds, warning = is_center_in_bounds(center, sample_bounds_tokyo)
        assert in_bounds is False
        assert "outside bounds" in warning
    
    def test_center_outside_bounds_north(self, sample_bounds_tokyo):
        """Test center north of bounds."""
        center = [139.75, 37.0]  # North of bounds
        in_bounds, warning = is_center_in_bounds(center, sample_bounds_tokyo)
        assert in_bounds is False
    
    def test_none_center(self, sample_bounds_tokyo):
        """Test None center."""
        in_bounds, warning = is_center_in_bounds(None, sample_bounds_tokyo)
        assert in_bounds is True  # None is OK
    
    def test_none_bounds(self, sample_center_tokyo):
        """Test None bounds."""
        in_bounds, warning = is_center_in_bounds(sample_center_tokyo, None)
        assert in_bounds is True  # None is OK
    
    def test_antimeridian_crossing(self, sample_bounds_antimeridian):
        """Test bounds crossing antimeridian."""
        # Bounds from 170E to 170W (crossing 180)
        # Point at 175E should be in bounds
        in_bounds, warning = is_center_in_bounds([175.0, -40.0], sample_bounds_antimeridian)
        assert in_bounds is True
        
        # Point at 175W should also be in bounds
        in_bounds, warning = is_center_in_bounds([-175.0, -40.0], sample_bounds_antimeridian)
        assert in_bounds is True
        
        # Point at 0 (prime meridian) should be outside
        in_bounds, warning = is_center_in_bounds([0.0, -40.0], sample_bounds_antimeridian)
        assert in_bounds is False


# ============================================================================
# Data Class Tests
# ============================================================================

class TestBoundsIssue:
    """Tests for BoundsIssue data class."""
    
    def test_create_issue(self):
        """Test creating a bounds issue."""
        issue = BoundsIssue(
            tileset_id="test-id",
            tileset_name="Test Tileset",
            issue_type="invalid_bounds",
            description="west out of range"
        )
        assert issue.tileset_id == "test-id"
        assert issue.issue_type == "invalid_bounds"
        assert issue.current_value is None
    
    def test_create_issue_with_values(self, sample_bounds_tokyo):
        """Test creating a bounds issue with values."""
        issue = BoundsIssue(
            tileset_id="test-id",
            tileset_name="Test Tileset",
            issue_type="bounds_mismatch",
            description="Bounds differ from calculated",
            current_value=str(sample_bounds_tokyo),
            suggested_value="[139.4, 35.4, 140.1, 36.1]"
        )
        assert issue.current_value is not None
        assert issue.suggested_value is not None


class TestFixResult:
    """Tests for FixResult data class."""
    
    def test_create_fix_result(self, sample_bounds_tokyo):
        """Test creating a fix result."""
        result = FixResult(
            tileset_id="test-id",
            tileset_name="Test Tileset",
            action="applied",
            old_bounds=sample_bounds_tokyo,
            new_bounds=[139.4, 35.4, 140.1, 36.1],
            feature_count=100
        )
        assert result.success is True
        assert result.error is None
    
    def test_create_failed_fix_result(self):
        """Test creating a failed fix result."""
        result = FixResult(
            tileset_id="test-id",
            tileset_name="Test Tileset",
            action="applied",
            success=False,
            error="Database error"
        )
        assert result.success is False
        assert result.error == "Database error"


class TestScanReport:
    """Tests for ScanReport data class."""
    
    def test_empty_report(self):
        """Test creating an empty report."""
        report = ScanReport()
        assert report.total_tilesets == 0
        assert report.issues == []
        assert report.fixes_applied == []
    
    def test_report_with_issues(self):
        """Test report with issues."""
        report = ScanReport(
            total_tilesets=10,
            vector_tilesets=5,
            raster_tilesets=3,
            pmtiles_tilesets=2
        )
        
        issue = BoundsIssue(
            tileset_id="test-id",
            tileset_name="Test",
            issue_type="invalid_bounds",
            description="test"
        )
        report.issues.append(issue)
        
        assert report.total_tilesets == 10
        assert len(report.issues) == 1


# ============================================================================
# Integration Tests (require database)
# ============================================================================

class TestDatabaseIntegration:
    """Integration tests requiring database connection."""
    
    @pytest.mark.skip(reason="Requires DATABASE_URL")
    def test_scan_and_fix_dry_run(self, database_url):
        """Test scanning tilesets in dry-run mode."""
        from fix_bounds import scan_and_fix
        
        report = scan_and_fix(
            database_url=database_url,
            dry_run=True,
            fix_issues=True
        )
        
        assert report.total_tilesets >= 0
        # No changes should be made in dry-run
