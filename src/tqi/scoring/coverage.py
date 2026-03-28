"""Coverage sub-score: what fraction of OD pairs are transit-reachable."""

import numpy as np

from tqi.scoring.tsr import valid_pair_mask


def compute_coverage_score(
    reachability: np.ndarray,
    distances_km: np.ndarray,
    weights: np.ndarray | None = None,
) -> float:
    """Coverage score (0-100): mean reachability across valid OD pairs.

    If weights are provided (per-origin), uses weighted mean.
    """
    mask = valid_pair_mask(distances_km)
    if not mask.any():
        return 0.0
    if weights is not None:
        # Weighted by origin: for each origin, compute mean reachability across valid dests
        n_origins = reachability.shape[0]
        origin_reach = np.array([
            float(np.mean(reachability[i, mask[i]])) if mask[i].any() else 0.0
            for i in range(n_origins)
        ])
        return float(np.average(origin_reach, weights=weights) * 100)
    return float(np.mean(reachability[mask]) * 100)
