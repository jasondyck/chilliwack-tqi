"""Build RAPTOR timetable data structures from parsed GTFS.

Two representations are maintained:
- RaptorTimetable: Python-object version (used for building, testing, pickling)
- FlatTimetable: Numba-compatible flat numpy arrays (used by the JIT engine)
"""

from dataclasses import dataclass
from math import radians, cos

import numpy as np
from scipy.spatial import cKDTree

from tqi.config import EARTH_RADIUS_M, MAX_TRANSFER_WALK_M, WALK_SPEED_M_PER_MIN
from tqi.gtfs.parse import GTFSFeed


@dataclass
class RaptorTimetable:
    """Pre-processed timetable for RAPTOR routing."""
    n_stops: int
    stop_ids: list[str]
    stop_id_to_idx: dict[str, int]

    n_patterns: int
    pattern_stops: list[list[int]]
    pattern_trips: list[np.ndarray]  # pattern_idx → (n_trips, n_stops_in_pattern, 2)

    stop_to_patterns: list[list[tuple[int, int]]]
    transfers: list[list[tuple[int, float]]]


@dataclass
class FlatTimetable:
    """Numba-compatible flat arrays for the JIT RAPTOR engine.

    All jagged lists are flattened into contiguous arrays with offset tables.
    """
    n_stops: int
    n_patterns: int

    # Pattern stops: flat array of stop indices + offsets
    ps_data: np.ndarray     # int32 — concatenated stop indices for all patterns
    ps_offsets: np.ndarray   # int32 — shape (n_patterns+1,), ps_data[ps_offsets[p]:ps_offsets[p+1]]

    # Trip times: flat array of (arr, dep) pairs + offsets per pattern
    # For pattern p with S stops and T trips: tt_data[offset : offset + T*S*2]
    # reshaped to (T, S, 2)
    tt_data: np.ndarray     # int32 — all trip arrival/departure times
    tt_offsets: np.ndarray   # int32 — shape (n_patterns+1,)
    tt_n_trips: np.ndarray   # int32 — shape (n_patterns,), number of trips per pattern
    tt_n_stops: np.ndarray   # int32 — shape (n_patterns,), number of stops per pattern

    # Stop → patterns: flat (pattern_idx, position) pairs + offsets
    sp_data: np.ndarray     # int32 — shape (N, 2), columns: [pattern_idx, position]
    sp_offsets: np.ndarray   # int32 — shape (n_stops+1,)

    # Transfers: flat (target_stop, walk_min_x100) pairs + offsets
    tr_data: np.ndarray     # int32 — shape (N, 2), columns: [target_stop_idx, walk_min*100]
    tr_offsets: np.ndarray   # int32 — shape (n_stops+1,)


def flatten_timetable(tt: RaptorTimetable) -> FlatTimetable:
    """Convert a RaptorTimetable to Numba-compatible flat arrays."""
    # Pattern stops
    ps_parts = []
    ps_offsets = [0]
    for stops in tt.pattern_stops:
        ps_parts.extend(stops)
        ps_offsets.append(len(ps_parts))
    ps_data = np.array(ps_parts, dtype=np.int32)
    ps_offsets = np.array(ps_offsets, dtype=np.int32)

    # Trip times
    tt_parts = []
    tt_offsets = [0]
    tt_n_trips = []
    tt_n_stops = []
    for trips_arr in tt.pattern_trips:
        n_t, n_s, _ = trips_arr.shape
        tt_n_trips.append(n_t)
        tt_n_stops.append(n_s)
        tt_parts.append(trips_arr.reshape(-1))
        tt_offsets.append(tt_offsets[-1] + n_t * n_s * 2)
    tt_data = np.concatenate(tt_parts).astype(np.int32) if tt_parts else np.empty(0, dtype=np.int32)
    tt_offsets = np.array(tt_offsets, dtype=np.int32)
    tt_n_trips_arr = np.array(tt_n_trips, dtype=np.int32)
    tt_n_stops_arr = np.array(tt_n_stops, dtype=np.int32)

    # Stop → patterns
    sp_parts = []
    sp_offsets = [0]
    for entries in tt.stop_to_patterns:
        for pidx, pos in entries:
            sp_parts.append((pidx, pos))
        sp_offsets.append(len(sp_parts))
    sp_data = np.array(sp_parts, dtype=np.int32).reshape(-1, 2) if sp_parts else np.empty((0, 2), dtype=np.int32)
    sp_offsets = np.array(sp_offsets, dtype=np.int32)

    # Transfers
    tr_parts = []
    tr_offsets = [0]
    for entries in tt.transfers:
        for target, walk_min in entries:
            # Store walk_min as int (×100 for precision)
            tr_parts.append((target, int(walk_min * 100)))
        tr_offsets.append(len(tr_parts))
    tr_data = np.array(tr_parts, dtype=np.int32).reshape(-1, 2) if tr_parts else np.empty((0, 2), dtype=np.int32)
    tr_offsets = np.array(tr_offsets, dtype=np.int32)

    return FlatTimetable(
        n_stops=tt.n_stops,
        n_patterns=tt.n_patterns,
        ps_data=ps_data,
        ps_offsets=ps_offsets,
        tt_data=tt_data,
        tt_offsets=tt_offsets,
        tt_n_trips=tt_n_trips_arr,
        tt_n_stops=tt_n_stops_arr,
        sp_data=sp_data,
        sp_offsets=sp_offsets,
        tr_data=tr_data,
        tr_offsets=tr_offsets,
    )


def build_raptor_timetable(feed: GTFSFeed) -> RaptorTimetable:
    """Convert a filtered GTFSFeed into RAPTOR data structures."""
    stop_ids = sorted(feed.stops["stop_id"].unique())
    stop_id_to_idx = {sid: i for i, sid in enumerate(stop_ids)}
    n_stops = len(stop_ids)

    st = feed.stop_times.sort_values(["trip_id", "stop_sequence"])

    trip_sequences: dict[str, list[tuple[int, int, int]]] = {}
    for _, row in st.iterrows():
        sid = row["stop_id"]
        if sid not in stop_id_to_idx:
            continue
        tid = row["trip_id"]
        if tid not in trip_sequences:
            trip_sequences[tid] = []
        trip_sequences[tid].append((
            stop_id_to_idx[sid],
            int(row["arrival_min"]),
            int(row["departure_min"]),
        ))

    pattern_key_to_idx: dict[tuple[int, ...], int] = {}
    pattern_stops: list[list[int]] = []
    pattern_trip_data: list[list[list[tuple[int, int]]]] = []

    for tid, seq in trip_sequences.items():
        stop_key = tuple(s[0] for s in seq)
        if stop_key not in pattern_key_to_idx:
            pattern_key_to_idx[stop_key] = len(pattern_stops)
            pattern_stops.append(list(stop_key))
            pattern_trip_data.append([])
        pidx = pattern_key_to_idx[stop_key]
        pattern_trip_data[pidx].append([(s[1], s[2]) for s in seq])

    pattern_trips: list[np.ndarray] = []
    for trips_for_pattern in pattern_trip_data:
        arr = np.array(trips_for_pattern, dtype=np.int32)
        order = np.argsort(arr[:, 0, 1])
        pattern_trips.append(arr[order])

    n_patterns = len(pattern_stops)

    stop_to_patterns: list[list[tuple[int, int]]] = [[] for _ in range(n_stops)]
    for pidx, stops in enumerate(pattern_stops):
        for pos, sidx in enumerate(stops):
            stop_to_patterns[sidx].append((pidx, pos))

    # Build transfer edges
    stop_lats = np.array([
        feed.stops.loc[feed.stops["stop_id"] == sid, "stop_lat"].iloc[0]
        for sid in stop_ids
    ], dtype=np.float64)
    stop_lons = np.array([
        feed.stops.loc[feed.stops["stop_id"] == sid, "stop_lon"].iloc[0]
        for sid in stop_ids
    ], dtype=np.float64)

    center_lat_rad = radians(stop_lats.mean())
    stop_xy = np.column_stack([
        np.radians(stop_lons) * EARTH_RADIUS_M * cos(center_lat_rad),
        np.radians(stop_lats) * EARTH_RADIUS_M,
    ])
    tree = cKDTree(stop_xy)

    stop_pattern_set: list[set[int]] = [set() for _ in range(n_stops)]
    for pidx, stops in enumerate(pattern_stops):
        for sidx in stops:
            stop_pattern_set[sidx].add(pidx)

    transfers: list[list[tuple[int, float]]] = [[] for _ in range(n_stops)]
    for sidx in range(n_stops):
        nearby = tree.query_ball_point(stop_xy[sidx], r=MAX_TRANSFER_WALK_M)
        for nidx in nearby:
            if nidx == sidx:
                continue
            if stop_pattern_set[nidx] == stop_pattern_set[sidx]:
                continue
            dx = stop_xy[nidx, 0] - stop_xy[sidx, 0]
            dy = stop_xy[nidx, 1] - stop_xy[sidx, 1]
            dist_m = (dx**2 + dy**2) ** 0.5
            walk_min = dist_m / WALK_SPEED_M_PER_MIN
            transfers[sidx].append((nidx, walk_min))

    print(f"RAPTOR timetable: {n_stops} stops, {n_patterns} patterns, "
          f"{sum(len(t) for t in pattern_trips)} trips")

    return RaptorTimetable(
        n_stops=n_stops,
        stop_ids=stop_ids,
        stop_id_to_idx=stop_id_to_idx,
        n_patterns=n_patterns,
        pattern_stops=pattern_stops,
        pattern_trips=pattern_trips,
        stop_to_patterns=stop_to_patterns,
        transfers=transfers,
    )
