package grid

import (
	"encoding/json"
	"os"
)

// ── GeoJSON parsing structs (minimal) ──

type geoJSONFile struct {
	Features []geoJSONFeature `json:"features"`
}

type geoJSONFeature struct {
	Geometry geoJSONGeometry `json:"geometry"`
}

type geoJSONGeometry struct {
	Type        string          `json:"type"`
	Coordinates json.RawMessage `json:"coordinates"`
}

// LoadBoundaryRings loads polygon rings from a GeoJSON file.
// It handles both Polygon and MultiPolygon geometry types.
// Returns nil if the file is missing or cannot be parsed.
func LoadBoundaryRings(path string) [][][]float64 {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}

	var gj geoJSONFile
	if err := json.Unmarshal(data, &gj); err != nil {
		return nil
	}

	var rings [][][]float64
	for _, feat := range gj.Features {
		switch feat.Geometry.Type {
		case "Polygon":
			var coords [][][]float64
			if err := json.Unmarshal(feat.Geometry.Coordinates, &coords); err == nil {
				rings = append(rings, coords...)
			}
		case "MultiPolygon":
			var multi [][][][]float64
			if err := json.Unmarshal(feat.Geometry.Coordinates, &multi); err == nil {
				for _, poly := range multi {
					rings = append(rings, poly...)
				}
			}
		}
	}
	return rings
}

// PointInPolygon tests whether (lon, lat) is inside a polygon ring
// using the ray-casting algorithm. Ring coordinates are [lon, lat].
func PointInPolygon(lon, lat float64, ring [][]float64) bool {
	n := len(ring)
	inside := false
	for i, j := 0, n-1; i < n; j, i = i, i+1 {
		xi, yi := ring[i][0], ring[i][1]
		xj, yj := ring[j][0], ring[j][1]
		if ((yi > lat) != (yj > lat)) &&
			(lon < (xj-xi)*(lat-yi)/(yj-yi)+xi) {
			inside = !inside
		}
	}
	return inside
}

// PointInBoundary tests if a geographic point is inside any of the given rings.
func PointInBoundary(lat, lon float64, rings [][][]float64) bool {
	for _, ring := range rings {
		if PointInPolygon(lon, lat, ring) {
			return true
		}
	}
	return false
}
