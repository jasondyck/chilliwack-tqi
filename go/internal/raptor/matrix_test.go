package raptor

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/scoring"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestComputeMatrix(t *testing.T) {
	feed := testFeed()
	tt := BuildTimetable(feed)

	// 3 stops at 49.15, 49.16, 49.17 lat, all -121.95 lon
	stopLats := []float64{49.15, 49.16, 49.17}
	stopLons := []float64{-121.95, -121.95, -121.95}

	// 2 grid points near the first two stops
	points := []grid.Point{
		{Lat: 49.1505, Lon: -121.9505},
		{Lat: 49.1605, Lon: -121.9505},
	}

	departureTimes := []int{480}

	m := ComputeMatrix(tt, points, stopLats, stopLons, departureTimes, 1, nil)

	require.NotNil(t, m)
	// MeanTravelTime should be nPoints x nPoints
	require.Len(t, m.MeanTravelTime, 2)
	require.Len(t, m.MeanTravelTime[0], 2)
	require.Len(t, m.MeanTravelTime[1], 2)

	// Reachability same shape
	require.Len(t, m.Reachability, 2)
	require.Len(t, m.Reachability[0], 2)

	// TravelTimeStd same shape
	require.Len(t, m.TravelTimeStd, 2)
	require.Len(t, m.TravelTimeStd[0], 2)

	// DistancesKM same shape
	require.Len(t, m.DistancesKM, 2)
	require.Len(t, m.DistancesKM[0], 2)

	// PerSlotCoverage: len = nDepartures
	require.Len(t, m.PerSlotCoverage, 1)
	// PerSlotMeanTSR: len = nDepartures
	require.Len(t, m.PerSlotMeanTSR, 1)

	// Self distances should be 0
	assert.Equal(t, 0.0, m.DistancesKM[0][0])
	assert.Equal(t, 0.0, m.DistancesKM[1][1])
}

func TestComputeMatrixSelfDistance(t *testing.T) {
	feed := testFeed()
	tt := BuildTimetable(feed)

	stopLats := []float64{49.15, 49.16, 49.17}
	stopLons := []float64{-121.95, -121.95, -121.95}

	// 1 grid point near stop S1
	points := []grid.Point{
		{Lat: 49.1505, Lon: -121.9505},
	}

	departureTimes := []int{480}

	m := ComputeMatrix(tt, points, stopLats, stopLons, departureTimes, 1, nil)

	require.NotNil(t, m)
	require.Len(t, m.DistancesKM, 1)
	require.Len(t, m.DistancesKM[0], 1)
	assert.Equal(t, 0.0, m.DistancesKM[0][0])
}

func TestSaveLoadCache(t *testing.T) {
	dir := t.TempDir()
	feedHash := "abc123def456789"

	m := &scoring.ODMetrics{
		MeanTravelTime:  [][]float64{{1.0, 2.0}, {3.0, 4.0}},
		Reachability:    [][]float64{{0.5, 1.0}, {1.0, 0.5}},
		TravelTimeStd:   [][]float64{{0.1, 0.2}, {0.3, 0.4}},
		PerSlotCoverage: []float64{0.8},
		PerSlotMeanTSR:  []float64{15.0},
		DistancesKM:     [][]float64{{0.0, 1.5}, {1.5, 0.0}},
	}

	err := SaveCache(dir, feedHash, 2, m)
	require.NoError(t, err)

	// Verify file exists
	expected := filepath.Join(dir, "od_metrics_abc123def456_2.gob")
	_, err = os.Stat(expected)
	require.NoError(t, err)

	loaded, err := LoadCache(dir, feedHash, 2)
	require.NoError(t, err)
	require.NotNil(t, loaded)

	assert.Equal(t, m.MeanTravelTime, loaded.MeanTravelTime)
	assert.Equal(t, m.Reachability, loaded.Reachability)
	assert.Equal(t, m.PerSlotCoverage, loaded.PerSlotCoverage)
	assert.Equal(t, m.PerSlotMeanTSR, loaded.PerSlotMeanTSR)
	assert.Equal(t, m.DistancesKM, loaded.DistancesKM)
}

func TestLoadCacheMissing(t *testing.T) {
	dir := t.TempDir()
	loaded, err := LoadCache(dir, "nonexistent", 5)
	require.Error(t, err)
	assert.Nil(t, loaded)
}
