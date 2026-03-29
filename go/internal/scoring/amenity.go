package scoring

import (
	"encoding/json"
	"math"
	"os"

	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/grid"
)

// Amenity represents a point of interest.
type Amenity struct {
	Name     string `json:"name"`
	Lat      float64 `json:"lat"`
	Lon      float64 `json:"lon"`
	Category string `json:"category"`
}

// AmenityResult holds accessibility metrics for a single amenity.
type AmenityResult struct {
	Name            string  `json:"name"`
	Category        string  `json:"category"`
	Lat             float64 `json:"lat"`
	Lon             float64 `json:"lon"`
	PctWithin30Min  float64 `json:"pct_within_30_min"`
	PctWithin60Min  float64 `json:"pct_within_60_min"`
	MeanTravelTime  float64 `json:"mean_travel_time"`
}

// LoadAmenities reads amenities from a JSON file.
func LoadAmenities(path string) ([]Amenity, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var amenities []Amenity
	if err := json.Unmarshal(data, &amenities); err != nil {
		return nil, err
	}
	return amenities, nil
}

// ComputeAmenityAccessibility calculates how accessible each amenity is from
// the grid points, using the OD travel time matrix.
func ComputeAmenityAccessibility(points []grid.Point, meanTT, distKM [][]float64, amenities []Amenity) []AmenityResult {
	n := len(points)
	results := make([]AmenityResult, len(amenities))

	for a, am := range amenities {
		// Find nearest grid point to amenity.
		bestIdx := -1
		bestDist := math.MaxFloat64
		for j := 0; j < n; j++ {
			d := geo.Haversine(am.Lat, am.Lon, points[j].Lat, points[j].Lon)
			if d < bestDist {
				bestDist = d
				bestIdx = j
			}
		}

		results[a] = AmenityResult{
			Name:     am.Name,
			Category: am.Category,
			Lat:      am.Lat,
			Lon:      am.Lon,
		}

		if bestIdx < 0 || bestIdx >= len(meanTT) {
			continue
		}

		var within30, within60 int
		var ttSum float64
		var ttCount int

		for i := 0; i < n; i++ {
			if i >= len(meanTT) || bestIdx >= len(meanTT[i]) {
				continue
			}
			tt := meanTT[i][bestIdx]
			if math.IsInf(tt, 1) || tt >= InfFloat {
				continue
			}
			ttSum += tt
			ttCount++
			if tt <= 30 {
				within30++
			}
			if tt <= 60 {
				within60++
			}
		}

		if n > 0 {
			results[a].PctWithin30Min = float64(within30) / float64(n) * 100.0
			results[a].PctWithin60Min = float64(within60) / float64(n) * 100.0
		}
		if ttCount > 0 {
			results[a].MeanTravelTime = ttSum / float64(ttCount)
		}
	}

	return results
}
