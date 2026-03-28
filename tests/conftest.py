"""Shared test fixtures."""

from pathlib import Path

import pandas as pd
import pytest

from tqi.gtfs.parse import GTFSFeed


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_gtfs_fixture() -> GTFSFeed:
    """Create a minimal synthetic GTFS feed for testing.

    Network:
        Route A: S1 → S2 → S3 (every 30 min from 06:00)
        Route B: S3 → S4 → S5 (every 30 min from 06:15)
    Transfer: S3 connects routes A and B (same stop).
    """
    stops = pd.DataFrame({
        "stop_id": ["S1", "S2", "S3", "S4", "S5"],
        "stop_name": ["Stop 1", "Stop 2", "Stop 3 (Exchange)", "Stop 4", "Stop 5"],
        "stop_lat": [49.160, 49.162, 49.165, 49.167, 49.170],
        "stop_lon": [-121.950, -121.945, -121.940, -121.935, -121.930],
    })

    routes = pd.DataFrame({
        "route_id": ["RA", "RB"],
        "route_short_name": ["1", "2"],
        "route_type": ["3", "3"],
    })

    calendar = pd.DataFrame({
        "service_id": ["WK"],
        "monday": ["1"], "tuesday": ["1"], "wednesday": ["1"],
        "thursday": ["1"], "friday": ["1"], "saturday": ["0"], "sunday": ["0"],
        "start_date": ["20250101"],
        "end_date": ["20261231"],
    })

    # Generate trips: 2 trips per route per direction
    trips_data = []
    st_data = []

    # Route A trips (S1→S2→S3)
    for i, dep_min in enumerate([360, 390, 420, 450]):  # 06:00, 06:30, 07:00, 07:30
        tid = f"RA_T{i}"
        trips_data.append({"trip_id": tid, "route_id": "RA", "service_id": "WK", "direction_id": "0"})
        for j, (sid, offset) in enumerate([("S1", 0), ("S2", 5), ("S3", 12)]):
            st_data.append({
                "trip_id": tid, "stop_id": sid, "stop_sequence": j,
                "arrival_time": _min_to_str(dep_min + offset),
                "departure_time": _min_to_str(dep_min + offset + 1),
                "arrival_min": dep_min + offset,
                "departure_min": dep_min + offset + 1,
            })

    # Route B trips (S3→S4→S5)
    for i, dep_min in enumerate([375, 405, 435, 465]):  # 06:15, 06:45, 07:15, 07:45
        tid = f"RB_T{i}"
        trips_data.append({"trip_id": tid, "route_id": "RB", "service_id": "WK", "direction_id": "0"})
        for j, (sid, offset) in enumerate([("S3", 0), ("S4", 7), ("S5", 15)]):
            st_data.append({
                "trip_id": tid, "stop_id": sid, "stop_sequence": j,
                "arrival_time": _min_to_str(dep_min + offset),
                "departure_time": _min_to_str(dep_min + offset + 1),
                "arrival_min": dep_min + offset,
                "departure_min": dep_min + offset + 1,
            })

    trips = pd.DataFrame(trips_data)
    stop_times = pd.DataFrame(st_data)
    stop_times["stop_sequence"] = stop_times["stop_sequence"].astype(int)

    return GTFSFeed(
        stops=stops,
        stop_times=stop_times,
        trips=trips,
        routes=routes,
        calendar=calendar,
        calendar_dates=None,
        shapes=None,
    )


def _min_to_str(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}:00"


@pytest.fixture
def synthetic_feed() -> GTFSFeed:
    return _make_gtfs_fixture()
