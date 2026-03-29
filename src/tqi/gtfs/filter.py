"""Filter GTFS feed to Chilliwack routes and a target service day."""

from datetime import date, datetime, timedelta

import pandas as pd

from tqi.config import CHILLIWACK_ROUTES
from tqi.gtfs.parse import GTFSFeed

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def _find_best_weekday(
    calendar: pd.DataFrame | None,
    calendar_dates: pd.DataFrame | None,
    trips: pd.DataFrame,
) -> tuple[str, date]:
    """Find the weekday with the most active trips.

    Handles both calendar.txt and calendar_dates.txt-only feeds.
    Returns (day_name, reference_date).
    """
    best_day = "wednesday"
    best_date = date.today()
    best_trips = 0

    # Collect candidate dates from calendar_dates.txt
    candidate_dates: list[date] = []

    if calendar_dates is not None and not calendar_dates.empty:
        for d_str in calendar_dates["date"].unique():
            try:
                d = datetime.strptime(str(d_str), "%Y%m%d").date()
                if d.weekday() < 5:  # weekdays only
                    candidate_dates.append(d)
            except ValueError:
                continue

    # Also try dates from calendar.txt range
    if calendar is not None and not calendar.empty and "start_date" in calendar.columns:
        start = datetime.strptime(calendar["start_date"].min(), "%Y%m%d").date()
        end = datetime.strptime(calendar["end_date"].max(), "%Y%m%d").date()
        d = start
        while d <= end and len(candidate_dates) < 100:
            if d.weekday() < 5:
                candidate_dates.append(d)
            d += timedelta(days=1)

    if not candidate_dates:
        # Last resort: try the next 7 days from today
        for i in range(7):
            d = date.today() + timedelta(days=i)
            if d.weekday() < 5:
                candidate_dates.append(d)

    # For each candidate date, count how many trips are active
    for d in candidate_dates:
        d_str = d.strftime("%Y%m%d")
        day_name = WEEKDAYS[d.weekday()]

        active_services: set[str] = set()

        # calendar.txt
        if calendar is not None and not calendar.empty:
            mask = calendar[day_name] == "1"
            if "start_date" in calendar.columns:
                mask = mask & (calendar["start_date"] <= d_str) & (calendar["end_date"] >= d_str)
            active_services = set(calendar.loc[mask, "service_id"])

        # calendar_dates.txt exceptions
        if calendar_dates is not None and not calendar_dates.empty:
            for _, row in calendar_dates[calendar_dates["date"] == d_str].iterrows():
                if row["exception_type"] == "1":
                    active_services.add(row["service_id"])
                elif row["exception_type"] == "2":
                    active_services.discard(row["service_id"])

        if active_services:
            n_trips = len(trips[trips["service_id"].isin(active_services)])
            if n_trips > best_trips:
                best_trips = n_trips
                best_day = day_name
                best_date = d

    return best_day, best_date


def filter_to_chilliwack(
    feed: GTFSFeed,
    target_day: str | None = None,
    routes: list[str] = CHILLIWACK_ROUTES,
) -> GTFSFeed:
    """Filter feed to Chilliwack routes on the best weekday.

    If target_day is None, automatically picks the weekday with the most trips.
    """
    if target_day is None:
        day_name, ref_date = _find_best_weekday(
            feed.calendar, feed.calendar_dates, feed.trips
        )
        print(f"Auto-selected best weekday: {day_name} ({ref_date})")
    else:
        day_name = target_day
        # Find a valid date for the requested day
        _, ref_date = _find_best_weekday(feed.calendar, feed.calendar_dates, feed.trips)
        # Override to find a date matching target_day
        day_index = WEEKDAYS.index(target_day) if target_day in WEEKDAYS else 2
        if ref_date.weekday() != day_index:
            # Adjust to nearest matching weekday
            diff = (day_index - ref_date.weekday()) % 7
            ref_date = ref_date + timedelta(days=diff)
        print(f"Using reference date: {ref_date} ({day_name})")

    # Resolve active services for that date
    active_services: set[str] = set()
    ref_str = ref_date.strftime("%Y%m%d")

    if feed.calendar is not None and not feed.calendar.empty:
        mask = feed.calendar[day_name] == "1"
        if "start_date" in feed.calendar.columns:
            mask = mask & (feed.calendar["start_date"] <= ref_str) & (feed.calendar["end_date"] >= ref_str)
        active_services = set(feed.calendar.loc[mask, "service_id"])

    if feed.calendar_dates is not None and not feed.calendar_dates.empty:
        for _, row in feed.calendar_dates[feed.calendar_dates["date"] == ref_str].iterrows():
            if row["exception_type"] == "1":
                active_services.add(row["service_id"])
            elif row["exception_type"] == "2":
                active_services.discard(row["service_id"])

    if not active_services:
        raise ValueError(f"No active services found for {day_name} on {ref_date}")
    print(f"Active services: {len(active_services)} ({', '.join(sorted(active_services))})")

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
