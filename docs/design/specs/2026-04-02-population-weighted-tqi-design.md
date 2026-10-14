# Population-Weighted TQI by Neighbourhood

**Date:** 2026-04-02
**Goal:** Replace the uniform grid-average TQI with a population-weighted score, and add per-neighbourhood breakdowns to the dashboard. This answers "how well are *people* served?" rather than "how well is *land* served?"

---

## 1. Go Backend

### 1.1 Neighbourhood Boundaries

**New package:** `internal/neighbourhood/`

**Data source:** Chilliwack Open Data Catalogue, Neighbourhoods layer (odID=197), GeoJSON format.
**URL:** `https://www.chilliwack.com/main/page.cfm?id=2331&odAction=JSON&odID=197`

Download during the existing GTFS download step (or separately). Cache to `data/neighbourhoods.geojson`. Skip download if file already exists (same pattern as GTFS caching).

**Functions:**
- `LoadBoundaries(path string) ([]Neighbourhood, error)` — parse GeoJSON into a list of neighbourhood polygons with names
- `AssignPoints(neighbourhoods []Neighbourhood, points []grid.Point) []int` — for each grid point, return the index of the neighbourhood it falls in (-1 if outside all). Uses ray-casting point-in-polygon.
- `FindNearest(neighbourhoods []Neighbourhood, lat, lon float64) int` — fallback for points outside all polygons, finds nearest neighbourhood centroid.

### 1.2 Population Data

Hardcoded 2021 Census populations (from StatCan via City of Chilliwack demographic profiles):

```go
var Population2021 = map[string]int{
    "Downtown":            31410,
    "Vedder":              22620,
    "Promontory":          11820,
    "Sardis":              10010,
    "Rosedale":             5700,
    "Fairfield Island":     4220,
    "Eastern Hillsides":    3450,
    "Yarrow":               3380,
    "Greendale":            3110,
    "Chilliwack Mountain":  2510,
    "Ryder Lake":           1290,
    "Little Mountain":      1170,
}
```

Total: 100,690 (2021 Census city total excluding some First Nations lands not covered by neighbourhood boundaries).

### 1.3 Per-Neighbourhood Scoring

For each neighbourhood:
1. Collect all grid points assigned to it
2. Compute mean TQI score (from per-origin grid scores)
3. Compute mean coverage score and mean speed score
4. Record grid point count

### 1.4 Population-Weighted City TQI

Replace the current uniform TQI with:

```
weighted_tqi = Σ(neighbourhood_mean_tqi × neighbourhood_population) / Σ(neighbourhood_population)
```

Same formula applied to coverage and speed sub-scores.

This replaces `TQIResult.TQI`, `TQIResult.CoverageScore`, and `TQIResult.SpeedScore` in the pipeline output. The per-slot TimeProfile remains unchanged (still uniform grid average — weighting time profiles by neighbourhood would add complexity for minimal insight).

### 1.5 API Response

Add to `PipelineResults`:

```go
type NeighbourhoodScore struct {
    Name           string  `json:"name"`
    Population     int     `json:"population"`
    TQI            float64 `json:"tqi"`
    CoverageScore  float64 `json:"coverage_score"`
    SpeedScore     float64 `json:"speed_score"`
    GridPointCount int     `json:"grid_point_count"`
}
```

Add field: `NeighbourhoodScores []NeighbourhoodScore json:"neighbourhood_scores,omitempty"`

Also add neighbourhood boundaries GeoJSON for the map layer:
`NeighbourhoodBoundaries json.RawMessage json:"neighbourhood_boundaries,omitempty"`

### 1.6 Pipeline Integration

In `runPipeline` (main.go), after computing grid scores and before assembling results:

1. Load neighbourhood boundaries from `data/neighbourhoods.geojson`
2. Assign each grid point to a neighbourhood
3. Compute per-neighbourhood scores
4. Compute population-weighted city scores
5. Overwrite `tqi.TQI`, `tqi.CoverageScore`, `tqi.SpeedScore` with weighted values
6. Add `NeighbourhoodScores` and `NeighbourhoodBoundaries` to results

If neighbourhood data is unavailable (file missing), skip weighting and keep the uniform scores (graceful degradation).

---

## 2. Frontend

### 2.1 TypeScript Types

Add to `types.ts`:

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

### 2.2 New Component: `NeighbourhoodTable.tsx`

Placed after ScoreCards, before Narrative in App.tsx.

**Layout:** Full-width table within a white card, matching the existing section style (heading + decorative line).

**Columns:**
- Neighbourhood name (left-aligned, bold)
- Population (right-aligned, with inline mini-bar showing relative population)
- TQI (right-aligned, color-coded: green ≥ 5, amber ≥ 2.5, red < 2.5)
- Coverage (right-aligned)
- Speed (right-aligned)
- Grid Points (right-aligned, muted)

**Sorting:** By population descending (highest-served areas first).

**Row styling:** Alternating stripes. The population column includes a horizontal mini-bar (width proportional to population / max population) behind the number, similar to the route headway bars.

**Section header:** "Neighbourhood Service Quality" with the standard flex heading + decorative line.

### 2.3 Heat Map Enhancement

Add neighbourhood boundary polygons as a toggleable Leaflet layer:
- Source: `data.neighbourhood_boundaries` (GeoJSON from API)
- Style: thin slate-600 borders (weight 2), no fill, labels on hover showing neighbourhood name
- Layer control: add "Neighbourhoods" to the existing LayersControl
- Default: checked (visible)

### 2.4 Hero Score

No code change needed. The Hero reads `data.tqi.TQI` which will now contain the population-weighted value. The subtitle could be updated to say "Population-Weighted" to clarify what the score represents.

---

## 3. Download Integration

Add neighbourhood GeoJSON download to the existing `download` command or the `serve`/`run` pipeline startup:

- Check if `data/neighbourhoods.geojson` exists
- If not, fetch from Chilliwack open data URL
- Parse and validate (should contain 12 polygon features)
- Cache for future runs

---

## 4. Implementation Order

1. **Neighbourhood package** — boundaries loading, point-in-polygon, population data
2. **Pipeline integration** — compute neighbourhood scores, population-weighted TQI
3. **API response** — add NeighbourhoodScore type and fields
4. **TypeScript types** — update PipelineResponse
5. **NeighbourhoodTable component** — new React component
6. **Heat map boundaries** — add neighbourhood polygons layer
7. **Hero subtitle update** — indicate population-weighted
8. **Download integration** — auto-fetch boundaries
9. **Tests + verification** — Go tests, Playwright
