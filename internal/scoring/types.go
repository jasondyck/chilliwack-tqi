package scoring

import "math"

// InfFloat is a sentinel for unreachable OD pairs.
const InfFloat = math.MaxFloat64

// ODMetrics holds the matrices produced by the RAPTOR router.
type ODMetrics struct {
	MeanTravelTime  [][]float64
	Reachability    [][]float64
	TravelTimeStd   [][]float64
	PerSlotCoverage []float64
	PerSlotMeanTSR  []float64
	DistancesKM     [][]float64
}

// TQIResult is the top-level Transit Quality Index output.
type TQIResult struct {
	TQI                  float64
	CoverageScore        float64
	SpeedScore           float64
	TimeProfile          []TimeSlotScore
	ReliabilityCV        float64
	ReliabilityPerOrigin []float64
}

// TimeSlotScore holds the TQI for a single departure time slot.
type TimeSlotScore struct {
	Label string
	Score float64
}

// DetailedAnalysis contains derived metrics for the frontend dashboard.
type DetailedAnalysis struct {
	// Coverage
	NOriginsWithService      int     `json:"n_origins_with_service"`
	NTransitDesertOrigins    int     `json:"n_transit_desert_origins"`
	TransitDesertPct         float64 `json:"transit_desert_pct"`
	NValidPairs              int     `json:"n_valid_pairs"`
	NReachablePairs          int     `json:"n_reachable_pairs"`
	ReachabilityRatePct      float64 `json:"reachability_rate_pct"`
	MaxOriginReachabilityPct float64 `json:"max_origin_reachability_pct"`

	// Speed / TSR
	MeanTSR                 float64            `json:"mean_tsr"`
	MedianTSR               float64            `json:"median_tsr"`
	TSRPercentiles          map[string]float64 `json:"tsr_percentiles"`
	TSRSlowerThanWalkingPct float64            `json:"tsr_slower_than_walking_pct"`
	TSR5To10Pct             float64            `json:"tsr_5_to_10_pct"`
	TSR10To20Pct            float64            `json:"tsr_10_to_20_pct"`
	TSR20PlusPct            float64            `json:"tsr_20_plus_pct"`

	// Travel time
	MeanTravelTimeMin     float64            `json:"mean_travel_time_min"`
	MedianTravelTimeMin   float64            `json:"median_travel_time_min"`
	TravelTimePercentiles map[string]float64 `json:"travel_time_percentiles"`

	// Time-of-day peaks
	PeakSlot   string  `json:"peak_slot"`
	PeakTQI    float64 `json:"peak_tqi"`
	LowestSlot string  `json:"lowest_slot"`
	LowestTQI  float64 `json:"lowest_tqi"`

	// Best-connected locations
	TopOrigins []TopOrigin `json:"top_origins"`

	// Reliability histogram
	ReliabilityHistogram HistogramData `json:"reliability_histogram"`

	// PTAL distribution
	PTALDistribution map[string]int `json:"ptal_distribution"`
}

// TopOrigin represents a well-connected origin point.
type TopOrigin struct {
	Lat             float64 `json:"lat"`
	Lon             float64 `json:"lon"`
	ReachabilityPct float64 `json:"reachability_pct"`
}

// HistogramData holds labels and counts for a histogram chart.
type HistogramData struct {
	Labels []string `json:"labels"`
	Counts []int    `json:"counts"`
}
