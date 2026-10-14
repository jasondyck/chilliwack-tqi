# Visual Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Go/React frontend visually identical to the Python-generated HTML report.

**Architecture:** Vertical slices — each task extends the Go API and builds/updates the corresponding React component. Data flows from Go pipeline → JSON API → React Query → components. Maps rendered natively in Leaflet with GeoJSON from Go (no Folium iframes).

**Tech Stack:** Go 1.22, React 19, Recharts, Leaflet/react-leaflet, Tailwind CSS 4, TanStack React Query

**Spec:** `docs/superpowers/specs/2026-03-29-visual-parity-design.md`

---

## File Structure

### Go (new files)
- `go/internal/scoring/detailed.go` — DetailedAnalysis struct + computation
- `go/internal/scoring/detailed_test.go` — tests for DetailedAnalysis
- `go/internal/isochrone/isochrone.go` — isochrone generation from RAPTOR
- `go/internal/isochrone/isochrone_test.go` — tests
- `go/internal/equity/equity.go` — census/equity overlay
- `go/internal/equity/equity_test.go` — tests

### Go (modified files)
- `go/internal/scoring/types.go` — add DetailedAnalysis, TopOrigin, HistogramData types
- `go/internal/scoring/amenity.go` — add PctWithin45Min field
- `go/internal/api/server.go` — add new fields to PipelineResults
- `go/cmd/tqi/main.go` — wire DetailedAnalysis, isochrone, equity into pipeline

### React (new files)
- `go/web/src/components/CoverageStats.tsx`
- `go/web/src/components/SpeedAnalysis.tsx`
- `go/web/src/components/ReliabilityHistogram.tsx`
- `go/web/src/components/TopOrigins.tsx`
- `go/web/src/components/IsochroneMaps.tsx`
- `go/web/src/components/EquityMap.tsx`
- `go/web/src/components/Methodology.tsx`
- `go/web/src/components/Standards.tsx`

### React (modified files)
- `go/web/src/lib/types.ts` — add DetailedAnalysis, IsochroneResult, EquityResult, RouteShape, TransitStop types
- `go/web/src/App.tsx` — new section order, new component imports
- `go/web/src/components/Hero.tsx` — 2-col layout with heatmap preview
- `go/web/src/components/ScoreCards.tsx` — hover effects, icon tweaks
- `go/web/src/components/ScoreBreakdown.tsx` — styling tweaks
- `go/web/src/components/WalkScoreTable.tsx` — amber highlight
- `go/web/src/components/RouteTable.tsx` — horizontal bars + dark sidebar
- `go/web/src/components/TimeProfile.tsx` — peak bands + peak/low cards
- `go/web/src/components/PTALChart.tsx` — minor color/label tweaks
- `go/web/src/components/HeatMap.tsx` — route lines, stops, layer control
- `go/web/src/components/AmenityCards.tsx` → rename to `AmenityTable.tsx`
- `go/web/src/components/Footer.tsx` — slim down

---

## Task 1: DetailedAnalysis — Go Types and Computation

**Files:**
- Modify: `go/internal/scoring/types.go`
- Create: `go/internal/scoring/detailed.go`
- Create: `go/internal/scoring/detailed_test.go`
- Modify: `go/internal/api/server.go:21-34`
- Modify: `go/cmd/tqi/main.go:381-393`

### Step 1: Add types

- [ ] **Add DetailedAnalysis and supporting types to `go/internal/scoring/types.go`**

Append after the existing `TimeSlotScore` struct (after line 32):

```go
// DetailedAnalysis contains derived metrics for the frontend dashboard.
type DetailedAnalysis struct {
	// Coverage
	NOriginsWithService      int     `json:"n_origins_with_service"`
	NTransitDesertOrigins    int     `json:"n_transit_desert_origins"`
	TransitDesertPct         float64 `json:"transit_desert_pct"`
	NValidPairs              int     `json:"n_valid_pairs"`
	NReachablePairs          int     `json:"n_reachable_pairs"`
	ReachabilityRatePct      float64 `json:"reachability_rate_pct"`
	MaxOriginReachabilityPct float64 `json:"max_origin_reachability_pct"`

	// Speed / TSR
	MeanTSR                 float64            `json:"mean_tsr"`
	MedianTSR               float64            `json:"median_tsr"`
	TSRPercentiles          map[string]float64 `json:"tsr_percentiles"`
	TSRSlowerThanWalkingPct float64            `json:"tsr_slower_than_walking_pct"`
	TSR5To10Pct             float64            `json:"tsr_5_to_10_pct"`
	TSR10To20Pct            float64            `json:"tsr_10_to_20_pct"`
	TSR20PlusPct            float64            `json:"tsr_20_plus_pct"`

	// Travel time
	MeanTravelTimeMin     float64            `json:"mean_travel_time_min"`
	MedianTravelTimeMin   float64            `json:"median_travel_time_min"`
	TravelTimePercentiles map[string]float64 `json:"travel_time_percentiles"`

	// Time-of-day peaks
	PeakSlot   string  `json:"peak_slot"`
	PeakTQI    float64 `json:"peak_tqi"`
	LowestSlot string  `json:"lowest_slot"`
	LowestTQI  float64 `json:"lowest_tqi"`

	// Best-connected locations
	TopOrigins []TopOrigin `json:"top_origins"`

	// Reliability histogram
	ReliabilityHistogram HistogramData `json:"reliability_histogram"`

	// PTAL distribution
	PTALDistribution map[string]int `json:"ptal_distribution"`
}

type TopOrigin struct {
	Lat             float64 `json:"lat"`
	Lon             float64 `json:"lon"`
	ReachabilityPct float64 `json:"reachability_pct"`
}

type HistogramData struct {
	Labels []string `json:"labels"`
	Counts []int    `json:"counts"`
}
```

### Step 2: Write the computation

- [ ] **Create `go/internal/scoring/detailed.go`**

```go
package scoring

import (
	"math"
	"sort"

	"tqi/internal/grid"
)

// ComputeDetailedAnalysis derives dashboard metrics from the OD matrices.
func ComputeDetailedAnalysis(
	points []grid.Point,
	metrics *ODMetrics,
	tqi *TQIResult,
	ptal *PTALResult,
	stopLats, stopLons []float64,
) *DetailedAnalysis {
	n := len(points)
	da := &DetailedAnalysis{
		TSRPercentiles:        make(map[string]float64),
		TravelTimePercentiles: make(map[string]float64),
		PTALDistribution:      make(map[string]int),
	}

	// --- Coverage ---
	const desertRadiusKM = 0.8
	for i := 0; i < n; i++ {
		hasStop := false
		for s := 0; s < len(stopLats); s++ {
			d := haversineKM(points[i].Lat, points[i].Lon, stopLats[s], stopLons[s])
			if d <= desertRadiusKM {
				hasStop = true
				break
			}
		}
		if hasStop {
			da.NOriginsWithService++
		} else {
			da.NTransitDesertOrigins++
		}
	}
	if n > 0 {
		da.TransitDesertPct = float64(da.NTransitDesertOrigins) / float64(n) * 100
	}

	// OD reachability: count pairs where mean travel time > 0 and <= 90 min
	var maxOriginReach int
	for i := 0; i < n; i++ {
		originReach := 0
		for j := 0; j < n; j++ {
			if i == j {
				continue
			}
			tt := metrics.MeanTravelTime[i][j]
			if tt > 0 && tt <= 90 {
				da.NValidPairs++
				if metrics.Reachability[i][j] > 0 {
					da.NReachablePairs++
					originReach++
				}
			}
		}
		if originReach > maxOriginReach {
			maxOriginReach = originReach
		}
	}
	if da.NValidPairs > 0 {
		da.ReachabilityRatePct = float64(da.NReachablePairs) / float64(da.NValidPairs) * 100
	}
	totalDests := n - 1
	if totalDests > 0 {
		da.MaxOriginReachabilityPct = float64(maxOriginReach) / float64(totalDests) * 100
	}

	// --- Speed / TSR ---
	var tsrValues []float64
	var ttValues []float64
	for i := 0; i < n; i++ {
		for j := 0; j < n; j++ {
			if i == j {
				continue
			}
			tt := metrics.MeanTravelTime[i][j]
			dist := metrics.DistancesKM[i][j]
			if tt > 0 && dist > 0 && metrics.Reachability[i][j] > 0 {
				tsr := dist / (tt / 60.0) // km/h
				tsrValues = append(tsrValues, tsr)
				ttValues = append(ttValues, tt)
			}
		}
	}

	if len(tsrValues) > 0 {
		sort.Float64s(tsrValues)
		sort.Float64s(ttValues)

		da.MeanTSR = mean(tsrValues)
		da.MedianTSR = percentile(tsrValues, 50)
		da.TSRPercentiles["p10"] = percentile(tsrValues, 10)
		da.TSRPercentiles["p25"] = percentile(tsrValues, 25)
		da.TSRPercentiles["p50"] = percentile(tsrValues, 50)
		da.TSRPercentiles["p75"] = percentile(tsrValues, 75)
		da.TSRPercentiles["p90"] = percentile(tsrValues, 90)
		da.TSRPercentiles["p95"] = percentile(tsrValues, 95)
		da.TSRPercentiles["p99"] = percentile(tsrValues, 99)

		var slower, band5, band10, band20 int
		for _, v := range tsrValues {
			switch {
			case v < 5:
				slower++
			case v < 10:
				band5++
			case v < 20:
				band10++
			default:
				band20++
			}
		}
		total := float64(len(tsrValues))
		da.TSRSlowerThanWalkingPct = float64(slower) / total * 100
		da.TSR5To10Pct = float64(band5) / total * 100
		da.TSR10To20Pct = float64(band10) / total * 100
		da.TSR20PlusPct = float64(band20) / total * 100

		da.MeanTravelTimeMin = mean(ttValues)
		da.MedianTravelTimeMin = percentile(ttValues, 50)
		da.TravelTimePercentiles["p10"] = percentile(ttValues, 10)
		da.TravelTimePercentiles["p25"] = percentile(ttValues, 25)
		da.TravelTimePercentiles["p50"] = percentile(ttValues, 50)
		da.TravelTimePercentiles["p75"] = percentile(ttValues, 75)
		da.TravelTimePercentiles["p90"] = percentile(ttValues, 90)
	}

	// --- Time-of-day peaks ---
	if len(tqi.TimeProfile) > 0 {
		bestIdx, worstIdx := 0, 0
		for i, tp := range tqi.TimeProfile {
			if tp.Score > tqi.TimeProfile[bestIdx].Score {
				bestIdx = i
			}
			if tp.Score < tqi.TimeProfile[worstIdx].Score {
				worstIdx = i
			}
		}
		da.PeakSlot = tqi.TimeProfile[bestIdx].Label
		da.PeakTQI = tqi.TimeProfile[bestIdx].Score
		da.LowestSlot = tqi.TimeProfile[worstIdx].Label
		da.LowestTQI = tqi.TimeProfile[worstIdx].Score
	}

	// --- Top origins ---
	type originReach struct {
		idx   int
		reach float64
	}
	origins := make([]originReach, n)
	for i := 0; i < n; i++ {
		reachCount := 0
		totalCount := 0
		for j := 0; j < n; j++ {
			if i == j {
				continue
			}
			if metrics.MeanTravelTime[i][j] > 0 && metrics.MeanTravelTime[i][j] <= 90 {
				totalCount++
				if metrics.Reachability[i][j] > 0 {
					reachCount++
				}
			}
		}
		pct := 0.0
		if totalCount > 0 {
			pct = float64(reachCount) / float64(totalCount) * 100
		}
		origins[i] = originReach{idx: i, reach: pct}
	}
	sort.Slice(origins, func(a, b int) bool {
		return origins[a].reach > origins[b].reach
	})
	topN := 10
	if topN > n {
		topN = n
	}
	da.TopOrigins = make([]TopOrigin, topN)
	for i := 0; i < topN; i++ {
		da.TopOrigins[i] = TopOrigin{
			Lat:             points[origins[i].idx].Lat,
			Lon:             points[origins[i].idx].Lon,
			ReachabilityPct: origins[i].reach,
		}
	}

	// --- Reliability histogram ---
	if len(tqi.ReliabilityPerOrigin) > 0 {
		const nBins = 25
		maxCV := 0.0
		for _, cv := range tqi.ReliabilityPerOrigin {
			if cv > maxCV {
				maxCV = cv
			}
		}
		if maxCV == 0 {
			maxCV = 1.0
		}
		binWidth := maxCV / float64(nBins)
		counts := make([]int, nBins)
		labels := make([]string, nBins)
		for i := 0; i < nBins; i++ {
			labels[i] = fmt.Sprintf("%.2f", float64(i)*binWidth+binWidth/2)
		}
		for _, cv := range tqi.ReliabilityPerOrigin {
			bin := int(cv / binWidth)
			if bin >= nBins {
				bin = nBins - 1
			}
			counts[bin]++
		}
		da.ReliabilityHistogram = HistogramData{Labels: labels, Counts: counts}
	}

	// --- PTAL distribution ---
	if ptal != nil {
		for _, g := range ptal.Grades {
			da.PTALDistribution[g]++
		}
	}

	return da
}

func haversineKM(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371.0
	dLat := (lat2 - lat1) * math.Pi / 180
	dLon := (lon2 - lon1) * math.Pi / 180
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*math.Pi/180)*math.Cos(lat2*math.Pi/180)*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	return R * 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
}

func mean(vals []float64) float64 {
	if len(vals) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range vals {
		sum += v
	}
	return sum / float64(len(vals))
}

func percentile(sorted []float64, p float64) float64 {
	if len(sorted) == 0 {
		return 0
	}
	idx := p / 100.0 * float64(len(sorted)-1)
	lower := int(math.Floor(idx))
	upper := int(math.Ceil(idx))
	if lower == upper || upper >= len(sorted) {
		return sorted[lower]
	}
	frac := idx - float64(lower)
	return sorted[lower]*(1-frac) + sorted[upper]*frac
}
```

Note: imports for this file are `"fmt"`, `"math"`, `"sort"`, and `"tqi/internal/grid"`.

### Step 3: Write tests

- [ ] **Create `go/internal/scoring/detailed_test.go`**

```go
package scoring

import (
	"testing"

	"tqi/internal/grid"
)

func TestComputeDetailedAnalysis(t *testing.T) {
	points := []grid.Point{
		{Lat: 49.16, Lon: -121.95},
		{Lat: 49.17, Lon: -121.95},
		{Lat: 49.18, Lon: -121.95},
	}
	// Stop near point 0 and 1, not near point 2
	stopLats := []float64{49.161, 49.171}
	stopLons := []float64{-121.951, -121.951}

	metrics := &ODMetrics{
		MeanTravelTime: [][]float64{
			{0, 20, 45},
			{20, 0, 30},
			{45, 30, 0},
		},
		Reachability: [][]float64{
			{0, 0.8, 0.5},
			{0.8, 0, 0.9},
			{0.5, 0.9, 0},
		},
		DistancesKM: [][]float64{
			{0, 1.1, 2.2},
			{1.1, 0, 1.1},
			{2.2, 1.1, 0},
		},
		TravelTimeStd: [][]float64{
			{0, 5, 10},
			{5, 0, 8},
			{10, 8, 0},
		},
	}

	tqi := &TQIResult{
		TimeProfile: []TimeSlotScore{
			{Label: "07:00", Score: 3.5},
			{Label: "08:00", Score: 5.2},
			{Label: "09:00", Score: 4.1},
		},
		ReliabilityPerOrigin: []float64{0.1, 0.3, 0.5},
	}

	ptal := &PTALResult{
		Values: []float64{5.0, 3.0, 1.0},
		Grades: []string{"4", "2", "1a"},
	}

	da := ComputeDetailedAnalysis(points, metrics, tqi, ptal, stopLats, stopLons)

	// Coverage: point 2 is a transit desert (no stop within 800m)
	if da.NOriginsWithService != 2 {
		t.Errorf("NOriginsWithService = %d, want 2", da.NOriginsWithService)
	}
	if da.NTransitDesertOrigins != 1 {
		t.Errorf("NTransitDesertOrigins = %d, want 1", da.NTransitDesertOrigins)
	}

	// Peak/low
	if da.PeakSlot != "08:00" {
		t.Errorf("PeakSlot = %q, want '08:00'", da.PeakSlot)
	}
	if da.LowestSlot != "07:00" {
		t.Errorf("LowestSlot = %q, want '07:00'", da.LowestSlot)
	}

	// Top origins should have 3 entries (only 3 points)
	if len(da.TopOrigins) != 3 {
		t.Errorf("TopOrigins len = %d, want 3", len(da.TopOrigins))
	}

	// PTAL distribution
	if da.PTALDistribution["4"] != 1 || da.PTALDistribution["2"] != 1 || da.PTALDistribution["1a"] != 1 {
		t.Errorf("PTALDistribution = %v, want {4:1, 2:1, 1a:1}", da.PTALDistribution)
	}

	// TSR values should be populated
	if da.MeanTSR <= 0 {
		t.Errorf("MeanTSR = %f, want > 0", da.MeanTSR)
	}

	// Reliability histogram should have bins
	if len(da.ReliabilityHistogram.Counts) == 0 {
		t.Error("ReliabilityHistogram.Counts is empty")
	}
}
```

- [ ] **Run test**

Run: `cd go && go test ./internal/scoring/ -run TestComputeDetailedAnalysis -v`
Expected: PASS

### Step 4: Wire into API

- [ ] **Add DetailedAnalysis to PipelineResults in `go/internal/api/server.go`**

Add field after the existing `SystemLOS` field (around line 26):

```go
DetailedAnalysis  *scoring.DetailedAnalysis      `json:"detailed_analysis,omitempty"`
```

- [ ] **Call ComputeDetailedAnalysis in pipeline (`go/cmd/tqi/main.go`)**

After the TQI computation (around line 324) and before the results assembly (around line 381), add:

```go
// Compute detailed analysis for dashboard
detailedAnalysis := scoring.ComputeDetailedAnalysis(points, metrics, tqi, ptal, stopLats, stopLons)
```

Then add to the results struct literal:

```go
DetailedAnalysis:  detailedAnalysis,
```

- [ ] **Build and verify**

Run: `cd go && go build ./cmd/tqi`
Expected: compiles without errors

- [ ] **Commit**

```bash
git add go/internal/scoring/types.go go/internal/scoring/detailed.go go/internal/scoring/detailed_test.go go/internal/api/server.go go/cmd/tqi/main.go
git commit -m "feat: add DetailedAnalysis computation for dashboard metrics"
```

---

## Task 2: TypeScript Types + PipelineResponse Update

**Files:**
- Modify: `go/web/src/lib/types.ts`

- [ ] **Update types.ts with all new interfaces**

Add the new interfaces after the existing `GridScorePoint` interface, and update `PipelineResponse`:

```typescript
export interface DetailedAnalysis {
  n_origins_with_service: number
  n_transit_desert_origins: number
  transit_desert_pct: number
  n_valid_pairs: number
  n_reachable_pairs: number
  reachability_rate_pct: number
  max_origin_reachability_pct: number
  mean_tsr: number
  median_tsr: number
  tsr_percentiles: Record<string, number>
  tsr_slower_than_walking_pct: number
  tsr_5_to_10_pct: number
  tsr_10_to_20_pct: number
  tsr_20_plus_pct: number
  mean_travel_time_min: number
  median_travel_time_min: number
  travel_time_percentiles: Record<string, number>
  peak_slot: string
  peak_tqi: number
  lowest_slot: string
  lowest_tqi: number
  top_origins: TopOrigin[]
  reliability_histogram: { labels: string[]; counts: number[] }
  ptal_distribution: Record<string, number>
}

export interface TopOrigin {
  lat: number
  lon: number
  reachability_pct: number
}

export interface IsochroneResult {
  departure_time: string
  label: string
  geojson: unknown
}

export interface EquityResult {
  geojson: unknown
  tqi_income_correlation: number
}

export interface RouteShape {
  route_id: string
  route_name: string
  color: string
  points: number[][]
}

export interface TransitStop {
  stop_id: string
  stop_name: string
  lat: number
  lon: number
}
```

Update `PipelineResponse` to add:

```typescript
export interface PipelineResponse {
  tqi: TQIResult
  route_los: RouteLOS[] | null
  system_los: SystemLOS | null
  ptal: PTALResult | null
  amenities: AmenityResult[] | null
  grid_points: number
  n_stops: number
  grid_scores: GridScorePoint[] | null
  narrative: string[] | null
  walkscore_category: string
  walkscore_desc: string
  detailed_analysis: DetailedAnalysis | null
  isochrones: IsochroneResult[] | null
  equity: EquityResult | null
  route_shapes: RouteShape[] | null
  transit_stops: TransitStop[] | null
}
```

- [ ] **Build frontend to verify types compile**

Run: `cd go/web && npx tsc --noEmit`
Expected: no errors (or only pre-existing ones)

- [ ] **Commit**

```bash
git add go/web/src/lib/types.ts
git commit -m "feat: add TypeScript types for DetailedAnalysis, isochrones, equity"
```

---

## Task 3: Coverage Stats Component

**Files:**
- Create: `go/web/src/components/CoverageStats.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Create `go/web/src/components/CoverageStats.tsx`**

```tsx
import type { DetailedAnalysis } from '../lib/types'

interface Props {
  da: DetailedAnalysis
  gridPoints: number
  nStops: number
}

interface StatCard {
  label: string
  value: string
  accent?: 'red' | 'amber'
}

export default function CoverageStats({ da, gridPoints, nStops }: Props) {
  const cards: StatCard[] = [
    { label: 'Grid Points', value: gridPoints.toLocaleString() },
    { label: 'Transit Stops', value: nStops.toLocaleString() },
    { label: 'Transit Deserts', value: `${da.transit_desert_pct.toFixed(1)}%`, accent: 'red' },
    { label: 'With Service', value: da.n_origins_with_service.toLocaleString() },
    { label: 'OD Reachable', value: `${da.reachability_rate_pct.toFixed(1)}%`, accent: 'amber' },
    { label: 'Best Location', value: `${da.max_origin_reachability_pct.toFixed(1)}%` },
  ]

  const accentStyles = {
    red: { border: 'border-l-4 border-l-red-500', text: 'text-red-500' },
    amber: { border: 'border-l-4 border-l-amber-500', text: 'text-amber-500' },
  }

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Coverage Analysis</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {cards.map((card) => {
          const accent = card.accent ? accentStyles[card.accent] : null
          return (
            <div
              key={card.label}
              className={`bg-white rounded-xl border border-slate-200 p-4 min-w-[150px] ${accent?.border ?? ''}`}
            >
              <div className={`text-2xl sm:text-3xl font-extrabold tabular-nums ${accent?.text ?? 'text-slate-900'}`}>
                {card.value}
              </div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mt-1">
                {card.label}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
```

- [ ] **Add CoverageStats to App.tsx**

Import at top of file:
```tsx
import CoverageStats from './components/CoverageStats'
```

Add after RouteTable (around line 55 in Dashboard):
```tsx
{data.detailed_analysis && (
  <CoverageStats da={data.detailed_analysis} gridPoints={data.grid_points} nStops={data.n_stops} />
)}
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`
Expected: builds successfully

- [ ] **Commit**

```bash
git add go/web/src/components/CoverageStats.tsx go/web/src/App.tsx
git commit -m "feat: add CoverageStats component"
```

---

## Task 4: Speed Analysis Component

**Files:**
- Create: `go/web/src/components/SpeedAnalysis.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Create `go/web/src/components/SpeedAnalysis.tsx`**

```tsx
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { DetailedAnalysis } from '../lib/types'

interface Props {
  da: DetailedAnalysis
}

const TSR_COLORS = ['#ef4444', '#f59e0b', '#22c55e', '#3b82f6']

export default function SpeedAnalysis({ da }: Props) {
  const doughnutData = [
    { name: '< 5 km/h', value: da.tsr_slower_than_walking_pct },
    { name: '5-10 km/h', value: da.tsr_5_to_10_pct },
    { name: '10-20 km/h', value: da.tsr_10_to_20_pct },
    { name: '20+ km/h', value: da.tsr_20_plus_pct },
  ]

  const travelTimeData = [
    { name: 'P10', value: da.travel_time_percentiles?.p10 ?? 0, fill: '#22c55e' },
    { name: 'P25', value: da.travel_time_percentiles?.p25 ?? 0, fill: '#84cc16' },
    { name: 'P50', value: da.travel_time_percentiles?.p50 ?? 0, fill: '#f59e0b' },
    { name: 'P75', value: da.travel_time_percentiles?.p75 ?? 0, fill: '#f97316' },
    { name: 'P90', value: da.travel_time_percentiles?.p90 ?? 0, fill: '#ef4444' },
  ]

  const metricCards = [
    { label: 'Mean TSR (km/h)', value: da.mean_tsr.toFixed(1), accent: 'border-l-4 border-l-amber-500' },
    { label: 'Median TSR (km/h)', value: da.median_tsr.toFixed(1), accent: '' },
    { label: 'Slower Than Walking', value: `${da.tsr_slower_than_walking_pct.toFixed(1)}%`, accent: 'border-l-4 border-l-red-500', textColor: 'text-red-500' },
    { label: 'Mean Trip Duration', value: `${da.mean_travel_time_min.toFixed(0)} min`, accent: '' },
  ]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Speed Analysis</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>

      {/* TSR Doughnut + Metric Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4 mb-4">
        {/* Doughnut */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col items-center">
          <div className="relative w-[200px] h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={doughnutData} cx="50%" cy="50%" innerRadius="55%" outerRadius="90%" dataKey="value" startAngle={90} endAngle={-270}>
                  {doughnutData.map((_, i) => (
                    <Cell key={i} fill={TSR_COLORS[i]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-extrabold text-slate-900">{da.mean_tsr.toFixed(1)}</span>
              <span className="text-xs text-slate-500">km/h avg TSR</span>
            </div>
          </div>
          <div className="flex gap-3 mt-2 text-[10px] text-slate-500">
            {doughnutData.map((d, i) => (
              <span key={d.name} className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: TSR_COLORS[i] }} />
                {d.name}
              </span>
            ))}
          </div>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-2 gap-3">
          {metricCards.map((card) => (
            <div key={card.label} className={`bg-white rounded-xl border border-slate-200 p-4 ${card.accent}`}>
              <div className={`text-2xl sm:text-3xl font-extrabold tabular-nums ${card.textColor ?? 'text-slate-900'}`}>
                {card.value}
              </div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mt-1">
                {card.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Travel Time Distribution */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Travel Time Distribution (minutes)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={travelTimeData} margin={{ top: 20, right: 20, bottom: 5, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, color: 'white', padding: '8px 12px', fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} label={{ position: 'top', fontSize: 11, fontWeight: 600, fill: '#334155' }}>
              {travelTimeData.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
```

- [ ] **Add SpeedAnalysis to App.tsx**

Import at top:
```tsx
import SpeedAnalysis from './components/SpeedAnalysis'
```

Add after CoverageStats:
```tsx
{data.detailed_analysis && <SpeedAnalysis da={data.detailed_analysis} />}
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`
Expected: builds successfully

- [ ] **Commit**

```bash
git add go/web/src/components/SpeedAnalysis.tsx go/web/src/App.tsx
git commit -m "feat: add SpeedAnalysis component with TSR doughnut and travel time chart"
```

---

## Task 5: Time Profile Enhancements

**Files:**
- Modify: `go/web/src/components/TimeProfile.tsx`

- [ ] **Enhance TimeProfile with peak bands and peak/low cards**

Replace the entire file:

```tsx
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea } from 'recharts'
import type { TimeSlotScore, DetailedAnalysis } from '../lib/types'

interface Props {
  data: TimeSlotScore[]
  da?: DetailedAnalysis | null
}

export default function TimeProfile({ data, da }: Props) {
  // Find indices for AM peak (7:00-9:00) and PM peak (15:00-18:00)
  const labels = data.map((d) => d.Label)
  const amStart = labels.findIndex((l) => l >= '07:00')
  const amEnd = labels.findIndex((l) => l > '09:00')
  const pmStart = labels.findIndex((l) => l >= '15:00')
  const pmEnd = labels.findIndex((l) => l > '18:00')

  const amStartLabel = amStart >= 0 ? labels[amStart] : undefined
  const amEndLabel = amEnd >= 0 ? labels[amEnd] : labels[labels.length - 1]
  const pmStartLabel = pmStart >= 0 ? labels[pmStart] : undefined
  const pmEndLabel = pmEnd >= 0 ? labels[pmEnd] : labels[labels.length - 1]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Time-of-Day Profile</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 5, left: 20 }}>
            <defs>
              <linearGradient id="tqiGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            {amStartLabel && (
              <ReferenceArea x1={amStartLabel} x2={amEndLabel} fill="#f59e0b" fillOpacity={0.08} label={{ value: 'AM Peak', position: 'insideTopLeft', fontSize: 10, fill: '#92400e' }} />
            )}
            {pmStartLabel && (
              <ReferenceArea x1={pmStartLabel} x2={pmEndLabel} fill="#f59e0b" fillOpacity={0.08} label={{ value: 'PM Peak', position: 'insideTopLeft', fontSize: 10, fill: '#92400e' }} />
            )}
            <XAxis
              dataKey="Label"
              tick={{ fontSize: 11, fill: '#64748b' }}
              interval={Math.max(0, Math.floor(data.length / 16) - 1)}
            />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, color: 'white', padding: '8px 12px', fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Area type="monotone" dataKey="Score" stroke="#3b82f6" strokeWidth={2} fill="url(#tqiGrad)" />
          </AreaChart>
        </ResponsiveContainer>

        {/* Peak / Low cards */}
        {da && (
          <div className="grid grid-cols-2 gap-3 mt-4">
            <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-emerald-500 p-3 flex items-center gap-3">
              <span className="material-symbols-outlined text-emerald-500">trending_up</span>
              <div>
                <div className="text-xs text-slate-500">Peak Service</div>
                <div className="text-sm font-bold text-slate-900">{da.peak_slot} — TQI {da.peak_tqi.toFixed(1)}</div>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 border-l-4 border-l-red-500 p-3 flex items-center gap-3">
              <span className="material-symbols-outlined text-red-500">trending_down</span>
              <div>
                <div className="text-xs text-slate-500">Lowest Service</div>
                <div className="text-sm font-bold text-slate-900">{da.lowest_slot} — TQI {da.lowest_tqi.toFixed(1)}</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
```

- [ ] **Update TimeProfile call in App.tsx to pass da prop**

```tsx
<TimeProfile data={data.tqi.TimeProfile} da={data.detailed_analysis} />
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`
Expected: builds successfully

- [ ] **Commit**

```bash
git add go/web/src/components/TimeProfile.tsx go/web/src/App.tsx
git commit -m "feat: add AM/PM peak bands and peak/low cards to TimeProfile"
```

---

## Task 6: Reliability Histogram Component

**Files:**
- Create: `go/web/src/components/ReliabilityHistogram.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Create `go/web/src/components/ReliabilityHistogram.tsx`**

```tsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { DetailedAnalysis } from '../lib/types'

interface Props {
  da: DetailedAnalysis
}

export default function ReliabilityHistogram({ da }: Props) {
  const hist = da.reliability_histogram
  if (!hist || hist.counts.length === 0) return null

  const chartData = hist.labels.map((label, i) => ({
    label,
    count: hist.counts[i],
  }))

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Temporal Reliability</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <p className="text-xs text-slate-500 mb-3">Lower CV = more predictable trip times</p>
        <ResponsiveContainer width="100%" height={256}>
          <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 5, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: '#64748b' }}
              interval={Math.max(0, Math.floor(chartData.length / 10) - 1)}
              label={{ value: 'Coefficient of Variation', position: 'insideBottom', offset: -2, fontSize: 11, fill: '#94a3b8' }}
            />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} label={{ value: 'Grid Points', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#94a3b8' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, color: 'white', padding: '8px 12px', fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
```

- [ ] **Add to App.tsx**

Import:
```tsx
import ReliabilityHistogram from './components/ReliabilityHistogram'
```

Add after EquityMap (or near end of dashboard):
```tsx
{data.detailed_analysis && <ReliabilityHistogram da={data.detailed_analysis} />}
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`
Expected: builds successfully

- [ ] **Commit**

```bash
git add go/web/src/components/ReliabilityHistogram.tsx go/web/src/App.tsx
git commit -m "feat: add ReliabilityHistogram component"
```

---

## Task 7: Top Origins Component

**Files:**
- Create: `go/web/src/components/TopOrigins.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Create `go/web/src/components/TopOrigins.tsx`**

```tsx
import type { TopOrigin } from '../lib/types'

interface Props {
  origins: TopOrigin[]
}

export default function TopOrigins({ origins }: Props) {
  if (!origins || origins.length === 0) return null

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Best-Connected Locations</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {origins.map((o, i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-blue-500 text-lg">location_on</span>
              <div className="text-sm tabular-nums text-slate-700">
                {o.lat.toFixed(4)}, {o.lon.toFixed(4)}
              </div>
            </div>
            <div className="text-lg font-bold text-blue-600 tabular-nums">
              {o.reachability_pct.toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
```

- [ ] **Add to App.tsx**

Import:
```tsx
import TopOrigins from './components/TopOrigins'
```

Add after HeatMap:
```tsx
{data.detailed_analysis?.top_origins && <TopOrigins origins={data.detailed_analysis.top_origins} />}
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`

- [ ] **Commit**

```bash
git add go/web/src/components/TopOrigins.tsx go/web/src/App.tsx
git commit -m "feat: add TopOrigins component for best-connected locations"
```

---

## Task 8: Route LOS Rework — Horizontal Bars + Dark Sidebar

**Files:**
- Modify: `go/web/src/components/RouteTable.tsx`

- [ ] **Replace RouteTable.tsx with horizontal bar layout**

```tsx
import type { RouteLOS, SystemLOS } from '../lib/types'

interface Props {
  routes: RouteLOS[]
  systemLos: SystemLOS | null
}

const barColors: Record<string, string> = {
  A: '#059669', B: '#22c55e', C: '#84cc16',
  D: '#f59e0b', E: '#f97316', F: '#e11d48',
}

const badgeBg: Record<string, string> = {
  A: 'bg-emerald-100 text-emerald-800',
  B: 'bg-green-100 text-green-700',
  C: 'bg-lime-100 text-lime-700',
  D: 'bg-amber-100 text-amber-800',
  E: 'bg-orange-100 text-orange-800',
  F: 'bg-red-100 text-red-800',
}

const gradeRef = [
  { grade: 'A', range: '≤ 10 min', desc: "Passengers don't need schedule", color: 'text-emerald-400' },
  { grade: 'B', range: '≤ 14 min', desc: 'Frequent service', color: 'text-green-400' },
  { grade: 'C', range: '≤ 20 min', desc: 'Maximum desirable wait', color: 'text-lime-400' },
  { grade: 'D', range: '≤ 30 min', desc: 'Unattractive to choice riders', color: 'text-amber-400' },
  { grade: 'E', range: '≤ 60 min', desc: 'Minimal service', color: 'text-orange-400' },
  { grade: 'F', range: '> 60 min', desc: 'Unattractive to all', color: 'text-rose-400' },
]

export default function RouteTable({ routes, systemLos }: Props) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Route-Level Service Quality (TCQSM)</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px]">
          {/* Headway bars */}
          <div className="p-4 overflow-x-auto">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Headway by Route</h3>
            <div className="min-w-[360px] space-y-2">
              {routes.map((r) => {
                const hw = r.median_headway ?? 0
                const pct = Math.min(hw, 80) / 80 * 100
                const color = barColors[r.los_grade] ?? '#94a3b8'
                return (
                  <div key={r.route_id} className="flex items-center gap-2">
                    <div className="w-9 text-right font-semibold text-sm text-slate-700 shrink-0">{r.route_name}</div>
                    <div className="w-[140px] text-xs text-slate-500 truncate shrink-0">{r.route_long_name}</div>
                    <div className="flex-1 h-6 bg-slate-100 rounded relative min-w-[100px]">
                      <div
                        className="absolute left-0 top-0 h-full rounded flex items-center justify-end pr-1.5"
                        style={{ width: `${pct}%`, background: color }}
                      >
                        {pct > 15 && (
                          <span className="text-[11px] font-bold text-white">{hw.toFixed(0)} min</span>
                        )}
                      </div>
                      {pct <= 15 && (
                        <span className="absolute left-[calc(var(--pct)+4px)] top-1/2 -translate-y-1/2 text-[11px] font-bold text-slate-600" style={{ '--pct': `${pct}%` } as React.CSSProperties}>
                          {hw.toFixed(0)} min
                        </span>
                      )}
                    </div>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${badgeBg[r.los_grade] ?? 'bg-slate-100 text-slate-600'}`}>
                      {r.los_grade}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Dark sidebar */}
          <div className="bg-slate-900 text-slate-200 p-4 lg:rounded-r-xl">
            {systemLos && (
              <>
                <h3 className="text-sm font-bold text-white mb-2">System Summary</h3>
                <div className="text-xs text-slate-400 space-y-1 mb-4">
                  <div>{systemLos.n_routes} routes</div>
                  <div>Median headway: <span className="text-white font-semibold">{systemLos.median_system_headway.toFixed(0)} min</span></div>
                  <div>Best grade: <span className={gradeRef.find((g) => g.grade === systemLos.best_grade)?.color ?? ''}>{systemLos.best_grade}</span></div>
                  <div>Worst grade: <span className={gradeRef.find((g) => g.grade === systemLos.worst_grade)?.color ?? ''}>{systemLos.worst_grade}</span></div>
                  <div>{systemLos.pct_los_d_or_worse.toFixed(0)}% LOS D or worse</div>
                </div>
              </>
            )}
            <h4 className="text-xs font-semibold text-slate-400 mb-2">TCQSM Reference</h4>
            <table className="w-full text-[11px]">
              <tbody>
                {gradeRef.map((g) => (
                  <tr key={g.grade} className="border-b border-slate-800 hover:bg-slate-800/50">
                    <td className={`py-1 font-bold ${g.color}`}>{g.grade}</td>
                    <td className="py-1 text-slate-400">{g.range}</td>
                    <td className="py-1 text-slate-500">{g.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <p className="text-xs text-slate-400 mt-2">
        Grading follows the Transit Capacity and Quality of Service Manual (TCQSM, TCRP Report 165, 3rd Edition).
      </p>
    </section>
  )
}
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`

- [ ] **Commit**

```bash
git add go/web/src/components/RouteTable.tsx
git commit -m "feat: rework RouteTable with horizontal bars and dark sidebar"
```

---

## Task 9: Amenity Table Rework

**Files:**
- Modify: `go/internal/scoring/amenity.go` — add PctWithin45Min
- Rename/Replace: `go/web/src/components/AmenityCards.tsx` → `go/web/src/components/AmenityTable.tsx`
- Modify: `go/web/src/lib/types.ts`
- Modify: `go/web/src/App.tsx`

- [ ] **Add PctWithin45Min to AmenityResult in Go**

In `go/internal/scoring/amenity.go`, add field to `AmenityResult` struct (around line 27):

```go
PctWithin45Min float64 `json:"pct_within_45_min"`
```

In the `ComputeAmenityAccessibility` function, add counting for 45-min threshold alongside existing 30/60-min counts. In the loop that checks travel times (around lines 73-92), add:

```go
var within45 int
// Inside the loop over grid points:
if tt <= 45 {
    within45++
}
// After the loop:
result.PctWithin45Min = float64(within45) / float64(len(points)) * 100
```

- [ ] **Update TypeScript AmenityResult type**

In `go/web/src/lib/types.ts`, add to `AmenityResult`:

```typescript
pct_within_45_min: number
```

- [ ] **Create `go/web/src/components/AmenityTable.tsx`**

```tsx
import type { AmenityResult } from '../lib/types'

interface Props {
  amenities: AmenityResult[]
}

function pctColor(pct: number, threshold: number): string {
  return pct >= threshold ? 'text-emerald-600' : 'text-red-500'
}

export default function AmenityTable({ amenities }: Props) {
  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Access to Essential Services</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 font-semibold text-slate-600 sticky left-0 bg-slate-50">Destination</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Category</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">30 min</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">45 min</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">60 min</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Median Time</th>
              </tr>
            </thead>
            <tbody>
              {amenities.map((a, i) => (
                <tr key={a.name} className={`border-b border-slate-100 ${i % 2 === 1 ? 'bg-slate-50/50' : ''}`}>
                  <td className="px-4 py-3 font-medium text-slate-900 sticky left-0 bg-inherit">{a.name}</td>
                  <td className="px-4 py-3 text-slate-500">{a.category}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${pctColor(a.pct_within_30_min, 25)}`}>
                    {a.pct_within_30_min.toFixed(0)}%
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${pctColor(a.pct_within_45_min, 50)}`}>
                    {a.pct_within_45_min.toFixed(0)}%
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold ${pctColor(a.pct_within_60_min, 75)}`}>
                    {a.pct_within_60_min.toFixed(0)}%
                  </td>
                  <td className="px-4 py-3 text-right text-slate-700">
                    {a.mean_travel_time > 0 ? `${a.mean_travel_time.toFixed(0)} min` : '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Update App.tsx import**

Replace:
```tsx
import AmenityCards from './components/AmenityCards'
```
With:
```tsx
import AmenityTable from './components/AmenityTable'
```

Replace usage:
```tsx
{data.amenities && <AmenityTable amenities={data.amenities} />}
```

- [ ] **Delete old AmenityCards.tsx**

Run: `rm go/web/src/components/AmenityCards.tsx`

- [ ] **Build and verify**

Run: `cd go && go build ./cmd/tqi && cd web && npm run build`

- [ ] **Commit**

```bash
git add go/internal/scoring/amenity.go go/web/src/lib/types.ts go/web/src/components/AmenityTable.tsx go/web/src/App.tsx
git rm go/web/src/components/AmenityCards.tsx
git commit -m "feat: rework amenity cards into full table with 45-min column"
```

---

## Task 10: Heat Map Enhancements — Routes, Stops, Layer Control

**Files:**
- Modify: `go/internal/api/server.go` — add route_shapes and transit_stops to response
- Modify: `go/cmd/tqi/main.go` — extract route shapes and stops
- Modify: `go/web/src/components/HeatMap.tsx` — add layers

- [ ] **Add RouteShape and TransitStop types to Go**

In `go/internal/api/server.go`, add types and fields to PipelineResults:

```go
type RouteShape struct {
	RouteID   string      `json:"route_id"`
	RouteName string      `json:"route_name"`
	Color     string      `json:"color"`
	Points    [][]float64 `json:"points"`
}

type TransitStop struct {
	StopID   string  `json:"stop_id"`
	StopName string  `json:"stop_name"`
	Lat      float64 `json:"lat"`
	Lon      float64 `json:"lon"`
}
```

Add to PipelineResults:
```go
RouteShapes  []RouteShape  `json:"route_shapes,omitempty"`
TransitStops []TransitStop  `json:"transit_stops,omitempty"`
```

- [ ] **Extract route shapes and stops in pipeline**

In `go/cmd/tqi/main.go`, after parsing the feed, extract route shapes from the GTFS shapes or trip stop sequences. Add before the results assembly:

```go
// Extract transit stops
transitStops := make([]api.TransitStop, len(feed.Stops))
for i, s := range feed.Stops {
	transitStops[i] = api.TransitStop{
		StopID: s.StopID, StopName: s.StopName,
		Lat: s.Lat, Lon: s.Lon,
	}
}

// Extract route shapes from trip stop sequences
routeColors := []string{"#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"}
var routeShapes []api.RouteShape
for i, route := range feed.Routes {
	// Find first trip for this route
	var tripStopCoords [][]float64
	for _, trip := range feed.Trips {
		if trip.RouteID == route.RouteID {
			// Collect stop coordinates in order
			type stopSeq struct {
				seq int
				lat, lon float64
			}
			var seqs []stopSeq
			for _, st := range feed.StopTimes {
				if st.TripID == trip.TripID {
					for _, s := range feed.Stops {
						if s.StopID == st.StopID {
							seqs = append(seqs, stopSeq{st.StopSequence, s.Lat, s.Lon})
							break
						}
					}
				}
			}
			sort.Slice(seqs, func(a, b int) bool { return seqs[a].seq < seqs[b].seq })
			for _, s := range seqs {
				tripStopCoords = append(tripStopCoords, []float64{s.lat, s.lon})
			}
			break // first trip only
		}
	}
	if len(tripStopCoords) > 0 {
		routeShapes = append(routeShapes, api.RouteShape{
			RouteID:   route.RouteID,
			RouteName: route.RouteName,
			Color:     routeColors[i%len(routeColors)],
			Points:    tripStopCoords,
		})
	}
}
```

Add to results assembly:
```go
RouteShapes:  routeShapes,
TransitStops: transitStops,
```

- [ ] **Enhance HeatMap.tsx with layers**

Replace `go/web/src/components/HeatMap.tsx`:

```tsx
import { MapContainer, TileLayer, CircleMarker, Polyline, LayersControl, LayerGroup, Tooltip } from 'react-leaflet'
import type { GridScorePoint, RouteShape, TransitStop } from '../lib/types'
import 'leaflet/dist/leaflet.css'

interface Props {
  points: GridScorePoint[]
  routeShapes?: RouteShape[] | null
  transitStops?: TransitStop[] | null
}

function scoreColor(score: number): string {
  if (score >= 50) return '#10b981'
  if (score >= 25) return '#f59e0b'
  if (score > 0) return '#ef4444'
  return '#d1d5db'
}

function scoreOpacity(score: number, maxScore: number): number {
  if (maxScore <= 0) return 0.25
  return 0.25 + 0.35 * (score / maxScore)
}

export default function HeatMap({ points, routeShapes, transitStops }: Props) {
  const center: [number, number] = [49.168, -121.951]
  const maxScore = Math.max(...points.map((p) => p.score), 1)

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Spatial Heat Map</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 500 }}>
        <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
          <TileLayer
            attribution='&copy; <a href="https://carto.com">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <LayersControl position="topright">
            <LayersControl.Overlay checked name="TQI Grid">
              <LayerGroup>
                {points.map((p, i) => (
                  <CircleMarker
                    key={i}
                    center={[p.lat, p.lon]}
                    radius={4}
                    pathOptions={{ color: scoreColor(p.score), fillColor: scoreColor(p.score), fillOpacity: scoreOpacity(p.score, maxScore), weight: 0 }}
                  />
                ))}
              </LayerGroup>
            </LayersControl.Overlay>
            {transitStops && transitStops.length > 0 && (
              <LayersControl.Overlay name="Transit Stops">
                <LayerGroup>
                  {transitStops.map((s) => (
                    <CircleMarker
                      key={s.stop_id}
                      center={[s.lat, s.lon]}
                      radius={3}
                      pathOptions={{ color: '#1e293b', fillColor: '#1e293b', fillOpacity: 0.7, weight: 1 }}
                    >
                      <Tooltip>{s.stop_name}</Tooltip>
                    </CircleMarker>
                  ))}
                </LayerGroup>
              </LayersControl.Overlay>
            )}
            {routeShapes && routeShapes.length > 0 && (
              <LayersControl.Overlay name="Bus Routes">
                <LayerGroup>
                  {routeShapes.map((r) => (
                    <Polyline
                      key={r.route_id}
                      positions={r.points.map((p) => [p[0], p[1]] as [number, number])}
                      pathOptions={{ color: r.color, weight: 3, opacity: 0.7 }}
                    >
                      <Tooltip>{r.route_name}</Tooltip>
                    </Polyline>
                  ))}
                </LayerGroup>
              </LayersControl.Overlay>
            )}
          </LayersControl>
        </MapContainer>
      </div>
      <div className="flex gap-4 justify-center mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> ≥ 50</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-amber-500 inline-block" /> ≥ 25</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> &gt; 0</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-slate-300 inline-block" /> 0</span>
      </div>
    </section>
  )
}
```

- [ ] **Update HeatMap call in App.tsx**

```tsx
{data.grid_scores && (
  <HeatMap points={data.grid_scores} routeShapes={data.route_shapes} transitStops={data.transit_stops} />
)}
```

- [ ] **Build and verify**

Run: `cd go && go build ./cmd/tqi && cd web && npm run build`

- [ ] **Commit**

```bash
git add go/internal/api/server.go go/cmd/tqi/main.go go/web/src/components/HeatMap.tsx go/web/src/App.tsx
git commit -m "feat: add route lines, stop markers, and layer control to heat map"
```

---

## Task 11: Hero Restyle — 2-Column with Heatmap Preview

**Files:**
- Modify: `go/web/src/components/Hero.tsx`

- [ ] **Add Space Grotesk font to `go/web/index.html`**

In the `<head>` section, add alongside the existing Inter font import:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
```

- [ ] **Replace Hero.tsx with 2-column layout**

```tsx
import type { TQIResult } from '../lib/types'

interface Props {
  tqi: TQIResult
  category: string
  desc: string
  gridPoints: number
  nStops: number
}

function categoryColor(cat: string): string {
  if (cat.includes('Paradise') || cat.includes('Excellent')) return 'bg-emerald-100 text-emerald-700'
  if (cat.includes('Good')) return 'bg-blue-100 text-blue-700'
  if (cat.includes('Some')) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}

function barGradient(score: number): string {
  if (score >= 70) return 'from-emerald-400 to-emerald-500'
  if (score >= 40) return 'from-amber-400 to-amber-500'
  return 'from-red-400 to-red-500'
}

export default function Hero({ tqi, category, desc, gridPoints, nStops }: Props) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* Main score card */}
      <div className="lg:col-span-8 bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 relative overflow-hidden">
        <div className="absolute -top-20 -right-20 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl" />
        <div className="relative">
          <div className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 flex items-center gap-1 mb-4">
            <span className="material-symbols-outlined text-sm text-blue-500">location_on</span>
            British Columbia &gt; Fraser Valley
          </div>
          <h1 className="text-2xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 mb-2">
            Chilliwack Transit Quality Index
          </h1>
          <p className="text-sm text-slate-500 max-w-xl mb-6">
            Comprehensive multi-metric assessment of public transit service quality &mdash; coverage, speed, reliability, and accessibility.
          </p>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-600 mb-1">Overall Score</div>
          <div className="flex items-baseline gap-2 mb-3">
            <span className="text-5xl sm:text-7xl font-extrabold tabular-nums text-slate-900">
              {tqi.TQI.toFixed(1)}
            </span>
            <span className="text-2xl text-slate-400">/ 100</span>
          </div>
          <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden mb-3">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${barGradient(tqi.TQI)}`}
              style={{ width: `${tqi.TQI}%` }}
            />
          </div>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${categoryColor(category)}`}>
            {category}
          </span>
        </div>
      </div>

      {/* Heatmap preview */}
      <div className="lg:col-span-4 bg-slate-900 rounded-xl border border-slate-800 overflow-hidden relative hidden lg:flex flex-col justify-end min-h-[280px]">
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent z-10" />
        <div className="relative z-20 p-4 text-white">
          <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Spatial Coverage</div>
          <div className="text-sm font-semibold">{gridPoints.toLocaleString()} grid points</div>
          <div className="text-xs text-slate-400">{nStops} transit stops analyzed</div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Update Hero call in App.tsx**

```tsx
<Hero tqi={data.tqi} category={data.walkscore_category} desc={data.walkscore_desc} gridPoints={data.grid_points} nStops={data.n_stops} />
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`

- [ ] **Commit**

```bash
git add go/web/src/components/Hero.tsx go/web/src/App.tsx
git commit -m "feat: restyle Hero with 2-column layout and heatmap preview"
```

---

## Task 12: Minor Styling Tweaks — ScoreCards, WalkScoreTable, ScoreBreakdown, PTALChart

**Files:**
- Modify: `go/web/src/components/ScoreCards.tsx`
- Modify: `go/web/src/components/WalkScoreTable.tsx`
- Modify: `go/web/src/components/ScoreBreakdown.tsx`
- Modify: `go/web/src/components/PTALChart.tsx`

- [ ] **ScoreCards.tsx — add hover border effects**

Update each card's className to include hover border transition. In the card rendering section, change the card div className to:

```tsx
className={`bg-white rounded-xl border border-slate-200 p-4 transition-colors hover:border-${card.hoverColor}`}
```

Add `hoverColor` to each card definition: `'amber-400'`, `'blue-400'`, `'emerald-400'`, `'violet-400'`.

Update icon container to use 10% opacity background:

```tsx
<div className={`w-8 h-8 rounded-lg flex items-center justify-center ${card.iconBg}`}>
```

And update icon names to match Python: `star`, `location_on`, `speed`, `schedule`.

- [ ] **WalkScoreTable.tsx — change highlight to amber**

Replace `bg-blue-50 text-blue-700` with `bg-amber-50 text-amber-700` for the active row.
Add alternating stripe: `className={i % 2 === 1 ? 'bg-amber-50/50' : ''}` for non-active rows.

- [ ] **ScoreBreakdown.tsx — tooltip and label styling**

Add dark tooltip styling:
```tsx
<Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: 8, color: 'white', padding: '8px 12px', fontSize: 12 }} labelStyle={{ color: '#94a3b8' }} />
```

Add value labels above bars:
```tsx
<Bar ... label={{ position: 'top', fontSize: 11, fontWeight: 600, fill: '#334155' }}>
```

- [ ] **PTALChart.tsx — verify colors and add count labels**

Ensure colors match: 1a=#ef4444, 1b=#f97316, 2=#f59e0b, 3=#eab308, 4=#84cc16, 5=#22c55e, 6a=#10b981, 6b=#059669.

Add bar labels:
```tsx
<Bar ... label={{ position: 'top', fontSize: 10, fill: '#334155' }}>
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`

- [ ] **Commit**

```bash
git add go/web/src/components/ScoreCards.tsx go/web/src/components/WalkScoreTable.tsx go/web/src/components/ScoreBreakdown.tsx go/web/src/components/PTALChart.tsx
git commit -m "feat: minor styling tweaks to match Python report"
```

---

## Task 13: Isochrone Generation + Maps

**Files:**
- Create: `go/internal/isochrone/isochrone.go`
- Create: `go/internal/isochrone/isochrone_test.go`
- Modify: `go/internal/api/server.go`
- Modify: `go/cmd/tqi/main.go`
- Create: `go/web/src/components/IsochroneMaps.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Create `go/internal/isochrone/isochrone.go`**

```go
package isochrone

import (
	"encoding/json"
	"fmt"
	"math"

	"tqi/internal/grid"
	"tqi/internal/raptor"
)

type Result struct {
	DepartureTime string          `json:"departure_time"`
	Label         string          `json:"label"`
	GeoJSON       json.RawMessage `json:"geojson"`
}

type Band struct {
	MinMin float64 `json:"min_minutes"`
	MaxMin float64 `json:"max_minutes"`
	Color  string  `json:"color"`
}

var DefaultBands = []Band{
	{0, 15, "#2e7d32"},
	{15, 30, "#4caf50"},
	{30, 45, "#ff9800"},
	{45, 60, "#f44336"},
	{60, 90, "#b71c1c"},
}

// Compute generates isochrone GeoJSON for a single departure time.
// It runs RAPTOR from the origin to all grid points and groups results into travel-time bands.
func Compute(
	tt *raptor.FlatTimetable,
	originLat, originLon float64,
	departureMins int,
	points []grid.Point,
	stopLats, stopLons []float64,
	spacingM float64,
) (*Result, error) {
	// Find nearest stop to origin
	bestStop := -1
	bestDist := math.MaxFloat64
	for i := 0; i < len(stopLats); i++ {
		d := haversineM(originLat, originLon, stopLats[i], stopLons[i])
		if d < bestDist {
			bestDist = d
			bestStop = i
		}
	}
	if bestStop < 0 {
		return nil, fmt.Errorf("no stops found")
	}

	// Run RAPTOR
	sources := []raptor.SourceStop{{StopIdx: bestStop, ArrivalTime: float64(departureMins)}}
	arrivals := raptor.RunRAPTOR(tt, sources, 2, float64(departureMins)+90)

	// Map stops to nearest grid points and record travel times
	gridTT := make([]float64, len(points)) // travel time in minutes for each grid point
	for i := range gridTT {
		gridTT[i] = -1 // unreachable
	}

	// For each grid point, find nearest stop and use its arrival time
	for pi, pt := range points {
		bestS := -1
		bestD := 1000.0 // max 1km walk
		for si := 0; si < len(stopLats); si++ {
			d := haversineM(pt.Lat, pt.Lon, stopLats[si], stopLons[si])
			if d < bestD {
				bestD = d
				bestS = si
			}
		}
		if bestS >= 0 && arrivals[bestS] < 1e8 {
			walkMin := bestD / 80.0 // 80 m/min walking speed
			tt := (arrivals[bestS] - float64(departureMins)) + walkMin
			if tt > 0 && tt <= 90 {
				gridTT[pi] = tt
			}
		}
	}

	// Build GeoJSON: each grid cell is a small square polygon
	halfLat := (spacingM / 111320.0) / 2
	halfLon := (spacingM / (111320.0 * math.Cos(originLat*math.Pi/180))) / 2

	type feature struct {
		Type       string                 `json:"type"`
		Properties map[string]interface{} `json:"properties"`
		Geometry   struct {
			Type        string          `json:"type"`
			Coordinates [][][][]float64 `json:"coordinates"`
		} `json:"geometry"`
	}

	var features []feature
	for _, band := range DefaultBands {
		var coords [][][]float64
		for pi, pt := range points {
			tt := gridTT[pi]
			if tt >= band.MinMin && tt < band.MaxMin {
				coords = append(coords, [][]float64{
					{pt.Lon - halfLon, pt.Lat - halfLat},
					{pt.Lon + halfLon, pt.Lat - halfLat},
					{pt.Lon + halfLon, pt.Lat + halfLat},
					{pt.Lon - halfLon, pt.Lat + halfLat},
					{pt.Lon - halfLon, pt.Lat - halfLat},
				})
			}
		}
		if len(coords) > 0 {
			f := feature{
				Type: "Feature",
				Properties: map[string]interface{}{
					"band":  fmt.Sprintf("%g-%g min", band.MinMin, band.MaxMin),
					"color": band.Color,
				},
			}
			f.Geometry.Type = "MultiPolygon"
			for _, c := range coords {
				f.Geometry.Coordinates = append(f.Geometry.Coordinates, [][]float64(c))
			}
			// Fix: MultiPolygon coordinates need extra nesting
			multiCoords := make([][][][]float64, len(coords))
			for i, c := range coords {
				multiCoords[i] = [][][]float64{c}
			}
			f.Geometry.Coordinates = multiCoords
			features = append(features, f)
		}
	}

	fc := struct {
		Type     string    `json:"type"`
		Features []feature `json:"features"`
	}{Type: "FeatureCollection", Features: features}

	geojsonBytes, err := json.Marshal(fc)
	if err != nil {
		return nil, err
	}

	label := "AM Peak"
	if departureMins >= 720 {
		label = "Midday"
	}

	return &Result{
		DepartureTime: fmt.Sprintf("%02d:%02d", departureMins/60, departureMins%60),
		Label:         label,
		GeoJSON:       json.RawMessage(geojsonBytes),
	}, nil
}

func haversineM(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371000.0
	dLat := (lat2 - lat1) * math.Pi / 180
	dLon := (lon2 - lon1) * math.Pi / 180
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*math.Pi/180)*math.Cos(lat2*math.Pi/180)*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	return R * 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
}
```

- [ ] **Add IsochroneResult to PipelineResults**

In `go/internal/api/server.go`, add:
```go
import "tqi/internal/isochrone"
```

Add field to PipelineResults:
```go
Isochrones []isochrone.Result `json:"isochrones,omitempty"`
```

- [ ] **Wire isochrone computation into pipeline**

In `go/cmd/tqi/main.go`, after computing route shapes and before results assembly:

```go
// Compute isochrones from stop centroid
var isoResults []isochrone.Result
centroidLat, centroidLon := 0.0, 0.0
for _, s := range feed.Stops {
	centroidLat += s.Lat
	centroidLon += s.Lon
}
centroidLat /= float64(len(feed.Stops))
centroidLon /= float64(len(feed.Stops))

for _, depMin := range []int{480, 720} { // 08:00 and 12:00
	iso, err := isochrone.Compute(flatTT, centroidLat, centroidLon, depMin, points, stopLats, stopLons, spacingM)
	if err != nil {
		log.Printf("isochrone at %d min: %v", depMin, err)
		continue
	}
	isoResults = append(isoResults, *iso)
}
```

Add to results assembly:
```go
Isochrones: isoResults,
```

Note: `flatTT` and `spacingM` must be accessible at this point in the pipeline. Check the actual variable names used in `main.go` and adjust accordingly.

- [ ] **Create `go/web/src/components/IsochroneMaps.tsx`**

```tsx
import { MapContainer, TileLayer, GeoJSON, LayersControl } from 'react-leaflet'
import type { IsochroneResult } from '../lib/types'
import 'leaflet/dist/leaflet.css'

interface Props {
  isochrones: IsochroneResult[]
}

const bandColors: Record<string, string> = {
  '0-15 min': '#2e7d32',
  '15-30 min': '#4caf50',
  '30-45 min': '#ff9800',
  '45-60 min': '#f44336',
  '60-90 min': '#b71c1c',
}

export default function IsochroneMaps({ isochrones }: Props) {
  if (!isochrones || isochrones.length === 0) return null

  const center: [number, number] = [49.168, -121.951]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Isochrone Maps</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {isochrones.map((iso) => (
          <div key={iso.departure_time} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className={`px-3 py-2 border-b border-slate-200 flex items-center gap-2 ${iso.label === 'AM Peak' ? 'bg-blue-50' : 'bg-violet-50'}`}>
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold text-white ${iso.label === 'AM Peak' ? 'bg-blue-500' : 'bg-violet-500'}`}>
                {iso.label}
              </span>
              <span className="text-sm font-semibold text-slate-700">{iso.departure_time} Isochrone</span>
            </div>
            <div style={{ height: 400 }}>
              <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
                <TileLayer
                  attribution='&copy; CARTO'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                />
                <LayersControl position="topright">
                  {(iso.geojson as any)?.features?.map((feature: any, i: number) => {
                    const band = feature.properties?.band ?? ''
                    const color = feature.properties?.color ?? bandColors[band] ?? '#999'
                    return (
                      <LayersControl.Overlay key={i} checked name={band}>
                        <GeoJSON
                          data={{ type: 'FeatureCollection', features: [feature] } as any}
                          style={() => ({ fillColor: color, color: color, weight: 0.5, fillOpacity: 0.4 })}
                        />
                      </LayersControl.Overlay>
                    )
                  })}
                </LayersControl>
              </MapContainer>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-3 justify-center mt-2 text-[10px] text-slate-500">
        {Object.entries(bandColors).map(([label, color]) => (
          <span key={label} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded inline-block" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
    </section>
  )
}
```

- [ ] **Add to App.tsx**

Import:
```tsx
import IsochroneMaps from './components/IsochroneMaps'
```

Add after AmenityTable:
```tsx
{data.isochrones && <IsochroneMaps isochrones={data.isochrones} />}
```

- [ ] **Build and verify**

Run: `cd go && go build ./cmd/tqi && cd web && npm run build`

- [ ] **Commit**

```bash
git add go/internal/isochrone/ go/internal/api/server.go go/cmd/tqi/main.go go/web/src/components/IsochroneMaps.tsx go/web/src/App.tsx
git commit -m "feat: add isochrone generation and maps"
```

---

## Task 14: Equity Overlay

**Files:**
- Create: `go/internal/equity/equity.go`
- Modify: `go/internal/api/server.go`
- Modify: `go/cmd/tqi/main.go`
- Create: `go/web/src/components/EquityMap.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Create `go/internal/equity/equity.go`**

```go
package equity

import (
	"encoding/json"
	"math"
	"os"

	"tqi/internal/grid"
)

type Result struct {
	GeoJSON     json.RawMessage `json:"geojson"`
	Correlation float64         `json:"tqi_income_correlation"`
}

type daFeature struct {
	DGUID      string  `json:"dguid"`
	Income     float64 `json:"median_income"`
	Population int     `json:"population"`
	MeanTQI    float64 `json:"mean_tqi"`
}

// Compute loads DA boundaries and income data, cross-references with grid TQI scores,
// and returns a GeoJSON with TQI and income properties per DA.
// boundaryPath: GeoJSON file with DA polygons (properties must include "DGUID")
// incomePath: JSON file mapping DGUID → {median_income, population}
func Compute(boundaryPath, incomePath string, points []grid.Point, gridScores []float64) (*Result, error) {
	// Load boundary GeoJSON
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

	// Load income data
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

	// For each DA feature, compute mean TQI of grid points within it
	// Simplified: use bounding box check (point-in-bbox) rather than full polygon containment
	type enrichedFeature struct {
		raw     json.RawMessage
		meanTQI float64
		income  float64
	}

	var enriched []enrichedFeature
	var tqiVals, incomeVals []float64

	for _, rawFeature := range fc.Features {
		var f struct {
			Properties struct {
				DGUID string `json:"DGUID"`
			} `json:"properties"`
			Geometry struct {
				Type        string          `json:"type"`
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

		// Get bounding box of the polygon
		bbox := extractBBox(f.Geometry.Coordinates)
		if bbox == nil {
			continue
		}

		// Find grid points within bbox
		var tqiSum float64
		var count int
		for i, pt := range points {
			if pt.Lat >= bbox[1] && pt.Lat <= bbox[3] && pt.Lon >= bbox[0] && pt.Lon <= bbox[2] {
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

		enriched = append(enriched, enrichedFeature{
			raw:     rawFeature,
			meanTQI: meanTQI,
			income:  inc.MedianIncome,
		})
		tqiVals = append(tqiVals, meanTQI)
		incomeVals = append(incomeVals, inc.MedianIncome)
	}

	// Compute Pearson correlation
	corr := pearson(tqiVals, incomeVals)

	// Build output GeoJSON with enriched properties
	var outFeatures []json.RawMessage
	for _, ef := range enriched {
		// Inject mean_tqi into feature properties
		var f map[string]json.RawMessage
		json.Unmarshal(ef.raw, &f)
		var props map[string]interface{}
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
	// Flatten all coordinates to find bounding box
	var allCoords [][]float64
	var flat interface{}
	json.Unmarshal(coords, &flat)
	flattenCoords(flat, &allCoords)
	if len(allCoords) == 0 {
		return nil
	}
	minLon, minLat := allCoords[0][0], allCoords[0][1]
	maxLon, maxLat := minLon, minLat
	for _, c := range allCoords[1:] {
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

func flattenCoords(v interface{}, out *[][]float64) {
	switch arr := v.(type) {
	case []interface{}:
		if len(arr) >= 2 {
			if _, ok := arr[0].(float64); ok {
				coord := make([]float64, len(arr))
				for i, x := range arr {
					coord[i] = x.(float64)
				}
				*out = append(*out, coord)
				return
			}
		}
		for _, item := range arr {
			flattenCoords(item, out)
		}
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
```

- [ ] **Add EquityResult to PipelineResults**

In `go/internal/api/server.go`:
```go
import "tqi/internal/equity"
```

Add field:
```go
Equity *equity.Result `json:"equity,omitempty"`
```

- [ ] **Wire into pipeline (conditional — only if census data files exist)**

In `go/cmd/tqi/main.go`, after isochrone computation:

```go
// Equity overlay (optional — requires census data files)
boundaryPath := filepath.Join(dataDir, "census", "da_boundaries.geojson")
incomePath := filepath.Join(dataDir, "census", "da_income.json")
if _, err := os.Stat(boundaryPath); err == nil {
	if _, err := os.Stat(incomePath); err == nil {
		// Extract per-origin scores as flat slice
		gridScoreValues := make([]float64, len(gridScores))
		for i, gs := range gridScores {
			gridScoreValues[i] = gs.Score
		}
		equityResult, err := equity.Compute(boundaryPath, incomePath, points, gridScoreValues)
		if err != nil {
			log.Printf("equity computation: %v", err)
		} else {
			results.Equity = equityResult
		}
	}
}
```

- [ ] **Create `go/web/src/components/EquityMap.tsx`**

```tsx
import { MapContainer, TileLayer, GeoJSON, LayersControl } from 'react-leaflet'
import type { EquityResult } from '../lib/types'
import 'leaflet/dist/leaflet.css'

interface Props {
  equity: EquityResult
}

function tqiColor(tqi: number): string {
  if (tqi >= 50) return '#22c55e'
  if (tqi >= 25) return '#f59e0b'
  return '#ef4444'
}

function incomeColor(income: number): string {
  if (income >= 60000) return '#4c1d95'
  if (income >= 40000) return '#7c3aed'
  return '#c4b5fd'
}

export default function EquityMap({ equity }: Props) {
  const center: [number, number] = [49.168, -121.951]
  const geojson = equity.geojson as any

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-slate-900">Equity Overlay</h2>
        <div className="flex-1 border-t border-slate-200" />
      </div>
      <p className="text-xs text-slate-500 mb-3">Cross-referenced with census income data by Dissemination Area</p>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 500 }}>
        <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={true}>
          <TileLayer
            attribution='&copy; CARTO'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
          <LayersControl position="topright">
            <LayersControl.Overlay checked name="TQI by DA">
              <GeoJSON
                data={geojson}
                style={(feature: any) => ({
                  fillColor: tqiColor(feature?.properties?.mean_tqi ?? 0),
                  color: '#475569',
                  weight: 1,
                  fillOpacity: 0.5,
                })}
                onEachFeature={(feature: any, layer: any) => {
                  const p = feature?.properties
                  if (p) {
                    layer.bindPopup(`<b>${p.DGUID}</b><br/>TQI: ${p.mean_tqi?.toFixed(1)}<br/>Income: $${p.median_income?.toLocaleString()}`)
                  }
                }}
              />
            </LayersControl.Overlay>
            <LayersControl.Overlay name="Income by DA">
              <GeoJSON
                data={geojson}
                style={(feature: any) => ({
                  fillColor: incomeColor(feature?.properties?.median_income ?? 0),
                  color: '#475569',
                  weight: 1,
                  fillOpacity: 0.5,
                })}
              />
            </LayersControl.Overlay>
          </LayersControl>
        </MapContainer>
      </div>
      <div className="mt-2 flex items-center justify-center gap-2 text-xs text-slate-500">
        <span className="material-symbols-outlined text-violet-500 text-sm">analytics</span>
        TQI–Income correlation: <span className="font-bold text-violet-600">r = {equity.tqi_income_correlation.toFixed(3)}</span>
      </div>
    </section>
  )
}
```

- [ ] **Add to App.tsx**

Import:
```tsx
import EquityMap from './components/EquityMap'
```

Add after IsochroneMaps:
```tsx
{data.equity && <EquityMap equity={data.equity} />}
```

- [ ] **Build and verify**

Run: `cd go && go build ./cmd/tqi && cd web && npm run build`

- [ ] **Commit**

```bash
git add go/internal/equity/ go/internal/api/server.go go/cmd/tqi/main.go go/web/src/components/EquityMap.tsx go/web/src/App.tsx
git commit -m "feat: add equity overlay with census DA boundaries and income correlation"
```

---

## Task 15: Methodology + Standards + Footer

**Files:**
- Create: `go/web/src/components/Methodology.tsx`
- Create: `go/web/src/components/Standards.tsx`
- Modify: `go/web/src/components/Footer.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Create `go/web/src/components/Methodology.tsx`**

```tsx
export default function Methodology() {
  return (
    <section className="bg-white rounded-xl border border-slate-200 border-l-[6px] border-l-blue-500 p-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-blue-500">lightbulb</span>
        <h2 className="text-xl font-bold text-slate-900">Methodology</h2>
      </div>
      <div className="text-sm text-slate-600 leading-relaxed space-y-3">
        <p>
          The Transit Quality Index (TQI) uses the RAPTOR (Round-bAsed Public Transit Optimized Router) algorithm
          to compute fastest journeys between all origin-destination pairs across multiple departure times.
          A 250m grid covers the study area, with travel times computed to every other grid point.
        </p>
        <p>
          The Transit Speed Ratio (TSR) measures effective door-to-door speed including walking, waiting,
          and in-vehicle time. Coverage scores reflect what fraction of the city is reachable by transit.
          Speed scores compare transit performance against walking. Reliability is measured via the
          coefficient of variation of travel times across departure windows.
        </p>
        <p>
          The overall TQI score (0-100) combines coverage, speed, and reliability into a single index.
          Route-level grading follows the Transit Capacity and Quality of Service Manual (TCQSM).
          Accessibility levels use Transport for London's PTAL methodology.
        </p>
      </div>
    </section>
  )
}
```

- [ ] **Create `go/web/src/components/Standards.tsx`**

```tsx
export default function Standards() {
  return (
    <section className="bg-white rounded-xl border border-slate-200 border-l-[6px] border-l-violet-500 p-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="material-symbols-outlined text-violet-500">menu_book</span>
        <h2 className="text-xl font-bold text-slate-900">Standards &amp; Sources</h2>
      </div>
      <div className="text-sm text-slate-600 leading-relaxed space-y-3">
        <p>
          <strong>Walk Score Transit Score</strong> — walkscore.com methodology for classifying transit service
          quality on a 0-100 scale based on distance to nearby transit and frequency of service.
        </p>
        <p>
          <strong>TCQSM</strong> — Transit Capacity and Quality of Service Manual, TCRP Report 165, 3rd Edition.
          Grades A-F based on median headway: A ≤ 10 min, B ≤ 14, C ≤ 20, D ≤ 30, E ≤ 60, F &gt; 60.
        </p>
        <p>
          <strong>PTAL</strong> — Public Transport Accessibility Level, Transport for London methodology.
          Measures network density and service frequency within walking distance (640m for bus).
          Grades from 1a (worst) to 6b (best).
        </p>
        <p>
          <strong>RAPTOR</strong> — Round-bAsed Public Transit Optimized Router (Delling et al., 2015).
          Multi-criteria journey planning algorithm operating directly on GTFS timetable data.
        </p>
      </div>
    </section>
  )
}
```

- [ ] **Slim down Footer.tsx**

```tsx
interface Props {
  gridPoints: number
  stops: number
}

export default function Footer({ gridPoints, stops }: Props) {
  return (
    <footer className="border-t border-slate-200 pt-6 mt-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
            <span className="material-symbols-outlined text-white text-xl">directions_bus</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-700">Chilliwack Transit Quality Index</div>
            <div className="text-xs text-slate-400">v0.1.0</div>
          </div>
        </div>
        <div className="text-xs text-slate-400 italic sm:ml-auto max-w-md">
          Generated {new Date().toLocaleDateString()} from BC Transit GTFS data.
          {gridPoints > 0 && ` ${gridPoints.toLocaleString()} grid points, ${stops} stops analyzed.`}
          {' '}Built with Go + React + Recharts + Leaflet.
        </div>
      </div>
    </footer>
  )
}
```

- [ ] **Update App.tsx with new components and final section order**

Add imports:
```tsx
import Methodology from './components/Methodology'
import Standards from './components/Standards'
```

Final Dashboard render order:
```tsx
<Hero tqi={data.tqi} category={data.walkscore_category} desc={data.walkscore_desc} gridPoints={data.grid_points} nStops={data.n_stops} />
<ScoreCards tqi={data.tqi} />
{data.narrative && <Narrative paragraphs={data.narrative} />}
<ScoreBreakdown tqi={data.tqi} />
<WalkScoreTable currentTQI={data.tqi.TQI} />
{data.route_los && <RouteTable routes={data.route_los} systemLos={data.system_los} />}
{data.detailed_analysis && <CoverageStats da={data.detailed_analysis} gridPoints={data.grid_points} nStops={data.n_stops} />}
{data.detailed_analysis && <SpeedAnalysis da={data.detailed_analysis} />}
<TimeProfile data={data.tqi.TimeProfile} da={data.detailed_analysis} />
{data.ptal && <PTALChart ptal={data.ptal} />}
{data.grid_scores && <HeatMap points={data.grid_scores} routeShapes={data.route_shapes} transitStops={data.transit_stops} />}
{data.detailed_analysis?.top_origins && <TopOrigins origins={data.detailed_analysis.top_origins} />}
{data.amenities && <AmenityTable amenities={data.amenities} />}
{data.isochrones && <IsochroneMaps isochrones={data.isochrones} />}
{data.equity && <EquityMap equity={data.equity} />}
{data.detailed_analysis && <ReliabilityHistogram da={data.detailed_analysis} />}
<Methodology />
<Standards />
<Footer gridPoints={data.grid_points} stops={data.n_stops} />
```

- [ ] **Build and verify**

Run: `cd go/web && npm run build`

- [ ] **Commit**

```bash
git add go/web/src/components/Methodology.tsx go/web/src/components/Standards.tsx go/web/src/components/Footer.tsx go/web/src/App.tsx
git commit -m "feat: add Methodology, Standards sections and slim Footer"
```

---

## Task 16: Final Build, Embed, and Playwright Verification

**Files:**
- Modify: `go/web/dist/` (rebuilt)
- Modify: `e2e/dashboard.spec.js`

- [ ] **Rebuild frontend**

Run: `cd go/web && npm run build`
Expected: builds successfully, output in `dist/`

- [ ] **Rebuild Go binary (re-embeds frontend)**

Run: `cd go && go build -o tqi ./cmd/tqi`
Expected: compiles without errors

- [ ] **Start server and run Playwright tests**

Start server:
```bash
./go/tqi serve --port 8080 &
```

Wait for startup, then run:
```bash
npx playwright test e2e/dashboard.spec.js --project=desktop
```

Expected: all tests pass (no JS errors, no NaN/undefined, route table visible)

- [ ] **Add new Playwright assertions for new sections**

Update `e2e/dashboard.spec.js` to add checks for new sections:

```javascript
test('coverage stats section renders', async ({ page }) => {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  const heading = page.locator('text=Coverage Analysis');
  await expect(heading.first()).toBeVisible();
});

test('speed analysis section renders', async ({ page }) => {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  const heading = page.locator('text=Speed Analysis');
  await expect(heading.first()).toBeVisible();
});

test('methodology section renders', async ({ page }) => {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  const heading = page.locator('text=Methodology');
  await expect(heading.first()).toBeVisible();
});
```

- [ ] **Run full test suite**

```bash
npx playwright test e2e/dashboard.spec.js --project=desktop
```

Expected: all tests pass

- [ ] **Commit**

```bash
git add e2e/dashboard.spec.js
git commit -m "test: add Playwright assertions for new dashboard sections"
```
