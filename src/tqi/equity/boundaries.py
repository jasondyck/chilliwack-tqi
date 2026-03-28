"""Load and filter DA boundary polygons."""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from tqi.config import BBOX_NE, BBOX_SW


def load_da_boundaries(
    shapefile_path: Path,
    bbox_sw: tuple[float, float] = BBOX_SW,
    bbox_ne: tuple[float, float] = BBOX_NE,
) -> gpd.GeoDataFrame:
    """Load DA boundary shapefile, filter to Chilliwack bbox.

    Returns GeoDataFrame in EPSG:4326 with DGUID column.
    """
    gdf = gpd.read_file(shapefile_path)

    # Reproject to WGS84 if needed
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Clip to bounding box
    bbox_geom = box(bbox_sw[1], bbox_sw[0], bbox_ne[1], bbox_ne[0])
    gdf = gdf[gdf.intersects(bbox_geom)].copy()

    # Normalise DGUID column name
    dguid_col = next((c for c in gdf.columns if "DGUID" in c.upper()), None)
    if dguid_col and dguid_col != "DGUID":
        gdf = gdf.rename(columns={dguid_col: "DGUID"})

    print(f"Loaded {len(gdf)} DAs within Chilliwack bbox")
    return gdf
