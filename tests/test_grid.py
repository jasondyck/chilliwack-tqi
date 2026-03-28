"""Tests for grid generation."""

import numpy as np
from haversine import haversine, Unit

from tqi.grid.generate import generate_grid


def test_grid_shape():
    grid = generate_grid()
    assert grid.ndim == 2
    assert grid.shape[1] == 2  # lat, lon


def test_grid_within_bbox():
    grid = generate_grid()
    assert grid[:, 0].min() >= 49.04
    assert grid[:, 0].max() <= 49.23
    assert grid[:, 1].min() >= -122.13
    assert grid[:, 1].max() <= -121.77


def test_grid_approximate_spacing():
    """Adjacent points should be ~250m apart."""
    grid = generate_grid(clip_to_boundary=False)
    p0 = (grid[0, 0], grid[0, 1])
    p1 = (grid[1, 0], grid[1, 1])
    dist = haversine(p0, p1, unit=Unit.METERS)
    assert 200 < dist < 350


def test_grid_count():
    grid = generate_grid()
    assert 2000 < len(grid) < 8000


def test_grid_clipped_smaller_than_full():
    """Clipped grid should have fewer points than full bbox grid."""
    clipped = generate_grid(clip_to_boundary=True)
    full = generate_grid(clip_to_boundary=False)
    assert len(clipped) < len(full)
