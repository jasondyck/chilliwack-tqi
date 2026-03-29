package scoring

import (
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/grid"
)

func TestComputeDetailedAnalysis(t *testing.T) {
	// 3 grid points. Point 0 and 1 are near a stop; point 2 is far away (transit desert).
	points := []grid.Point{
		{Lat: 49.0, Lon: -122.0},
		{Lat: 49.001, Lon: -122.001},
		{Lat: 50.0, Lon: -120.0}, // far away
	}

	// 2 stops near points 0 and 1.
	stopLats := []float64{49.0001, 49.0015}
	stopLons := []float64{-122.0001, -122.0015}

	n := len(points)

	// Build OD matrices (3x3).
	meanTT := make([][]float64, n)
	reach := make([][]float64, n)
	dist := make([][]float64, n)
	ttStd := make([][]float64, n)
	for i := 0; i < n; i++ {
		meanTT[i] = make([]float64, n)
		reach[i] = make([]float64, n)
		dist[i] = make([]float64, n)
		ttStd[i] = make([]float64, n)
	}

	// Set some reachable pairs with plausible values.
	// 0->1: 15 min, 10 km, reachable
	meanTT[0][1] = 15
	reach[0][1] = 1.0
	dist[0][1] = 10.0
	ttStd[0][1] = 2.0

	// 0->2: 45 min, 50 km, reachable
	meanTT[0][2] = 45
	reach[0][2] = 1.0
	dist[0][2] = 50.0
	ttStd[0][2] = 5.0

	// 1->0: 20 min, 10 km, reachable
	meanTT[1][0] = 20
	reach[1][0] = 1.0
	dist[1][0] = 10.0
	ttStd[1][0] = 3.0

	// 1->2: 60 min, 40 km, reachable
	meanTT[1][2] = 60
	reach[1][2] = 1.0
	dist[1][2] = 40.0
	ttStd[1][2] = 8.0

	// 2->0: 30 min, 50 km, reachable
	meanTT[2][0] = 30
	reach[2][0] = 1.0
	dist[2][0] = 50.0
	ttStd[2][0] = 4.0

	// 2->1: unreachable (reachability 0)
	meanTT[2][1] = 80
	reach[2][1] = 0.0
	dist[2][1] = 40.0

	metrics := &ODMetrics{
		MeanTravelTime: meanTT,
		Reachability:   reach,
		DistancesKM:    dist,
		TravelTimeStd:  ttStd,
	}

	tqi := &TQIResult{
		TQI:           55.0,
		CoverageScore: 60.0,
		SpeedScore:    50.0,
		TimeProfile: []TimeSlotScore{
			{Label: "07:00", Score: 60.0},
			{Label: "09:00", Score: 70.0},
			{Label: "12:00", Score: 45.0},
			{Label: "17:00", Score: 65.0},
		},
		ReliabilityCV:        0.15,
		ReliabilityPerOrigin: []float64{0.1, 0.3, 0.5, 0.2, 0.4, 0.05, 0.35, 0.25},
	}

	ptal := &PTALResult{
		Values: []float64{10.0, 5.0, 1.0},
		Grades: []string{"6a", "4", "1a"},
	}

	da := ComputeDetailedAnalysis(points, metrics, tqi, ptal, stopLats, stopLons)

	// Coverage checks.
	if da.NOriginsWithService != 2 {
		t.Errorf("NOriginsWithService = %d, want 2", da.NOriginsWithService)
	}
	if da.NTransitDesertOrigins != 1 {
		t.Errorf("NTransitDesertOrigins = %d, want 1", da.NTransitDesertOrigins)
	}

	// Peak / lowest slot.
	if da.PeakSlot != "09:00" {
		t.Errorf("PeakSlot = %q, want \"09:00\"", da.PeakSlot)
	}
	if da.LowestSlot != "12:00" {
		t.Errorf("LowestSlot = %q, want \"12:00\"", da.LowestSlot)
	}

	// Top origins: should have 3 entries (one per point).
	if len(da.TopOrigins) != 3 {
		t.Errorf("len(TopOrigins) = %d, want 3", len(da.TopOrigins))
	}

	// PTAL distribution.
	if da.PTALDistribution["6a"] != 1 || da.PTALDistribution["4"] != 1 || da.PTALDistribution["1a"] != 1 {
		t.Errorf("PTALDistribution = %v, want each grade count = 1", da.PTALDistribution)
	}

	// TSR should be positive.
	if da.MeanTSR <= 0 {
		t.Errorf("MeanTSR = %f, want > 0", da.MeanTSR)
	}

	// Reliability histogram should have bins.
	if len(da.ReliabilityHistogram.Labels) == 0 {
		t.Error("ReliabilityHistogram has no bins")
	}
	if len(da.ReliabilityHistogram.Counts) != len(da.ReliabilityHistogram.Labels) {
		t.Error("ReliabilityHistogram labels/counts length mismatch")
	}

	// Reachable pairs: 5 out of 6 valid pairs (2->1 is valid but not reachable).
	if da.NReachablePairs != 5 {
		t.Errorf("NReachablePairs = %d, want 5", da.NReachablePairs)
	}
	if da.NValidPairs != 6 {
		t.Errorf("NValidPairs = %d, want 6", da.NValidPairs)
	}
}
