"""Amenity accessibility: can people reach essential destinations by transit?"""

import json
from pathlib import Path

import numpy as np

from tqi.config import DATA_DIR, WALK_SPEED_KMH

AMENITIES_FILE = DATA_DIR / "amenities.json"

INF = float("inf")

# Time thresholds for reporting (minutes)
TIME_THRESHOLDS = [30, 45, 60]


def load_amenities(path: Path = AMENITIES_FILE) -> list[dict]:
    """Load amenity definitions from JSON."""
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def compute_amenity_accessibility(
    grid: np.ndarray,
    mean_travel_time: np.ndarray,
    distances_km: np.ndarray,
    amenities: list[dict],
) -> list[dict]:
    """For each amenity, find the nearest grid point and compute accessibility.

    Returns list of dicts with amenity info + access stats.
    """
    from haversine import haversine, Unit

    n_grid = len(grid)
    results = []

    for amenity in amenities:
        a_lat, a_lon = amenity["lat"], amenity["lon"]

        # Find the closest grid point to this amenity
        dists_to_amenity = np.array([
            haversine((a_lat, a_lon), (grid[i, 0], grid[i, 1]), unit=Unit.KILOMETERS)
            for i in range(n_grid)
        ])
        amenity_grid_idx = int(np.argmin(dists_to_amenity))

        # Travel times from all grid points TO this amenity's grid point
        # mean_travel_time[origin, dest] — we want column amenity_grid_idx
        tt_to_amenity = mean_travel_time[:, amenity_grid_idx]

        # Walking competitor: exclude if walking is faster
        walk_times = distances_km[:, amenity_grid_idx] / (WALK_SPEED_KMH / 60.0)
        effective_tt = np.where(
            (tt_to_amenity < INF) & (tt_to_amenity < walk_times),
            tt_to_amenity,
            INF,
        )

        # Compute % reachable within each time threshold
        threshold_pcts = {}
        for t in TIME_THRESHOLDS:
            reachable = (effective_tt <= t).sum()
            threshold_pcts[t] = float(reachable / n_grid * 100)

        any_reachable = (effective_tt < INF).sum()
        median_tt = float(np.median(effective_tt[effective_tt < INF])) if any_reachable > 0 else None

        results.append({
            "name": amenity["name"],
            "category": amenity["category"],
            "lat": a_lat,
            "lon": a_lon,
            "grid_idx": amenity_grid_idx,
            "pct_within_30min": threshold_pcts.get(30, 0),
            "pct_within_45min": threshold_pcts.get(45, 0),
            "pct_within_60min": threshold_pcts.get(60, 0),
            "pct_reachable": float(any_reachable / n_grid * 100),
            "median_travel_time": median_tt,
        })

    return results
