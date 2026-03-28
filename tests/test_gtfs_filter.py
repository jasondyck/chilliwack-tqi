"""Tests for GTFS filtering."""

from tqi.gtfs.filter import filter_to_chilliwack


def test_filter_keeps_matching_routes(synthetic_feed):
    """Routes with short_name '1' and '2' should be kept."""
    filtered = filter_to_chilliwack(synthetic_feed, routes=["1", "2"])
    assert len(filtered.routes) == 2
    assert len(filtered.trips) == 8  # 4 trips per route


def test_filter_removes_non_matching_routes(synthetic_feed):
    """Only route '1' should survive."""
    filtered = filter_to_chilliwack(synthetic_feed, routes=["1"])
    assert len(filtered.routes) == 1
    assert set(filtered.routes["route_short_name"]) == {"1"}
    # Only Route A trips
    assert all(t.startswith("RA") for t in filtered.trips["trip_id"])


def test_filter_preserves_stops(synthetic_feed):
    """Filtered feed should only contain stops referenced by surviving trips."""
    filtered = filter_to_chilliwack(synthetic_feed, routes=["1"])
    # Route A visits S1, S2, S3
    assert set(filtered.stops["stop_id"]) == {"S1", "S2", "S3"}
