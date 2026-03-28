"""Orchestrate RAPTOR runs to build the travel time matrix."""

import multiprocessing as mp
from dataclasses import dataclass
from math import cos, radians
from pathlib import Path

import numpy as np

from tqi.config import (
    CACHE_DIR,
    DEPARTURE_TIMES,
    EARTH_RADIUS_M,
    MAX_TRANSFERS,
    MAX_TRIP_MIN,
    MAX_WALK_TO_STOP_M,
    MIN_OD_DIST_KM,
    WALK_SPEED_KMH,
    WALK_SPEED_M_PER_MIN,
)

INF = float("inf")
INF_F64 = 1e18


@dataclass
class ODMetrics:
    """Aggregated origin-destination metrics."""
    mean_travel_time: np.ndarray   # (n_origins, n_dests) — inf if never reachable
    reachability: np.ndarray       # (n_origins, n_dests) — fraction of time slots reachable
    travel_time_std: np.ndarray    # (n_origins, n_dests) — std dev across reachable times
    per_slot_coverage: np.ndarray  # (n_times,) — fraction of OD pairs reachable per slot
    per_slot_mean_tsr: np.ndarray  # (n_times,) — mean TSR per slot (for reachable pairs)
    distances_km: np.ndarray       # (n_origins, n_dests) — haversine distances


def _haversine_matrix(grid: np.ndarray) -> np.ndarray:
    """Vectorized pairwise haversine distance in km. grid shape (N, 2) = [lat, lon]."""
    lat = np.radians(grid[:, 0])
    lon = np.radians(grid[:, 1])
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def _precompute_nearby_stops(
    grid_xy: np.ndarray,
    stop_xy: np.ndarray,
    radius_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Precompute which stops are near each grid point.

    Returns:
        indices: flat array of stop indices
        walk_min: flat array of walk times (minutes)
        offsets: shape (n_points+1,), indices[offsets[i]:offsets[i+1]] are stops near point i
    """
    from scipy.spatial import cKDTree
    tree = cKDTree(stop_xy)
    all_indices = []
    all_walk_min = []
    offsets = [0]

    for i in range(len(grid_xy)):
        nearby = tree.query_ball_point(grid_xy[i], r=radius_m)
        for si in nearby:
            dx = stop_xy[si, 0] - grid_xy[i, 0]
            dy = stop_xy[si, 1] - grid_xy[i, 1]
            dist_m = (dx**2 + dy**2) ** 0.5
            all_indices.append(si)
            all_walk_min.append(dist_m / WALK_SPEED_M_PER_MIN)
        offsets.append(len(all_indices))

    return (
        np.array(all_indices, dtype=np.int32),
        np.array(all_walk_min, dtype=np.float64),
        np.array(offsets, dtype=np.int32),
    )


# ── Global state for worker processes (set by initializer) ──
_worker_ft = None
_worker_departure_times = None
_worker_dest_indices = None
_worker_dest_walk_min = None
_worker_dest_offsets = None
_worker_stop_xy = None
_worker_grid_xy = None
_worker_n_dests = None
_worker_distances_km_row = None  # not used per-worker, but kept for API
_worker_origin_indices = None
_worker_origin_walk_min = None
_worker_origin_offsets = None


def _init_worker(ft_dict, departure_times, dest_indices, dest_walk_min, dest_offsets,
                 origin_indices, origin_walk_min, origin_offsets, stop_xy, grid_xy, n_dests):
    """Initialize worker process with shared read-only data."""
    global _worker_ft, _worker_departure_times
    global _worker_dest_indices, _worker_dest_walk_min, _worker_dest_offsets
    global _worker_origin_indices, _worker_origin_walk_min, _worker_origin_offsets
    global _worker_stop_xy, _worker_grid_xy, _worker_n_dests

    # Reconstruct FlatTimetable from dict
    from tqi.raptor.timetable import FlatTimetable
    _worker_ft = FlatTimetable(**ft_dict)
    _worker_departure_times = departure_times
    _worker_dest_indices = dest_indices
    _worker_dest_walk_min = dest_walk_min
    _worker_dest_offsets = dest_offsets
    _worker_origin_indices = origin_indices
    _worker_origin_walk_min = origin_walk_min
    _worker_origin_offsets = origin_offsets
    _worker_stop_xy = stop_xy
    _worker_grid_xy = grid_xy
    _worker_n_dests = n_dests


def _compute_origin_jit(origin_idx: int):
    """Worker function for a single origin using JIT RAPTOR."""
    from tqi.raptor.engine import raptor_jit

    ft = _worker_ft
    departure_times = _worker_departure_times
    n_dests = _worker_n_dests
    n_times = len(departure_times)

    # Origin nearby stops
    o_start = _worker_origin_offsets[origin_idx]
    o_end = _worker_origin_offsets[origin_idx + 1]

    if o_start == o_end:
        # No nearby stops
        return (
            origin_idx,
            np.full(n_dests, INF),
            np.zeros(n_dests),
            np.zeros(n_dests),
            np.zeros(n_times),
            np.zeros(n_times),
        )

    origin_stop_indices = _worker_origin_indices[o_start:o_end]
    origin_walk_times = _worker_origin_walk_min[o_start:o_end]

    # Run RAPTOR for each departure time, collect travel times to all dests
    travel_times = np.full((n_times, n_dests), INF)

    for ti in range(n_times):
        t_depart = departure_times[ti]
        max_time = t_depart + MAX_TRIP_MIN

        source_stops = [
            (int(origin_stop_indices[j]), t_depart + origin_walk_times[j])
            for j in range(len(origin_stop_indices))
        ]

        arrivals = raptor_jit(ft, source_stops, MAX_TRANSFERS, max_time)

        # For each destination, find best arrival via its nearby stops
        for di in range(n_dests):
            d_start = _worker_dest_offsets[di]
            d_end = _worker_dest_offsets[di + 1]
            best_arr = INF_F64
            for j in range(d_start, d_end):
                si = _worker_dest_indices[j]
                total = arrivals[si] + _worker_dest_walk_min[j]
                if total < best_arr:
                    best_arr = total
            if best_arr < INF_F64:
                travel_times[ti, di] = best_arr - t_depart

    # Walking-as-competitor: if transit is slower than walking, mark as unreachable.
    # Walking time = distance_km / walk_speed_kmh * 60 (in minutes).
    ox, oy = float(_worker_grid_xy[origin_idx, 0]), float(_worker_grid_xy[origin_idx, 1])
    dest_dx = _worker_grid_xy[:, 0] - ox
    dest_dy = _worker_grid_xy[:, 1] - oy
    dest_dist_km = np.sqrt(dest_dx**2 + dest_dy**2) / 1000.0
    walk_time_min = dest_dist_km / (WALK_SPEED_KMH / 60.0)  # km / (km/min) = min

    for ti in range(n_times):
        for di in range(n_dests):
            if travel_times[ti, di] < INF and travel_times[ti, di] >= walk_time_min[di]:
                travel_times[ti, di] = INF  # walking is faster — transit provides no value

    # Aggregate
    reachable_mask = travel_times < INF
    reachable_count = reachable_mask.sum(axis=0)
    reachability = reachable_count / n_times

    tt_safe = np.where(reachable_mask, travel_times, np.nan)
    with np.errstate(all="ignore"):
        mean_tt = np.nanmean(tt_safe, axis=0)
        tt_std = np.nanstd(tt_safe, axis=0)
    mean_tt = np.where(reachable_count > 0, mean_tt, INF)
    tt_std = np.where(reachable_count > 0, tt_std, 0.0)

    # Per-slot TSR: use precomputed origin→dest distances (dest_dist_km computed above)
    slot_tsr_sum = np.zeros(n_times)
    slot_reachable_count = np.zeros(n_times)

    for ti in range(n_times):
        for di in range(n_dests):
            if travel_times[ti, di] < INF and dest_dist_km[di] > MIN_OD_DIST_KM:
                tsr = dest_dist_km[di] / (travel_times[ti, di] / 60.0)
                slot_tsr_sum[ti] += tsr
                slot_reachable_count[ti] += 1

    return (origin_idx, mean_tt, reachability, tt_std, slot_tsr_sum, slot_reachable_count)


def compute_matrix(
    tt,  # RaptorTimetable
    grid: np.ndarray,
    stop_lats: np.ndarray,
    stop_lons: np.ndarray,
    departure_times: list[int] = DEPARTURE_TIMES,
    parallel: bool = True,
    workers: int | None = None,
    cache_dir: Path = CACHE_DIR,
    feed_hash: str | None = None,
) -> ODMetrics:
    """Main entry point for computing the travel time matrix."""
    from tqi.raptor.timetable import flatten_timetable

    n_origins = len(grid)
    n_dests = len(grid)
    n_times = len(departure_times)

    # Check cache (validate grid size matches)
    if feed_hash and cache_dir.exists():
        cache_file = cache_dir / f"od_metrics_{feed_hash[:12]}_{n_origins}.npz"
        if cache_file.exists():
            print(f"Loading cached metrics from {cache_file}")
            return _load_cache(cache_file)

    center_lat = float(grid[:, 0].mean())
    center_lat_rad = radians(center_lat)

    # Project coordinates to metres
    stop_xy = np.column_stack([
        np.radians(stop_lons) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(stop_lats) * EARTH_RADIUS_M,
    ])
    grid_xy = np.column_stack([
        np.radians(grid[:, 1]) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(grid[:, 0]) * EARTH_RADIUS_M,
    ])

    # Precompute nearby stops for all grid points (used as both origins and destinations)
    print("Precomputing nearby stops for all grid points ...")
    nb_indices, nb_walk_min, nb_offsets = _precompute_nearby_stops(
        grid_xy, stop_xy, MAX_WALK_TO_STOP_M
    )
    print(f"  {len(nb_indices)} grid-stop pairs within {MAX_WALK_TO_STOP_M}m")

    # Flatten timetable for JIT
    ft = flatten_timetable(tt)

    # Warm up Numba JIT (first call compiles)
    print("Warming up JIT compiler ...")
    from tqi.raptor.engine import raptor_jit
    _warmup_src = [(int(nb_indices[0]), float(departure_times[0]))] if len(nb_indices) > 0 else [(0, 360.0)]
    raptor_jit(ft, _warmup_src, MAX_TRANSFERS, departure_times[0] + MAX_TRIP_MIN)
    print("  JIT ready")

    # Vectorized pairwise distance matrix
    print("Computing pairwise distances ...")
    distances_km = _haversine_matrix(grid)

    # Prepare FlatTimetable as dict for pickling to workers
    ft_dict = {
        "n_stops": ft.n_stops, "n_patterns": ft.n_patterns,
        "ps_data": ft.ps_data, "ps_offsets": ft.ps_offsets,
        "tt_data": ft.tt_data, "tt_offsets": ft.tt_offsets,
        "tt_n_trips": ft.tt_n_trips, "tt_n_stops": ft.tt_n_stops,
        "sp_data": ft.sp_data, "sp_offsets": ft.sp_offsets,
        "tr_data": ft.tr_data, "tr_offsets": ft.tr_offsets,
    }

    dep_arr = np.array(departure_times, dtype=np.int32)

    # Allocate results
    mean_tt = np.full((n_origins, n_dests), INF)
    reachability = np.zeros((n_origins, n_dests))
    tt_std = np.zeros((n_origins, n_dests))
    slot_tsr_sum_total = np.zeros(n_times)
    slot_reachable_total = np.zeros(n_times)

    print(f"Computing travel times: {n_origins} origins × {n_times} time slots = "
          f"{n_origins * n_times:,} RAPTOR runs")

    if parallel and n_origins > 1:
        n_workers = workers or min(mp.cpu_count(), 8)
        print(f"Using {n_workers} parallel workers")
        with mp.Pool(
            n_workers,
            initializer=_init_worker,
            initargs=(ft_dict, dep_arr, nb_indices, nb_walk_min, nb_offsets,
                      nb_indices, nb_walk_min, nb_offsets, stop_xy, grid_xy, n_dests),
        ) as pool:
            for i, result in enumerate(pool.imap_unordered(_compute_origin_jit, range(n_origins))):
                oidx, m_tt, reach, std, s_tsr, s_reach = result
                mean_tt[oidx] = m_tt
                reachability[oidx] = reach
                tt_std[oidx] = std
                slot_tsr_sum_total += s_tsr
                slot_reachable_total += s_reach
                if (i + 1) % 100 == 0 or (i + 1) == n_origins:
                    print(f"  {i + 1}/{n_origins} origins complete")
    else:
        # Single-process: use globals directly
        _init_worker(ft_dict, dep_arr, nb_indices, nb_walk_min, nb_offsets,
                     nb_indices, nb_walk_min, nb_offsets, stop_xy, grid_xy, n_dests)
        for i in range(n_origins):
            result = _compute_origin_jit(i)
            oidx, m_tt, reach, std, s_tsr, s_reach = result
            mean_tt[oidx] = m_tt
            reachability[oidx] = reach
            tt_std[oidx] = std
            slot_tsr_sum_total += s_tsr
            slot_reachable_total += s_reach
            if (i + 1) % 100 == 0 or (i + 1) == n_origins:
                print(f"  {i + 1}/{n_origins} origins complete")

    # Per-slot aggregate metrics
    with np.errstate(divide="ignore", invalid="ignore"):
        per_slot_mean_tsr = np.where(
            slot_reachable_total > 0,
            slot_tsr_sum_total / slot_reachable_total,
            0.0,
        )
    max_pairs = n_origins * n_dests
    per_slot_coverage = slot_reachable_total / max_pairs if max_pairs > 0 else np.zeros(n_times)

    metrics = ODMetrics(
        mean_travel_time=mean_tt,
        reachability=reachability,
        travel_time_std=tt_std,
        per_slot_coverage=per_slot_coverage,
        per_slot_mean_tsr=per_slot_mean_tsr,
        distances_km=distances_km,
    )

    # Save cache (include grid size in filename to prevent stale loads)
    if feed_hash:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"od_metrics_{feed_hash[:12]}_{n_origins}.npz"
        _save_cache(cache_file, metrics)

    return metrics


def _save_cache(path: Path, m: ODMetrics) -> None:
    np.savez_compressed(
        path,
        mean_travel_time=m.mean_travel_time,
        reachability=m.reachability,
        travel_time_std=m.travel_time_std,
        per_slot_coverage=m.per_slot_coverage,
        per_slot_mean_tsr=m.per_slot_mean_tsr,
        distances_km=m.distances_km,
    )
    print(f"Cached metrics to {path}")


def _load_cache(path: Path) -> ODMetrics:
    data = np.load(path)
    return ODMetrics(
        mean_travel_time=data["mean_travel_time"],
        reachability=data["reachability"],
        travel_time_std=data["travel_time_std"],
        per_slot_coverage=data["per_slot_coverage"],
        per_slot_mean_tsr=data["per_slot_mean_tsr"],
        distances_km=data["distances_km"],
    )
