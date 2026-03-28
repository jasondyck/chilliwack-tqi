"""Time-of-day TQI profile."""

import numpy as np

from tqi.config import DEPARTURE_TIMES, TSR_CAR, TSR_WALK


def compute_time_profile(
    per_slot_coverage: np.ndarray,
    per_slot_mean_tsr: np.ndarray,
) -> list[tuple[str, float]]:
    """Compute TQI for each time slot.

    Returns list of (time_label, tqi_score) tuples.
    """
    results = []
    for i, t_min in enumerate(DEPARTURE_TIMES):
        h, m = divmod(t_min, 60)
        label = f"{h:02d}:{m:02d}"

        cov_score = float(per_slot_coverage[i]) * 100
        tsr = float(per_slot_mean_tsr[i])
        spd_score = float(np.clip((tsr - TSR_WALK) / (TSR_CAR - TSR_WALK) * 100, 0, 100))
        slot_tqi = 0.5 * cov_score + 0.5 * spd_score

        results.append((label, slot_tqi))
    return results
