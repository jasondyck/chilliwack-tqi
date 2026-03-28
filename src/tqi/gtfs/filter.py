"""Filter GTFS feed to Chilliwack routes and a target service day."""

from datetime import date, datetime

import pandas as pd

from tqi.config import CHILLIWACK_ROUTES
from tqi.gtfs.parse import GTFSFeed


def _resolve_active_services(
    calendar: pd.DataFrame | None,
    calendar_dates: pd.DataFrame | None,
    target_day: str,
    ref_date: date | None = None,
) -> set[str]:
    """Return set of active service_id values for the target day of week."""
    active: set[str] = set()

    if ref_date is None:
        ref_date = date.today()
    ref_str = ref_date.strftime("%Y%m%d")

    # calendar.txt: services running on target weekday within date range
    if calendar is not None and not calendar.empty:
        mask = calendar[target_day] == "1"
        if "start_date" in calendar.columns and "end_date" in calendar.columns:
            mask = mask & (calendar["start_date"] <= ref_str) & (calendar["end_date"] >= ref_str)
        active = set(calendar.loc[mask, "service_id"])

    # calendar_dates.txt: exceptions (1 = added, 2 = removed)
    if calendar_dates is not None and not calendar_dates.empty:
        for _, row in calendar_dates.iterrows():
            if row["date"] == ref_str:
                if row["exception_type"] == "1":
                    active.add(row["service_id"])
                elif row["exception_type"] == "2":
                    active.discard(row["service_id"])

    return active


def _find_reference_date(
    calendar: pd.DataFrame | None,
    target_day: str,
) -> date:
    """Find a valid reference date (a target weekday within the feed's date range)."""
    day_index = [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ].index(target_day)

    if calendar is not None and not calendar.empty and "start_date" in calendar.columns:
        start = datetime.strptime(calendar["start_date"].min(), "%Y%m%d").date()
        end = datetime.strptime(calendar["end_date"].max(), "%Y%m%d").date()
        # Find the first target weekday in the range
        d = start
        from datetime import timedelta
        while d <= end:
            if d.weekday() == day_index:
                return d
            d += timedelta(days=1)

    # Fallback: use today
    return date.today()


def filter_to_chilliwack(
    feed: GTFSFeed,
    target_day: str = "wednesday",
    routes: list[str] = CHILLIWACK_ROUTES,
) -> GTFSFeed:
    """Filter feed to Chilliwack routes active on the target day."""
    # Find a valid reference date within the feed's calendar
    ref_date = _find_reference_date(feed.calendar, target_day)
    print(f"Using reference date: {ref_date} ({target_day})")

    # Resolve active services
    active_services = _resolve_active_services(
        feed.calendar, feed.calendar_dates, target_day, ref_date
    )
    if not active_services:
        raise ValueError(f"No active services found for {target_day} on {ref_date}")
    print(f"Active services: {len(active_services)}")

    # Filter routes by short_name
    route_mask = feed.routes["route_short_name"].isin(routes)
    filtered_routes = feed.routes[route_mask]
    route_ids = set(filtered_routes["route_id"])
    print(f"Chilliwack routes matched: {len(route_ids)}")

    # Filter trips
    trip_mask = feed.trips["route_id"].isin(route_ids) & feed.trips["service_id"].isin(
        active_services
    )
    filtered_trips = feed.trips[trip_mask]
    trip_ids = set(filtered_trips["trip_id"])
    print(f"Active trips: {len(trip_ids)}")

    # Filter stop_times
    filtered_stop_times = feed.stop_times[feed.stop_times["trip_id"].isin(trip_ids)]

    # Filter stops to only those referenced
    used_stop_ids = set(filtered_stop_times["stop_id"])
    filtered_stops = feed.stops[feed.stops["stop_id"].isin(used_stop_ids)]
    print(f"Stops in use: {len(filtered_stops)}")

    return GTFSFeed(
        stops=filtered_stops.reset_index(drop=True),
        stop_times=filtered_stop_times.reset_index(drop=True),
        trips=filtered_trips.reset_index(drop=True),
        routes=filtered_routes.reset_index(drop=True),
        calendar=feed.calendar,
        calendar_dates=feed.calendar_dates,
        shapes=feed.shapes,
    )
