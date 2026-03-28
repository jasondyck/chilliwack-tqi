"""Parse GTFS CSV files into structured DataFrames."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tqi.config import GTFS_DIR


def parse_time(time_str: str) -> int:
    """Parse GTFS time string to minutes since midnight.

    Handles times > 24:00:00 (e.g. "25:30:00" → 1530 minutes).
    """
    parts = time_str.strip().split(":")
    h, m = int(parts[0]), int(parts[1])
    return h * 60 + m


@dataclass
class GTFSFeed:
    stops: pd.DataFrame
    stop_times: pd.DataFrame
    trips: pd.DataFrame
    routes: pd.DataFrame
    calendar: pd.DataFrame | None
    calendar_dates: pd.DataFrame | None
    shapes: pd.DataFrame | None


def load_gtfs(gtfs_dir: Path = GTFS_DIR) -> GTFSFeed:
    """Load all GTFS CSVs and parse time columns."""
    def _read(name: str) -> pd.DataFrame | None:
        path = gtfs_dir / name
        if path.exists():
            return pd.read_csv(path, dtype=str)
        return None

    stops = _read("stops.txt")
    stop_times = _read("stop_times.txt")
    trips = _read("trips.txt")
    routes = _read("routes.txt")
    calendar = _read("calendar.txt")
    calendar_dates = _read("calendar_dates.txt")
    shapes = _read("shapes.txt")

    if stops is None or stop_times is None or trips is None or routes is None:
        raise FileNotFoundError("Missing required GTFS files (stops, stop_times, trips, routes)")

    # Parse coordinates
    stops["stop_lat"] = stops["stop_lat"].astype(float)
    stops["stop_lon"] = stops["stop_lon"].astype(float)

    # Parse times to minutes since midnight
    stop_times["arrival_min"] = stop_times["arrival_time"].apply(parse_time)
    stop_times["departure_min"] = stop_times["departure_time"].apply(parse_time)
    stop_times["stop_sequence"] = stop_times["stop_sequence"].astype(int)

    return GTFSFeed(
        stops=stops,
        stop_times=stop_times,
        trips=trips,
        routes=routes,
        calendar=calendar,
        calendar_dates=calendar_dates,
        shapes=shapes,
    )
