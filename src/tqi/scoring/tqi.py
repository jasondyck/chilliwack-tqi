"""Final TQI aggregation and detailed analysis."""

from dataclasses import dataclass, field

import numpy as np

from tqi.config import MIN_OD_DIST_KM, TSR_CAR, TSR_WALK, WALKSCORE_RANGES
from tqi.raptor.matrix import ODMetrics
from tqi.scoring.coverage import compute_coverage_score
from tqi.scoring.speed import compute_speed_score
from tqi.scoring.time_profile import compute_time_profile
from tqi.scoring.reliability import compute_reliability
from tqi.scoring.tsr import compute_tsr_matrix, valid_pair_mask

INF = float("inf")


@dataclass
class TQIResult:
    tqi: float
    coverage_score: float
    speed_score: float
    time_profile: list[tuple[str, float]]
    reliability_mean_cv: float
    reliability_per_origin: list[float]


@dataclass
class DetailedAnalysis:
    """Rich analysis data for the report."""
    # Grid / network stats
    n_grid_points: int
    n_stops: int
    n_origins_with_service: int
    n_transit_desert_origins: int
    transit_desert_pct: float

    # OD pair stats
    n_valid_pairs: int
    n_reachable_pairs: int
    reachability_rate_pct: float
    max_origin_reachability_pct: float

    # TSR distribution (reachable pairs only)
    mean_tsr: float
    median_tsr: float
    tsr_percentiles: dict[int, float]
    tsr_slower_than_walking_pct: float
    tsr_5_to_10_pct: float
    tsr_10_to_20_pct: float
    tsr_20_plus_pct: float

    # Travel time distribution (reachable pairs)
    mean_travel_time_min: float
    median_travel_time_min: float
    travel_time_percentiles: dict[int, float]

    # Top connected locations
    top_origins: list[dict]

    # Time-of-day
    peak_slot: str
    peak_tqi: float
    lowest_slot: str
    lowest_tqi: float

    # Established metrics
    walkscore_category: str
    walkscore_description: str
    route_los: list | None          # list[RouteLOS] from tcqsm module
    system_los_summary: dict | None
    ptal_values: np.ndarray | None  # per-grid-point AI
    ptal_grades: np.ndarray | None  # per-grid-point grade strings
    ptal_distribution: dict | None  # grade → count

    # Narrative interpretation
    narrative: list[str]


def _walkscore_category(tqi: float) -> tuple[str, str]:
    """Map TQI to Walk Score Transit Score category."""
    for low, high, name, desc in WALKSCORE_RANGES:
        if low <= tqi <= high:
            return name, desc
    return "Minimal Transit", "It is possible to get on a bus"


def compute_tqi(
    metrics: ODMetrics,
    coverage_weight: float = 0.5,
    speed_weight: float = 0.5,
) -> TQIResult:
    """Compute the overall TQI and all sub-scores."""
    coverage = compute_coverage_score(metrics.reachability, metrics.distances_km)
    speed = compute_speed_score(metrics.distances_km, metrics.mean_travel_time)
    tqi = coverage_weight * coverage + speed_weight * speed

    time_profile = compute_time_profile(
        metrics.per_slot_coverage,
        metrics.per_slot_mean_tsr,
    )

    rel_mean_cv, rel_per_origin = compute_reliability(
        metrics.mean_travel_time,
        metrics.travel_time_std,
        metrics.distances_km,
    )

    return TQIResult(
        tqi=tqi,
        coverage_score=coverage,
        speed_score=speed,
        time_profile=time_profile,
        reliability_mean_cv=rel_mean_cv,
        reliability_per_origin=rel_per_origin,
    )


def compute_detailed_analysis(
    metrics: ODMetrics,
    result: TQIResult,
    grid: np.ndarray,
    n_stops: int,
    route_los: list | None = None,
    system_los_summary: dict | None = None,
    ptal_values: np.ndarray | None = None,
    ptal_grades: np.ndarray | None = None,
) -> DetailedAnalysis:
    """Compute all the detailed statistics for the report."""
    n_grid = len(grid)
    dist = metrics.distances_km
    mt = metrics.mean_travel_time
    reach = metrics.reachability

    valid = valid_pair_mask(dist)
    reachable = (mt < INF) & valid

    n_valid = int(valid.sum())
    n_reachable = int(reachable.sum())
    reachability_rate = n_reachable / n_valid * 100 if n_valid > 0 else 0.0

    # Per-origin reachability
    origin_reach_rate = reach.mean(axis=1)
    n_with_service = int((origin_reach_rate > 0).sum())
    n_desert = n_grid - n_with_service
    desert_pct = n_desert / n_grid * 100
    max_origin_reach = float(origin_reach_rate.max()) * 100

    # TSR distribution
    tsr_matrix = compute_tsr_matrix(dist, mt)
    reachable_tsr = tsr_matrix[reachable]

    if len(reachable_tsr) > 0:
        mean_tsr = float(reachable_tsr.mean())
        median_tsr = float(np.median(reachable_tsr))
        tsr_pcts = {p: float(np.percentile(reachable_tsr, p)) for p in [10, 25, 50, 75, 90, 95, 99]}
        slower_pct = float((reachable_tsr < TSR_WALK).sum() / len(reachable_tsr) * 100)
        band_5_10 = float(((reachable_tsr >= 5) & (reachable_tsr < 10)).sum() / len(reachable_tsr) * 100)
        band_10_20 = float(((reachable_tsr >= 10) & (reachable_tsr < 20)).sum() / len(reachable_tsr) * 100)
        band_20_plus = float((reachable_tsr >= 20).sum() / len(reachable_tsr) * 100)
    else:
        mean_tsr = median_tsr = 0.0
        tsr_pcts = {}
        slower_pct = band_5_10 = band_10_20 = band_20_plus = 0.0

    # Travel time distribution
    reachable_times = mt[reachable]
    if len(reachable_times) > 0:
        mean_tt = float(reachable_times.mean())
        median_tt = float(np.median(reachable_times))
        tt_pcts = {p: float(np.percentile(reachable_times, p)) for p in [10, 25, 50, 75, 90]}
    else:
        mean_tt = median_tt = 0.0
        tt_pcts = {}

    # Top connected origins
    best_idx = np.argsort(origin_reach_rate)[-10:][::-1]
    top_origins = [
        {
            "lat": float(grid[i, 0]),
            "lon": float(grid[i, 1]),
            "reachability_pct": float(origin_reach_rate[i] * 100),
        }
        for i in best_idx if origin_reach_rate[i] > 0
    ]

    # Time-of-day peak/lowest
    tp = result.time_profile
    scores = [s for _, s in tp]
    labels = [l for l, _ in tp]
    peak_idx = int(np.argmax(scores))
    low_idx = int(np.argmin(scores))

    # Walk Score category
    ws_cat, ws_desc = _walkscore_category(result.tqi)

    # PTAL distribution
    ptal_dist = None
    if ptal_grades is not None:
        ptal_dist = {}
        for grade in ["1a", "1b", "2", "3", "4", "5", "6a", "6b"]:
            ptal_dist[grade] = int((ptal_grades == grade).sum())

    # Narrative
    narrative = _build_narrative(
        result, n_grid, n_stops, n_with_service, desert_pct,
        reachability_rate, mean_tsr, slower_pct, mean_tt, max_origin_reach,
        ws_cat, route_los, system_los_summary, ptal_dist,
    )

    return DetailedAnalysis(
        n_grid_points=n_grid,
        n_stops=n_stops,
        n_origins_with_service=n_with_service,
        n_transit_desert_origins=n_desert,
        transit_desert_pct=desert_pct,
        n_valid_pairs=n_valid,
        n_reachable_pairs=n_reachable,
        reachability_rate_pct=reachability_rate,
        max_origin_reachability_pct=max_origin_reach,
        mean_tsr=mean_tsr,
        median_tsr=median_tsr,
        tsr_percentiles=tsr_pcts,
        tsr_slower_than_walking_pct=slower_pct,
        tsr_5_to_10_pct=band_5_10,
        tsr_10_to_20_pct=band_10_20,
        tsr_20_plus_pct=band_20_plus,
        mean_travel_time_min=mean_tt,
        median_travel_time_min=median_tt,
        travel_time_percentiles=tt_pcts,
        top_origins=top_origins,
        peak_slot=labels[peak_idx],
        peak_tqi=scores[peak_idx],
        lowest_slot=labels[low_idx],
        lowest_tqi=scores[low_idx],
        walkscore_category=ws_cat,
        walkscore_description=ws_desc,
        route_los=route_los,
        system_los_summary=system_los_summary,
        ptal_values=ptal_values,
        ptal_grades=ptal_grades,
        ptal_distribution=ptal_dist,
        narrative=narrative,
    )


def _build_narrative(
    result, n_grid, n_stops, n_with_service, desert_pct,
    reachability_rate, mean_tsr, slower_pct, mean_tt, max_origin_reach,
    ws_category, route_los, system_los_summary, ptal_dist,
) -> list[str]:
    """Generate human-readable analysis paragraphs referencing established standards."""
    paras = []

    # Overall verdict using Walk Score classification
    paras.append(
        f"Chilliwack scores {result.tqi:.1f} out of 100, placing it in the "
        f"\"{ws_category}\" category on the Walk Score Transit Score scale (0–24). "
        f"Per the Walk Score methodology: \"{_walkscore_category(result.tqi)[1]}.\""
    )

    # TCQSM context
    if system_los_summary:
        pct_poor = system_los_summary.get("pct_los_d_or_worse", 0)
        med_hw = system_los_summary.get("median_system_headway_min", 0)
        best = system_los_summary.get("best_grade", "F")
        paras.append(
            f"Per the Transit Capacity and Quality of Service Manual (TCQSM, TCRP Report 165), "
            f"{pct_poor:.0f}% of Chilliwack's routes operate at Level of Service D or worse "
            f"(headways exceeding 20 minutes). The system-wide median headway is {med_hw:.0f} minutes. "
            f"The best-performing route achieves LOS {best}. "
            f"TCQSM classifies headways over 30 minutes as 'unattractive to choice riders' (LOS D) "
            f"and over 60 minutes as 'unattractive to all riders' (LOS F)."
        )

    # Coverage analysis
    if desert_pct > 50:
        paras.append(
            f"Coverage is the primary deficit: {desert_pct:.0f}% of locations within city limits "
            f"({n_grid - n_with_service:,} of {n_grid:,} grid points) are transit deserts "
            f"with no bus stop within 800m. Only {n_with_service:,} locations have any transit access. "
            f"Of reachable origin-destination pairs, only {reachability_rate:.1f}% can be completed "
            f"by transit within 90 minutes."
        )
    else:
        paras.append(
            f"{n_with_service:,} of {n_grid:,} locations ({100 - desert_pct:.0f}%) have "
            f"transit access within 800m. {reachability_rate:.1f}% of OD pairs are reachable "
            f"within 90 minutes."
        )

    # Speed analysis
    if result.speed_score < 1:
        paras.append(
            f"Effective transit speed averages {mean_tsr:.1f} km/h door-to-door — at or below "
            f"walking pace (5 km/h). {slower_pct:.0f}% of reachable trips are slower than walking. "
            f"Mean trip duration is {mean_tt:.0f} minutes. Long headways (30–60 min per TCQSM LOS E/F) "
            f"mean wait time dominates total travel time, making a 10-minute bus ride into a "
            f"50+ minute door-to-door journey."
        )
    elif result.speed_score < 20:
        paras.append(
            f"Effective speed averages {mean_tsr:.1f} km/h, marginally faster than walking. "
            f"{slower_pct:.0f}% of trips are slower than walking. Mean trip: {mean_tt:.0f} minutes."
        )
    else:
        paras.append(
            f"Transit averages {mean_tsr:.1f} km/h effective speed with mean trip "
            f"duration of {mean_tt:.0f} minutes."
        )

    # PTAL context
    if ptal_dist:
        total = sum(ptal_dist.values())
        poor_ptal = ptal_dist.get("1a", 0) + ptal_dist.get("1b", 0)
        poor_pct = poor_ptal / total * 100 if total > 0 else 0
        if poor_pct > 50:
            paras.append(
                f"Using the Transport for London PTAL methodology, {poor_pct:.0f}% of grid points "
                f"score PTAL grade 1a or 1b ('very poor' to 'extremely poor' accessibility). "
                f"PTAL measures the density of transit service accessible on foot — a low grade "
                f"indicates few routes, long headways, or long walks to stops."
            )

    # Reliability
    cv = result.reliability_mean_cv
    if cv < 0.15:
        rel_desc = "relatively consistent"
    elif cv < 0.30:
        rel_desc = "moderately variable"
    else:
        rel_desc = "highly variable"
    paras.append(
        f"Travel times are {rel_desc} (CV = {cv:.2f}), varying ~{cv*100:.0f}% by departure time."
    )

    return paras
