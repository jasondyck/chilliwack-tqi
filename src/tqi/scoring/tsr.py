"""Transit Speed Ratio computation."""

import numpy as np

from tqi.config import MIN_OD_DIST_KM

INF = float("inf")


def compute_tsr_matrix(
    distances_km: np.ndarray,
    mean_travel_time: np.ndarray,
) -> np.ndarray:
    """Compute TSR (effective speed km/h) for each OD pair.

    Returns array of same shape as inputs. Zero where unreachable.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        tsr = np.where(
            (mean_travel_time < INF) & (mean_travel_time > 0),
            distances_km / (mean_travel_time / 60.0),
            0.0,
        )
    return tsr


def valid_pair_mask(distances_km: np.ndarray) -> np.ndarray:
    """Boolean mask excluding trivially walkable pairs (< 500m) and self-pairs."""
    return distances_km >= MIN_OD_DIST_KM
