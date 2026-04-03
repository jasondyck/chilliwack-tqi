package neighbourhood

import (
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// square creates a unit square polygon from (0,0) to (1,1) offset by (lonOff, latOff).
func square(lonOff, latOff float64) [][]float64 {
	return [][]float64{
		{lonOff, latOff},
		{lonOff + 1, latOff},
		{lonOff + 1, latOff + 1},
		{lonOff, latOff + 1},
		{lonOff, latOff}, // closed ring
	}
}

func TestPointInPolygon(t *testing.T) {
	poly := square(0, 0) // (0,0) to (1,1)

	assert.True(t, pointInPolygon(0.5, 0.5, poly), "point inside should return true")
	assert.False(t, pointInPolygon(2.0, 2.0, poly), "point outside should return false")
}

func TestAssignPoints(t *testing.T) {
	neighbourhoods := []Neighbourhood{
		{Name: "A", Population: 100, Polygon: square(0, 0)},   // (0,0)-(1,1)
		{Name: "B", Population: 200, Polygon: square(10, 10)}, // (10,10)-(11,11)
	}

	points := []grid.Point{
		{Lat: 0.5, Lon: 0.5},   // inside A
		{Lat: 10.5, Lon: 10.5}, // inside B
		{Lat: 9.0, Lon: 9.0},   // outside both, nearest to B centroid (10.5,10.5) vs A centroid (0.5,0.5)
	}

	assignments := AssignPoints(neighbourhoods, points)

	require.Len(t, assignments, 3)
	assert.Equal(t, 0, assignments[0], "point should be in neighbourhood A")
	assert.Equal(t, 1, assignments[1], "point should be in neighbourhood B")
	assert.Equal(t, 1, assignments[2], "fallback should assign to nearest (B)")
}

func TestComputeScores(t *testing.T) {
	neighbourhoods := []Neighbourhood{
		{Name: "A", Population: 1000, Polygon: square(0, 0)},
		{Name: "B", Population: 3000, Polygon: square(10, 10)},
	}

	// 4 points: 2 in A (idx 0), 2 in B (idx 1)
	assignments := []int{0, 0, 1, 1}
	gridTQI := []float64{40, 60, 70, 90}
	gridCov := []float64{0.5, 0.7, 0.8, 1.0}
	gridSpd := []float64{10, 20, 30, 40}

	scores, wTQI, wCov, wSpd := ComputeScores(neighbourhoods, assignments, gridTQI, gridCov, gridSpd)

	require.Len(t, scores, 2)

	// A: avg TQI = 50, avg Cov = 0.6, avg Spd = 15
	assert.Equal(t, "A", scores[0].Name)
	assert.InDelta(t, 50.0, scores[0].TQI, 0.001)
	assert.InDelta(t, 0.6, scores[0].CoverageScore, 0.001)
	assert.InDelta(t, 15.0, scores[0].SpeedScore, 0.001)
	assert.Equal(t, 2, scores[0].GridPointCount)

	// B: avg TQI = 80, avg Cov = 0.9, avg Spd = 35
	assert.Equal(t, "B", scores[1].Name)
	assert.InDelta(t, 80.0, scores[1].TQI, 0.001)
	assert.InDelta(t, 0.9, scores[1].CoverageScore, 0.001)
	assert.InDelta(t, 35.0, scores[1].SpeedScore, 0.001)
	assert.Equal(t, 2, scores[1].GridPointCount)

	// Population-weighted: (50*1000 + 80*3000) / 4000 = 290000/4000 = 72.5
	assert.InDelta(t, 72.5, wTQI, 0.001)
	// (0.6*1000 + 0.9*3000) / 4000 = 3300/4000 = 0.825
	assert.InDelta(t, 0.825, wCov, 0.001)
	// (15*1000 + 35*3000) / 4000 = 120000/4000 = 30.0
	assert.InDelta(t, 30.0, wSpd, 0.001)
}

func TestMergeTargets(t *testing.T) {
	neighbourhoods := []Neighbourhood{
		{Name: "Chilliwack Proper", Population: 31410, Polygon: square(0, 0)},
		{Name: "Village West", Population: 0, Polygon: square(2, 0)},
	}

	// 3 points: 2 in Chilliwack Proper (idx 0), 1 in Village West (idx 1)
	assignments := []int{0, 0, 1}
	gridTQI := []float64{50, 60, 70}
	gridCov := []float64{0.5, 0.6, 0.7}
	gridSpd := []float64{10, 20, 30}

	scores, wTQI, _, _ := ComputeScores(neighbourhoods, assignments, gridTQI, gridCov, gridSpd)

	// Only Chilliwack Proper should appear (Village West has pop=0 and is a merge target)
	require.Len(t, scores, 1)
	assert.Equal(t, "Chilliwack Proper", scores[0].Name)

	// All 3 points should be merged into Chilliwack Proper: avg TQI = (50+60+70)/3 = 60
	assert.InDelta(t, 60.0, scores[0].TQI, 0.001)
	assert.Equal(t, 3, scores[0].GridPointCount)

	// Weighted TQI = just Chilliwack Proper's average since it's the only neighbourhood
	assert.InDelta(t, 60.0, wTQI, 0.001)
}
