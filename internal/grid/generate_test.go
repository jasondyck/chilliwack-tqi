package grid

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestGenerateGrid(t *testing.T) {
	sw := [2]float64{49.10, -122.00}
	ne := [2]float64{49.12, -121.98}
	pts := Generate(sw, ne, 500, "")

	require.True(t, len(pts) > 0, "expected at least one grid point")
	for _, p := range pts {
		assert.GreaterOrEqual(t, p.Lat, sw[0])
		assert.LessOrEqual(t, p.Lat, ne[0])
		assert.GreaterOrEqual(t, p.Lon, sw[1])
		assert.LessOrEqual(t, p.Lon, ne[1])
	}
}

func TestGenerateGridSpacing(t *testing.T) {
	sw := [2]float64{49.10, -122.00}
	ne := [2]float64{49.12, -121.98}
	coarse := Generate(sw, ne, 1000, "")
	fine := Generate(sw, ne, 250, "")

	require.True(t, len(fine) > len(coarse),
		"finer spacing should produce more points (fine=%d, coarse=%d)", len(fine), len(coarse))
}

func TestPointInPolygon(t *testing.T) {
	// Square polygon: (0,0) -> (0,10) -> (10,10) -> (10,0) -> (0,0)
	ring := [][]float64{
		{0, 0}, {0, 10}, {10, 10}, {10, 0}, {0, 0},
	}

	assert.True(t, PointInPolygon(5, 5, ring), "center should be inside")
	assert.True(t, PointInPolygon(1, 1, ring), "near corner should be inside")
	assert.False(t, PointInPolygon(-1, 5, ring), "outside left should be outside")
	assert.False(t, PointInPolygon(15, 5, ring), "far right should be outside")
	assert.False(t, PointInPolygon(5, -1, ring), "below should be outside")
}
