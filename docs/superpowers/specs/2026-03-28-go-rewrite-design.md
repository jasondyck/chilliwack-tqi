# Chilliwack TQI — Go Rewrite Design Spec

## Overview

Full rewrite of the Chilliwack Transit Quality Index from Python (~4,700 LOC) to Go, with a React/TypeScript frontend. The Go binary embeds the compiled frontend — single binary deployment with a modern web UI.

### Goals

1. **Performance** — native RAPTOR engine with goroutine parallelism (2-5x over Numba JIT)
2. **Deployment** — single binary, no runtime dependencies
3. **Web service** — REST API + interactive dashboard (replaces static HTML report)
4. **Full parity** — all features including multi-city comparison, equity overlay, amenity scoring
5. **Learning** — idiomatic Go project structure

### Non-Goals

- Mobile app
- User authentication / multi-tenant
- Real-time GTFS integration
- Database (all computation is ephemeral or file-cached)

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | Go 1.22+ stdlib `net/http` | Pattern matching in 1.22 ServeMux eliminates need for third-party routers |
| CLI | cobra | Industry standard Go CLI framework |
| API spec | OpenAPI 3.1 + oapi-codegen | Type-safe generated server stubs and types |
| Frontend | React 18 + TypeScript 5 + Vite 6 | Standard SPA toolchain |
| UI components | shadcn/ui + Tailwind CSS 4 | Copy-paste component library, full ownership |
| Maps | Mapbox GL JS via react-map-gl | WebGL-accelerated, handles 5k+ points |
| Charts | Recharts | React-native, good for dashboard charts |
| Data fetching | TanStack Query v5 | Caching, loading states, background refetch |
| Embedding | `go:embed` | Vite dist baked into Go binary |
| Testing (Go) | stdlib `testing` + testify | Standard assertion library |
| Testing (frontend) | Vitest + Testing Library | Vite-native test runner |

---

## Project Structure

```
go/
├── cmd/
│   └── tqi/
│       └── main.go                  # Entrypoint: CLI + HTTP server
├── internal/
│   ├── config/
│   │   └── config.go               # Constants, city configs, CLI flags
│   ├── gtfs/
│   │   ├── download.go             # HTTP download GTFS ZIP + SHA256 hash
│   │   ├── parse.go                # Parse CSV: stops, routes, trips, stop_times, calendar, shapes
│   │   ├── filter.go               # Filter feed to city routes + select best weekday
│   │   └── types.go                # Feed, Stop, Route, Trip, StopTime, Shape structs
│   ├── grid/
│   │   ├── generate.go             # Lat/lon grid within bounding box
│   │   ├── boundary.go             # GeoJSON boundary clipping (point-in-polygon)
│   │   └── types.go                # GridPoint struct
│   ├── geo/
│   │   └── haversine.go            # Haversine distance, bearing, projection
│   ├── raptor/
│   │   ├── timetable.go            # Build flat timetable arrays from GTFS feed
│   │   ├── engine.go               # Core RAPTOR: round-based arrival time propagation
│   │   ├── matrix.go               # Travel time matrix: goroutine pool over origins x departures
│   │   ├── cache.go                # Gob encode/decode matrix to disk
│   │   └── types.go                # Timetable, FlatTimetable, MatrixMetrics structs
│   ├── scoring/
│   │   ├── tqi.go                  # Master TQI: 50% coverage + 50% speed
│   │   ├── tsr.go                  # Transit Speed Ratio (distance / travel_time)
│   │   ├── coverage.go             # Reachability fraction across OD pairs
│   │   ├── speed.go                # Speed score: normalized TSR
│   │   ├── reliability.go          # Coefficient of variation across departure times
│   │   ├── tcqsm.go               # TCQSM LOS grading per route (headway-based A-F)
│   │   ├── ptal.go                 # Public Transport Accessibility Level (TfL method)
│   │   ├── amenity.go              # Amenity accessibility (hospital, grocery, schools)
│   │   ├── time_profile.go         # Score breakdown by time-of-day
│   │   └── types.go                # TQIResult, DetailedAnalysis, RouteLOS structs
│   ├── equity/
│   │   ├── census.go               # Download + parse StatCan census CSV
│   │   ├── boundaries.go           # Load dissemination area GeoJSON boundaries
│   │   ├── overlay.go              # Spatial join: grid scores -> DA polygons
│   │   └── types.go                # EquityResult, CensusData structs
│   └── api/
│       ├── server.go               # HTTP server: middleware, routing, embedded SPA
│       ├── handlers.go             # Handler functions for each endpoint
│       ├── sse.go                  # Server-Sent Events for pipeline progress
│       ├── openapi.yaml            # OpenAPI 3.1 spec
│       └── embed.go                # //go:embed web/dist
├── web/                            # React frontend (Vite project)
│   ├── src/
│   │   ├── main.tsx                # React entrypoint
│   │   ├── App.tsx                 # Router + layout
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx      # App header with nav
│   │   │   │   ├── Sidebar.tsx     # Section navigation
│   │   │   │   └── Layout.tsx      # Shell layout
│   │   │   ├── dashboard/
│   │   │   │   ├── Dashboard.tsx   # Main view: assembles all panels
│   │   │   │   ├── ScoreCard.tsx   # Hero TQI gauge (0-100)
│   │   │   │   ├── ScoreBreakdown.tsx # Coverage + Speed bars
│   │   │   │   └── TimeProfile.tsx # Line chart: score across day
│   │   │   ├── maps/
│   │   │   │   ├── HeatMap.tsx     # Mapbox GL grid heatmap + route overlays
│   │   │   │   ├── IsochroneMap.tsx # Isochrone with time slider
│   │   │   │   └── EquityMap.tsx   # Choropleth by DA income
│   │   │   ├── routes/
│   │   │   │   └── RouteTable.tsx  # Sortable TCQSM grade table
│   │   │   ├── amenities/
│   │   │   │   └── AmenityCard.tsx # % reachable within 30/60 min
│   │   │   └── compare/
│   │   │       └── CompareView.tsx # Multi-city side-by-side + radar
│   │   ├── hooks/
│   │   │   ├── useResults.ts       # TanStack Query: fetch TQI results
│   │   │   ├── usePipeline.ts      # SSE hook: pipeline progress
│   │   │   └── useCompare.ts       # TanStack Query: comparison results
│   │   ├── lib/
│   │   │   ├── api.ts              # Fetch wrapper / API client
│   │   │   └── types.ts            # TypeScript types (mirror Go structs)
│   │   └── styles/
│   │       └── globals.css         # Tailwind imports + custom tokens
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
├── Makefile
├── go.mod
├── go.sum
└── README.md
```

---

## API Design

### Endpoints

```
GET  /api/health                         → { status: "ok" }

POST /api/run                            → SSE stream (pipeline progress)
  Query: ?download=true&cache=true&equity=false&workers=0

GET  /api/results                        → TQIResponse (scores + detailed analysis)
GET  /api/results/grid                   → GeoJSON FeatureCollection (grid scores)
GET  /api/results/isochrone?time=480     → GeoJSON FeatureCollection (travel times)
GET  /api/results/routes                 → RouteLOS[] (TCQSM grades)
GET  /api/results/ptal                   → GeoJSON FeatureCollection (PTAL scores)
GET  /api/results/amenities              → AmenityResult[]
GET  /api/results/equity                 → EquityResponse (DA-level data)
GET  /api/results/time-profile           → TimeProfileEntry[]

POST /api/compare                        → SSE stream (comparison progress)
  Body: { cities: ["chilliwack", "victoria", "kelowna"] }

GET  /api/compare/results                → CityComparison[]

GET  /                                   → Embedded React SPA (catch-all)
```

### SSE Progress Events

```
event: progress
data: {"step": "downloading_gtfs", "pct": 0, "message": "Downloading GTFS..."}

event: progress
data: {"step": "raptor_matrix", "pct": 45, "message": "Computing travel times (2100/4700 origins)"}

event: complete
data: {"tqi": 24.3, "duration_sec": 12.5}

event: error
data: {"message": "Failed to download GTFS: connection refused"}
```

### Key Response Types

```typescript
interface TQIResponse {
  tqi: number;
  coverage_score: number;
  speed_score: number;
  reliability_mean_cv: number;
  grid_points: number;
  stops: number;
  detailed: {
    transit_desert_pct: number;
    origins_with_service: number;
    reachability_rate_pct: number;
    mean_tsr_kmh: number;
    median_tsr_kmh: number;
    trips_slower_than_walking_pct: number;
    mean_travel_time_min: number;
    median_travel_time_min: number;
    max_origin_reachability_pct: number;
  };
  route_los: RouteLOS[];
  ptal_summary: { points_with_service: number; total_points: number };
  amenities: AmenityResult[];
  time_profile: Array<{ time: number; score: number }>;
  system_los: { grade: string; description: string; median_headway: number };
}

interface RouteLOS {
  route_name: string;
  route_long_name: string;
  median_headway_min: number;
  los_grade: string;
  los_description: string;
  trip_count: number;
}

interface AmenityResult {
  name: string;
  lat: number;
  lon: number;
  pct_within_30min: number;
  pct_within_60min: number;
  mean_travel_time_min: number;
}

interface CityComparison {
  city: string;
  tqi: number;
  coverage: number;
  speed: number;
  grid_points: number;
  stops: number;
  routes: number;
}
```

---

## Core Algorithm: RAPTOR Engine

Direct port of the Numba JIT implementation to native Go. The algorithm is identical — only the language changes.

### Data Structures

```go
type FlatTimetable struct {
    NStops    int
    NPatterns int
    StopIDs   []string

    // Pattern → stops: PSData[PSOffsets[p]..PSOffsets[p+1]]
    PSData    []int32
    PSOffsets []int32

    // Pattern → timetable: TTData[TTOffsets[p]..], row-major [trips × stops_in_pattern]
    // Each cell = departure_time (minutes since midnight, float64)
    TTData    []float64
    TTOffsets []int32
    TTNTrips  []int32
    TTNStops  []int32

    // Stop → patterns: SPData[SPOffsets[s]..SPOffsets[s+1]]
    SPData    []int32
    SPOffsets []int32

    // Transfer → (target_stop, walk_time): TRData[TROffsets[s]..TROffsets[s+1]]
    TRData    []float64 // pairs: [target_idx, walk_min, target_idx, walk_min, ...]
    TROffsets []int32
}
```

### Algorithm (pseudocode matching Python)

```
function raptor(timetable, sources, max_transfers, max_time):
    tau[k][s] = INF for all k, s
    best[s] = INF for all s

    // Initialize sources
    for (stop, time) in sources:
        tau[0][stop] = time
        best[stop] = time
        mark(stop)

    for k = 1 to max_transfers:
        // Route scanning
        for each pattern p containing a marked stop:
            board_time = INF
            for each stop s in pattern p (in order):
                if tau[k-1][s] < board_time:
                    // Board here: find earliest trip departing after tau[k-1][s]
                    board_time = earliest_trip_departure(p, s, tau[k-1][s])
                arrival = arrival_time(p, s, boarded_trip)
                if arrival < tau[k][s] and arrival < best[s]:
                    tau[k][s] = arrival
                    best[s] = arrival
                    mark(s)

        // Transfers (walking between stops)
        for each marked stop s:
            for each transfer (target, walk_time) from s:
                arrival = best[s] + walk_time
                if arrival < tau[k][s] and arrival < best[target] and arrival < max_time:
                    tau[k][target] = arrival
                    best[target] = arrival
                    mark(target)

    return best
```

### Parallelism Strategy

```go
func ComputeMatrix(tt *FlatTimetable, grid []GridPoint, ..., workers int) *MatrixMetrics {
    if workers == 0 {
        workers = runtime.NumCPU()
    }

    origins := make(chan int, len(grid))
    var wg sync.WaitGroup

    // Each worker gets its own pre-allocated RAPTOR working memory
    for w := 0; w < workers; w++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            workspace := newRaptorWorkspace(tt.NStops) // reused per origin
            for originIdx := range origins {
                for _, depTime := range departureTimes {
                    raptor(tt, workspace, sources, depTime)
                    // store results into shared matrix (no contention: each origin is independent)
                }
            }
        }()
    }

    for i := range grid {
        origins <- i
    }
    close(origins)
    wg.Wait()
}
```

Key optimizations:
- Pre-allocated `tau`, `best`, `marked` arrays per goroutine — zero allocations in hot loop
- Flat arrays with offset indexing — cache-friendly, no pointer chasing
- Each origin is fully independent — no locks needed on the results matrix
- Worker count defaults to `runtime.NumCPU()`

---

## GTFS Parsing

Parse GTFS ZIP directly from memory (no temp extraction). Use `archive/zip` + `encoding/csv`.

### Files Parsed

| GTFS File | Go Struct | Key Fields |
|-----------|-----------|------------|
| stops.txt | `Stop` | stop_id, stop_name, stop_lat, stop_lon |
| routes.txt | `Route` | route_id, route_short_name, route_long_name |
| trips.txt | `Trip` | trip_id, route_id, service_id, shape_id, direction_id |
| stop_times.txt | `StopTime` | trip_id, stop_id, arrival_time, departure_time, stop_sequence |
| calendar.txt | `Calendar` | service_id, monday-sunday, start_date, end_date |
| calendar_dates.txt | `CalendarDate` | service_id, date, exception_type |
| shapes.txt | `Shape` | shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence |

### Filtering Logic (port of filter.py)

1. Find the best representative weekday (most trips active) within the calendar window
2. Filter trips to only those running on the best weekday
3. Filter to only routes in the city's route list
4. Cascade filter: trips → stop_times → stops (only stops served by remaining trips)

---

## Scoring Modules

All scoring is a direct port of the Python implementations.

### TQI Master Score (tqi.go)

```
TQI = 0.5 × coverage_score + 0.5 × speed_score
```

- **Coverage score** (0-100): fraction of OD pairs where transit is reachable (excluding pairs < 0.5km)
- **Speed score** (0-100): normalized mean TSR, clipped to [5 km/h (walk) ... 40 km/h (car)]

### Transit Speed Ratio (tsr.go)

```
TSR = distance_km / (travel_time_min / 60)
```

Only for pairs where transit beats walking (TSR > 5 km/h).

### TCQSM Level of Service (tcqsm.go)

Per-route grading based on median headway:
- A: ≤10 min, B: ≤14, C: ≤20, D: ≤30, E: ≤60, F: >60

### PTAL (ptal.go)

Transport for London methodology:
1. For each grid point, find bus stops within 640m (8-min walk at 80m/min)
2. For each stop, compute Average Wait Time from service frequency
3. Accessibility Index = sum of (1/AWT) across all accessible stops
4. Map AI to grade: 1a through 6b

### Amenity Accessibility (amenity.go)

Load amenity locations from `data/amenities.json`. For each grid point, compute travel time to each amenity. Report % of grid reachable within 30/60 minutes.

### Reliability (reliability.go)

Coefficient of variation of travel times across departure times for each OD pair.

### Time Profile (time_profile.go)

Compute TQI subscores for each departure time slot independently.

---

## Grid Generation

- Bounding box from config (SW/NE corners)
- 250m spacing (configurable)
- Points generated in lat/lon using meter-to-degree projection at local latitude
- Optional clipping to municipal boundary GeoJSON (point-in-polygon via ray casting)
- For comparison cities: no boundary clipping, just bounding box

---

## Equity Overlay

Optional feature (triggered by `--equity` flag or UI toggle).

1. Download Statistics Canada dissemination area boundaries (shapefile → GeoJSON)
2. Download census profile CSV
3. Parse median after-tax income per DA
4. Spatial join: assign each grid point to its DA
5. Aggregate grid TQI scores per DA
6. Compute correlation between DA income and DA TQI score
7. Serve as choropleth-ready GeoJSON

---

## Frontend Design

### Pages / Views

1. **Dashboard** (default) — hero score, breakdown bars, time profile chart, quick stats
2. **Maps** — tabbed: Heatmap | Isochrone | Equity (if available)
3. **Routes** — TCQSM table with sortable columns, grade badges
4. **Amenities** — cards per amenity with reach percentages
5. **Compare** — multi-city trigger + results with radar chart overlay

### State Management

- TanStack Query handles all server state (caching, refetch, loading)
- No global state library needed — component-local state + query cache
- Pipeline progress via custom `usePipeline` hook wrapping EventSource

### Responsive Layout

- Desktop: sidebar nav + main content area
- Tablet/mobile: collapsible nav, stacked panels
- Maps resize to container via Mapbox GL resize observer

---

## CLI Commands

```
tqi run [flags]           # Run full pipeline, print results to stdout
    --no-download         # Skip GTFS download
    --no-cache            # Ignore cached matrix
    --workers N           # Parallel workers (default: NumCPU)
    --equity              # Include equity overlay
    --output-dir PATH     # Write JSON results here

tqi download              # Download GTFS only

tqi compare [flags]       # Multi-city comparison
    --cities LIST         # Comma-separated (default: chilliwack,victoria,kelowna)
    --workers N

tqi serve [flags]         # Start web UI
    --port N              # HTTP port (default: 8080)
    --open                # Open browser automatically
```

`tqi run` and `tqi serve` share the same pipeline code. `run` executes once and exits. `serve` keeps the server alive and exposes the API.

---

## Build & Development

### Makefile Targets

```makefile
dev-api:     # Run Go server with hot reload (air)
dev-web:     # Run Vite dev server (proxies /api to Go)
dev:         # Run both concurrently
build-web:   # Vite build → go/web/dist/
build:       # build-web + go build → single binary
test:        # Go tests + Vitest
lint:        # golangci-lint + eslint
```

### Development Workflow

1. `make dev` starts Go backend (port 8080) + Vite dev server (port 5173, proxies API)
2. Frontend hot-reloads on file changes
3. Backend rebuilds via `air` on Go file changes

### Production Build

1. `npm run build` in `go/web/` → produces `go/web/dist/`
2. `go build` in `go/cmd/tqi/` → embeds `web/dist/` via `//go:embed`
3. Output: single `tqi` binary (~15-20MB), ships everything

---

## Testing Strategy

### Go Tests

- **Unit tests** per package: scoring math, RAPTOR correctness, GTFS parsing
- **Integration test**: small synthetic GTFS feed → full pipeline → verify TQI output
- **Benchmark tests**: RAPTOR engine with `testing.B` to track performance

### Frontend Tests

- **Component tests**: Vitest + Testing Library for key components
- **No E2E in Go rewrite scope** — existing Playwright tests cover the Python version's HTML output, not applicable here

---

## Configuration

### Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `MAPBOX_TOKEN` | Yes (for maps) | — | Mapbox GL JS access token |
| `TQI_PORT` | No | `8080` | HTTP server port |
| `TQI_DATA_DIR` | No | `../data` (relative to binary) | Path to data directory |

The frontend reads `MAPBOX_TOKEN` from `/api/config` (served by Go, never exposed in client bundle).

### Server Behavior

- `tqi serve` starts the HTTP server but does NOT auto-run the pipeline
- The UI shows a "Run Analysis" button that triggers `POST /api/run`
- If a previous run's results exist in memory, they're served immediately
- Only one pipeline run at a time (subsequent requests get 409 Conflict)

---

## Migration Notes

### What Changes

- Python → Go for all backend computation
- Static HTML report → React SPA served by Go
- Folium maps → Mapbox GL JS
- Matplotlib/Chart.js embedded in HTML → Recharts
- Jinja2 templates → React components
- Numba JIT → native Go
- pandas DataFrames → Go slices/maps + standard library

### What Stays the Same

- All algorithms (RAPTOR, scoring formulas, PTAL, TCQSM)
- All constants and thresholds
- GTFS data source and format
- `data/` directory structure (amenities.json, boundary GeoJSON, GTFS cache)
- Project lives in same repo under `go/` directory

### Data Files Shared

The Go binary reads from the same `data/` directory:
- `data/gtfs/` — downloaded GTFS ZIP contents
- `data/chilliwack_boundary.geojson` — municipal boundary
- `data/amenities.json` — amenity locations
- `data/cache/` — matrix cache files (new format: gob instead of numpy)
- `data/census/` — downloaded census data (equity overlay)
