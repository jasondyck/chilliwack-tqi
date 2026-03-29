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
