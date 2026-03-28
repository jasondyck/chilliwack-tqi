"""Core RAPTOR algorithm — Numba JIT-compiled and pure-Python fallback."""

import numpy as np
import numba as nb

from tqi.config import MAX_TRANSFERS
from tqi.raptor.timetable import FlatTimetable, RaptorTimetable

INF_F64 = 1e18  # Numba-friendly sentinel (float64)
INF = float("inf")


# ──────────────────────────────────────────────────────────────────────
# Numba JIT-compiled RAPTOR
# ──────────────────────────────────────────────────────────────────────

@nb.njit(cache=True)
def _raptor_jit(
    n_stops: int,
    n_patterns: int,
    max_transfers: int,
    max_time: float,
    # Source stops
    source_stop_idx: np.ndarray,   # int32
    source_arr_time: np.ndarray,   # float64
    # Flat timetable arrays
    ps_data: np.ndarray,
    ps_offsets: np.ndarray,
    tt_data: np.ndarray,
    tt_offsets: np.ndarray,
    tt_n_trips: np.ndarray,
    tt_n_stops: np.ndarray,
    sp_data: np.ndarray,
    sp_offsets: np.ndarray,
    tr_data: np.ndarray,
    tr_offsets: np.ndarray,
) -> np.ndarray:
    K = max_transfers + 1

    # tau[k, s] = earliest arrival at stop s using at most k vehicle legs
    tau = np.full((K + 1, n_stops), INF_F64)
    best = np.full(n_stops, INF_F64)

    # marked[s] = 1 if stop s was improved in the current round
    marked = np.zeros(n_stops, dtype=nb.int32)

    # Initialise sources
    for i in range(len(source_stop_idx)):
        s = source_stop_idx[i]
        t = source_arr_time[i]
        if t < tau[0, s]:
            tau[0, s] = t
            best[s] = t
            marked[s] = 1

    # Initial transfers from source stops
    _transfers_jit(tau, 0, best, marked, n_stops, max_time, tr_data, tr_offsets)

    for k in range(1, K + 1):
        # Copy previous round
        for s in range(n_stops):
            tau[k, s] = tau[k - 1, s]

        new_marked = np.zeros(n_stops, dtype=nb.int32)

        # Collect patterns to scan (pattern_idx → earliest boarding position)
        pat_board_pos = np.full(n_patterns, -1, dtype=nb.int32)
        for s in range(n_stops):
            if marked[s] == 0:
                continue
            for j in range(sp_offsets[s], sp_offsets[s + 1]):
                pidx = sp_data[j, 0]
                pos = sp_data[j, 1]
                if pat_board_pos[pidx] < 0 or pos < pat_board_pos[pidx]:
                    pat_board_pos[pidx] = pos

        # Route scanning
        for pidx in range(n_patterns):
            if pat_board_pos[pidx] < 0:
                continue

            board_pos = pat_board_pos[pidx]
            n_t = tt_n_trips[pidx]
            n_s = tt_n_stops[pidx]
            if n_t == 0:
                continue

            # Trip times for this pattern: flat slice → virtual (n_t, n_s, 2)
            tt_off = tt_offsets[pidx]
            current_trip = -1

            for pos in range(board_pos, n_s):
                stop_idx = ps_data[ps_offsets[pidx] + pos]

                # Can current trip improve arrival at this stop?
                if current_trip >= 0:
                    # arr = tt_data[tt_off + current_trip * n_s * 2 + pos * 2 + 0]
                    arr_time = tt_data[tt_off + current_trip * n_s * 2 + pos * 2]
                    if arr_time < best[stop_idx] and arr_time <= max_time:
                        if arr_time < tau[k, stop_idx]:
                            tau[k, stop_idx] = arr_time
                        if arr_time < best[stop_idx]:
                            best[stop_idx] = arr_time
                        new_marked[stop_idx] = 1

                # Can we board an earlier trip at this stop?
                earliest_board = tau[k - 1, stop_idx]
                if earliest_board < INF_F64:
                    # Binary search for earliest trip with dep >= earliest_board
                    lo, hi = 0, n_t
                    while lo < hi:
                        mid = (lo + hi) // 2
                        dep = tt_data[tt_off + mid * n_s * 2 + pos * 2 + 1]
                        if dep < earliest_board:
                            lo = mid + 1
                        else:
                            hi = mid
                    if lo < n_t:
                        if current_trip < 0 or lo < current_trip:
                            current_trip = lo

        # Transfer phase
        _transfers_jit(tau, k, best, new_marked, n_stops, max_time, tr_data, tr_offsets)

        # Check if anything improved
        any_marked = 0
        for s in range(n_stops):
            marked[s] = new_marked[s]
            if new_marked[s]:
                any_marked = 1
        if any_marked == 0:
            break

    return best


@nb.njit(cache=True)
def _transfers_jit(tau, k, best, marked, n_stops, max_time, tr_data, tr_offsets):
    """Apply walking transfers from marked stops."""
    new_marks = np.zeros(n_stops, dtype=nb.int32)
    for s in range(n_stops):
        if marked[s] == 0:
            continue
        for j in range(tr_offsets[s], tr_offsets[s + 1]):
            target = tr_data[j, 0]
            walk_min = tr_data[j, 1] / 100.0  # stored as ×100 int
            arr = tau[k, s] + walk_min
            if arr < tau[k, target] and arr <= max_time:
                tau[k, target] = arr
                if arr < best[target]:
                    best[target] = arr
                new_marks[target] = 1
    # Merge new marks
    for s in range(n_stops):
        if new_marks[s]:
            marked[s] = 1


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

def raptor_jit(
    ft: FlatTimetable,
    source_stops: list[tuple[int, float]],
    max_transfers: int = MAX_TRANSFERS,
    max_time: float = INF_F64,
) -> np.ndarray:
    """Run JIT-compiled RAPTOR. Returns earliest arrival at every stop."""
    src_idx = np.array([s[0] for s in source_stops], dtype=np.int32)
    src_time = np.array([s[1] for s in source_stops], dtype=np.float64)

    return _raptor_jit(
        ft.n_stops, ft.n_patterns, max_transfers, max_time,
        src_idx, src_time,
        ft.ps_data, ft.ps_offsets,
        ft.tt_data, ft.tt_offsets, ft.tt_n_trips, ft.tt_n_stops,
        ft.sp_data, ft.sp_offsets,
        ft.tr_data, ft.tr_offsets,
    )


def raptor(
    tt: RaptorTimetable,
    source_stops: list[tuple[int, float]],
    max_transfers: int = MAX_TRANSFERS,
    max_time: float = INF,
) -> np.ndarray:
    """Pure-Python RAPTOR fallback (used in tests with RaptorTimetable)."""
    from bisect import bisect_left

    n_stops = tt.n_stops
    K = max_transfers + 1
    tau = np.full((K + 1, n_stops), INF, dtype=np.float64)
    best = np.full(n_stops, INF, dtype=np.float64)

    marked: set[int] = set()
    for stop_idx, arr_time in source_stops:
        if arr_time < tau[0, stop_idx]:
            tau[0, stop_idx] = arr_time
            best[stop_idx] = arr_time
            marked.add(stop_idx)

    _apply_transfers_py(tt, tau, 0, best, marked, max_time)

    for k in range(1, K + 1):
        tau[k] = tau[k - 1].copy()
        new_marked: set[int] = set()

        patterns_to_scan: dict[int, int] = {}
        for stop_idx in marked:
            for pattern_idx, pos in tt.stop_to_patterns[stop_idx]:
                if pattern_idx not in patterns_to_scan or pos < patterns_to_scan[pattern_idx]:
                    patterns_to_scan[pattern_idx] = pos

        for pattern_idx, board_pos in patterns_to_scan.items():
            stops_in_pattern = tt.pattern_stops[pattern_idx]
            trips = tt.pattern_trips[pattern_idx]
            n_trips = trips.shape[0]
            if n_trips == 0:
                continue

            current_trip_idx = -1

            for pos in range(board_pos, len(stops_in_pattern)):
                stop_idx = stops_in_pattern[pos]

                if current_trip_idx >= 0:
                    arr_time = float(trips[current_trip_idx, pos, 0])
                    if arr_time < best[stop_idx] and arr_time <= max_time:
                        tau[k, stop_idx] = min(tau[k, stop_idx], arr_time)
                        best[stop_idx] = min(best[stop_idx], arr_time)
                        new_marked.add(stop_idx)

                earliest_board = tau[k - 1, stop_idx]
                if earliest_board < INF:
                    dep_times = trips[:, pos, 1]
                    candidate = bisect_left(dep_times, earliest_board)
                    if candidate < n_trips:
                        if current_trip_idx < 0 or candidate < current_trip_idx:
                            current_trip_idx = candidate

        _apply_transfers_py(tt, tau, k, best, new_marked, max_time)
        marked = new_marked
        if not marked:
            break

    return best


def _apply_transfers_py(tt, tau, k, best, marked, max_time):
    newly_marked: set[int] = set()
    for stop_idx in list(marked):
        for target_idx, walk_min in tt.transfers[stop_idx]:
            arr = tau[k, stop_idx] + walk_min
            if arr < tau[k, target_idx] and arr <= max_time:
                tau[k, target_idx] = arr
                best[target_idx] = min(best[target_idx], arr)
                newly_marked.add(target_idx)
    marked.update(newly_marked)
