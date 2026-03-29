package grid

import (
	"math"
	"os"

	"github.com/jasondyck/chwk-tqi/internal/config"
)

// Generate creates a grid of points within the bounding box defined by bboxSW
// and bboxNE (each [lat, lon]), with the given spacing in metres.
// If boundaryPath is non-empty and the file exists, points are clipped to the
// boundary polygon.
func Generate(bboxSW, bboxNE [2]float64, spacingM float64, boundaryPath string) []Point {
	centerLat := (bboxSW[0] + bboxNE[0]) / 2.0
	latStep := spacingM / config.EarthRadiusM * (180.0 / math.Pi)
	lonStep := spacingM / (config.EarthRadiusM * math.Cos(centerLat*math.Pi/180.0)) * (180.0 / math.Pi)

	// Load boundary rings if a valid path is provided.
	var rings [][][]float64
	if boundaryPath != "" {
		if _, err := os.Stat(boundaryPath); err == nil {
			rings = LoadBoundaryRings(boundaryPath)
		}
	}

	var pts []Point
	for lat := bboxSW[0]; lat <= bboxNE[0]; lat += latStep {
		for lon := bboxSW[1]; lon <= bboxNE[1]; lon += lonStep {
			if rings != nil && !PointInBoundary(lat, lon, rings) {
				continue
			}
			pts = append(pts, Point{Lat: lat, Lon: lon})
		}
	}
	return pts
}
