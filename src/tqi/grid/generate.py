"""Generate analysis grid and spatial index for stop lookups."""

import json
from math import cos, radians
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point, shape

from tqi.config import (
    BBOX_NE,
    BBOX_SW,
    BOUNDARY_GEOJSON,
    EARTH_RADIUS_M,
    GRID_SPACING_M,
    WALK_SPEED_M_PER_MIN,
)


def _load_boundary(geojson_path: Path = BOUNDARY_GEOJSON):
    """Load municipal boundary polygon from GeoJSON. Returns shapely geometry or None."""
    if not geojson_path.exists():
        return None
    with open(geojson_path) as f:
        data = json.load(f)
    features = data.get("features", [])
    if features:
        return shape(features[0]["geometry"])
    return None


def generate_grid(
    bbox_sw: tuple[float, float] = BBOX_SW,
    bbox_ne: tuple[float, float] = BBOX_NE,
    spacing_m: float = GRID_SPACING_M,
    clip_to_boundary: bool = True,
) -> np.ndarray:
    """Generate a regular grid of (lat, lon) points at ~spacing_m apart.

    If clip_to_boundary is True and the municipal boundary GeoJSON exists,
    only points inside the boundary polygon are kept.

    Returns array of shape (N, 2) with columns [lat, lon].
    """
    center_lat = (bbox_sw[0] + bbox_ne[0]) / 2
    deg_per_m_lat = 1 / (EARTH_RADIUS_M * radians(1))
    deg_per_m_lon = 1 / (EARTH_RADIUS_M * cos(radians(center_lat)) * radians(1))

    lat_step = spacing_m * deg_per_m_lat
    lon_step = spacing_m * deg_per_m_lon

    lats = np.arange(bbox_sw[0], bbox_ne[0], lat_step)
    lons = np.arange(bbox_sw[1], bbox_ne[1], lon_step)

    grid = np.array([(lat, lon) for lat in lats for lon in lons])

    if clip_to_boundary:
        boundary = _load_boundary()
        if boundary is not None:
            # Filter to points inside the municipal boundary
            # Use prepared geometry for fast contains checks
            from shapely.prepared import prep
            prepared = prep(boundary)
            mask = np.array([
                prepared.contains(Point(lon, lat))
                for lat, lon in grid
            ])
            grid = grid[mask]

    return grid


def _to_cartesian(lat: float, lon: float, center_lat_rad: float) -> tuple[float, float]:
    """Project lat/lon to approximate Cartesian (metres) for cKDTree."""
    lat_rad = radians(lat)
    lon_rad = radians(lon)
    x = lon_rad * EARTH_RADIUS_M * cos(center_lat_rad)
    y = lat_rad * EARTH_RADIUS_M
    return x, y


def build_stop_tree(
    stop_lats: np.ndarray, stop_lons: np.ndarray, center_lat: float
) -> tuple[cKDTree, np.ndarray]:
    """Build a cKDTree from stop coordinates in projected metres.

    Returns (tree, stop_xy) where stop_xy is shape (N, 2).
    """
    center_lat_rad = radians(center_lat)
    stop_xy = np.column_stack([
        np.radians(stop_lons) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(stop_lats) * EARTH_RADIUS_M,
    ])
    return cKDTree(stop_xy), stop_xy


def find_nearby_stops(
    tree: cKDTree,
    stop_xy: np.ndarray,
    point_lat: float,
    point_lon: float,
    center_lat_rad: float,
    radius_m: float,
) -> list[tuple[int, float]]:
    """Find stops within radius_m of a point.

    Returns list of (stop_index, walk_time_minutes).
    """
    px, py = _to_cartesian(point_lat, point_lon, center_lat_rad)
    indices = tree.query_ball_point([px, py], r=radius_m)
    results = []
    for idx in indices:
        dx = stop_xy[idx, 0] - px
        dy = stop_xy[idx, 1] - py
        dist_m = (dx**2 + dy**2) ** 0.5
        walk_min = dist_m / WALK_SPEED_M_PER_MIN
        results.append((idx, walk_min))
    return results


def project_grid(grid: np.ndarray, center_lat: float) -> np.ndarray:
    """Project grid lat/lon to Cartesian metres. Returns shape (N, 2)."""
    center_lat_rad = radians(center_lat)
    x = np.radians(grid[:, 1]) * EARTH_RADIUS_M * cos(center_lat_rad)
    y = np.radians(grid[:, 0]) * EARTH_RADIUS_M
    return np.column_stack([x, y])


def compute_grid_weights(
    grid: np.ndarray,
    da_boundaries,
    census_data,
) -> np.ndarray:
    """Assign population-based weights to each grid point.

    Each grid point gets weight = DA_population / n_grid_points_in_that_DA.
    Points not in any DA get weight = 1 (uniform fallback).

    Args:
        grid: (N, 2) array of [lat, lon].
        da_boundaries: GeoDataFrame with DA polygons and DGUID column.
        census_data: DataFrame indexed by DGUID with 'population' column.

    Returns:
        weights: (N,) array of population weights (normalized to sum to N).
    """
    import geopandas as gpd
    from shapely.geometry import Point

    n = len(grid)
    weights = np.ones(n)

    geometry = [Point(lon, lat) for lat, lon in grid]
    grid_gdf = gpd.GeoDataFrame({"idx": range(n)}, geometry=geometry, crs="EPSG:4326")

    joined = gpd.sjoin(grid_gdf, da_boundaries[["DGUID", "geometry"]], how="left", predicate="within")

    if "population" not in census_data.columns:
        return weights

    # Count grid points per DA
    da_counts = joined.groupby("DGUID").size().to_dict()

    # Assign weights
    for _, row in joined.iterrows():
        idx = row["idx"]
        dguid = row.get("DGUID")
        if dguid and dguid in census_data.index:
            pop = census_data.loc[dguid, "population"]
            if pop and pop > 0 and dguid in da_counts:
                weights[idx] = float(pop) / da_counts[dguid]

    # Normalize so weights sum to N (so weighted mean behaves like unweighted when uniform)
    weights = weights / weights.mean()
    return weights
