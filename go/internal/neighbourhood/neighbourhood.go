package neighbourhood

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"

	"github.com/jasondyck/chwk-tqi/internal/grid"
)

// Neighbourhood represents a geographic neighbourhood with its boundary polygon.
type Neighbourhood struct {
	Name       string
	Population int
	Polygon    [][]float64 // outer ring as [lon, lat] pairs
}

// Score holds per-neighbourhood scoring results.
type Score struct {
	Name           string  `json:"name"`
	Population     int     `json:"population"`
	TQI            float64 `json:"tqi"`
	CoverageScore  float64 `json:"coverage_score"`
	SpeedScore     float64 `json:"speed_score"`
	GridPointCount int     `json:"grid_point_count"`
}

// population2021 contains hardcoded 2021 Census populations keyed by GeoJSON NAME field.
var population2021 = map[string]int{
	"Chilliwack Proper":  31410,
	"Vedder":             22620,
	"Promontory":         11820,
	"Sardis":             10010,
	"Rosedale":           5700,
	"Fairfield":          4220,
	"Eastern Hillsides":  3450,
	"Yarrow":             3380,
	"Greendale":          3110,
	"Chilliwack Mountain": 2510,
	"Ryder Lake":         1290,
	"Little Mountain":    1170,
	"Village West":       0,
	"Cattermole":         0,
}

// mergeTargets maps small areas into a parent neighbourhood for scoring.
var mergeTargets = map[string]string{
	"Village West": "Chilliwack Proper",
	"Cattermole":   "Chilliwack Proper",
}

// geoJSON types for parsing
type featureCollection struct {
	Type     string          `json:"type"`
	Features []feature       `json:"features"`
	Name     string          `json:"name,omitempty"`
}

type feature struct {
	Type       string          `json:"type"`
	Geometry   geometry        `json:"geometry"`
	Properties map[string]interface{} `json:"properties"`
}

type geometry struct {
	Type        string          `json:"type"`
	Coordinates json.RawMessage `json:"coordinates"`
}

// LoadBoundaries parses the GeoJSON file and returns neighbourhoods plus the raw GeoJSON for the frontend.
func LoadBoundaries(path string) ([]Neighbourhood, json.RawMessage, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, nil, fmt.Errorf("read boundaries: %w", err)
	}

	var fc featureCollection
	if err := json.Unmarshal(data, &fc); err != nil {
		return nil, nil, fmt.Errorf("parse boundaries: %w", err)
	}

	var neighbourhoods []Neighbourhood
	for _, feat := range fc.Features {
		name, _ := feat.Properties["NAME"].(string)
		if name == "" {
			continue
		}

		pop := population2021[name]

		// Parse polygon coordinates.
		// Polygon: [ring][point][lon,lat]
		// MultiPolygon: [polygon][ring][point][lon,lat]
		var outerRing [][]float64
		if feat.Geometry.Type == "MultiPolygon" {
			var multi [][][][]float64
			if err := json.Unmarshal(feat.Geometry.Coordinates, &multi); err != nil {
				log.Printf("skip MultiPolygon %s: %v", name, err)
				continue
			}
			for _, poly := range multi {
				if len(poly) > 0 && len(poly[0]) > len(outerRing) {
					ring := make([][]float64, len(poly[0]))
					for i, pt := range poly[0] {
						ring[i] = []float64{pt[0], pt[1]}
					}
					outerRing = ring
				}
			}
		} else {
			var rings [][][]float64
			if err := json.Unmarshal(feat.Geometry.Coordinates, &rings); err != nil {
				log.Printf("skip Polygon %s: %v", name, err)
				continue
			}
			if len(rings) > 0 {
				outerRing = make([][]float64, len(rings[0]))
				for i, pt := range rings[0] {
					outerRing[i] = []float64{pt[0], pt[1]}
				}
			}
		}
		if len(outerRing) == 0 {
			continue
		}

		neighbourhoods = append(neighbourhoods, Neighbourhood{
			Name:       name,
			Population: pop,
			Polygon:    outerRing,
		})
	}

	return neighbourhoods, json.RawMessage(data), nil
}

// AssignPoints assigns each grid point to a neighbourhood using point-in-polygon,
// with fallback to nearest centroid. Returns a slice of neighbourhood indices.
func AssignPoints(neighbourhoods []Neighbourhood, points []grid.Point) []int {
	assignments := make([]int, len(points))
	for i, pt := range points {
		assigned := -1
		for j, n := range neighbourhoods {
			if pointInPolygon(pt.Lon, pt.Lat, n.Polygon) {
				assigned = j
				break
			}
		}
		if assigned == -1 {
			assigned = findNearest(pt, neighbourhoods)
		}
		assignments[i] = assigned
	}
	return assignments
}

// ComputeScores calculates per-neighbourhood averages and population-weighted city totals.
// Returns (scores, weightedTQI, weightedCoverage, weightedSpeed).
func ComputeScores(
	neighbourhoods []Neighbourhood,
	assignments []int,
	gridTQI []float64,
	gridCoverage []float64,
	gridSpeed []float64,
) ([]Score, float64, float64, float64) {
	type accumulator struct {
		tqiSum      float64
		covSum      float64
		spdSum      float64
		count       int
	}

	accum := make(map[string]*accumulator)

	for i, idx := range assignments {
		if idx < 0 || idx >= len(neighbourhoods) {
			continue
		}
		n := neighbourhoods[idx]

		// Determine the target neighbourhood name (apply merge)
		targetName := n.Name
		if merged, ok := mergeTargets[n.Name]; ok {
			targetName = merged
		}

		if _, ok := accum[targetName]; !ok {
			accum[targetName] = &accumulator{}
		}
		a := accum[targetName]
		a.tqiSum += gridTQI[i]
		a.covSum += gridCoverage[i]
		a.spdSum += gridSpeed[i]
		a.count++
	}

	var scores []Score
	var totalPop int
	var wTQI, wCov, wSpd float64

	for _, n := range neighbourhoods {
		// Skip merge sources and zero-population neighbourhoods
		if _, isMergeSource := mergeTargets[n.Name]; isMergeSource {
			continue
		}
		if n.Population <= 0 {
			continue
		}

		a, ok := accum[n.Name]
		if !ok || a.count == 0 {
			continue
		}

		avgTQI := a.tqiSum / float64(a.count)
		avgCov := a.covSum / float64(a.count)
		avgSpd := a.spdSum / float64(a.count)

		scores = append(scores, Score{
			Name:           n.Name,
			Population:     n.Population,
			TQI:            avgTQI,
			CoverageScore:  avgCov,
			SpeedScore:     avgSpd,
			GridPointCount: a.count,
		})

		pop := float64(n.Population)
		totalPop += n.Population
		wTQI += avgTQI * pop
		wCov += avgCov * pop
		wSpd += avgSpd * pop
	}

	if totalPop > 0 {
		tp := float64(totalPop)
		wTQI /= tp
		wCov /= tp
		wSpd /= tp
	}

	return scores, wTQI, wCov, wSpd
}

// pointInPolygon uses the ray-casting algorithm to test if a point is inside a polygon.
// Polygon coords are [lon, lat] pairs (GeoJSON order).
func pointInPolygon(lon, lat float64, polygon [][]float64) bool {
	n := len(polygon)
	inside := false
	for i, j := 0, n-1; i < n; j, i = i, i+1 {
		xi, yi := polygon[i][0], polygon[i][1]
		xj, yj := polygon[j][0], polygon[j][1]

		if ((yi > lat) != (yj > lat)) &&
			(lon < (xj-xi)*(lat-yi)/(yj-yi)+xi) {
			inside = !inside
		}
	}
	return inside
}

// findNearest returns the index of the neighbourhood whose centroid is nearest to the point.
func findNearest(pt grid.Point, neighbourhoods []Neighbourhood) int {
	best := 0
	bestDist := math.MaxFloat64
	for i, n := range neighbourhoods {
		cx, cy := centroid(n.Polygon)
		dx := pt.Lon - cx
		dy := pt.Lat - cy
		d := dx*dx + dy*dy
		if d < bestDist {
			bestDist = d
			best = i
		}
	}
	return best
}

// centroid calculates the centroid of a polygon (simple average of vertices).
func centroid(polygon [][]float64) (lon, lat float64) {
	n := float64(len(polygon))
	if n == 0 {
		return 0, 0
	}
	for _, pt := range polygon {
		lon += pt[0]
		lat += pt[1]
	}
	return lon / n, lat / n
}
