package scoring

import (
	"math"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestComputeTSR(t *testing.T) {
	// 10 km in 30 min = 20 km/h
	tsr := ComputeTSR(10.0, 30.0)
	assert.InDelta(t, 20.0, tsr, 0.01)
}

func TestComputeTSRUnreachable(t *testing.T) {
	tsr := ComputeTSR(10.0, math.Inf(1))
	assert.Equal(t, 0.0, tsr)
}

func TestValidPairMask(t *testing.T) {
	assert.True(t, IsValidPair(1.0))
	assert.False(t, IsValidPair(0.3))
}

func TestCoverageScore(t *testing.T) {
	// 2x2 all reachability=0.5, dist=2.0
	reach := [][]float64{
		{0, 0.5},
		{0.5, 0},
	}
	dist := [][]float64{
		{0, 2.0},
		{2.0, 0},
	}
	score := ComputeCoverageScore(reach, dist)
	assert.InDelta(t, 50.0, score, 0.01)
}

func TestSpeedScore(t *testing.T) {
	// dist=10, time=30 → TSR=20 → score=(20-5)/(40-5)*100=42.86
	dist := [][]float64{
		{0, 10.0},
		{10.0, 0},
	}
	tt := [][]float64{
		{0, 30.0},
		{30.0, 0},
	}
	score := ComputeSpeedScore(dist, tt)
	assert.InDelta(t, 42.86, score, 0.01)
}

func TestComputeTQI(t *testing.T) {
	metrics := &ODMetrics{
		MeanTravelTime: [][]float64{
			{0, 30.0},
			{30.0, 0},
		},
		Reachability: [][]float64{
			{0, 0.8},
			{0.8, 0},
		},
		TravelTimeStd: [][]float64{
			{0, 5.0},
			{5.0, 0},
		},
		PerSlotCoverage: []float64{0.8, 0.7},
		PerSlotMeanTSR:  []float64{20.0, 18.0},
		DistancesKM: [][]float64{
			{0, 10.0},
			{10.0, 0},
		},
	}
	result := ComputeTQI(metrics)
	require.NotNil(t, result)
	assert.Greater(t, result.TQI, 0.0)
	assert.Greater(t, result.CoverageScore, 0.0)
	assert.Greater(t, result.SpeedScore, 0.0)
}
