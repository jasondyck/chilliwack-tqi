"""Temporal reliability: travel time variability across departure times."""

import numpy as np

from tqi.scoring.tsr import valid_pair_mask

INF = float("inf")


def compute_reliability(
    mean_travel_time: np.ndarray,
    travel_time_std: np.ndarray,
    distances_km: np.ndarray,
) -> tuple[float, list[float]]:
    """Compute reliability metrics.

    Returns:
        mean_cv: Mean coefficient of variation across all valid, reachable pairs.
        per_origin_cv: List of mean CV per origin (for spatial mapping).
    """
    mask = valid_pair_mask(distances_km) & (mean_travel_time < INF) & (mean_travel_time > 0)

    # Coefficient of variation = std / mean
    with np.errstate(divide="ignore", invalid="ignore"):
        cv = np.where(mask, travel_time_std / mean_travel_time, np.nan)

    # Overall mean CV
    valid_cv = cv[mask]
    mean_cv = float(np.nanmean(valid_cv)) if len(valid_cv) > 0 else 0.0

    # Per-origin mean CV
    n_origins = mean_travel_time.shape[0]
    per_origin_cv = []
    for i in range(n_origins):
        row_mask = mask[i]
        if row_mask.any():
            per_origin_cv.append(float(np.nanmean(cv[i, row_mask])))
        else:
            per_origin_cv.append(0.0)

    return mean_cv, per_origin_cv
