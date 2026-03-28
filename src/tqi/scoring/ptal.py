"""PTAL (Public Transport Accessibility Level) computation.

Reference: Transport for London PTAL methodology.
Originally developed by London Borough of Hammersmith and Fulham (1992),
now standard across London and adopted internationally.
"""

from math import cos, radians

import numpy as np
from scipy.spatial import cKDTree

from tqi.config import (
    EARTH_RADIUS_M,
    PTAL_BUS_CATCHMENT_M,
    PTAL_GRADES,
    PTAL_WALK_SPEED_M_PER_MIN,
)
from tqi.gtfs.parse import GTFSFeed


def ptal_grade(ai: float) -> str:
    """Map an Accessibility Index value to a PTAL grade (1a–6b)."""
    for max_ai, grade in PTAL_GRADES:
        if ai <= max_ai:
            return grade
    return "6b"


def compute_ptal(
    grid: np.ndarray,
    feed: GTFSFeed,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute PTAL Accessibility Index for each grid point.

    Args:
        grid: (N, 2) array of [lat, lon].
        feed: Filtered GTFSFeed with stop_times, trips, routes, stops.

    Returns:
        ai_values: (N,) array of Accessibility Index values.
        grades: (N,) array of PTAL grade strings.
    """
    n_points = len(grid)

    # Build stop spatial index
    stop_lats = feed.stops["stop_lat"].values.astype(float)
    stop_lons = feed.stops["stop_lon"].values.astype(float)
    stop_ids = feed.stops["stop_id"].values

    center_lat_rad = radians(float(stop_lats.mean()))
    stop_xy = np.column_stack([
        np.radians(stop_lons) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(stop_lats) * EARTH_RADIUS_M,
    ])
    tree = cKDTree(stop_xy)

    # Project grid
    grid_xy = np.column_stack([
        np.radians(grid[:, 1]) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(grid[:, 0]) * EARTH_RADIUS_M,
    ])

    # Precompute route headways at each stop
    # For each (stop_id, route_short_name): median headway in minutes
    st = feed.stop_times.merge(feed.trips[["trip_id", "route_id"]], on="trip_id")
    st = st.merge(feed.routes[["route_id", "route_short_name"]], on="route_id")

    stop_route_headways: dict[tuple[str, str], float] = {}

    for (stop_id, route_name), group in st.groupby(["stop_id", "route_short_name"]):
        dep_times = sorted(group["departure_min"].unique())
        if len(dep_times) < 2:
            stop_route_headways[(stop_id, route_name)] = 120.0  # single trip, very long headway
            continue
        headways = np.diff(dep_times)
        headways = headways[headways > 0]
        if len(headways) > 0:
            stop_route_headways[(stop_id, route_name)] = float(np.median(headways))
        else:
            stop_route_headways[(stop_id, route_name)] = 120.0

    # Build stop_id → list of (route_name, headway) lookup
    stop_routes: dict[str, list[tuple[str, float]]] = {}
    for (stop_id, route_name), hw in stop_route_headways.items():
        if stop_id not in stop_routes:
            stop_routes[stop_id] = []
        stop_routes[stop_id].append((route_name, hw))

    # Compute PTAL for each grid point
    ai_values = np.zeros(n_points)

    for i in range(n_points):
        nearby_idx = tree.query_ball_point(grid_xy[i], r=PTAL_BUS_CATCHMENT_M)
        if not nearby_idx:
            continue

        # Collect all (route_name, EDF) pairs from all nearby stops
        route_best_edf: dict[str, float] = {}

        for si in nearby_idx:
            sid = stop_ids[si]
            if sid not in stop_routes:
                continue

            # Walk distance and time
            dx = stop_xy[si, 0] - grid_xy[i, 0]
            dy = stop_xy[si, 1] - grid_xy[i, 1]
            dist_m = (dx**2 + dy**2) ** 0.5
            walk_min = dist_m / PTAL_WALK_SPEED_M_PER_MIN

            for route_name, headway in stop_routes[sid]:
                # Total access time = walk time + average wait (half headway)
                total_access = walk_min + headway / 2.0
                if total_access <= 0:
                    continue
                # Equivalent Doorstep Frequency
                edf = 30.0 / total_access
                # Keep best EDF for each route (closest stop / best headway)
                if route_name not in route_best_edf or edf > route_best_edf[route_name]:
                    route_best_edf[route_name] = edf

        if not route_best_edf:
            continue

        # PTAL weighting: best route = 1.0, all others = 0.5
        edfs = sorted(route_best_edf.values(), reverse=True)
        ai = edfs[0]  # best route, weight 1.0
        for edf in edfs[1:]:
            ai += 0.5 * edf  # other routes, weight 0.5

        ai_values[i] = ai

    # Map to grades
    grades = np.array([ptal_grade(ai) for ai in ai_values])

    return ai_values, grades
