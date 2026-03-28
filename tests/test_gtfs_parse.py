"""Tests for GTFS time parsing."""

from tqi.gtfs.parse import parse_time


def test_parse_time_normal():
    assert parse_time("08:30:00") == 510


def test_parse_time_midnight():
    assert parse_time("00:00:00") == 0


def test_parse_time_overnight():
    """Times > 24:00 are valid in GTFS for overnight trips."""
    assert parse_time("25:30:00") == 1530


def test_parse_time_noon():
    assert parse_time("12:00:00") == 720


def test_parse_time_end_of_day():
    assert parse_time("23:59:00") == 1439
