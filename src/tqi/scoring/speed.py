"""Speed sub-score: how fast is transit relative to walking."""

import numpy as np

from tqi.config import TSR_CAR, TSR_WALK
from tqi.scoring.tsr import compute_tsr_matrix, valid_pair_mask

INF = float("inf")


def compute_speed_score(
    distances_km: np.ndarray,
    mean_travel_time: np.ndarray,
    weights: np.ndarray | None = None,
) -> float:
    """Speed score (0-100): normalised mean TSR for reachable pairs.

    If weights are provided (per-origin), uses weighted mean TSR.
    """
    tsr = compute_tsr_matrix(distances_km, mean_travel_time)
    mask = valid_pair_mask(distances_km) & (mean_travel_time < INF)
    if not mask.any():
        return 0.0
    if weights is not None:
        n_origins = tsr.shape[0]
        origin_tsr = np.array([
            float(np.mean(tsr[i, mask[i]])) if mask[i].any() else 0.0
            for i in range(n_origins)
        ])
        mean_tsr = float(np.average(origin_tsr, weights=weights))
    else:
        mean_tsr = float(np.mean(tsr[mask]))
    score = (mean_tsr - TSR_WALK) / (TSR_CAR - TSR_WALK) * 100
    return float(np.clip(score, 0, 100))
