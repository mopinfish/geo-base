#!/usr/bin/env python3
"""
Fix bounds/center for existing tilesets.

This script recalculates and fixes bounds/center values for tilesets
that have incorrect or missing geographic metadata.

Features:
- Dry-run mode for safe preview
- Validates existing bounds/center values
- Recalculates from features for vector tilesets
- Reports anomalies and fixes applied

Usage:
    # Dry run (preview changes)
    python fix_bounds.py --dry-run

    # Apply fixes
    python fix_bounds.py

    # Fix specific tileset
    python fix_bounds.py --tileset-id <uuid>

    # Verbose output
    python fix_bounds.py --verbose

Environment variables:
    DATABASE_URL - PostgreSQL connection string (required)
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 is required. Install with: pip install psycopg2-binary")
    sys.exit(1)


# ============================================================================
# Constants
# ============================================================================

LON_MIN, LON_MAX = -180.0, 180.0
LAT_MIN, LAT_MAX = -90.0, 90.0


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BoundsIssue:
    """Represents an issue with bounds/center values."""
    tileset_id: str
    tileset_name: str
    issue_type: str
    description: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None


@dataclass
class FixResult:
    """Result of a fix operation."""
    tileset_id: str
    tileset_name: str
    action: str
    old_bounds: Optional[List[float]] = None
    new_bounds: Optional[List[float]] = None
    old_center: Optional[List[float]] = None
    new_center: Optional[List[float]] = None
    feature_count: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class ScanReport:
    """Report from scanning tilesets."""
    total_tilesets: int = 0
    vector_tilesets: int = 0
    raster_tilesets: int = 0
    pmtiles_tilesets: int = 0
    issues: List[BoundsIssue] = field(default_factory=list)
    fixes_applied: List[FixResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ============================================================================
# Validation Functions
# ============================================================================

def validate_bounds(bounds: Optional[List[float]]) -> Tuple[bool, Optional[str]]:
    """
    Validate bounds values.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if bounds is None:
        return True, None  # None is valid (just missing)
    
    if len(bounds) != 4:
        return False, f"bounds must have 4 values, got {len(bounds)}"
    
    west, south, east, north = bounds
    
    # Check for NaN or infinity
    for i, val in enumerate(bounds):
        if val != val:  # NaN check
            return False, f"bounds[{i}] is NaN"
        if abs(val) == float('inf'):
            return False, f"bounds[{i}] is infinite"
    
    # Validate ranges
    if not (LON_MIN <= west <= LON_MAX):
        return False, f"west ({west}) out of range [{LON_MIN}, {LON_MAX}]"
    if not (LON_MIN <= east <= LON_MAX):
        return False, f"east ({east}) out of range [{LON_MIN}, {LON_MAX}]"
    if not (LAT_MIN <= south <= LAT_MAX):
        return False, f"south ({south}) out of range [{LAT_MIN}, {LAT_MAX}]"
    if not (LAT_MIN <= north <= LAT_MAX):
        return False, f"north ({north}) out of range [{LAT_MIN}, {LAT_MAX}]"
    
    # Validate south <= north
    if south > north:
        return False, f"south ({south}) > north ({north})"
    
    return True, None


def validate_center(center: Optional[List[float]]) -> Tuple[bool, Optional[str]]:
    """
    Validate center values.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if center is None:
        return True, None  # None is valid (just missing)
    
    if len(center) < 2:
        return False, f"center must have at least 2 values, got {len(center)}"
    
    lon, lat = center[0], center[1]
    
    # Check for NaN or infinity
    if lon != lon or lat != lat:
        return False, "center contains NaN"
    if abs(lon) == float('inf') or abs(lat) == float('inf'):
        return False, "center contains infinite value"
    
    # Validate ranges
    if not (LON_MIN <= lon <= LON_MAX):
        return False, f"center longitude ({lon}) out of range"
    if not (LAT_MIN <= lat <= LAT_MAX):
        return False, f"center latitude ({lat}) out of range"
    
    return True, None


def is_center_in_bounds(
    center: Optional[List[float]], 
    bounds: Optional[List[float]]
) -> Tuple[bool, Optional[str]]:
    """
    Check if center is within bounds.
    
    Returns:
        Tuple of (is_in_bounds, warning_message)
    """
    if center is None or bounds is None:
        return True, None
    
    lon, lat = center[0], center[1]
    west, south, east, north = bounds
    
    lat_in_bounds = south <= lat <= north
    
    # Handle antimeridian crossing
    if west <= east:
        lon_in_bounds = west <= lon <= east
    else:
        lon_in_bounds = lon >= west or lon <= east
    
    if not lat_in_bounds or not lon_in_bounds:
        return False, f"center ({lon}, {lat}) is outside bounds"
    
    return True, None


# ============================================================================
# Database Functions
# ============================================================================

def get_connection(database_url: str):
    """Create database connection."""
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def get_all_tilesets(conn, tileset_id: Optional[str] = None) -> List[dict]:
    """Fetch all tilesets or a specific tileset."""
    with conn.cursor() as cur:
        if tileset_id:
            cur.execute(
                """
                SELECT 
                    id, name, type, format,
                    ST_XMin(bounds) as bounds_west,
                    ST_YMin(bounds) as bounds_south,
                    ST_XMax(bounds) as bounds_east,
                    ST_YMax(bounds) as bounds_north,
                    ST_X(center) as center_lon,
                    ST_Y(center) as center_lat,
                    user_id, created_at, updated_at
                FROM tilesets
                WHERE id = %s
                """,
                (tileset_id,)
            )
        else:
            cur.execute(
                """
                SELECT 
                    id, name, type, format,
                    ST_XMin(bounds) as bounds_west,
                    ST_YMin(bounds) as bounds_south,
                    ST_XMax(bounds) as bounds_east,
                    ST_YMax(bounds) as bounds_north,
                    ST_X(center) as center_lon,
                    ST_Y(center) as center_lat,
                    user_id, created_at, updated_at
                FROM tilesets
                ORDER BY created_at DESC
                """
            )
        return cur.fetchall()


def get_feature_count(conn, tileset_id: str) -> int:
    """Get the number of features in a tileset."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) as count FROM features WHERE tileset_id = %s",
            (tileset_id,)
        )
        row = cur.fetchone()
        return row['count'] if row else 0


def calculate_bounds_from_features(
    conn, 
    tileset_id: str
) -> Tuple[Optional[List[float]], Optional[List[float]], int]:
    """
    Calculate bounds and center from features.
    
    Returns:
        Tuple of (bounds, center, feature_count)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 
                ST_XMin(ST_Extent(geom)) as xmin,
                ST_YMin(ST_Extent(geom)) as ymin,
                ST_XMax(ST_Extent(geom)) as xmax,
                ST_YMax(ST_Extent(geom)) as ymax,
                ST_X(ST_Centroid(ST_Extent(geom))) as center_x,
                ST_Y(ST_Centroid(ST_Extent(geom))) as center_y,
                COUNT(*) as feature_count
            FROM features
            WHERE tileset_id = %s
            """,
            (tileset_id,)
        )
        row = cur.fetchone()
        
        if not row or row['xmin'] is None:
            return None, None, 0
        
        bounds = [row['xmin'], row['ymin'], row['xmax'], row['ymax']]
        center = [row['center_x'], row['center_y']]
        feature_count = row['feature_count']
        
        return bounds, center, feature_count


def update_tileset_bounds(
    conn, 
    tileset_id: str, 
    bounds: Optional[List[float]], 
    center: Optional[List[float]],
    dry_run: bool = True
) -> bool:
    """
    Update tileset bounds and center.
    
    Returns:
        True if successful
    """
    if dry_run:
        return True
    
    try:
        with conn.cursor() as cur:
            if bounds and center:
                cur.execute(
                    """
                    UPDATE tilesets
                    SET bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                        center = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (*bounds, *center, tileset_id)
                )
            elif bounds:
                cur.execute(
                    """
                    UPDATE tilesets
                    SET bounds = ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (*bounds, tileset_id)
                )
            elif center:
                cur.execute(
                    """
                    UPDATE tilesets
                    SET center = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (*center, tileset_id)
                )
            else:
                return True  # Nothing to update
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        raise e


# ============================================================================
# Scan and Fix Functions
# ============================================================================

def scan_tileset(conn, tileset: dict, report: ScanReport, verbose: bool = False):
    """Scan a single tileset for issues."""
    tileset_id = str(tileset['id'])
    tileset_name = tileset['name']
    tileset_type = tileset['type']
    
    # Build current bounds/center
    current_bounds = None
    if tileset['bounds_west'] is not None:
        current_bounds = [
            tileset['bounds_west'],
            tileset['bounds_south'],
            tileset['bounds_east'],
            tileset['bounds_north']
        ]
    
    current_center = None
    if tileset['center_lon'] is not None:
        current_center = [tileset['center_lon'], tileset['center_lat']]
    
    # Validate current bounds
    bounds_valid, bounds_error = validate_bounds(current_bounds)
    if not bounds_valid:
        report.issues.append(BoundsIssue(
            tileset_id=tileset_id,
            tileset_name=tileset_name,
            issue_type="invalid_bounds",
            description=bounds_error,
            current_value=str(current_bounds)
        ))
    
    # Validate current center
    center_valid, center_error = validate_center(current_center)
    if not center_valid:
        report.issues.append(BoundsIssue(
            tileset_id=tileset_id,
            tileset_name=tileset_name,
            issue_type="invalid_center",
            description=center_error,
            current_value=str(current_center)
        ))
    
    # Check if center is in bounds
    if bounds_valid and center_valid:
        in_bounds, in_bounds_warning = is_center_in_bounds(current_center, current_bounds)
        if not in_bounds:
            report.issues.append(BoundsIssue(
                tileset_id=tileset_id,
                tileset_name=tileset_name,
                issue_type="center_outside_bounds",
                description=in_bounds_warning,
                current_value=f"center={current_center}, bounds={current_bounds}"
            ))
    
    # For vector tilesets, check against actual features
    if tileset_type == "vector":
        feature_count = get_feature_count(conn, tileset_id)
        
        if feature_count > 0:
            calc_bounds, calc_center, _ = calculate_bounds_from_features(conn, tileset_id)
            
            # Check for missing bounds
            if current_bounds is None and calc_bounds is not None:
                report.issues.append(BoundsIssue(
                    tileset_id=tileset_id,
                    tileset_name=tileset_name,
                    issue_type="missing_bounds",
                    description=f"Tileset has {feature_count} features but no bounds",
                    suggested_value=str(calc_bounds)
                ))
            
            # Check for missing center
            if current_center is None and calc_center is not None:
                report.issues.append(BoundsIssue(
                    tileset_id=tileset_id,
                    tileset_name=tileset_name,
                    issue_type="missing_center",
                    description=f"Tileset has {feature_count} features but no center",
                    suggested_value=str(calc_center)
                ))
            
            # Check for significant difference in bounds
            if current_bounds is not None and calc_bounds is not None:
                # Calculate difference
                diff_west = abs(current_bounds[0] - calc_bounds[0])
                diff_south = abs(current_bounds[1] - calc_bounds[1])
                diff_east = abs(current_bounds[2] - calc_bounds[2])
                diff_north = abs(current_bounds[3] - calc_bounds[3])
                
                max_diff = max(diff_west, diff_south, diff_east, diff_north)
                
                # Threshold: 0.001 degrees is about 100m at equator
                if max_diff > 0.001:
                    report.issues.append(BoundsIssue(
                        tileset_id=tileset_id,
                        tileset_name=tileset_name,
                        issue_type="bounds_mismatch",
                        description=f"Stored bounds differ from calculated (max diff: {max_diff:.6f})",
                        current_value=str(current_bounds),
                        suggested_value=str(calc_bounds)
                    ))
        
        elif current_bounds is not None:
            # Has bounds but no features
            report.issues.append(BoundsIssue(
                tileset_id=tileset_id,
                tileset_name=tileset_name,
                issue_type="empty_tileset_with_bounds",
                description="Tileset has bounds but no features"
            ))
    
    if verbose:
        print(f"  Scanned: {tileset_name} ({tileset_type})")


def fix_tileset(
    conn, 
    tileset: dict, 
    report: ScanReport, 
    dry_run: bool = True,
    verbose: bool = False
) -> Optional[FixResult]:
    """Fix bounds/center for a single tileset."""
    tileset_id = str(tileset['id'])
    tileset_name = tileset['name']
    tileset_type = tileset['type']
    
    # Only fix vector tilesets (we can recalculate from features)
    if tileset_type != "vector":
        return None
    
    # Get current values
    current_bounds = None
    if tileset['bounds_west'] is not None:
        current_bounds = [
            tileset['bounds_west'],
            tileset['bounds_south'],
            tileset['bounds_east'],
            tileset['bounds_north']
        ]
    
    current_center = None
    if tileset['center_lon'] is not None:
        current_center = [tileset['center_lon'], tileset['center_lat']]
    
    # Calculate from features
    calc_bounds, calc_center, feature_count = calculate_bounds_from_features(conn, tileset_id)
    
    if feature_count == 0:
        return None  # No features to calculate from
    
    # Check if update is needed
    needs_bounds_update = False
    needs_center_update = False
    
    # Check bounds
    bounds_valid, _ = validate_bounds(current_bounds)
    if not bounds_valid or current_bounds is None:
        needs_bounds_update = True
    elif calc_bounds is not None:
        max_diff = max(
            abs(current_bounds[0] - calc_bounds[0]),
            abs(current_bounds[1] - calc_bounds[1]),
            abs(current_bounds[2] - calc_bounds[2]),
            abs(current_bounds[3] - calc_bounds[3])
        )
        if max_diff > 0.001:
            needs_bounds_update = True
    
    # Check center
    center_valid, _ = validate_center(current_center)
    if not center_valid or current_center is None:
        needs_center_update = True
    
    if not needs_bounds_update and not needs_center_update:
        return None  # No update needed
    
    # Apply fix
    result = FixResult(
        tileset_id=tileset_id,
        tileset_name=tileset_name,
        action="dry_run" if dry_run else "applied",
        old_bounds=current_bounds,
        new_bounds=calc_bounds if needs_bounds_update else current_bounds,
        old_center=current_center,
        new_center=calc_center if needs_center_update else current_center,
        feature_count=feature_count
    )
    
    try:
        new_bounds = calc_bounds if needs_bounds_update else None
        new_center = calc_center if needs_center_update else None
        
        update_tileset_bounds(conn, tileset_id, new_bounds, new_center, dry_run)
        
        if verbose:
            action = "Would update" if dry_run else "Updated"
            print(f"  {action}: {tileset_name}")
            if needs_bounds_update:
                print(f"    bounds: {current_bounds} -> {calc_bounds}")
            if needs_center_update:
                print(f"    center: {current_center} -> {calc_center}")
        
    except Exception as e:
        result.success = False
        result.error = str(e)
        report.errors.append(f"Failed to update {tileset_name}: {str(e)}")
    
    return result


def scan_and_fix(
    database_url: str,
    tileset_id: Optional[str] = None,
    dry_run: bool = True,
    verbose: bool = False,
    fix_issues: bool = True
) -> ScanReport:
    """
    Scan tilesets and optionally fix issues.
    
    Args:
        database_url: PostgreSQL connection string
        tileset_id: Optional specific tileset to scan/fix
        dry_run: If True, don't apply changes
        verbose: Print detailed output
        fix_issues: If True, attempt to fix issues found
        
    Returns:
        ScanReport with findings and actions
    """
    report = ScanReport()
    
    conn = get_connection(database_url)
    
    try:
        # Fetch tilesets
        tilesets = get_all_tilesets(conn, tileset_id)
        report.total_tilesets = len(tilesets)
        
        print(f"\nScanning {report.total_tilesets} tileset(s)...")
        print("=" * 60)
        
        for tileset in tilesets:
            tileset_type = tileset['type']
            
            # Count by type
            if tileset_type == "vector":
                report.vector_tilesets += 1
            elif tileset_type == "raster":
                report.raster_tilesets += 1
            elif tileset_type == "pmtiles":
                report.pmtiles_tilesets += 1
            
            # Scan for issues
            scan_tileset(conn, tileset, report, verbose)
            
            # Fix if requested
            if fix_issues:
                result = fix_tileset(conn, tileset, report, dry_run, verbose)
                if result:
                    report.fixes_applied.append(result)
        
        print("=" * 60)
        
    finally:
        conn.close()
    
    return report


def print_report(report: ScanReport, dry_run: bool = True):
    """Print the scan report."""
    print("\n" + "=" * 60)
    print("SCAN REPORT")
    print("=" * 60)
    
    print(f"\nTilesets scanned: {report.total_tilesets}")
    print(f"  - Vector: {report.vector_tilesets}")
    print(f"  - Raster: {report.raster_tilesets}")
    print(f"  - PMTiles: {report.pmtiles_tilesets}")
    
    print(f"\nIssues found: {len(report.issues)}")
    
    if report.issues:
        print("\n--- Issues ---")
        for issue in report.issues:
            print(f"\n  [{issue.issue_type}] {issue.tileset_name}")
            print(f"    ID: {issue.tileset_id}")
            print(f"    Description: {issue.description}")
            if issue.current_value:
                print(f"    Current: {issue.current_value}")
            if issue.suggested_value:
                print(f"    Suggested: {issue.suggested_value}")
    
    print(f"\nFixes {'to apply' if dry_run else 'applied'}: {len(report.fixes_applied)}")
    
    if report.fixes_applied:
        print("\n--- Fixes ---")
        for fix in report.fixes_applied:
            status = "✓" if fix.success else "✗"
            print(f"\n  {status} {fix.tileset_name} ({fix.feature_count} features)")
            print(f"    ID: {fix.tileset_id}")
            if fix.old_bounds != fix.new_bounds:
                print(f"    bounds: {fix.old_bounds} -> {fix.new_bounds}")
            if fix.old_center != fix.new_center:
                print(f"    center: {fix.old_center} -> {fix.new_center}")
            if fix.error:
                print(f"    Error: {fix.error}")
    
    if report.errors:
        print(f"\nErrors: {len(report.errors)}")
        for error in report.errors:
            print(f"  - {error}")
    
    print("\n" + "=" * 60)
    
    if dry_run and report.fixes_applied:
        print("\n⚠️  DRY RUN MODE - No changes were applied.")
        print("    Run without --dry-run to apply fixes.")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Fix bounds/center for existing tilesets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run (preview changes)
    python fix_bounds.py --dry-run

    # Apply fixes
    python fix_bounds.py

    # Fix specific tileset
    python fix_bounds.py --tileset-id 123e4567-e89b-12d3-a456-426614174000

    # Scan only (no fixes)
    python fix_bounds.py --scan-only

Environment variables:
    DATABASE_URL - PostgreSQL connection string (required)
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--tileset-id",
        type=str,
        help="Fix specific tileset by ID"
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan for issues, don't fix"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output"
    )
    parser.add_argument(
        "--database-url",
        type=str,
        help="PostgreSQL connection string (overrides DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable or --database-url argument is required")
        sys.exit(1)
    
    # Determine mode
    dry_run = args.dry_run
    fix_issues = not args.scan_only
    
    print(f"\n{'=' * 60}")
    print(f"geo-base Bounds Fix Tool")
    print(f"{'=' * 60}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY FIXES'}")
    print(f"Fix issues: {'Yes' if fix_issues else 'No (scan only)'}")
    print(f"Tileset: {args.tileset_id or 'All'}")
    print(f"Time: {datetime.now().isoformat()}")
    
    try:
        report = scan_and_fix(
            database_url=database_url,
            tileset_id=args.tileset_id,
            dry_run=dry_run,
            verbose=args.verbose,
            fix_issues=fix_issues
        )
        
        print_report(report, dry_run)
        
        # Exit code
        if report.errors:
            sys.exit(1)
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
