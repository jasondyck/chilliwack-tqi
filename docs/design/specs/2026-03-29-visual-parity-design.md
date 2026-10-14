# Visual Parity: React Frontend ↔ Python Report

**Date:** 2026-03-29
**Goal:** Make the Go/React frontend visually identical to the Python-generated HTML report.
**Approach:** Vertical slices — for each section, extend the Go API then build/update the React component.
**Charting:** Stay with Recharts, style to match Chart.js look (gradients, tooltips, bar radius).
**Maps:** Render natively in Leaflet with GeoJSON from the Go API (no Folium iframes).

---

## 1. Go API Extensions

### 1.1 DetailedAnalysis Struct

Add a `DetailedAnalysis` struct to `internal/scoring/` and include it in the `PipelineResults` response under `"detailed_analysis"`.

```go
type DetailedAnalysis struct {
    // Coverage
    NOriginsWithService     int     `json:"n_origins_with_service"`
    NTransitDesertOrigins   int     `json:"n_transit_desert_origins"`
    TransitDesertPct        float64 `json:"transit_desert_pct"`
    NValidPairs             int     `json:"n_valid_pairs"`
    NReachablePairs         int     `json:"n_reachable_pairs"`
    ReachabilityRatePct     float64 `json:"reachability_rate_pct"`
    MaxOriginReachabilityPct float64 `json:"max_origin_reachability_pct"`

    // Speed / TSR
    MeanTSR                  float64            `json:"mean_tsr"`
    MedianTSR                float64            `json:"median_tsr"`
    TSRPercentiles           map[string]float64 `json:"tsr_percentiles"`
    TSRSlowerThanWalkingPct  float64            `json:"tsr_slower_than_walking_pct"`
    TSR5To10Pct              float64            `json:"tsr_5_to_10_pct"`
    TSR10To20Pct             float64            `json:"tsr_10_to_20_pct"`
    TSR20PlusPct             float64            `json:"tsr_20_plus_pct"`

    // Travel time
    MeanTravelTimeMin        float64            `json:"mean_travel_time_min"`
    MedianTravelTimeMin      float64            `json:"median_travel_time_min"`
    TravelTimePercentiles    map[string]float64 `json:"travel_time_percentiles"`

    // Time-of-day peaks
    PeakSlot    string  `json:"peak_slot"`
    PeakTQI     float64 `json:"peak_tqi"`
    LowestSlot  string  `json:"lowest_slot"`
    LowestTQI   float64 `json:"lowest_tqi"`

    // Best-connected locations
    TopOrigins []TopOrigin `json:"top_origins"`

    // Reliability histogram
    ReliabilityHistogram HistogramData `json:"reliability_histogram"`

    // PTAL distribution (grade → count)
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

**Computation:** Most of these derive from the existing `Metrics` matrices (`Reachability`, `MeanTravelTime`, `DistancesKM`, `TravelTimeStd`) which are already computed but excluded from JSON via `json:"-"`. The pipeline should build `DetailedAnalysis` from these matrices before discarding them.

- **Coverage stats:** Count origins where any destination is reachable within 90 min. Transit deserts = origins with no stop within 800m (use stop coordinates vs grid coordinates). OD pairs = count non-zero entries in reachability matrix.
- **TSR stats:** Compute TSR = distance_km / (travel_time_min / 60) for each reachable OD pair. Aggregate into percentiles and speed bands.
- **Travel time stats:** Percentiles from the flattened reachable travel-time values.
- **Peak/low:** Scan existing `TimeProfile` for max/min TQI scores.
- **Top origins:** Sort origins by reachability count descending, take top 10.
- **Reliability histogram:** Bin the per-origin CV values (already computed for `ReliabilityCV`) into 25 bins.
- **PTAL distribution:** Count occurrences of each grade in the existing `PTALResult.Grades` array. This is a simple aggregation, not a new computation — the per-grid-point grades are already computed.

### 1.2 Isochrone Generation

New package: `internal/isochrone/`

**Input:** GTFS feed, origin coordinates (centroid of all transit stops, matching Python's behavior), departure times (08:00, 12:00).
**Process:** Run RAPTOR from origin at each departure time. For each destination grid point, record shortest travel time. Group destinations into bands (0-15, 15-30, 30-45, 45-60, 60-90 min). Generate concave hulls or grid-cell polygons for each band.
**Output:** GeoJSON FeatureCollection per departure time, with features for each travel-time band.

```go
type IsochroneResult struct {
    DepartureTime string          `json:"departure_time"`
    Label         string          `json:"label"`
    GeoJSON       json.RawMessage `json:"geojson"`
}
```

Add to API response: `"isochrones": [IsochroneResult]`

**Simplification:** Use grid-cell squares (250m × 250m polygons at each grid point) rather than true concave hulls. This matches the heatmap grid resolution and avoids complex geometry libraries. Each band is a MultiPolygon of grid cells in that travel-time range.

### 1.3 Equity Overlay

New package: `internal/equity/`

**Input:** Grid TQI scores, StatCan Dissemination Area boundaries (GeoJSON), income data (CSV).
**Process:** Load DA boundaries. Join income data by DGUID. For each DA, compute mean TQI of grid points within the polygon. Compute Pearson correlation between mean DA TQI and median income.
**Output:** GeoJSON with TQI and income properties per DA, plus correlation coefficient.

```go
type EquityResult struct {
    GeoJSON     json.RawMessage `json:"geojson"`
    Correlation float64         `json:"tqi_income_correlation"`
}
```

Add to API response: `"equity": EquityResult` (nullable — omitted if census data not available).

**Data files:** Census DA boundaries (StatCan 2021 Census, Dissemination Area boundary shapefile for BC, converted to GeoJSON) and income data (StatCan Census Profile table 98-10-0006, median total income by DA). These should be downloaded/cached alongside GTFS data. The `download` command can be extended to fetch these from the StatCan open data portal, or they can be bundled as static assets in `data/census/`.

### 1.4 Additional API Fields

Add to existing response (currently missing):
- `AmenityResult` struct needs a new field: `PctWithin45Min float64 json:"pct_within_45_min"`. Compute during amenity analysis alongside the existing 30/60-min fields.
- Route stops and route shapes for the heat map layer control (polylines + stop markers)

```go
type RouteShape struct {
    RouteID   string      `json:"route_id"`
    RouteName string      `json:"route_name"`
    Color     string      `json:"color"`
    Points    [][]float64 `json:"points"` // [[lat, lon], ...]
}

type TransitStop struct {
    StopID   string  `json:"stop_id"`
    StopName string  `json:"stop_name"`
    Lat      float64 `json:"lat"`
    Lon      float64 `json:"lon"`
}
```

Add to response: `"route_shapes": []RouteShape`, `"transit_stops": []TransitStop`

---

## 2. Frontend Sections (top-to-bottom)

### 2.1 Hero (restyle existing)

**Current:** Single-column score display with progress bar and category badge.
**Target:** Two-column grid on desktop (8-col score + 4-col heatmap thumbnail).

- Left column: breadcrumb ("British Columbia > Fraser Valley"), title, subtitle, large score display, progress bar, category badge.
- Right column: dark card (slate-900 bg) showing a miniature version of the heat map as a preview. Gradient overlay with metadata text (grid points, stops).
- Decorative gradient blob in top-right corner: `bg-amber-500/5`, 256px, blur-3xl.
- Labels use Space Grotesk font, uppercase, tracking-wider.
- Score label in amber/warning color.
- Mobile: stacks to single column, heatmap preview hidden.

### 2.2 Score Cards (minor tweaks)

- Add hover effect: `transition-colors` on border, border changes to semantic color on hover (amber for TQI, blue for coverage, emerald for speed, violet for reliability).
- Icon container: 32px square, rounded-lg, semantic color at 10% opacity background.
- Match Material icon names: `star` (TQI), `location_on` (coverage), `speed` (speed), `schedule` (reliability).

### 2.3 Narrative (no changes needed)

Already matches — blue left-border card with lightbulb icon.

### 2.4 Score Breakdown (minor Recharts styling)

- Match bar border-radius: 4px.
- Tooltip: slate-800 background, white text, rounded-lg, 10px padding.
- Bar colors: blue (#3b82f6) for coverage, emerald (#10b981) for speed, amber (#f59e0b) for TQI.
- Add value labels above bars (bold, slate-900).

### 2.5 Walk Score Table (color change)

- Change highlighted current-range row from blue to amber (`bg-amber-50`, `text-amber-700`).
- Add alternating row stripes: every other row gets `bg-amber-50/50`.

### 2.6 Route-Level LOS — TCQSM (major rework)

**Current:** HTML table with grade badges.
**Target:** Horizontal bar chart + dark sidebar.

**Layout:** 2-column grid on desktop. Left: headway bars. Right: dark sidebar (280px).
**Mobile:** Stacks vertically. Bars section at full width. Sidebar below at full width.

**Headway bars (left column):**
- Section title: "Headway by Route"
- Each route row: route number (36px fixed) | route name (truncated, 140px) | horizontal bar | LOS badge (28px circle)
- Bar container: slate-100 background, 24px height, rounded
- Bar fill: width = `min(headway, 80) / 80 * 100%`
- Bar color by grade: A=#059669, B=#22c55e, C=#84cc16, D=#f59e0b, E=#f97316, F=#e11d48
- Headway value label inside bar (right-aligned, white, bold, 11px)
- LOS badge: 28px circle, grade-colored background (light), grade-colored text (dark)
- Minimum bar section width: 100px. If container is narrower, enable horizontal scroll.

**Dark sidebar (right column):**
- Background: slate-900
- Border-radius: right corners only on desktop, all corners on mobile
- System summary: best/worst grades with colored text
- Median headway with progress bar
- TCQSM reference table: 6 rows (A-F), columns: grade (colored), headway range, description
- Row hover: bg-slate-800/50

### 2.7 Coverage Analysis (new component: `CoverageStats.tsx`)

6-stat grid. 3 columns on desktop, 2 on mobile. Minimum card width: 150px.

Cards:
1. Grid Points — plain (integer, no accent)
2. Transit Stops — plain (integer, no accent)
3. Transit Deserts — red left-border accent, red value text, percentage
4. With Service — plain (integer)
5. OD Reachable — amber left-border accent, amber value text, percentage
6. Best Location — plain, percentage

Card styling: white bg, slate-200 border, rounded-xl, 16px padding. Value: 28px, extrabold, tabular-nums. Label: 11px, semibold, uppercase, tracking-wider, slate-500.

### 2.8 Speed Analysis (new component: `SpeedAnalysis.tsx`)

Three sub-sections stacked vertically:

**A) TSR Doughnut + Metric Cards** (side-by-side on desktop, stacked on mobile):
- Left: Recharts PieChart with 55% inner radius (doughnut). 4 segments: <5 km/h (red), 5-10 (amber), 10-20 (green), 20+ (blue). Center label: mean TSR value + "km/h avg TSR". Legend below with circular markers.
- Right: 2×2 grid of metric cards:
  - Mean TSR (amber left-border)
  - Median TSR (plain)
  - Slower than walking % (red left-border, red text)
  - Mean trip duration (plain)

**B) Travel Time Distribution:**
- Recharts BarChart with 5 bars (P10, P25, P50, P75, P90).
- Bar colors: green→red gradient (P10=#22c55e, P25=#84cc16, P50=#f59e0b, P75=#f97316, P90=#ef4444).
- Value labels above bars.
- White card container with title "Travel Time Distribution (minutes)".

### 2.9 Time Profile (enhance existing)

Add to existing AreaChart:
- AM peak reference band: ReferenceArea from 07:00 to 09:00, amber fill at 50% opacity, label "AM Peak"
- PM peak reference band: ReferenceArea from 15:00 to 18:00, amber fill at 50% opacity, label "PM Peak"
- Below chart: two cards side-by-side
  - Peak time card: green left-border, trending_up icon, peak slot + TQI value
  - Lowest time card: red left-border, trending_down icon, lowest slot + TQI value

### 2.10 PTAL Distribution (minor styling)

- Verify bar colors match Python gradient: 1a=#ef4444, 1b=#f97316, 2=#f59e0b, 3=#eab308, 4=#84cc16, 5=#22c55e, 6a=#10b981, 6b=#059669
- Add count labels above bars.
- Ensure consistent height (288px) matching Python.

### 2.11 Spatial Heat Map (enhance existing)

Add to existing Leaflet map:
- **Route polylines layer:** Render `route_shapes` as colored polylines (3px weight). Each route gets a distinct color.
- **Stop markers layer:** Render `transit_stops` as small circles (radius 3px, dark navy fill).
- **Layer control:** Leaflet LayersControl with toggleable overlays: "TQI Grid", "Transit Stops", "Bus Routes".
- Match Python's CartoDB positron tile layer.
- Grid circle styling: match Python's opacity logic (25%-60% based on normalized score).

### 2.12 Best-Connected Locations (new component: `TopOrigins.tsx`)

Grid of location cards. 3 columns on desktop, 2 on tablet, 1 on mobile.

Each card: white bg, slate-200 border, rounded-xl. Contains:
- Lat/lon coordinates in tabular-nums, slate-700
- Reachability percentage in primary blue, bold, right-aligned
- Small map pin icon

### 2.13 Access to Essential Services (rework `AmenityCards.tsx` → `AmenityTable.tsx`)

**Current:** Card grid showing name, category, 30-min %, 60-min %, mean time.
**Target:** Full-width responsive table.

Columns: Destination | Category | 30-min % | 45-min % | 60-min % | Median Time
- Header: uppercase, slate-50 bg, semibold
- Alternating row backgrounds: normal / slate-50/50
- Color-coded percentages: red if below threshold, green if above
- Horizontal scroll on mobile with sticky first column

### 2.14 Isochrone Maps (new component: `IsochroneMaps.tsx`)

Two maps side-by-side on desktop, stacked on mobile.

Each map:
- White card with colored header bar (blue badge "AM Peak" / purple badge "Midday")
- Leaflet MapContainer rendering GeoJSON polygons
- 5 layers: 0-15 min (#2e7d32), 15-30 (#4caf50), 30-45 (#ff9800), 45-60 (#f44336), 60-90 (#b71c1c)
- Origin marker: black star icon at center
- Layer control for toggling bands
- Height: 300px mobile, 450px desktop
- Shared color legend below both maps

### 2.15 Equity Overlay (new component: `EquityMap.tsx`)

Single Leaflet map with two toggleable choropleth layers:
- TQI layer (default visible): red→green gradient based on mean DA TQI
- Income layer (hidden by default): light purple→dark blue based on median income
- Layer control to toggle between them
- Popup on click: DGUID, TQI value or income, population
- Below map: correlation stat badge ("TQI–Income correlation: r = 0.342") in purple

### 2.16 Reliability Histogram (new component: `ReliabilityHistogram.tsx`)

Recharts BarChart:
- Purple bars (#8b5cf6) with white edges
- X-axis: Coefficient of Variation bin labels
- Y-axis: Grid point count
- Subtitle text: "Lower CV = more predictable trip times"
- Height: 256px
- Card container: white bg, slate-200 border

### 2.17 Methodology (extract from Footer)

New standalone component: `Methodology.tsx`
- White card, blue left-border (6px), rounded-xl
- Lightbulb icon in blue
- Title: "Methodology" in 2xl bold
- Body: Paragraphs explaining RAPTOR algorithm, TSR computation, scoring methodology
- Content is static text (hardcoded, matching Python report)

### 2.18 Standards & Sources (new component: `Standards.tsx`)

- White card, purple left-border (6px), rounded-xl
- Book icon in purple
- Title: "Standards & Sources" in 2xl bold
- Body: References to Walk Score, TCQSM (TCRP Report 165), PTAL (TfL), RAPTOR
- Content is static text

### 2.19 Footer (slim down)

Reduce to:
- Blue logo box (40px) with bus icon
- "Chilliwack Transit Quality Index v0.1.0"
- Generation date
- Italic description text (xs, slate-400)
- Remove methodology content (moved to section 2.17)

---

## 3. TypeScript Types

Update `go/web/src/lib/types.ts` to add:

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
  geojson: GeoJSON.FeatureCollection
}

export interface EquityResult {
  geojson: GeoJSON.FeatureCollection
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

Update `PipelineResponse` to include:
```typescript
export interface PipelineResponse {
  // ... existing fields ...
  detailed_analysis: DetailedAnalysis | null
  isochrones: IsochroneResult[] | null
  equity: EquityResult | null
  route_shapes: RouteShape[] | null
  transit_stops: TransitStop[] | null
}
```

---

## 4. Responsive Design Rules

All sections follow these breakpoints (Tailwind defaults):
- **Mobile** (<640px): single column, cards stack, maps 300px height
- **Tablet** (640-1024px): 2-column grids, maps 400px height
- **Desktop** (>1024px): full layout (3-4 columns, side-by-side maps), maps 450-560px height

Grid card minimum width: 150px. If cards would be smaller, reduce column count.
Horizontal bar chart (Route LOS): minimum bar area width 100px, horizontal scroll if narrower.
Tables: horizontal scroll on mobile with sticky first column.

---

## 5. Section Order in App.tsx

```
Hero
ScoreCards
Narrative
ScoreBreakdown
WalkScoreTable
RouteLOS
CoverageStats
SpeedAnalysis
TimeProfile
PTALChart
HeatMap (enhanced)
TopOrigins
AmenityTable
IsochroneMaps
EquityMap
ReliabilityHistogram
Methodology
Standards
Footer
```

---

## 6. Implementation Order (vertical slices)

Each slice: Go API change → TypeScript types → React component → verify.

1. **DetailedAnalysis computation** — build the struct from existing matrices, wire into API response
2. **Coverage stats** — new `CoverageStats.tsx`
3. **Speed analysis** — new `SpeedAnalysis.tsx` (doughnut + cards + travel time chart)
4. **Time profile enhancements** — peak/low cards, reference bands
5. **Reliability histogram** — new `ReliabilityHistogram.tsx`
6. **PTAL distribution** — use `ptal_distribution` from DetailedAnalysis, minor styling
7. **Top origins** — new `TopOrigins.tsx`
8. **Route LOS rework** — horizontal bars + dark sidebar
9. **Amenity table** — rework cards to table, add 45-min column
10. **Heat map enhancements** — route shapes, stops, layer control
11. **Hero restyle** — 2-col layout with heatmap thumbnail
12. **Score cards / Walk Score table / Score breakdown** — minor styling tweaks
13. **Isochrone generation + maps** — new Go package + `IsochroneMaps.tsx`
14. **Equity overlay** — new Go package + `EquityMap.tsx`
15. **Methodology + Standards + Footer** — static content sections
16. **Final responsive polish** — test all breakpoints, fix any crush/overflow issues
