// Package isochrone computes travel-time isochrone GeoJSON from RAPTOR results.
package isochrone

import (
	"encoding/json"
	"fmt"
	"math"

	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/raptor"
)

// Result holds one isochrone computation (for a single departure time).
type Result struct {
	DepartureTime string          `json:"departure_time"`
	Label         string          `json:"label"`
	GeoJSON       json.RawMessage `json:"geojson"`
}

type band struct {
	minMin float64
	maxMin float64
	color  string
	label  string
}

var defaultBands = []band{
	{0, 15, "#2e7d32", "0-15 min"},
	{15, 30, "#4caf50", "15-30 min"},
	{30, 45, "#ff9800", "30-45 min"},
	{45, 60, "#f44336", "45-60 min"},
	{60, 90, "#b71c1c", "60-90 min"},
}

const (
	walkSpeedMPerMin = 80.0  // matches PTAL config
	maxWalkM         = 1000.0
	maxTransfers     = 2
)

// Compute generates isochrone GeoJSON for a single departure time.
//
// It finds the nearest stop to (originLat, originLon), runs RAPTOR from that
// stop, then for each grid point computes total travel time = RAPTOR arrival
// at nearest stop + walk time from stop to grid point. Grid points are grouped
// into time bands and returned as a GeoJSON FeatureCollection.
func Compute(
	tt *raptor.Timetable,
	originLat, originLon float64,
	departureMins int,
	points []grid.Point,
	stopLats, stopLons []float64,
	spacingM float64,
) (*Result, error) {
	nStops := len(stopLats)
	if nStops == 0 {
		return nil, fmt.Errorf("no stops available")
	}

	// 1. Find nearest stop to origin.
	bestDist := math.MaxFloat64
	bestStop := 0
	for i := 0; i < nStops; i++ {
		d := geo.Haversine(originLat, originLon, stopLats[i], stopLons[i])
		if d < bestDist {
			bestDist = d
			bestStop = i
		}
	}

	// 2. Run RAPTOR from that stop.
	ft := raptor.Flatten(tt)
	depTime := float64(departureMins)
	maxTime := depTime + 90.0 // 90 min max travel
	sources := []raptor.SourceStop{{StopIdx: bestStop, ArrivalTime: depTime}}
	arrivals := raptor.RunRAPTOR(ft, sources, maxTransfers, maxTime)

	// 3. For each grid point, find nearest stop and compute total travel time.
	travelMins := make([]float64, len(points))
	for i, pt := range points {
		bestTT := math.MaxFloat64
		for j := 0; j < nStops; j++ {
			if arrivals[j] >= raptor.Inf {
				continue
			}
			distKM := geo.Haversine(pt.Lat, pt.Lon, stopLats[j], stopLons[j])
			distM := distKM * 1000.0
			if distM > maxWalkM {
				continue
			}
			walkMin := distM / walkSpeedMPerMin
			totalMin := (arrivals[j] - depTime) + walkMin
			if totalMin < bestTT {
				bestTT = totalMin
			}
		}
		travelMins[i] = bestTT
	}

	// 4. Group grid points into bands and build GeoJSON.
	halfLatDeg := spacingM / 111320.0 / 2.0
	cosLat := math.Cos(originLat * math.Pi / 180.0)
	halfLonDeg := spacingM / (111320.0 * cosLat) / 2.0

	type geoFeature struct {
		Type       string         `json:"type"`
		Properties map[string]any `json:"properties"`
		Geometry   geoGeometry    `json:"geometry"`
	}
	type featureCollection struct {
		Type     string       `json:"type"`
		Features []geoFeature `json:"features"`
	}

	fc := featureCollection{Type: "FeatureCollection"}

	for _, b := range defaultBands {
		// MultiPolygon coords: [polygon_idx][ring_idx][point_idx][lon,lat]
		var multiPoly [][][][2]float64
		for i, pt := range points {
			tt := travelMins[i]
			if tt >= b.minMin && tt < b.maxMin {
				ring := [][2]float64{
					{pt.Lon - halfLonDeg, pt.Lat - halfLatDeg},
					{pt.Lon + halfLonDeg, pt.Lat - halfLatDeg},
					{pt.Lon + halfLonDeg, pt.Lat + halfLatDeg},
					{pt.Lon - halfLonDeg, pt.Lat + halfLatDeg},
					{pt.Lon - halfLonDeg, pt.Lat - halfLatDeg}, // close ring
				}
				// Each polygon is an array of rings; we have one ring per cell.
				multiPoly = append(multiPoly, [][][2]float64{ring})
			}
		}

		if len(multiPoly) == 0 {
			continue
		}

		feat := geoFeature{
			Type: "Feature",
			Properties: map[string]any{
				"band":  b.label,
				"color": b.color,
				"min":   b.minMin,
				"max":   b.maxMin,
			},
			Geometry: geoGeometry{
				Type:        "MultiPolygon",
				Coordinates: multiPoly,
			},
		}
		fc.Features = append(fc.Features, feat)
	}

	geojsonBytes, err := json.Marshal(fc)
	if err != nil {
		return nil, fmt.Errorf("marshal geojson: %w", err)
	}

	// Format label.
	hours := departureMins / 60
	mins := departureMins % 60
	timeStr := fmt.Sprintf("%02d:%02d", hours, mins)
	label := "Midday"
	if departureMins < 600 {
		label = "AM Peak"
	}

	return &Result{
		DepartureTime: timeStr,
		Label:         label,
		GeoJSON:       json.RawMessage(geojsonBytes),
	}, nil
}

// geoGeometry is a minimal GeoJSON geometry.
type geoGeometry struct {
	Type        string          `json:"type"`
	Coordinates [][][][2]float64 `json:"coordinates"`
}
