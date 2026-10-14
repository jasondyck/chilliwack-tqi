package geo

import (
	"math"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHaversine(t *testing.T) {
	// Vancouver to Seattle ~199 km
	dist := Haversine(49.2827, -123.1207, 47.6062, -122.3321)
	assert.InDelta(t, 195.0, dist, 2.0, "Vancouver to Seattle should be ~195 km")
}

func TestHaversineZero(t *testing.T) {
	dist := Haversine(49.2827, -123.1207, 49.2827, -123.1207)
	assert.Equal(t, 0.0, dist, "Same point should yield 0.0")
}

func TestHaversineMatrix(t *testing.T) {
	lats := []float64{49.2827, 47.6062}
	lons := []float64{-123.1207, -122.3321}

	mat := HaversineMatrix(lats, lons)

	// Diagonal should be zero
	assert.Equal(t, 0.0, mat[0][0])
	assert.Equal(t, 0.0, mat[1][1])

	// Off-diagonal should be positive
	assert.Greater(t, mat[0][1], 0.0)
	assert.Greater(t, mat[1][0], 0.0)

	// Symmetric
	assert.Equal(t, mat[0][1], mat[1][0])
}

func TestProjectToXY(t *testing.T) {
	centerLatRad := deg2rad(49.2827)
	x, y := ProjectToXY(49.2827, -123.1207, centerLatRad)
	// At least one of x, y should be non-zero for a non-origin point
	assert.True(t, x != 0.0 || y != 0.0, "ProjectToXY should produce non-zero output")
}

func TestProjectSliceToXY(t *testing.T) {
	lats := []float64{49.2827, 47.6062}
	lons := []float64{-123.1207, -122.3321}
	centerLatRad := deg2rad(49.2827)

	xs, ys := ProjectSliceToXY(lats, lons, centerLatRad)
	assert.Len(t, xs, 2)
	assert.Len(t, ys, 2)
}

func TestDistance2D(t *testing.T) {
	d := Distance2D(0, 0, 3, 4)
	assert.InDelta(t, 5.0, d, 1e-9)
}

func TestDeg2rad(t *testing.T) {
	assert.InDelta(t, math.Pi, deg2rad(180.0), 1e-9)
}
