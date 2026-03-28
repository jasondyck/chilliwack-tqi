"""Cross-reference TQI spatial scores with census demographics."""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


def compute_equity_overlay(
    grid_points: np.ndarray,
    grid_tqi_scores: np.ndarray,
    da_boundaries: gpd.GeoDataFrame,
    census_data: pd.DataFrame,
) -> pd.DataFrame:
    """Assign grid points to DAs and compute equity metrics.

    Args:
        grid_points: (N, 2) array of [lat, lon].
        grid_tqi_scores: (N,) array of per-grid-point outbound TQI scores.
        da_boundaries: GeoDataFrame with DA polygons and DGUID.
        census_data: DataFrame indexed by DGUID with income/demographic columns.

    Returns:
        DataFrame with one row per DA: DGUID, da_tqi, population, median_income, etc.
    """
    # Build GeoDataFrame of grid points
    geometry = [Point(lon, lat) for lat, lon in grid_points]
    grid_gdf = gpd.GeoDataFrame(
        {"tqi_score": grid_tqi_scores},
        geometry=geometry,
        crs="EPSG:4326",
    )

    # Spatial join: assign each grid point to a DA
    joined = gpd.sjoin(grid_gdf, da_boundaries[["DGUID", "geometry"]], how="left", predicate="within")

    # Aggregate TQI per DA
    da_tqi = joined.groupby("DGUID")["tqi_score"].agg(["mean", "count"]).reset_index()
    da_tqi.columns = ["DGUID", "da_tqi", "grid_point_count"]

    # Merge with census data
    result = da_tqi.merge(census_data, left_on="DGUID", right_index=True, how="left")

    # Compute correlation between TQI and income
    if "median_after_tax_income" in result.columns:
        valid = result.dropna(subset=["da_tqi", "median_after_tax_income"])
        if len(valid) > 2:
            corr = valid["da_tqi"].corr(valid["median_after_tax_income"])
            print(f"TQI-Income correlation (Pearson r): {corr:.3f}")

    return result
