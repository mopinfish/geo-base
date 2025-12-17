"""
Colormap endpoints for raster visualization.
"""

from fastapi import APIRouter, HTTPException

from lib.raster_tiles import list_colormaps, is_rasterio_available


router = APIRouter(prefix="/api/colormaps", tags=["colormaps"])


@router.get("")
def get_colormaps():
    """
    List all available colormaps for raster visualization.
    
    Returns:
        List of colormap names with descriptions
    """
    try:
        colormaps = list_colormaps()
        
        descriptions = {
            "ndvi": "Vegetation index - red to yellow to green",
            "vegetation": "Alias for NDVI colormap",
            "terrain": "Elevation/DEM - green to brown to white",
            "elevation": "Alias for terrain colormap",
            "dem": "Alias for terrain colormap",
            "temperature": "Cool to warm - blue to white to red",
            "coolwarm": "Alias for temperature colormap",
            "precipitation": "Rainfall - white to blue to purple",
            "rainfall": "Alias for precipitation colormap",
            "bathymetry": "Ocean depth - deep blue to turquoise",
            "ocean": "Alias for bathymetry colormap",
            "grayscale": "Black to white gradient",
            "hillshade": "Alias for grayscale colormap",
            "viridis": "Perceptually uniform - purple to green to yellow",
        }
        
        return {
            "colormaps": [
                {
                    "name": cm,
                    "description": descriptions.get(cm, ""),
                }
                for cm in colormaps
            ],
            "count": len(colormaps),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing colormaps: {str(e)}")


@router.get("/{name}")
def get_colormap_info(name: str):
    """
    Get information about a specific colormap.
    
    Args:
        name: Colormap name
        
    Returns:
        Colormap details including color stops
    """
    try:
        from lib.raster_tiles import get_colormap, COLORMAP_PRESETS
        
        cmap = get_colormap(name)
        if not cmap:
            raise HTTPException(status_code=404, detail=f"Colormap '{name}' not found")
        
        # Extract color stops
        color_stops = []
        for value, rgba in sorted(cmap.items()):
            color_stops.append({
                "value": value,
                "color": f"rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3] / 255:.2f})",
                "hex": f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}",
            })
        
        return {
            "name": name,
            "color_stops": color_stops,
            "is_preset": name.lower() in COLORMAP_PRESETS,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting colormap: {str(e)}")
