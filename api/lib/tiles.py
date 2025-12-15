"""
Tile serving utilities for geo-base API.

Features:
- MBTiles/PMTiles static tile serving
- Dynamic MVT generation from PostGIS
- Multi-layer MVT support (each layer_name as separate MVT layer)
- Attribute filtering
- Zoom-level based geometry simplification
- Optimized cache headers
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from pymbtiles import MBtiles

# =============================================================================
# Constants
# =============================================================================

VECTOR_TILE_MEDIA_TYPE = "application/vnd.mapbox-vector-tile"
PNG_MEDIA_TYPE = "image/png"
JPG_MEDIA_TYPE = "image/jpeg"
WEBP_MEDIA_TYPE = "image/webp"

FORMAT_MEDIA_TYPES = {
    "pbf": VECTOR_TILE_MEDIA_TYPE,
    "mvt": VECTOR_TILE_MEDIA_TYPE,
    "png": PNG_MEDIA_TYPE,
    "jpg": JPG_MEDIA_TYPE,
    "jpeg": JPG_MEDIA_TYPE,
    "webp": WEBP_MEDIA_TYPE,
}

# =============================================================================
# Coordinate Conversion
# =============================================================================


def xyz_to_tms(z: int, y: int) -> int:
    """Convert XYZ tile coordinates to TMS coordinates."""
    return (2**z) - y - 1


def tms_to_xyz(z: int, y: int) -> int:
    """Convert TMS tile coordinates to XYZ coordinates."""
    return (2**z) - y - 1


# =============================================================================
# Zoom-Level Based Configuration
# =============================================================================


def get_simplification_tolerance(z: int) -> float:
    """
    Calculate geometry simplification tolerance based on zoom level.
    
    Lower zoom levels (zoomed out) get more aggressive simplification.
    Higher zoom levels (zoomed in) get minimal or no simplification.
    
    The tolerance is in Web Mercator units (meters at equator).
    
    Args:
        z: Zoom level (0-22)
        
    Returns:
        Simplification tolerance in meters
    """
    # At zoom 0, one tile covers the whole world (~40,075 km)
    # At zoom 22, one tile is ~9.5 meters
    # We want more simplification at low zooms
    
    if z >= 16:
        # High zoom: no simplification needed
        return 0
    elif z >= 12:
        # Medium-high zoom: minimal simplification
        return 1  # 1 meter
    elif z >= 8:
        # Medium zoom: moderate simplification
        return 10  # 10 meters
    elif z >= 4:
        # Low-medium zoom: more simplification
        return 100  # 100 meters
    else:
        # Very low zoom: aggressive simplification
        return 1000  # 1 km


def get_cache_ttl(z: int, is_static: bool = False) -> int:
    """
    Calculate cache TTL (Time To Live) based on zoom level and data type.
    
    Static tiles can be cached longer.
    Lower zoom levels (overview tiles) change less frequently.
    
    Args:
        z: Zoom level (0-22)
        is_static: Whether the tile is from static source (MBTiles, etc.)
        
    Returns:
        Cache TTL in seconds
    """
    if is_static:
        # Static tiles: long cache
        return 604800  # 7 days
    
    # Dynamic tiles: cache varies by zoom
    if z <= 6:
        # Overview tiles: cache longer (data changes less impact these)
        return 86400  # 24 hours
    elif z <= 12:
        # Mid-level tiles
        return 3600  # 1 hour
    else:
        # Detail tiles: shorter cache for more frequent updates
        return 300  # 5 minutes


def get_cache_headers(z: int, is_static: bool = False) -> dict:
    """
    Generate optimized cache headers based on zoom level.
    
    Args:
        z: Zoom level
        is_static: Whether the tile is static
        
    Returns:
        Dict of HTTP headers
    """
    ttl = get_cache_ttl(z, is_static)
    
    headers = {
        "Cache-Control": f"public, max-age={ttl}, s-maxage={ttl}",
        "Access-Control-Allow-Origin": "*",
    }
    
    # Add stale-while-revalidate for dynamic tiles
    if not is_static:
        headers["Cache-Control"] += f", stale-while-revalidate={ttl // 2}"
    
    return headers


# =============================================================================
# Attribute Filtering
# =============================================================================


def parse_filter_expression(filter_str: str) -> tuple[str, dict]:
    """
    Parse a filter expression string into SQL WHERE clause and parameters.
    
    Supported formats:
    - Simple equality: "type=station"
    - Multiple values: "type=station,landmark"
    - Comparison: "population>1000000"
    - JSONB path: "properties.category=restaurant"
    
    Args:
        filter_str: Filter expression string
        
    Returns:
        Tuple of (SQL WHERE clause, parameters dict)
    """
    if not filter_str:
        return "TRUE", {}
    
    conditions = []
    params = {}
    param_counter = 0
    
    # Split by comma for OR conditions at top level, semicolon for AND
    # Example: "type=station;name_en=Tokyo" -> type=station AND name_en=Tokyo
    
    for expr in filter_str.split(";"):
        expr = expr.strip()
        if not expr:
            continue
        
        # Parse comparison operators
        match = re.match(r"^([\w.]+)\s*(=|!=|>|>=|<|<=|~)\s*(.+)$", expr)
        if not match:
            continue
        
        field, operator, value = match.groups()
        param_name = f"filter_{param_counter}"
        param_counter += 1
        
        # Check if it's a JSONB property access
        if "." in field:
            parts = field.split(".", 1)
            if parts[0] == "properties":
                # JSONB access: properties.key
                json_key = parts[1]
                
                if operator == "=":
                    # Handle multiple values (OR)
                    if "," in value:
                        values = [v.strip() for v in value.split(",")]
                        value_params = []
                        for i, v in enumerate(values):
                            p_name = f"{param_name}_{i}"
                            params[p_name] = v
                            value_params.append(f"%({p_name})s")
                        conditions.append(
                            f"(properties->>'{json_key}') IN ({', '.join(value_params)})"
                        )
                    else:
                        params[param_name] = value
                        conditions.append(f"(properties->>'{json_key}') = %({param_name})s")
                elif operator == "!=":
                    params[param_name] = value
                    conditions.append(f"(properties->>'{json_key}') != %({param_name})s")
                elif operator == "~":
                    # Pattern matching (LIKE)
                    params[param_name] = f"%{value}%"
                    conditions.append(f"(properties->>'{json_key}') ILIKE %({param_name})s")
                else:
                    # Numeric comparison for JSONB
                    params[param_name] = value
                    conditions.append(
                        f"(properties->>'{json_key}')::numeric {operator} %({param_name})s"
                    )
        else:
            # Regular column access
            if operator == "=":
                if "," in value:
                    values = [v.strip() for v in value.split(",")]
                    value_params = []
                    for i, v in enumerate(values):
                        p_name = f"{param_name}_{i}"
                        params[p_name] = v
                        value_params.append(f"%({p_name})s")
                    conditions.append(f"{field} IN ({', '.join(value_params)})")
                else:
                    params[param_name] = value
                    conditions.append(f"{field} = %({param_name})s")
            elif operator == "!=":
                params[param_name] = value
                conditions.append(f"{field} != %({param_name})s")
            elif operator == "~":
                params[param_name] = f"%{value}%"
                conditions.append(f"{field} ILIKE %({param_name})s")
            else:
                params[param_name] = value
                conditions.append(f"{field} {operator} %({param_name})s")
    
    if not conditions:
        return "TRUE", {}
    
    return " AND ".join(conditions), params


def build_bbox_filter(
    bbox: Optional[str],
    geometry_column: str = "geom",
    srid: int = 4326,
) -> tuple[str, dict]:
    """
    Build a bounding box filter for spatial queries.
    
    Args:
        bbox: Bounding box string "minx,miny,maxx,maxy"
        geometry_column: Name of the geometry column
        srid: SRID of the bounding box coordinates
        
    Returns:
        Tuple of (SQL WHERE clause, parameters dict)
    """
    if not bbox:
        return "TRUE", {}
    
    try:
        coords = [float(c.strip()) for c in bbox.split(",")]
        if len(coords) != 4:
            raise ValueError("BBOX must have 4 coordinates")
        
        minx, miny, maxx, maxy = coords
        
        return (
            f"{geometry_column} && ST_MakeEnvelope(%(minx)s, %(miny)s, %(maxx)s, %(maxy)s, {srid})",
            {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}
        )
    except Exception:
        return "TRUE", {}


# =============================================================================
# MBTiles Functions
# =============================================================================


def get_tile_from_mbtiles(
    mbtiles_path: str | Path,
    z: int,
    x: int,
    y: int,
    use_tms: bool = True,
) -> bytes | None:
    """Get a tile from an MBTiles file."""
    if use_tms:
        y = xyz_to_tms(z, y)

    with MBtiles(str(mbtiles_path)) as mbtiles:
        tile_data = mbtiles.read_tile(z=z, x=x, y=y)

    return tile_data


def get_mbtiles_metadata(mbtiles_path: str | Path) -> dict[str, Any]:
    """Get metadata from an MBTiles file."""
    with MBtiles(str(mbtiles_path)) as mbtiles:
        metadata = dict(mbtiles.meta)

    return metadata


# =============================================================================
# Dynamic MVT Generation
# =============================================================================


def generate_mvt_from_postgis(
    conn,
    table_name: str,
    z: int,
    x: int,
    y: int,
    geometry_column: str = "geom",
    layer_name: str | None = None,
    columns: list[str] | None = None,
    srid: int = 4326,
    simplify: bool = True,
    where_clause: str = "TRUE",
    params: dict | None = None,
) -> bytes:
    """
    Generate a Mapbox Vector Tile from PostGIS data.
    
    Features:
    - Automatic geometry simplification based on zoom level
    - Custom WHERE clause for filtering
    - Configurable columns to include
    
    Args:
        conn: Database connection
        table_name: Name of the table to query
        z: Zoom level
        x: X coordinate
        y: Y coordinate
        geometry_column: Name of the geometry column
        layer_name: Name of the layer in the MVT (defaults to table_name)
        columns: List of columns to include in properties
        srid: SRID of the source geometry
        simplify: Whether to apply zoom-based simplification
        where_clause: Additional WHERE clause for filtering
        params: Parameters for the WHERE clause
        
    Returns:
        MVT data as bytes
    """
    if layer_name is None:
        layer_name = table_name
    
    if params is None:
        params = {}
    
    # Always include these params
    params.update({"z": z, "x": x, "y": y, "layer_name": layer_name})

    # Build column selection
    if columns:
        column_select = ", " + ", ".join(columns)
    else:
        column_select = ""

    # Get simplification tolerance
    tolerance = get_simplification_tolerance(z) if simplify else 0
    
    # Build geometry transformation
    # First transform to Web Mercator (3857), then optionally simplify
    if tolerance > 0:
        geom_transform = f"""
            ST_SimplifyPreserveTopology(
                ST_Transform({geometry_column}, 3857),
                {tolerance}
            )
        """
    else:
        geom_transform = f"ST_Transform({geometry_column}, 3857)"

    # Build the query
    query = f"""
        WITH mvtgeom AS (
            SELECT
                ST_AsMVTGeom(
                    {geom_transform},
                    ST_TileEnvelope(%(z)s, %(x)s, %(y)s),
                    4096,
                    256,
                    true
                ) AS geom
                {column_select}
            FROM {table_name}
            WHERE ST_Transform({geometry_column}, 3857) && ST_TileEnvelope(%(z)s, %(x)s, %(y)s)
              AND ({where_clause})
        )
        SELECT ST_AsMVT(mvtgeom.*, %(layer_name)s, 4096, 'geom')
        FROM mvtgeom
        WHERE geom IS NOT NULL;
    """

    with conn.cursor() as cur:
        cur.execute(query, params)
        result = cur.fetchone()

    if result and result[0]:
        return result[0].tobytes()

    return b""


def generate_features_mvt(
    conn,
    z: int,
    x: int,
    y: int,
    tileset_id: str | None = None,
    layer_name: str | None = None,
    filter_expr: str | None = None,
    simplify: bool = True,
) -> bytes:
    """
    Generate MVT from the features table with multi-layer support.
    
    When layer_name is specified, generates a single layer with that name.
    When layer_name is None, generates multiple layers - one for each distinct
    layer_name in the database. This allows QGIS and other GIS tools to display
    each layer with different styles.
    
    Args:
        conn: Database connection
        z: Zoom level
        x: X coordinate  
        y: Y coordinate
        tileset_id: Optional tileset ID filter
        layer_name: Optional layer name filter (also used as MVT layer name)
        filter_expr: Optional attribute filter expression
        simplify: Whether to apply zoom-based simplification
        
    Returns:
        MVT data as bytes
    """
    # Get simplification tolerance
    tolerance = get_simplification_tolerance(z) if simplify else 0
    
    # Build geometry transformation
    if tolerance > 0:
        geom_transform = f"""
            ST_SimplifyPreserveTopology(
                ST_Transform(geom, 3857),
                {tolerance}
            )
        """
    else:
        geom_transform = "ST_Transform(geom, 3857)"
    
    # Parse attribute filter if provided
    filter_clause = "TRUE"
    filter_params = {}
    if filter_expr:
        filter_clause, filter_params = parse_filter_expression(filter_expr)
    
    # If specific layer_name is requested, generate single layer
    if layer_name:
        params = {"z": z, "x": x, "y": y, "layer_name": layer_name}
        
        conditions = [f"layer_name = %(layer_name)s"]
        if tileset_id:
            conditions.append("tileset_id = %(tileset_id)s")
            params["tileset_id"] = tileset_id
        if filter_clause != "TRUE":
            conditions.append(filter_clause)
            params.update(filter_params)
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            WITH mvtgeom AS (
                SELECT
                    ST_AsMVTGeom(
                        {geom_transform},
                        ST_TileEnvelope(%(z)s, %(x)s, %(y)s),
                        4096,
                        256,
                        true
                    ) AS geom,
                    id::text as feature_id,
                    layer_name,
                    properties
                FROM features
                WHERE ST_Transform(geom, 3857) && ST_TileEnvelope(%(z)s, %(x)s, %(y)s)
                  AND ({where_clause})
            )
            SELECT ST_AsMVT(mvtgeom.*, %(layer_name)s, 4096, 'geom')
            FROM mvtgeom
            WHERE geom IS NOT NULL;
        """
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchone()
        
        if result and result[0]:
            return result[0].tobytes()
        return b""
    
    # Multi-layer mode: generate separate MVT layer for each layer_name
    # First, get all distinct layer names within the tile bounds
    layer_query_params = {"z": z, "x": x, "y": y}
    layer_conditions = ["ST_Transform(geom, 3857) && ST_TileEnvelope(%(z)s, %(x)s, %(y)s)"]
    
    if tileset_id:
        layer_conditions.append("tileset_id = %(tileset_id)s")
        layer_query_params["tileset_id"] = tileset_id
    if filter_clause != "TRUE":
        layer_conditions.append(filter_clause)
        layer_query_params.update(filter_params)
    
    layer_where = " AND ".join(layer_conditions)
    
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT DISTINCT layer_name
            FROM features
            WHERE {layer_where}
            ORDER BY layer_name
            """,
            layer_query_params
        )
        layer_names = [row[0] for row in cur.fetchall()]
    
    if not layer_names:
        return b""
    
    # Generate MVT for each layer and concatenate using PostgreSQL's || operator
    # This creates a single MVT with multiple named layers
    mvt_parts = []
    
    for ln in layer_names:
        params = {"z": z, "x": x, "y": y, "current_layer": ln}
        
        conditions = ["layer_name = %(current_layer)s"]
        if tileset_id:
            conditions.append("tileset_id = %(tileset_id)s")
            params["tileset_id"] = tileset_id
        if filter_clause != "TRUE":
            conditions.append(filter_clause)
            params.update(filter_params)
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            WITH mvtgeom AS (
                SELECT
                    ST_AsMVTGeom(
                        {geom_transform},
                        ST_TileEnvelope(%(z)s, %(x)s, %(y)s),
                        4096,
                        256,
                        true
                    ) AS geom,
                    id::text as feature_id,
                    layer_name,
                    properties
                FROM features
                WHERE ST_Transform(geom, 3857) && ST_TileEnvelope(%(z)s, %(x)s, %(y)s)
                  AND ({where_clause})
            )
            SELECT ST_AsMVT(mvtgeom.*, %(current_layer)s, 4096, 'geom')
            FROM mvtgeom
            WHERE geom IS NOT NULL;
        """
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchone()
        
        if result and result[0]:
            mvt_parts.append(result[0].tobytes())
    
    if not mvt_parts:
        return b""
    
    # Concatenate all MVT parts
    # MVT is a Protobuf format where multiple layers can be concatenated
    return b"".join(mvt_parts)


# =============================================================================
# TileJSON Generation
# =============================================================================


def generate_tilejson(
    tileset_id: str,
    name: str,
    base_url: str,
    tile_format: str = "pbf",
    min_zoom: int = 0,
    max_zoom: int = 22,
    bounds: list[float] | None = None,
    center: list[float] | None = None,
    description: str | None = None,
    attribution: str | None = None,
    vector_layers: list[dict] | None = None,
) -> dict[str, Any]:
    """Generate a TileJSON specification."""
    if bounds is None:
        bounds = [-180, -85.051129, 180, 85.051129]

    if center is None:
        center = [0, 0, 2]

    tilejson = {
        "tilejson": "3.0.0",
        "name": name,
        "tiles": [f"{base_url}/api/tiles/{tileset_id}/{{z}}/{{x}}/{{y}}.{tile_format}"],
        "minzoom": min_zoom,
        "maxzoom": max_zoom,
        "bounds": bounds,
        "center": center,
    }

    if description:
        tilejson["description"] = description

    if attribution:
        tilejson["attribution"] = attribution

    if vector_layers:
        tilejson["vector_layers"] = vector_layers

    return tilejson
