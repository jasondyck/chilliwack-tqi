"""Tests for scoring functions."""

import numpy as np

from tqi.scoring.tsr import compute_tsr_matrix, valid_pair_mask
from tqi.scoring.coverage import compute_coverage_score
from tqi.scoring.speed import compute_speed_score

INF = float("inf")


def test_tsr_basic():
    distances = np.array([[0, 5.0], [5.0, 0]])
    travel_times = np.array([[0, 30.0], [30.0, 0]])  # 30 min
    tsr = compute_tsr_matrix(distances, travel_times)
    # 5 km / 0.5 h = 10 km/h
    assert abs(tsr[0, 1] - 10.0) < 0.01


def test_tsr_unreachable():
    distances = np.array([[0, 5.0], [5.0, 0]])
    travel_times = np.array([[0, INF], [INF, 0]])
    tsr = compute_tsr_matrix(distances, travel_times)
    assert tsr[0, 1] == 0.0


def test_valid_pair_mask():
    distances = np.array([[0, 0.3, 1.0], [0.3, 0, 0.8], [1.0, 0.8, 0]])
    mask = valid_pair_mask(distances)
    # Only pairs >= 0.5 km
    assert mask[0, 2] == True
    assert mask[2, 0] == True
    assert mask[0, 1] == False  # 0.3 km < 0.5 km


def test_coverage_score():
    reachability = np.array([[0, 0.5, 1.0], [0.5, 0, 0.8], [1.0, 0.8, 0]])
    distances = np.array([[0, 0.3, 2.0], [0.3, 0, 1.5], [2.0, 1.5, 0]])
    score = compute_coverage_score(reachability, distances)
    # Valid pairs: (0,2)=1.0, (1,2)=0.8, (2,0)=1.0, (2,1)=0.8
    # Mean = (1.0 + 0.8 + 1.0 + 0.8) / 4 = 0.9 → 90.0
    assert abs(score - 90.0) < 0.1


def test_speed_score_walking_pace():
    """If transit is exactly walking speed, speed score should be ~0."""
    distances = np.array([[0, 2.0], [2.0, 0]])
    # 2 km at 5 km/h = 24 min
    travel_times = np.array([[0, 24.0], [24.0, 0]])
    score = compute_speed_score(distances, travel_times)
    assert score < 5  # close to 0


def test_speed_score_fast():
    """If transit is at car speed (40 km/h), speed score should be ~100."""
    distances = np.array([[0, 2.0], [2.0, 0]])
    # 2 km at 40 km/h = 3 min
    travel_times = np.array([[0, 3.0], [3.0, 0]])
    score = compute_speed_score(distances, travel_times)
    assert score > 90
