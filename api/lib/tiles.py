"""
Tile serving utilities for geo-base API.
"""

from pathlib import Path
from typing import Any

from pymbtiles import MBtiles

# Tile format constants
VECTOR_TILE_MEDIA_TYPE = "application/vnd.mapbox-vector-tile"
PNG_MEDIA_TYPE = "image/png"
JPG_MEDIA_TYPE = "image/jpeg"
WEBP_MEDIA_TYPE = "image/webp"

# Format to media type mapping
FORMAT_MEDIA_TYPES = {
    "pbf": VECTOR_TILE_MEDIA_TYPE,
    "mvt": VECTOR_TILE_MEDIA_TYPE,
    "png": PNG_MEDIA_TYPE,
    "jpg": JPG_MEDIA_TYPE,
    "jpeg": JPG_MEDIA_TYPE,
    "webp": WEBP_MEDIA_TYPE,
}


def xyz_to_tms(z: int, y: int) -> int:
    """
    Convert XYZ tile coordinates to TMS coordinates.

    XYZ: Origin at top-left (used by most web maps)
    TMS: Origin at bottom-left (used by MBTiles)

    Args:
        z: Zoom level
        y: Y coordinate in XYZ scheme

    Returns:
        Y coordinate in TMS scheme
    """
    return (2**z) - y - 1


def tms_to_xyz(z: int, y: int) -> int:
    """
    Convert TMS tile coordinates to XYZ coordinates.

    Args:
        z: Zoom level
        y: Y coordinate in TMS scheme

    Returns:
        Y coordinate in XYZ scheme
    """
    return (2**z) - y - 1


def get_tile_from_mbtiles(
    mbtiles_path: str | Path,
    z: int,
    x: int,
    y: int,
    use_tms: bool = True,
) -> bytes | None:
    """
    Get a tile from an MBTiles file.

    Args:
        mbtiles_path: Path to the MBTiles file
        z: Zoom level
        x: X coordinate
        y: Y coordinate (in XYZ scheme)
        use_tms: If True, convert XYZ to TMS coordinates

    Returns:
        Tile data as bytes, or None if tile doesn't exist
    """
    if use_tms:
        y = xyz_to_tms(z, y)

    with MBtiles(str(mbtiles_path)) as mbtiles:
        tile_data = mbtiles.read_tile(z=z, x=x, y=y)

    return tile_data


def get_mbtiles_metadata(mbtiles_path: str | Path) -> dict[str, Any]:
    """
    Get metadata from an MBTiles file.

    Args:
        mbtiles_path: Path to the MBTiles file

    Returns:
        Dictionary containing metadata
    """
    with MBtiles(str(mbtiles_path)) as mbtiles:
        metadata = dict(mbtiles.meta)

    return metadata


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
) -> bytes:
    """
    Generate a Mapbox Vector Tile from PostGIS data.

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

    Returns:
        MVT data as bytes
    """
    if layer_name is None:
        layer_name = table_name

    # Build column selection
    if columns:
        column_select = ", ".join(columns)
        column_select = f", {column_select}"
    else:
        column_select = ""

    # Build the query
    query = f"""
        WITH mvtgeom AS (
            SELECT
                ST_AsMVTGeom(
                    ST_Transform({geometry_column}, 3857),
                    ST_TileEnvelope(%(z)s, %(x)s, %(y)s)
                ) AS geom
                {column_select}
            FROM {table_name}
            WHERE ST_Transform({geometry_column}, 3857) && ST_TileEnvelope(%(z)s, %(x)s, %(y)s)
        )
        SELECT ST_AsMVT(mvtgeom.*, %(layer_name)s)
        FROM mvtgeom;
    """

    with conn.cursor() as cur:
        cur.execute(query, {"z": z, "x": x, "y": y, "layer_name": layer_name})
        result = cur.fetchone()

    if result and result[0]:
        return result[0].tobytes()

    return b""


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
    """
    Generate a TileJSON specification.

    Args:
        tileset_id: Unique identifier for the tileset
        name: Human-readable name
        base_url: Base URL for tile requests
        tile_format: Tile format (pbf, png, jpg, etc.)
        min_zoom: Minimum zoom level
        max_zoom: Maximum zoom level
        bounds: Bounding box [west, south, east, north]
        center: Center point [lon, lat, zoom]
        description: Description of the tileset
        attribution: Attribution string
        vector_layers: Vector layer definitions (for vector tiles)

    Returns:
        TileJSON dictionary
    """
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
