package equity

import (
	"encoding/json"
	"math"
	"os"

	"github.com/jasondyck/chwk-tqi/internal/grid"
)

// Result holds equity overlay data.
type Result struct {
	GeoJSON     json.RawMessage `json:"geojson"`
	Correlation float64         `json:"tqi_income_correlation"`
}

// Compute loads DA boundaries and income data, cross-references with grid TQI
// scores, and returns GeoJSON with TQI and income properties per DA.
//
// boundaryPath: GeoJSON file with DA polygons (properties must include "DGUID")
// incomePath: JSON file mapping DGUID -> {median_income, population}
func Compute(boundaryPath, incomePath string, points []grid.Point, gridScores []float64) (*Result, error) {
	boundaryData, err := os.ReadFile(boundaryPath)
	if err != nil {
		return nil, err
	}

	var fc struct {
		Type     string            `json:"type"`
		Features []json.RawMessage `json:"features"`
	}
	if err := json.Unmarshal(boundaryData, &fc); err != nil {
		return nil, err
	}

	incomeData, err := os.ReadFile(incomePath)
	if err != nil {
		return nil, err
	}
	var incomeMap map[string]struct {
		MedianIncome float64 `json:"median_income"`
		Population   int     `json:"population"`
	}
	if err := json.Unmarshal(incomeData, &incomeMap); err != nil {
		return nil, err
	}

	type enriched struct {
		raw     json.RawMessage
		meanTQI float64
		income  float64
	}
	var results []enriched
	var tqiVals, incomeVals []float64

	for _, rawFeature := range fc.Features {
		var f struct {
			Properties struct {
				DGUID string `json:"DGUID"`
			} `json:"properties"`
			Geometry struct {
				Coordinates json.RawMessage `json:"coordinates"`
			} `json:"geometry"`
		}
		if err := json.Unmarshal(rawFeature, &f); err != nil {
			continue
		}

		inc, ok := incomeMap[f.Properties.DGUID]
		if !ok {
			continue
		}

		bbox := extractBBox(f.Geometry.Coordinates)
		if bbox == nil {
			continue
		}

		var tqiSum float64
		var count int
		for i, pt := range points {
			if pt.Lat >= bbox[1] && pt.Lat <= bbox[3] &&
				pt.Lon >= bbox[0] && pt.Lon <= bbox[2] {
				if i < len(gridScores) {
					tqiSum += gridScores[i]
					count++
				}
			}
		}
		if count == 0 {
			continue
		}
		meanTQI := tqiSum / float64(count)

		results = append(results, enriched{raw: rawFeature, meanTQI: meanTQI, income: inc.MedianIncome})
		tqiVals = append(tqiVals, meanTQI)
		incomeVals = append(incomeVals, inc.MedianIncome)
	}

	corr := pearson(tqiVals, incomeVals)

	var outFeatures []json.RawMessage
	for _, ef := range results {
		var f map[string]json.RawMessage
		json.Unmarshal(ef.raw, &f)
		var props map[string]any
		json.Unmarshal(f["properties"], &props)
		props["mean_tqi"] = ef.meanTQI
		props["median_income"] = ef.income
		propsBytes, _ := json.Marshal(props)
		f["properties"] = propsBytes
		featBytes, _ := json.Marshal(f)
		outFeatures = append(outFeatures, featBytes)
	}

	outFC := struct {
		Type     string            `json:"type"`
		Features []json.RawMessage `json:"features"`
	}{Type: "FeatureCollection", Features: outFeatures}

	geojsonBytes, _ := json.Marshal(outFC)

	return &Result{
		GeoJSON:     json.RawMessage(geojsonBytes),
		Correlation: corr,
	}, nil
}

func extractBBox(coords json.RawMessage) []float64 {
	var all [][]float64
	var raw any
	json.Unmarshal(coords, &raw)
	flattenCoords(raw, &all)
	if len(all) == 0 {
		return nil
	}
	minLon, minLat := all[0][0], all[0][1]
	maxLon, maxLat := minLon, minLat
	for _, c := range all[1:] {
		if c[0] < minLon {
			minLon = c[0]
		}
		if c[0] > maxLon {
			maxLon = c[0]
		}
		if c[1] < minLat {
			minLat = c[1]
		}
		if c[1] > maxLat {
			maxLat = c[1]
		}
	}
	return []float64{minLon, minLat, maxLon, maxLat}
}

func flattenCoords(v any, out *[][]float64) {
	arr, ok := v.([]any)
	if !ok || len(arr) == 0 {
		return
	}
	if _, isNum := arr[0].(float64); isNum && len(arr) >= 2 {
		coord := make([]float64, len(arr))
		for i, x := range arr {
			coord[i] = x.(float64)
		}
		*out = append(*out, coord)
		return
	}
	for _, item := range arr {
		flattenCoords(item, out)
	}
}

func pearson(x, y []float64) float64 {
	n := len(x)
	if n < 2 || len(y) != n {
		return 0
	}
	mx, my := 0.0, 0.0
	for i := range x {
		mx += x[i]
		my += y[i]
	}
	mx /= float64(n)
	my /= float64(n)

	var num, dx2, dy2 float64
	for i := range x {
		dx := x[i] - mx
		dy := y[i] - my
		num += dx * dy
		dx2 += dx * dx
		dy2 += dy * dy
	}
	denom := math.Sqrt(dx2 * dy2)
	if denom == 0 {
		return 0
	}
	return num / denom
}
