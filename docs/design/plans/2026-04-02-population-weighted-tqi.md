# Population-Weighted TQI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the uniform grid-average TQI with a population-weighted score by neighbourhood, and add a per-neighbourhood breakdown table to the dashboard.

**Architecture:** Load Chilliwack neighbourhood boundary polygons (GeoJSON, 14 features), assign each grid point to a neighbourhood via point-in-polygon, compute per-neighbourhood TQI averages, then produce a population-weighted city-wide score. Frontend renders a neighbourhood score table and boundary overlay on the heat map.

**Tech Stack:** Go, React 19, Recharts, Leaflet/react-leaflet, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-04-02-population-weighted-tqi-design.md`

---

## File Structure

### Go (new files)
- `go/internal/neighbourhood/neighbourhood.go` — boundary loading, point-in-polygon, population data, scoring
- `go/internal/neighbourhood/neighbourhood_test.go` — tests

### Go (modified files)
- `go/internal/api/server.go` — add NeighbourhoodScore type, fields to PipelineResults
- `go/cmd/tqi/main.go` — wire neighbourhood scoring into pipeline

### React (new files)
- `go/web/src/components/NeighbourhoodTable.tsx` — per-neighbourhood score table

### React (modified files)
- `go/web/src/lib/types.ts` — add NeighbourhoodScore type, update PipelineResponse
- `go/web/src/App.tsx` — add NeighbourhoodTable, pass boundary data to HeatMap
- `go/web/src/components/HeatMap.tsx` — add neighbourhood boundary polygon layer
- `go/web/src/components/Hero.tsx` — update subtitle to indicate population-weighted

### Data
- `data/neighbourhoods.geojson` — already downloaded (14 polygon features, property key: `NAME`)

---

## Name Mapping

The GeoJSON has 14 neighbourhoods with `NAME` property. The census data uses different names. Mapping:

| GeoJSON NAME | Census Name | 2021 Population |
|---|---|---|
| Chilliwack Proper | Downtown | 31,410 |
| Vedder | Vedder | 22,620 |
| Promontory | Promontory | 11,820 |
| Sardis | Sardis | 10,010 |
| Rosedale | Rosedale | 5,700 |
| Fairfield | Fairfield Island | 4,220 |
| Eastern Hillsides | Eastern Hillsides | 3,450 |
| Yarrow | Yarrow | 3,380 |
| Greendale | Greendale | 3,110 |
| Chilliwack Mountain | Chilliwack Mountain | 2,510 |
| Ryder Lake | Ryder Lake | 1,290 |
| Little Mountain | Little Mountain | 1,170 |
| Village West | (not in census — include in Downtown) | 0 |
| Cattermole | (not in census — include in Downtown) | 0 |

Village West and Cattermole are small areas adjacent to Downtown that the census groups together. Grid points in these areas should contribute to the Downtown neighbourhood score.

---

## Task 1: Neighbourhood Package — Types, Population Data, Point-in-Polygon

**Files:**
- Create: `go/internal/neighbourhood/neighbourhood.go`
- Create: `go/internal/neighbourhood/neighbourhood_test.go`

- [ ] **Step 1: Create `go/internal/neighbourhood/neighbourhood.go`**

```go
package neighbourhood

import (
	"encoding/json"
	"math"
	"os"

	"github.com/jasondyck/chwk-tqi/internal/grid"
)

// Neighbourhood represents a named area with a polygon boundary and population.
type Neighbourhood struct {
	Name       string
	Population int
	Polygon    [][]float64 // [][lon, lat] — outer ring only
}

// Score holds computed TQI metrics for one neighbourhood.
type Score struct {
	Name           string  `json:"name"`
	Population     int     `json:"population"`
	TQI            float64 `json:"tqi"`
	CoverageScore  float64 `json:"coverage_score"`
	SpeedScore     float64 `json:"speed_score"`
	GridPointCount int     `json:"grid_point_count"`
}

// population2021 maps GeoJSON NAME to 2021 Census population.
// Village West and Cattermole are grouped with Chilliwack Proper (Downtown).
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

// mergeTargets maps zero-population neighbourhoods to the neighbourhood
// whose score they should contribute to.
var mergeTargets = map[string]string{
	"Village West": "Chilliwack Proper",
	"Cattermole":   "Chilliwack Proper",
}

// LoadBoundaries reads a GeoJSON file of neighbourhood polygons.
func LoadBoundaries(path string) ([]Neighbourhood, json.RawMessage, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, nil, err
	}

	var fc struct {
		Type     string `json:"type"`
		Features []struct {
			Properties struct {
				NAME string `json:"NAME"`
			} `json:"properties"`
			Geometry struct {
				Type        string          `json:"type"`
				Coordinates json.RawMessage `json:"coordinates"`
			} `json:"geometry"`
		} `json:"features"`
	}
	if err := json.Unmarshal(data, &fc); err != nil {
		return nil, nil, err
	}

	var neighbourhoods []Neighbourhood
	for _, f := range fc.Features {
		// Parse outer ring of polygon
		var coords [][][]float64 // [ring][point][lon,lat]
		if f.Geometry.Type == "Polygon" {
			json.Unmarshal(f.Geometry.Coordinates, &coords)
		} else if f.Geometry.Type == "MultiPolygon" {
			var multi [][][][]float64
			json.Unmarshal(f.Geometry.Coordinates, &multi)
			if len(multi) > 0 {
				coords = multi[0]
			}
		}
		if len(coords) == 0 || len(coords[0]) == 0 {
			continue
		}

		// Flatten to [][lon, lat]
		ring := make([][]float64, len(coords[0]))
		for i, pt := range coords[0] {
			ring[i] = pt
		}

		pop := population2021[f.Properties.NAME]
		neighbourhoods = append(neighbourhoods, Neighbourhood{
			Name:       f.Properties.NAME,
			Population: pop,
			Polygon:    ring,
		})
	}

	return neighbourhoods, json.RawMessage(data), nil
}

// AssignPoints returns a slice mapping each grid point index to a neighbourhood
// index. Points outside all polygons are assigned to the nearest neighbourhood
// centroid.
func AssignPoints(neighbourhoods []Neighbourhood, points []grid.Point) []int {
	assignments := make([]int, len(points))
	for i, pt := range points {
		idx := -1
		for j, nb := range neighbourhoods {
			if pointInPolygon(pt.Lon, pt.Lat, nb.Polygon) {
				idx = j
				break
			}
		}
		if idx < 0 {
			idx = findNearest(neighbourhoods, pt.Lat, pt.Lon)
		}
		assignments[i] = idx
	}
	return assignments
}

// ComputeScores computes per-neighbourhood TQI, coverage, and speed averages,
// then returns neighbourhood scores and a population-weighted city-wide TQI.
func ComputeScores(
	neighbourhoods []Neighbourhood,
	assignments []int,
	gridTQI []float64,
	gridCoverage []float64,
	gridSpeed []float64,
) (scores []Score, weightedTQI, weightedCoverage, weightedSpeed float64) {
	type accum struct {
		tqiSum, covSum, spdSum float64
		count                  int
	}

	// Accumulate per-neighbourhood, merging Village West/Cattermole into Chilliwack Proper
	byName := make(map[string]*accum)
	for i, nbIdx := range assignments {
		if nbIdx < 0 || nbIdx >= len(neighbourhoods) {
			continue
		}
		name := neighbourhoods[nbIdx].Name
		// Merge zero-population areas
		if target, ok := mergeTargets[name]; ok {
			name = target
		}
		if byName[name] == nil {
			byName[name] = &accum{}
		}
		a := byName[name]
		if i < len(gridTQI) {
			a.tqiSum += gridTQI[i]
		}
		if i < len(gridCoverage) {
			a.covSum += gridCoverage[i]
		}
		if i < len(gridSpeed) {
			a.spdSum += gridSpeed[i]
		}
		a.count++
	}

	// Build scores for neighbourhoods with population > 0
	var totalPop int
	for _, nb := range neighbourhoods {
		if nb.Population == 0 {
			continue
		}
		a := byName[nb.Name]
		if a == nil || a.count == 0 {
			scores = append(scores, Score{
				Name:       nb.Name,
				Population: nb.Population,
			})
			continue
		}
		s := Score{
			Name:           nb.Name,
			Population:     nb.Population,
			TQI:            a.tqiSum / float64(a.count),
			CoverageScore:  a.covSum / float64(a.count),
			SpeedScore:     a.spdSum / float64(a.count),
			GridPointCount: a.count,
		}
		scores = append(scores, s)
		weightedTQI += s.TQI * float64(nb.Population)
		weightedCoverage += s.CoverageScore * float64(nb.Population)
		weightedSpeed += s.SpeedScore * float64(nb.Population)
		totalPop += nb.Population
	}

	if totalPop > 0 {
		weightedTQI /= float64(totalPop)
		weightedCoverage /= float64(totalPop)
		weightedSpeed /= float64(totalPop)
	}

	return scores, weightedTQI, weightedCoverage, weightedSpeed
}

// pointInPolygon uses ray-casting to test if (x, y) is inside the polygon.
// polygon is [][lon, lat].
func pointInPolygon(x, y float64, polygon [][]float64) bool {
	n := len(polygon)
	inside := false
	j := n - 1
	for i := 0; i < n; i++ {
		xi, yi := polygon[i][0], polygon[i][1]
		xj, yj := polygon[j][0], polygon[j][1]
		if ((yi > y) != (yj > y)) && (x < (xj-xi)*(y-yi)/(yj-yi)+xi) {
			inside = !inside
		}
		j = i
	}
	return inside
}

func findNearest(neighbourhoods []Neighbourhood, lat, lon float64) int {
	best := 0
	bestDist := math.MaxFloat64
	for i, nb := range neighbourhoods {
		cx, cy := centroid(nb.Polygon)
		dx := lon - cx
		dy := lat - cy
		d := dx*dx + dy*dy
		if d < bestDist {
			bestDist = d
			best = i
		}
	}
	return best
}

func centroid(polygon [][]float64) (lon, lat float64) {
	for _, pt := range polygon {
		lon += pt[0]
		lat += pt[1]
	}
	n := float64(len(polygon))
	if n > 0 {
		lon /= n
		lat /= n
	}
	return
}
```

- [ ] **Step 2: Create `go/internal/neighbourhood/neighbourhood_test.go`**

```go
package neighbourhood

import (
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/grid"
)

func TestPointInPolygon(t *testing.T) {
	// Simple square: (0,0) to (10,10)
	square := [][]float64{{0, 0}, {10, 0}, {10, 10}, {0, 10}, {0, 0}}

	if !pointInPolygon(5, 5, square) {
		t.Error("(5,5) should be inside square")
	}
	if pointInPolygon(15, 5, square) {
		t.Error("(15,5) should be outside square")
	}
	if pointInPolygon(-1, -1, square) {
		t.Error("(-1,-1) should be outside square")
	}
}

func TestAssignPoints(t *testing.T) {
	nbs := []Neighbourhood{
		{Name: "A", Population: 1000, Polygon: [][]float64{{0, 0}, {10, 0}, {10, 10}, {0, 10}, {0, 0}}},
		{Name: "B", Population: 2000, Polygon: [][]float64{{10, 0}, {20, 0}, {20, 10}, {10, 10}, {10, 0}}},
	}
	points := []grid.Point{
		{Lat: 5, Lon: 5},   // inside A
		{Lat: 5, Lon: 15},  // inside B
		{Lat: 5, Lon: 25},  // outside both — nearest to B
	}
	assignments := AssignPoints(nbs, points)

	if assignments[0] != 0 {
		t.Errorf("point 0: got %d, want 0 (A)", assignments[0])
	}
	if assignments[1] != 1 {
		t.Errorf("point 1: got %d, want 1 (B)", assignments[1])
	}
	if assignments[2] != 1 {
		t.Errorf("point 2: got %d, want 1 (B, nearest)", assignments[2])
	}
}

func TestComputeScores(t *testing.T) {
	nbs := []Neighbourhood{
		{Name: "A", Population: 1000, Polygon: nil},
		{Name: "B", Population: 3000, Polygon: nil},
	}
	// 4 grid points: 2 in A (scores 10, 20), 2 in B (scores 30, 40)
	assignments := []int{0, 0, 1, 1}
	gridTQI := []float64{10, 20, 30, 40}
	gridCov := []float64{5, 5, 15, 15}
	gridSpd := []float64{2, 4, 6, 8}

	scores, wTQI, _, _ := ComputeScores(nbs, assignments, gridTQI, gridCov, gridSpd)

	// A: mean TQI = 15, B: mean TQI = 35
	// Weighted: (15*1000 + 35*3000) / 4000 = (15000+105000)/4000 = 30
	if len(scores) != 2 {
		t.Fatalf("got %d scores, want 2", len(scores))
	}
	if scores[0].TQI != 15 {
		t.Errorf("A TQI = %f, want 15", scores[0].TQI)
	}
	if scores[1].TQI != 35 {
		t.Errorf("B TQI = %f, want 35", scores[1].TQI)
	}
	if wTQI != 30 {
		t.Errorf("weighted TQI = %f, want 30", wTQI)
	}
}

func TestMergeTargets(t *testing.T) {
	nbs := []Neighbourhood{
		{Name: "Chilliwack Proper", Population: 31410, Polygon: [][]float64{{0, 0}, {10, 0}, {10, 10}, {0, 10}, {0, 0}}},
		{Name: "Village West", Population: 0, Polygon: [][]float64{{10, 0}, {20, 0}, {20, 10}, {10, 10}, {10, 0}}},
	}
	assignments := []int{0, 1} // one point in each
	gridTQI := []float64{10, 20}
	gridCov := []float64{5, 15}
	gridSpd := []float64{3, 7}

	scores, _, _, _ := ComputeScores(nbs, assignments, gridTQI, gridCov, gridSpd)

	// Village West (pop 0) should be merged into Chilliwack Proper
	// Only Chilliwack Proper should appear in results
	if len(scores) != 1 {
		t.Fatalf("got %d scores, want 1 (Village West merged)", len(scores))
	}
	if scores[0].Name != "Chilliwack Proper" {
		t.Errorf("name = %q, want 'Chilliwack Proper'", scores[0].Name)
	}
	// Mean of both points: (10+20)/2 = 15
	if scores[0].TQI != 15 {
		t.Errorf("TQI = %f, want 15 (merged)", scores[0].TQI)
	}
	if scores[0].GridPointCount != 2 {
		t.Errorf("GridPointCount = %d, want 2", scores[0].GridPointCount)
	}
}
```

- [ ] **Step 3: Run tests**

Run: `cd go && go test ./internal/neighbourhood/ -v`
Expected: all 4 tests PASS

- [ ] **Step 4: Commit**

```bash
git add go/internal/neighbourhood/
git commit -m "feat: add neighbourhood package with boundaries, point-in-polygon, and scoring"
```

---

## Task 2: Pipeline Integration — Wire Neighbourhood Scoring

**Files:**
- Modify: `go/internal/api/server.go`
- Modify: `go/cmd/tqi/main.go`

- [ ] **Step 1: Add types and fields to `go/internal/api/server.go`**

Add import:
```go
"github.com/jasondyck/chwk-tqi/internal/neighbourhood"
```

Add fields to `PipelineResults` struct:
```go
NeighbourhoodScores     []neighbourhood.Score `json:"neighbourhood_scores,omitempty"`
NeighbourhoodBoundaries json.RawMessage       `json:"neighbourhood_boundaries,omitempty"`
```

(Also add `"encoding/json"` to imports if not already present.)

- [ ] **Step 2: Wire into pipeline in `go/cmd/tqi/main.go`**

Read the file first to find the exact location. After grid scores are computed and before the results struct literal, add:

```go
// Neighbourhood-level scoring with population weighting.
nbPath := filepath.Join("data", "neighbourhoods.geojson")
var nbScores []neighbourhood.Score
var nbBoundaries json.RawMessage
if _, err := os.Stat(nbPath); err == nil {
	fmt.Println("Computing neighbourhood scores...")
	nbs, rawGeoJSON, err := neighbourhood.LoadBoundaries(nbPath)
	if err != nil {
		log.Printf("neighbourhood boundaries: %v", err)
	} else {
		nbBoundaries = rawGeoJSON
		assignments := neighbourhood.AssignPoints(nbs, points)

		// Build per-origin score array from grid scores.
		// gridScores[i].Score is mean reachability * 100 for origin i — it
		// captures coverage and speed in a single composite number.
		// Coverage and speed sub-scores are city-wide aggregates (not per-origin),
		// so we pass them uniformly and only population-weight the TQI.
		gridTQIVals := make([]float64, len(gridScores))
		for i, gs := range gridScores {
			gridTQIVals[i] = gs.Score
		}
		gridCov := make([]float64, len(points))
		gridSpd := make([]float64, len(points))
		for i := range gridCov {
			gridCov[i] = tqi.CoverageScore
			gridSpd[i] = tqi.SpeedScore
		}

		var wTQI, wCov, wSpd float64
		nbScores, wTQI, wCov, wSpd = neighbourhood.ComputeScores(nbs, assignments, gridTQIVals, gridCov, gridSpd)

		// Replace uniform TQI with population-weighted TQI
		tqi.TQI = wTQI
		tqi.CoverageScore = wCov
		tqi.SpeedScore = wSpd
		fmt.Printf("Population-weighted TQI: %.2f (from %d neighbourhoods)\n", wTQI, len(nbScores))
	}
}
```

Add to the results struct literal:
```go
NeighbourhoodScores:     nbScores,
NeighbourhoodBoundaries: nbBoundaries,
```

Add imports at top of file:
```go
"github.com/jasondyck/chwk-tqi/internal/neighbourhood"
```

- [ ] **Step 3: Build and verify**

Run: `cd go && go build ./cmd/tqi`
Expected: compiles cleanly

- [ ] **Step 4: Commit**

```bash
git add go/internal/api/server.go go/cmd/tqi/main.go
git commit -m "feat: wire neighbourhood scoring and population-weighted TQI into pipeline"
```

---

## Task 3: TypeScript Types

**Files:**
- Modify: `go/web/src/lib/types.ts`

- [ ] **Step 1: Add NeighbourhoodScore interface and update PipelineResponse**

Add after existing interfaces:

```typescript
export interface NeighbourhoodScore {
  name: string
  population: number
  tqi: number
  coverage_score: number
  speed_score: number
  grid_point_count: number
}
```

Add to `PipelineResponse`:
```typescript
neighbourhood_scores: NeighbourhoodScore[] | null
neighbourhood_boundaries: unknown | null
```

- [ ] **Step 2: Build frontend**

Run: `cd go/web && npm run build`
Expected: builds successfully

- [ ] **Step 3: Commit**

```bash
git add go/web/src/lib/types.ts
git commit -m "feat: add NeighbourhoodScore TypeScript type"
```

---

## Task 4: NeighbourhoodTable Component

**Files:**
- Create: `go/web/src/components/NeighbourhoodTable.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Step 1: Create `go/web/src/components/NeighbourhoodTable.tsx`**

```tsx
import type { NeighbourhoodScore } from '../lib/types'

interface Props {
  scores: NeighbourhoodScore[]
}

function tqiColor(tqi: number): string {
  if (tqi >= 5) return 'text-emerald-600'
  if (tqi >= 2.5) return 'text-amber-600'
  return 'text-red-600'
}

export default function NeighbourhoodTable({ scores }: Props) {
  const sorted = [...scores].sort((a, b) => b.population - a.population)
  const maxPop = Math.max(...sorted.map((s) => s.population), 1)

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Neighbourhood Service Quality</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Neighbourhood</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600 min-w-[160px]">Population</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">TQI</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Coverage</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Speed</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600 text-slate-400">Points</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s, i) => {
                const popPct = (s.population / maxPop) * 100
                return (
                  <tr key={s.name} className={`border-b border-slate-100 ${i % 2 === 1 ? 'bg-slate-50/50' : ''}`}>
                    <td className="px-4 py-3 font-medium text-slate-900">{s.name}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden hidden sm:block">
                          <div className="h-full bg-blue-400 rounded-full" style={{ width: `${popPct}%` }} />
                        </div>
                        <span className="tabular-nums text-slate-700">{s.population.toLocaleString()}</span>
                      </div>
                    </td>
                    <td className={`px-4 py-3 text-right font-bold tabular-nums ${tqiColor(s.tqi)}`}>
                      {s.tqi.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                      {s.coverage_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                      {s.speed_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                      {s.grid_point_count.toLocaleString()}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-xs text-slate-400 mt-2">
        City-wide TQI is population-weighted: neighbourhoods with more residents contribute proportionally more to the overall score.
      </p>
    </section>
  )
}
```

- [ ] **Step 2: Add to App.tsx**

Import:
```tsx
import NeighbourhoodTable from './components/NeighbourhoodTable'
```

Add after ScoreCards, before Narrative:
```tsx
{data.neighbourhood_scores && <NeighbourhoodTable scores={data.neighbourhood_scores} />}
```

- [ ] **Step 3: Build and verify**

Run: `cd go/web && npm run build`
Expected: builds successfully

- [ ] **Step 4: Commit**

```bash
git add go/web/src/components/NeighbourhoodTable.tsx go/web/src/App.tsx
git commit -m "feat: add NeighbourhoodTable component"
```

---

## Task 5: Heat Map — Neighbourhood Boundary Overlay

**Files:**
- Modify: `go/web/src/components/HeatMap.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Step 1: Add neighbourhood boundaries prop and layer to HeatMap.tsx**

Read the current file first. Add a new prop:
```tsx
neighbourhoodBoundaries?: unknown | null
```

Inside the `<LayersControl>`, add a new overlay after the existing ones:

```tsx
{neighbourhoodBoundaries && (
  <LayersControl.Overlay checked name="Neighbourhoods">
    <GeoJSON
      data={neighbourhoodBoundaries as any}
      style={() => ({
        color: '#475569',
        weight: 2,
        fillOpacity: 0,
        dashArray: '4 4',
      })}
      onEachFeature={(feature: any, layer: any) => {
        const name = feature?.properties?.NAME
        if (name) {
          layer.bindTooltip(name, { sticky: true, className: 'text-xs' })
        }
      }}
    />
  </LayersControl.Overlay>
)}
```

Add `GeoJSON` to the react-leaflet import if not already imported.

- [ ] **Step 2: Update HeatMap call in App.tsx**

Pass the new prop:
```tsx
{data.grid_scores && (
  <HeatMap
    points={data.grid_scores}
    routeShapes={data.route_shapes}
    transitStops={data.transit_stops}
    neighbourhoodBoundaries={data.neighbourhood_boundaries}
  />
)}
```

- [ ] **Step 3: Build and verify**

Run: `cd go/web && npm run build`
Expected: builds successfully

- [ ] **Step 4: Commit**

```bash
git add go/web/src/components/HeatMap.tsx go/web/src/App.tsx
git commit -m "feat: add neighbourhood boundary polygons to heat map"
```

---

## Task 6: Hero Subtitle Update

**Files:**
- Modify: `go/web/src/components/Hero.tsx`

- [ ] **Step 1: Update Hero subtitle**

Read the current file. Find the subtitle paragraph (the `<p>` with "Comprehensive multi-metric assessment...") and update it:

```tsx
<p className="text-sm text-slate-500 max-w-xl mb-6">
  Population-weighted assessment of public transit service quality &mdash; coverage, speed, reliability, and accessibility across 12 neighbourhoods.
</p>
```

Also update the "Overall Score" label to "Population-Weighted Score":

```tsx
<div className="text-[11px] font-semibold uppercase tracking-wider text-amber-600 mb-1">Population-Weighted Score</div>
```

- [ ] **Step 2: Build and verify**

Run: `cd go/web && npm run build`

- [ ] **Step 3: Commit**

```bash
git add go/web/src/components/Hero.tsx
git commit -m "feat: update Hero to indicate population-weighted TQI"
```

---

## Task 7: Final Build, Embed, and Verification

**Files:**
- Modify: `go/web/dist/` (rebuilt)
- Modify: `e2e/dashboard.spec.js`

- [ ] **Step 1: Rebuild frontend**

Run: `cd go/web && npm run build`

- [ ] **Step 2: Rebuild Go binary**

Run: `cd go && go build -o tqi ./cmd/tqi`

- [ ] **Step 3: Run pipeline and start server**

```bash
./go/tqi serve --port 8080 --no-download
```

Wait for pipeline completion (~30s). Verify the API returns neighbourhood data:

```bash
curl -s http://localhost:8080/api/results | python3 -c "
import json, sys
d = json.load(sys.stdin)
ns = d.get('neighbourhood_scores')
print(f'Neighbourhoods: {len(ns) if ns else 0}')
if ns:
    for s in sorted(ns, key=lambda x: -x['population'])[:3]:
        print(f\"  {s['name']}: pop={s['population']}, tqi={s['tqi']:.1f}\")
print(f\"Weighted TQI: {d['tqi']['TQI']:.2f}\")
"
```

- [ ] **Step 4: Add Playwright test**

Add to `e2e/dashboard.spec.js`:

```javascript
test('neighbourhood table renders', async ({ page }) => {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  const heading = page.locator('text=Neighbourhood Service Quality');
  await expect(heading.first()).toBeVisible();
});
```

Run: `npx playwright test e2e/dashboard.spec.js --project=desktop`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add e2e/dashboard.spec.js
git commit -m "test: add Playwright test for neighbourhood table"
```
