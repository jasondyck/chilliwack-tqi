"""TCQSM Level of Service computation per route.

Reference: Transit Capacity and Quality of Service Manual, 3rd Edition
(TCRP Report 165, Transportation Research Board).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from tqi.config import TCQSM_LOS
from tqi.gtfs.parse import GTFSFeed


@dataclass
class RouteLOS:
    route_name: str
    route_long_name: str
    route_id: str
    n_trips: int
    median_headway_min: float
    peak_headway_min: float | None  # AM peak 7-9
    los_grade: str
    los_description: str


def _headway_to_los(headway_min: float) -> tuple[str, str]:
    """Map median headway to TCQSM LOS grade."""
    for max_hw, grade, desc in TCQSM_LOS:
        if headway_min <= max_hw:
            return grade, desc
    return "F", "Service unattractive to all riders"


def compute_route_los(feed: GTFSFeed) -> list[RouteLOS]:
    """Compute TCQSM LOS for each route in the filtered feed."""
    route_cols = ["route_id", "route_short_name"]
    if "route_long_name" in feed.routes.columns:
        route_cols.append("route_long_name")

    st = feed.stop_times.merge(feed.trips[["trip_id", "route_id", "direction_id"]], on="trip_id")
    st = st.merge(feed.routes[route_cols], on="route_id")

    # Build route_id → long name lookup
    long_names: dict[str, str] = {}
    if "route_long_name" in feed.routes.columns:
        for _, row in feed.routes.iterrows():
            long_names[str(row["route_id"])] = str(row.get("route_long_name", ""))

    results = []

    for (route_id, route_name), group in st.groupby(["route_id", "route_short_name"]):
        # Compute headway per direction separately, then take the better one.
        # Mixing directions inflates frequency (two 30-min routes interleave to look like 15-min).
        n_trips = group["trip_id"].nunique()
        dir_headways = []
        for d_id, d_group in group.groupby("direction_id"):
            d_starts = (
                d_group.sort_values("stop_sequence")
                .groupby("trip_id")["departure_min"]
                .first()
                .sort_values()
            )
            if len(d_starts) >= 2:
                hws = np.diff(d_starts.values.astype(float))
                hws = hws[hws > 0]
                if len(hws) > 0:
                    dir_headways.append(float(np.median(hws)))
        # If we have per-direction data, use the best (lowest) direction headway.
        # If only one direction exists, use that.
        if dir_headways:
            trip_starts_median = min(dir_headways)
        else:
            # Fallback: all trips combined
            all_starts = (
                group.sort_values("stop_sequence")
                .groupby("trip_id")["departure_min"]
                .first()
                .sort_values()
            )
            hws = np.diff(all_starts.values.astype(float))
            hws = hws[hws > 0]
            trip_starts_median = float(np.median(hws)) if len(hws) > 0 else 999.0

        if n_trips < 2:
            results.append(RouteLOS(
                route_name=str(route_name),
                route_long_name=long_names.get(str(route_id), ""),
                route_id=str(route_id),
                n_trips=n_trips,
                median_headway_min=999.0,
                peak_headway_min=None,
                los_grade="F",
                los_description="Service unattractive to all riders",
            ))
            continue

        median_hw = trip_starts_median

        # AM peak headway per direction (7:00-9:00 = 420-540 min)
        peak_hw = None
        for d_id, d_group in group.groupby("direction_id"):
            d_starts = (
                d_group.sort_values("stop_sequence")
                .groupby("trip_id")["departure_min"]
                .first()
                .sort_values()
            ).values.astype(float)
            peak_s = d_starts[(d_starts >= 420) & (d_starts <= 540)]
            if len(peak_s) >= 2:
                phw = np.diff(peak_s)
                phw = phw[phw > 0]
                if len(phw) > 0:
                    candidate = float(np.median(phw))
                    if peak_hw is None or candidate < peak_hw:
                        peak_hw = candidate

        grade, desc = _headway_to_los(median_hw)

        results.append(RouteLOS(
            route_name=str(route_name),
            route_long_name=long_names.get(str(route_id), ""),
            route_id=str(route_id),
            n_trips=n_trips,
            median_headway_min=round(median_hw, 1),
            peak_headway_min=round(peak_hw, 1) if peak_hw else None,
            los_grade=grade,
            los_description=desc,
        ))

    # Sort by route name (numeric sort where possible)
    results.sort(key=lambda r: (r.route_name.zfill(5)))
    return results


def compute_system_los_summary(route_los: list[RouteLOS]) -> dict:
    """Aggregate system-level LOS statistics."""
    grades = [r.los_grade for r in route_los]
    headways = [r.median_headway_min for r in route_los if r.median_headway_min < 999]

    grade_counts = {}
    for g in ["A", "B", "C", "D", "E", "F"]:
        grade_counts[g] = grades.count(g)

    return {
        "n_routes": len(route_los),
        "grade_counts": grade_counts,
        "median_system_headway_min": float(np.median(headways)) if headways else 0,
        "best_grade": min(grades) if grades else "F",
        "worst_grade": max(grades) if grades else "F",
        "pct_los_d_or_worse": sum(1 for g in grades if g >= "D") / len(grades) * 100 if grades else 0,
    }
