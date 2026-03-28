"""Isochrone map: "from point X, here's where you can reach in N minutes."""

from math import cos, radians

import numpy as np
import folium
from scipy.interpolate import griddata

from tqi.config import (
    DEPARTURE_TIMES,
    EARTH_RADIUS_M,
    MAX_TRANSFERS,
    MAX_TRIP_MIN,
    MAX_WALK_TO_STOP_M,
    WALK_SPEED_KMH,
    WALK_SPEED_M_PER_MIN,
)


# Isochrone time bands in minutes and their colors
ISOCHRONE_BANDS = [
    (15, "#2e7d32", "0–15 min"),
    (30, "#4caf50", "15–30 min"),
    (45, "#ff9800", "30–45 min"),
    (60, "#f44336", "45–60 min"),
    (90, "#b71c1c", "60–90 min"),
]


def compute_isochrone_times(
    origin_lat: float,
    origin_lon: float,
    grid: np.ndarray,
    timetable,
    flat_timetable,
    stop_lats: np.ndarray,
    stop_lons: np.ndarray,
    departure_time: int,
) -> np.ndarray:
    """Compute travel time from a single origin to every grid point.

    Returns (N,) array of travel times in minutes (INF if unreachable).
    """
    from tqi.raptor.engine import raptor_jit

    center_lat_rad = radians(float(stop_lats.mean()))

    # Project origin
    ox = radians(origin_lon) * EARTH_RADIUS_M * cos(center_lat_rad)
    oy = radians(origin_lat) * EARTH_RADIUS_M

    # Find nearby stops to origin
    stop_xy = np.column_stack([
        np.radians(stop_lons) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(stop_lats) * EARTH_RADIUS_M,
    ])
    dists = np.sqrt((stop_xy[:, 0] - ox)**2 + (stop_xy[:, 1] - oy)**2)
    nearby_mask = dists <= MAX_WALK_TO_STOP_M
    nearby_idx = np.where(nearby_mask)[0]

    n_dests = len(grid)
    travel_times = np.full(n_dests, float("inf"))

    if len(nearby_idx) == 0:
        return travel_times

    walk_to_stop = dists[nearby_idx] / WALK_SPEED_M_PER_MIN
    source_stops = [
        (int(idx), departure_time + wt)
        for idx, wt in zip(nearby_idx, walk_to_stop)
    ]
    max_time = departure_time + MAX_TRIP_MIN

    arrivals = raptor_jit(flat_timetable, source_stops, MAX_TRANSFERS, max_time)

    # Project grid for egress walk computation
    grid_xy = np.column_stack([
        np.radians(grid[:, 1]) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(grid[:, 0]) * EARTH_RADIUS_M,
    ])

    # For each grid point, find best arrival via nearby stops
    from scipy.spatial import cKDTree
    stop_tree = cKDTree(stop_xy)

    for di in range(n_dests):
        gx, gy = grid_xy[di]
        nearby_dest = stop_tree.query_ball_point([gx, gy], r=MAX_WALK_TO_STOP_M)
        best_tt = float("inf")
        for si in nearby_dest:
            egress_walk = np.sqrt((stop_xy[si, 0] - gx)**2 + (stop_xy[si, 1] - gy)**2) / WALK_SPEED_M_PER_MIN
            total = arrivals[si] + egress_walk
            if total < best_tt:
                best_tt = total
        if best_tt < 1e17:
            tt = best_tt - departure_time
            # Walking competitor: only count if transit is faster than walking
            walk_dist = np.sqrt((grid_xy[di, 0] - ox)**2 + (grid_xy[di, 1] - oy)**2) / 1000.0
            walk_time = walk_dist / (WALK_SPEED_KMH / 60.0)
            if tt < walk_time:
                travel_times[di] = tt

    return travel_times


def create_isochrone_map(
    origin_lat: float,
    origin_lon: float,
    grid: np.ndarray,
    travel_times: np.ndarray,
    label: str = "Isochrone",
    center: tuple[float, float] | None = None,
) -> folium.Map:
    """Render an isochrone map as colored grid point circles."""
    if center is None:
        center = (origin_lat, origin_lon)

    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

    # Origin marker
    folium.Marker(
        location=[origin_lat, origin_lon],
        popup=f"Origin: {label}",
        icon=folium.Icon(color="black", icon="star"),
    ).add_to(m)

    # Draw grid points colored by travel time band
    for band_max, color, band_label in ISOCHRONE_BANDS:
        band_min = 0 if band_max == ISOCHRONE_BANDS[0][0] else ISOCHRONE_BANDS[
            [b[0] for b in ISOCHRONE_BANDS].index(band_max) - 1
        ][0]
        group = folium.FeatureGroup(name=band_label, show=True)

        for i in range(len(grid)):
            tt = travel_times[i]
            if tt < float("inf") and band_min <= tt < band_max:
                folium.CircleMarker(
                    location=[float(grid[i, 0]), float(grid[i, 1])],
                    radius=3,
                    color=color,
                    weight=0,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.6,
                    popup=f"{tt:.0f} min",
                ).add_to(group)

        group.add_to(m)

    # Unreachable points (faint)
    unreach_group = folium.FeatureGroup(name="Unreachable", show=False)
    for i in range(len(grid)):
        if travel_times[i] >= float("inf"):
            folium.CircleMarker(
                location=[float(grid[i, 0]), float(grid[i, 1])],
                radius=1,
                color="#ccc",
                weight=0,
                fill=True,
                fill_color="#ccc",
                fill_opacity=0.2,
            ).add_to(unreach_group)
    unreach_group.add_to(m)

    folium.LayerControl().add_to(m)
    return m
