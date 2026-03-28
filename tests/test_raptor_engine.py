"""Tests for the RAPTOR routing engine."""

import numpy as np

from tqi.raptor.timetable import build_raptor_timetable, flatten_timetable
from tqi.raptor.engine import raptor, raptor_jit

INF = float("inf")


def test_direct_route(synthetic_feed):
    """Travel from S1 to S3 on Route A should take ~12 minutes."""
    tt = build_raptor_timetable(synthetic_feed)
    s1 = tt.stop_id_to_idx["S1"]
    s3 = tt.stop_id_to_idx["S3"]

    # Depart at 06:00 (360 min) — first RA trip departs S1 at 361 (360+1 dep)
    arrivals = raptor(tt, [(s1, 360)], max_transfers=2, max_time=450)
    # S3 arrival: 360 + 12 = 372
    assert arrivals[s3] == 372


def test_transfer(synthetic_feed):
    """Travel from S1 to S5 requires transferring at S3."""
    tt = build_raptor_timetable(synthetic_feed)
    s1 = tt.stop_id_to_idx["S1"]
    s5 = tt.stop_id_to_idx["S5"]

    # Depart at 06:00. Arrive S3 at 372. RB first trip departs S3 at 376 (375+1).
    # Arrive S5 at 375+15=390.
    arrivals = raptor(tt, [(s1, 360)], max_transfers=2, max_time=480)
    assert arrivals[s5] < INF
    # Should arrive at S5 by 390
    assert arrivals[s5] == 390


def test_unreachable_with_zero_transfers(synthetic_feed):
    """S1→S5 should be unreachable with 0 transfers (requires Route A then B)."""
    tt = build_raptor_timetable(synthetic_feed)
    s1 = tt.stop_id_to_idx["S1"]
    s5 = tt.stop_id_to_idx["S5"]

    # With 0 transfers, only direct routes are usable
    arrivals = raptor(tt, [(s1, 360)], max_transfers=0, max_time=480)
    # S5 is only on Route B, so without transfer it should be unreachable
    # unless S3→S5 counts as a transfer. Since S3 is served by both routes,
    # a 0-transfer RAPTOR can board route A, ride to S3, then board route B at S3.
    # In RAPTOR, "transfers" are walking between stops. Boarding a different route
    # at the same stop happens in the next round's route scanning.
    # Round 0: initial stops. Round 1: ride routes from initial.
    # With max_transfers=0, we get K=1 round, which means we can ride exactly one route.
    # So S1→S3 via Route A is round 1. To then ride Route B from S3, we'd need round 2.
    assert arrivals[s5] == INF


def test_max_time_cutoff(synthetic_feed):
    """Arrivals beyond max_time should not be recorded."""
    tt = build_raptor_timetable(synthetic_feed)
    s1 = tt.stop_id_to_idx["S1"]
    s3 = tt.stop_id_to_idx["S3"]

    # S3 arrival would be 372, but set max_time to 370
    arrivals = raptor(tt, [(s1, 360)], max_transfers=2, max_time=370)
    assert arrivals[s3] == INF


def test_multiple_source_stops(synthetic_feed):
    """Starting from multiple stops should use the best option."""
    tt = build_raptor_timetable(synthetic_feed)
    s1 = tt.stop_id_to_idx["S1"]
    s2 = tt.stop_id_to_idx["S2"]
    s3 = tt.stop_id_to_idx["S3"]

    # Starting from both S1 (at 360) and S2 (at 360), S3 should be reached
    # via S2 faster (S2→S3 is 7 min on route A: arrive 365, dep 366, arrive S3 at 372)
    # Actually S1 departure at 361 arrives S2 at 365, S3 at 372
    # Starting at S2 at 360, first trip departs S2 at 366 (dep_min of first trip at S2)
    # No wait — actually: RA_T0 departs S2 at 366, arrives S3 at 372
    # From S2 at 360, we board at 366 departure, arrive S3 at 372
    # From S1 at 360, we board at 361 departure, arrive S3 at 372
    # Same arrival. But if S2 start is earlier, it could be faster.
    arrivals = raptor(tt, [(s1, 360), (s2, 358)], max_transfers=2, max_time=480)
    # From S2 at 358, board first trip at 366, arrive S3 at 372
    assert arrivals[s3] <= 372


def test_jit_matches_python(synthetic_feed):
    """JIT engine should produce same results as pure-Python engine."""
    tt = build_raptor_timetable(synthetic_feed)
    ft = flatten_timetable(tt)
    s1 = tt.stop_id_to_idx["S1"]

    py_arrivals = raptor(tt, [(s1, 360)], max_transfers=2, max_time=480)
    jit_arrivals = raptor_jit(ft, [(s1, 360)], max_transfers=2, max_time=480)

    for s in range(tt.n_stops):
        py_val = py_arrivals[s]
        jit_val = jit_arrivals[s]
        if py_val == INF:
            assert jit_val >= 1e17, f"Stop {s}: Python=INF but JIT={jit_val}"
        else:
            assert abs(py_val - jit_val) < 0.1, f"Stop {s}: Python={py_val} JIT={jit_val}"
