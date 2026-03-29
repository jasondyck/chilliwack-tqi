# TQI Go Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Chilliwack Transit Quality Index from Python to Go with a React/TypeScript frontend, producing a single binary that serves an interactive dashboard.

**Architecture:** Go backend with stdlib `net/http` router, cobra CLI, goroutine-parallel RAPTOR engine, REST API with SSE progress streaming. React 18 + TypeScript + Vite frontend with shadcn/ui, Mapbox GL maps, Recharts charts, embedded in Go binary via `go:embed`.

**Tech Stack:** Go 1.22+, cobra, React 18, TypeScript 5, Vite 6, Tailwind CSS 4, shadcn/ui, Mapbox GL JS (react-map-gl), Recharts, TanStack Query v5, testify

---

## Task 1: Go Module + Project Scaffold

**Files:**
- Create: `go/go.mod`
- Create: `go/cmd/tqi/main.go`
- Create: `go/internal/config/config.go`
- Create: `go/Makefile`

- [ ] **Step 1: Initialize Go module**

```bash
mkdir -p go/cmd/tqi go/internal/config
cd go && go mod init github.com/jasondyck/chwk-tqi
```

- [ ] **Step 2: Write config.go with all constants**

Create `go/internal/config/config.go`:

```go
package config

import "math"

// Project paths (resolved relative to data dir)
var DataDir = "../data"

// GTFS source
const GTFSUrl = "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=13"

// Chilliwack municipal boundary
var BoundaryGeoJSON = "chilliwack_boundary.geojson"

// Bounding box (SW, NE)
var BBoxSW = [2]float64{49.045918, -122.124370}
var BBoxNE = [2]float64{49.225607, -121.777247}

// Chilliwack route short names
var ChilliwackRoutes = []string{
	"51", "52", "53", "54", "55", "57", "58", "59", "66",
}

// Grid parameters
const GridSpacingM = 250.0

// Walking / routing parameters
const (
	WalkSpeedKMH      = 5.0
	WalkSpeedMPerMin  = WalkSpeedKMH * 1000.0 / 60.0 // 83.33 m/min
	MaxWalkToStopM    = 800.0
	MaxTransferWalkM  = 400.0
	MaxTripMin        = 90.0
	MaxTransfers      = 2
)

// Time window (minutes since midnight)
const (
	TimeStart = 6 * 60  // 06:00
	TimeEnd   = 22 * 60 // 22:00
	TimeStep  = 15      // 15-minute resolution
)

// DepartureTimes generates the list of departure slots.
func DepartureTimes() []int {
	times := make([]int, 0, (TimeEnd-TimeStart)/TimeStep)
	for t := TimeStart; t < TimeEnd; t += TimeStep {
		times = append(times, t)
	}
	return times
}

// Scoring normalisation
const (
	TSRWalk      = 5.0  // km/h — walking baseline (score = 0)
	TSRCar       = 40.0 // km/h — car baseline (score = 100)
	MinODDistKM  = 0.5  // exclude trivially walkable pairs
)

// Walk Score Transit Score ranges
var WalkScoreRanges = [][4]interface{}{
	{90, 100, "Rider's Paradise", "World-class public transportation"},
	{70, 89, "Excellent Transit", "Transit convenient for most trips"},
	{50, 69, "Good Transit", "Many nearby public transportation options"},
	{25, 49, "Some Transit", "A few nearby public transportation options"},
	{0, 24, "Minimal Transit", "It is possible to get on a bus"},
}

// WalkScoreCategory maps a TQI value to its Walk Score category.
type WalkScoreRange struct {
	Low, High   int
	Name, Desc  string
}

func GetWalkScoreRanges() []WalkScoreRange {
	return []WalkScoreRange{
		{90, 100, "Rider's Paradise", "World-class public transportation"},
		{70, 89, "Excellent Transit", "Transit convenient for most trips"},
		{50, 69, "Good Transit", "Many nearby public transportation options"},
		{25, 49, "Some Transit", "A few nearby public transportation options"},
		{0, 24, "Minimal Transit", "It is possible to get on a bus"},
	}
}

func WalkScoreCategory(tqi float64) (string, string) {
	for _, r := range GetWalkScoreRanges() {
		if int(tqi) >= r.Low && int(tqi) <= r.High {
			return r.Name, r.Desc
		}
	}
	return "Minimal Transit", "It is possible to get on a bus"
}

// TCQSM LOS grades (TCRP Report 165, 3rd Edition)
type TCQSMLOSGrade struct {
	MaxHeadway  float64
	Grade       string
	Description string
}

func TCQSMLOSGrades() []TCQSMLOSGrade {
	return []TCQSMLOSGrade{
		{10, "A", "Passengers don't need schedules"},
		{14, "B", "Frequent service, passengers consult schedules"},
		{20, "C", "Maximum desirable wait if bus is missed"},
		{30, "D", "Service unattractive to choice riders"},
		{60, "E", "Service available during the hour"},
		{999, "F", "Service unattractive to all riders"},
	}
}

// PTAL grade boundaries (TfL methodology)
type PTALGrade struct {
	MaxAI float64
	Grade string
}

func PTALGrades() []PTALGrade {
	return []PTALGrade{
		{2.5, "1a"},
		{5.0, "1b"},
		{10.0, "2"},
		{15.0, "3"},
		{20.0, "4"},
		{25.0, "5"},
		{40.0, "6a"},
		{math.Inf(1), "6b"},
	}
}

const (
	PTALWalkSpeedMPerMin = 80.0 // PTAL standard: 80m/min (4.8 km/h)
	PTALBusCatchmentM    = 640  // 8 min walk at 80m/min
)

const EarthRadiusM = 6_371_000

// Multi-city comparison configs
type CityConfig struct {
	OperatorID int
	URL        string
	BBoxSW     [2]float64
	BBoxNE     [2]float64
	Routes     []string // nil means use all routes
}

func CityConfigs() map[string]CityConfig {
	return map[string]CityConfig{
		"chilliwack": {
			OperatorID: 13,
			URL:        "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=13",
			BBoxSW:     [2]float64{49.045918, -122.124370},
			BBoxNE:     [2]float64{49.225607, -121.777247},
			Routes:     ChilliwackRoutes,
		},
		"victoria": {
			OperatorID: 48,
			URL:        "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=48",
			BBoxSW:     [2]float64{48.40, -123.50},
			BBoxNE:     [2]float64{48.55, -123.30},
			Routes:     nil,
		},
		"kelowna": {
			OperatorID: 47,
			URL:        "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=47",
			BBoxSW:     [2]float64{49.82, -119.55},
			BBoxNE:     [2]float64{49.95, -119.40},
			Routes:     nil,
		},
		"kamloops": {
			OperatorID: 46,
			URL:        "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=46",
			BBoxSW:     [2]float64{50.65, -120.45},
			BBoxNE:     [2]float64{50.75, -120.25},
			Routes:     nil,
		},
		"nanaimo": {
			OperatorID: 41,
			URL:        "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=41",
			BBoxSW:     [2]float64{49.12, -124.00},
			BBoxNE:     [2]float64{49.22, -123.90},
			Routes:     nil,
		},
	}
}
```

- [ ] **Step 3: Write minimal main.go**

Create `go/cmd/tqi/main.go`:

```go
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

func main() {
	root := &cobra.Command{
		Use:   "tqi",
		Short: "Chilliwack Transit Quality Index",
		Long:  "Measure how well transit connects Chilliwack, BC.",
	}

	root.AddCommand(newServeCmd())
	root.AddCommand(newRunCmd())
	root.AddCommand(newDownloadCmd())
	root.AddCommand(newCompareCmd())

	if err := root.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func newServeCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "serve",
		Short: "Start the web UI",
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Println("serve not yet implemented")
			return nil
		},
	}
	cmd.Flags().IntP("port", "p", 8080, "HTTP port")
	return cmd
}

func newRunCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "run",
		Short: "Run the full TQI analysis pipeline",
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Println("run not yet implemented")
			return nil
		},
	}
	cmd.Flags().Bool("no-download", false, "Skip GTFS download")
	cmd.Flags().Bool("no-cache", false, "Ignore cached matrix")
	cmd.Flags().IntP("workers", "w", 0, "Number of parallel workers (0 = NumCPU)")
	cmd.Flags().Bool("equity", false, "Include census equity overlay")
	cmd.Flags().StringP("output-dir", "o", "output", "Output directory")
	return cmd
}

func newDownloadCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "download",
		Short: "Download GTFS data from BC Transit",
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Println("download not yet implemented")
			return nil
		},
	}
}

func newCompareCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "compare",
		Short: "Compare TQI across multiple BC Transit cities",
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Println("compare not yet implemented")
			return nil
		},
	}
	cmd.Flags().String("cities", "chilliwack,victoria,kelowna", "Comma-separated list of cities")
	cmd.Flags().IntP("workers", "w", 0, "Number of parallel workers")
	return cmd
}
```

- [ ] **Step 4: Add cobra dependency and verify build**

```bash
cd go && go get github.com/spf13/cobra && go build ./cmd/tqi/
```

Expected: binary `tqi` compiles with no errors.

- [ ] **Step 5: Write Makefile**

Create `go/Makefile`:

```makefile
.PHONY: build build-web dev dev-api dev-web test lint clean

build-web:
	cd web && npm run build

build: build-web
	go build -o bin/tqi ./cmd/tqi/

dev-api:
	go run ./cmd/tqi/ serve

dev-web:
	cd web && npm run dev

test:
	go test ./... -v

lint:
	golangci-lint run ./...

clean:
	rm -rf bin/ web/dist/
```

- [ ] **Step 6: Commit**

```bash
git add go/
git commit -m "feat: scaffold Go project with config, CLI, and Makefile"
```

---

## Task 2: Geo Utilities

**Files:**
- Create: `go/internal/geo/haversine.go`
- Create: `go/internal/geo/haversine_test.go`

- [ ] **Step 1: Write the failing test**

Create `go/internal/geo/haversine_test.go`:

```go
package geo

import (
	"math"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHaversine(t *testing.T) {
	// Vancouver to Seattle: ~199 km
	d := Haversine(49.2827, -123.1207, 47.6062, -122.3321)
	assert.InDelta(t, 199.0, d, 2.0, "Vancouver-Seattle distance")
}

func TestHaversineZero(t *testing.T) {
	d := Haversine(49.0, -122.0, 49.0, -122.0)
	assert.Equal(t, 0.0, d)
}

func TestHaversineMatrix(t *testing.T) {
	lats := []float64{49.0, 49.1}
	lons := []float64{-122.0, -122.1}
	m := HaversineMatrix(lats, lons)
	assert.Equal(t, 2, len(m))
	assert.Equal(t, 2, len(m[0]))
	assert.Equal(t, 0.0, m[0][0])
	assert.Equal(t, 0.0, m[1][1])
	assert.InDelta(t, m[0][1], m[1][0], 0.001)
	assert.True(t, m[0][1] > 0)
}

func TestProjectToXY(t *testing.T) {
	x, y := ProjectToXY(49.168, -121.951, math.Pi/180.0*49.15)
	assert.NotEqual(t, 0.0, x)
	assert.NotEqual(t, 0.0, y)
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd go && go get github.com/stretchr/testify && go test ./internal/geo/ -v
```

Expected: FAIL — package does not exist yet.

- [ ] **Step 3: Write implementation**

Create `go/internal/geo/haversine.go`:

```go
package geo

import "math"

const EarthRadiusKM = 6371.0
const EarthRadiusM = 6_371_000.0

// Haversine returns the great-circle distance in km between two lat/lon points.
func Haversine(lat1, lon1, lat2, lon2 float64) float64 {
	dLat := deg2rad(lat2 - lat1)
	dLon := deg2rad(lon2 - lon1)
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(deg2rad(lat1))*math.Cos(deg2rad(lat2))*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	return 2 * EarthRadiusKM * math.Asin(math.Sqrt(a))
}

// HaversineMatrix computes pairwise distances in km.
// Returns [N][N]float64 where N = len(lats) = len(lons).
func HaversineMatrix(lats, lons []float64) [][]float64 {
	n := len(lats)
	m := make([][]float64, n)
	for i := range m {
		m[i] = make([]float64, n)
	}
	for i := 0; i < n; i++ {
		for j := i + 1; j < n; j++ {
			d := Haversine(lats[i], lons[i], lats[j], lons[j])
			m[i][j] = d
			m[j][i] = d
		}
	}
	return m
}

// ProjectToXY projects lat/lon to approximate Cartesian meters
// using an equirectangular projection at the given center latitude (in radians).
func ProjectToXY(lat, lon, centerLatRad float64) (x, y float64) {
	lonRad := deg2rad(lon)
	latRad := deg2rad(lat)
	x = lonRad * EarthRadiusM * math.Cos(centerLatRad)
	y = latRad * EarthRadiusM
	return
}

// ProjectSliceToXY projects a slice of lat/lon pairs to Cartesian meters.
// lats and lons must have the same length. Returns xs and ys slices.
func ProjectSliceToXY(lats, lons []float64, centerLatRad float64) (xs, ys []float64) {
	n := len(lats)
	xs = make([]float64, n)
	ys = make([]float64, n)
	for i := 0; i < n; i++ {
		xs[i], ys[i] = ProjectToXY(lats[i], lons[i], centerLatRad)
	}
	return
}

// Distance2D returns Euclidean distance between two 2D points.
func Distance2D(x1, y1, x2, y2 float64) float64 {
	dx := x2 - x1
	dy := y2 - y1
	return math.Sqrt(dx*dx + dy*dy)
}

func deg2rad(d float64) float64 {
	return d * math.Pi / 180.0
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd go && go test ./internal/geo/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add go/internal/geo/
git commit -m "feat: add geo utilities — haversine, projection, distance"
```

---

## Task 3: GTFS Types + Parsing

**Files:**
- Create: `go/internal/gtfs/types.go`
- Create: `go/internal/gtfs/parse.go`
- Create: `go/internal/gtfs/parse_test.go`

- [ ] **Step 1: Write GTFS types**

Create `go/internal/gtfs/types.go`:

```go
package gtfs

// Feed holds all parsed GTFS data.
type Feed struct {
	Stops         []Stop
	StopTimes     []StopTime
	Trips         []Trip
	Routes        []Route
	Calendar      []Calendar
	CalendarDates []CalendarDate
	Shapes        []Shape
}

type Stop struct {
	StopID   string
	StopName string
	StopLat  float64
	StopLon  float64
}

type StopTime struct {
	TripID       string
	StopID       string
	ArrivalMin   int // minutes since midnight
	DepartureMin int // minutes since midnight
	StopSequence int
}

type Trip struct {
	TripID      string
	RouteID     string
	ServiceID   string
	ShapeID     string
	DirectionID string
}

type Route struct {
	RouteID        string
	RouteShortName string
	RouteLongName  string
}

type Calendar struct {
	ServiceID string
	Monday    bool
	Tuesday   bool
	Wednesday bool
	Thursday  bool
	Friday    bool
	Saturday  bool
	Sunday    bool
	StartDate string // YYYYMMDD
	EndDate   string // YYYYMMDD
}

type CalendarDate struct {
	ServiceID     string
	Date          string // YYYYMMDD
	ExceptionType int    // 1=added, 2=removed
}

type Shape struct {
	ShapeID     string
	ShapePtLat  float64
	ShapePtLon  float64
	ShapePtSeq  int
}
```

- [ ] **Step 2: Write failing test for parsing**

Create `go/internal/gtfs/parse_test.go`:

```go
package gtfs

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupTestGTFS(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()

	writeCSV(t, dir, "stops.txt", `stop_id,stop_name,stop_lat,stop_lon
S1,Stop One,49.168,-121.951
S2,Stop Two,49.170,-121.955
`)
	writeCSV(t, dir, "routes.txt", `route_id,route_short_name,route_long_name
R1,51,Downtown
R2,52,Sardis
`)
	writeCSV(t, dir, "trips.txt", `trip_id,route_id,service_id,shape_id,direction_id
T1,R1,SVC1,,0
T2,R2,SVC1,,1
`)
	writeCSV(t, dir, "stop_times.txt", `trip_id,stop_id,arrival_time,departure_time,stop_sequence
T1,S1,08:00:00,08:01:00,1
T1,S2,08:10:00,08:11:00,2
T2,S2,09:00:00,09:01:00,1
T2,S1,09:15:00,09:16:00,2
`)
	writeCSV(t, dir, "calendar.txt", `service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
SVC1,1,1,1,1,1,0,0,20260101,20261231
`)
	return dir
}

func writeCSV(t *testing.T, dir, name, content string) {
	t.Helper()
	err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0644)
	require.NoError(t, err)
}

func TestLoadGTFS(t *testing.T) {
	dir := setupTestGTFS(t)
	feed, err := LoadGTFS(dir)
	require.NoError(t, err)

	assert.Len(t, feed.Stops, 2)
	assert.Equal(t, "S1", feed.Stops[0].StopID)
	assert.InDelta(t, 49.168, feed.Stops[0].StopLat, 0.001)

	assert.Len(t, feed.Routes, 2)
	assert.Equal(t, "51", feed.Routes[0].RouteShortName)

	assert.Len(t, feed.Trips, 2)
	assert.Len(t, feed.StopTimes, 4)

	// Check time parsing: 08:00 = 480 min
	assert.Equal(t, 480, feed.StopTimes[0].ArrivalMin)
	assert.Equal(t, 481, feed.StopTimes[0].DepartureMin)

	assert.Len(t, feed.Calendar, 1)
	assert.True(t, feed.Calendar[0].Monday)
	assert.False(t, feed.Calendar[0].Saturday)
}

func TestParseTime(t *testing.T) {
	assert.Equal(t, 480, ParseTime("08:00:00"))
	assert.Equal(t, 1530, ParseTime("25:30:00")) // past midnight
	assert.Equal(t, 0, ParseTime("00:00:00"))
}
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd go && go test ./internal/gtfs/ -v
```

Expected: FAIL — `LoadGTFS` not defined.

- [ ] **Step 4: Write parse.go implementation**

Create `go/internal/gtfs/parse.go`:

```go
package gtfs

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// ParseTime converts a GTFS time string "HH:MM:SS" to minutes since midnight.
// Handles hours >= 24 (e.g., "25:30:00" → 1530).
func ParseTime(s string) int {
	parts := strings.Split(strings.TrimSpace(s), ":")
	if len(parts) < 2 {
		return 0
	}
	h, _ := strconv.Atoi(parts[0])
	m, _ := strconv.Atoi(parts[1])
	return h*60 + m
}

// LoadGTFS reads all GTFS CSV files from the given directory.
func LoadGTFS(dir string) (*Feed, error) {
	feed := &Feed{}
	var err error

	feed.Stops, err = parseStops(filepath.Join(dir, "stops.txt"))
	if err != nil {
		return nil, fmt.Errorf("stops.txt: %w", err)
	}

	feed.Routes, err = parseRoutes(filepath.Join(dir, "routes.txt"))
	if err != nil {
		return nil, fmt.Errorf("routes.txt: %w", err)
	}

	feed.Trips, err = parseTrips(filepath.Join(dir, "trips.txt"))
	if err != nil {
		return nil, fmt.Errorf("trips.txt: %w", err)
	}

	feed.StopTimes, err = parseStopTimes(filepath.Join(dir, "stop_times.txt"))
	if err != nil {
		return nil, fmt.Errorf("stop_times.txt: %w", err)
	}

	// Optional files
	feed.Calendar, _ = parseCalendar(filepath.Join(dir, "calendar.txt"))
	feed.CalendarDates, _ = parseCalendarDates(filepath.Join(dir, "calendar_dates.txt"))
	feed.Shapes, _ = parseShapes(filepath.Join(dir, "shapes.txt"))

	return feed, nil
}

func readCSV(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.TrimLeadingSpace = true

	records, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(records) < 1 {
		return nil, nil
	}

	header := records[0]
	rows := make([]map[string]string, 0, len(records)-1)
	for _, rec := range records[1:] {
		row := make(map[string]string, len(header))
		for i, col := range header {
			if i < len(rec) {
				row[col] = rec[i]
			}
		}
		rows = append(rows, row)
	}
	return rows, nil
}

func parseStops(path string) ([]Stop, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	stops := make([]Stop, 0, len(rows))
	for _, r := range rows {
		lat, _ := strconv.ParseFloat(r["stop_lat"], 64)
		lon, _ := strconv.ParseFloat(r["stop_lon"], 64)
		stops = append(stops, Stop{
			StopID:   r["stop_id"],
			StopName: r["stop_name"],
			StopLat:  lat,
			StopLon:  lon,
		})
	}
	return stops, nil
}

func parseRoutes(path string) ([]Route, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	routes := make([]Route, 0, len(rows))
	for _, r := range rows {
		routes = append(routes, Route{
			RouteID:        r["route_id"],
			RouteShortName: r["route_short_name"],
			RouteLongName:  r["route_long_name"],
		})
	}
	return routes, nil
}

func parseTrips(path string) ([]Trip, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	trips := make([]Trip, 0, len(rows))
	for _, r := range rows {
		trips = append(trips, Trip{
			TripID:      r["trip_id"],
			RouteID:     r["route_id"],
			ServiceID:   r["service_id"],
			ShapeID:     r["shape_id"],
			DirectionID: r["direction_id"],
		})
	}
	return trips, nil
}

func parseStopTimes(path string) ([]StopTime, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	sts := make([]StopTime, 0, len(rows))
	for _, r := range rows {
		seq, _ := strconv.Atoi(r["stop_sequence"])
		sts = append(sts, StopTime{
			TripID:       r["trip_id"],
			StopID:       r["stop_id"],
			ArrivalMin:   ParseTime(r["arrival_time"]),
			DepartureMin: ParseTime(r["departure_time"]),
			StopSequence: seq,
		})
	}
	return sts, nil
}

func parseCalendar(path string) ([]Calendar, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	cals := make([]Calendar, 0, len(rows))
	for _, r := range rows {
		cals = append(cals, Calendar{
			ServiceID: r["service_id"],
			Monday:    r["monday"] == "1",
			Tuesday:   r["tuesday"] == "1",
			Wednesday: r["wednesday"] == "1",
			Thursday:  r["thursday"] == "1",
			Friday:    r["friday"] == "1",
			Saturday:  r["saturday"] == "1",
			Sunday:    r["sunday"] == "1",
			StartDate: r["start_date"],
			EndDate:   r["end_date"],
		})
	}
	return cals, nil
}

func parseCalendarDates(path string) ([]CalendarDate, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	cds := make([]CalendarDate, 0, len(rows))
	for _, r := range rows {
		et, _ := strconv.Atoi(r["exception_type"])
		cds = append(cds, CalendarDate{
			ServiceID:     r["service_id"],
			Date:          r["date"],
			ExceptionType: et,
		})
	}
	return cds, nil
}

func parseShapes(path string) ([]Shape, error) {
	rows, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	shapes := make([]Shape, 0, len(rows))
	for _, r := range rows {
		lat, _ := strconv.ParseFloat(r["shape_pt_lat"], 64)
		lon, _ := strconv.ParseFloat(r["shape_pt_lon"], 64)
		seq, _ := strconv.Atoi(r["shape_pt_sequence"])
		shapes = append(shapes, Shape{
			ShapeID:    r["shape_id"],
			ShapePtLat: lat,
			ShapePtLon: lon,
			ShapePtSeq: seq,
		})
	}
	return shapes, nil
}
```

- [ ] **Step 5: Run tests**

```bash
cd go && go test ./internal/gtfs/ -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add go/internal/gtfs/
git commit -m "feat: GTFS types and CSV parser"
```

---

## Task 4: GTFS Download

**Files:**
- Create: `go/internal/gtfs/download.go`
- Create: `go/internal/gtfs/download_test.go`

- [ ] **Step 1: Write failing test**

Create `go/internal/gtfs/download_test.go`:

```go
package gtfs

import (
	"archive/zip"
	"bytes"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func makeTestZip(t *testing.T) []byte {
	t.Helper()
	var buf bytes.Buffer
	w := zip.NewWriter(&buf)
	for _, name := range []string{"stops.txt", "stop_times.txt", "trips.txt", "routes.txt"} {
		f, err := w.Create(name)
		require.NoError(t, err)
		_, err = f.Write([]byte("header\n"))
		require.NoError(t, err)
	}
	require.NoError(t, w.Close())
	return buf.Bytes()
}

func TestDownloadGTFS(t *testing.T) {
	zipData := makeTestZip(t)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write(zipData)
	}))
	defer srv.Close()

	dir := t.TempDir()
	hash, err := DownloadGTFS(srv.URL, dir)
	require.NoError(t, err)
	assert.NotEmpty(t, hash)
	assert.FileExists(t, filepath.Join(dir, "stops.txt"))
}

func TestGetFeedHash(t *testing.T) {
	dir := t.TempDir()
	require.NoError(t, os.WriteFile(filepath.Join(dir, ".feed_hash"), []byte("abc123"), 0644))
	hash := GetFeedHash(dir)
	assert.Equal(t, "abc123", hash)
}

func TestGetFeedHashMissing(t *testing.T) {
	dir := t.TempDir()
	hash := GetFeedHash(dir)
	assert.Empty(t, hash)
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd go && go test ./internal/gtfs/ -run TestDownload -v
```

Expected: FAIL — `DownloadGTFS` not defined.

- [ ] **Step 3: Write download.go**

Create `go/internal/gtfs/download.go`:

```go
package gtfs

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
)

var ExpectedFiles = []string{"stops.txt", "stop_times.txt", "trips.txt", "routes.txt"}

// DownloadGTFS downloads a GTFS zip from url, extracts to destDir.
// Returns the SHA-256 hash of the zip content.
func DownloadGTFS(url, destDir string) (string, error) {
	if err := os.MkdirAll(destDir, 0755); err != nil {
		return "", fmt.Errorf("mkdir: %w", err)
	}

	fmt.Printf("Downloading GTFS feed from %s ...\n", url)
	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("download: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("download: HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read body: %w", err)
	}

	hash := fmt.Sprintf("%x", sha256.Sum256(body))
	if err := os.WriteFile(filepath.Join(destDir, ".feed_hash"), []byte(hash), 0644); err != nil {
		return "", fmt.Errorf("write hash: %w", err)
	}

	zr, err := zip.NewReader(bytes.NewReader(body), int64(len(body)))
	if err != nil {
		return "", fmt.Errorf("open zip: %w", err)
	}

	for _, f := range zr.File {
		outPath := filepath.Join(destDir, f.Name)
		rc, err := f.Open()
		if err != nil {
			return "", fmt.Errorf("open %s: %w", f.Name, err)
		}
		data, err := io.ReadAll(rc)
		rc.Close()
		if err != nil {
			return "", fmt.Errorf("read %s: %w", f.Name, err)
		}
		if err := os.WriteFile(outPath, data, 0644); err != nil {
			return "", fmt.Errorf("write %s: %w", f.Name, err)
		}
	}

	// Validate
	for _, name := range ExpectedFiles {
		if _, err := os.Stat(filepath.Join(destDir, name)); os.IsNotExist(err) {
			return "", fmt.Errorf("missing expected file: %s", name)
		}
	}

	fmt.Printf("GTFS extracted to %s\n", destDir)
	return hash, nil
}

// GetFeedHash reads the stored SHA-256 hash of the last download, or returns empty string.
func GetFeedHash(gtfsDir string) string {
	data, err := os.ReadFile(filepath.Join(gtfsDir, ".feed_hash"))
	if err != nil {
		return ""
	}
	return string(bytes.TrimSpace(data))
}
```

- [ ] **Step 4: Run tests**

```bash
cd go && go test ./internal/gtfs/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add go/internal/gtfs/download.go go/internal/gtfs/download_test.go
git commit -m "feat: GTFS download with zip extraction and hash"
```

---

## Task 5: GTFS Filtering

**Files:**
- Create: `go/internal/gtfs/filter.go`
- Create: `go/internal/gtfs/filter_test.go`

- [ ] **Step 1: Write failing test**

Create `go/internal/gtfs/filter_test.go`:

```go
package gtfs

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func makeTestFeed() *Feed {
	return &Feed{
		Stops: []Stop{
			{StopID: "S1", StopName: "A", StopLat: 49.168, StopLon: -121.951},
			{StopID: "S2", StopName: "B", StopLat: 49.170, StopLon: -121.955},
			{StopID: "S3", StopName: "C", StopLat: 49.180, StopLon: -121.960},
		},
		Routes: []Route{
			{RouteID: "R1", RouteShortName: "51", RouteLongName: "Downtown"},
			{RouteID: "R2", RouteShortName: "52", RouteLongName: "Sardis"},
			{RouteID: "R3", RouteShortName: "99", RouteLongName: "Other City"},
		},
		Trips: []Trip{
			{TripID: "T1", RouteID: "R1", ServiceID: "SVC1", DirectionID: "0"},
			{TripID: "T2", RouteID: "R2", ServiceID: "SVC1", DirectionID: "1"},
			{TripID: "T3", RouteID: "R3", ServiceID: "SVC1", DirectionID: "0"},
		},
		StopTimes: []StopTime{
			{TripID: "T1", StopID: "S1", ArrivalMin: 480, DepartureMin: 481, StopSequence: 1},
			{TripID: "T1", StopID: "S2", ArrivalMin: 490, DepartureMin: 491, StopSequence: 2},
			{TripID: "T2", StopID: "S2", ArrivalMin: 540, DepartureMin: 541, StopSequence: 1},
			{TripID: "T2", StopID: "S1", ArrivalMin: 555, DepartureMin: 556, StopSequence: 2},
			{TripID: "T3", StopID: "S3", ArrivalMin: 600, DepartureMin: 601, StopSequence: 1},
		},
		Calendar: []Calendar{
			{ServiceID: "SVC1", Monday: true, Tuesday: true, Wednesday: true,
				Thursday: true, Friday: true, Saturday: false, Sunday: false,
				StartDate: "20260101", EndDate: "20261231"},
		},
	}
}

func TestFilterToRoutes(t *testing.T) {
	feed := makeTestFeed()
	filtered, err := FilterFeed(feed, []string{"51", "52"}, "")
	require.NoError(t, err)

	// Should keep only routes 51 and 52
	assert.Len(t, filtered.Routes, 2)
	// Trips T1 and T2 only
	assert.Len(t, filtered.Trips, 2)
	// Stop S3 should be gone (only used by T3)
	for _, s := range filtered.Stops {
		assert.NotEqual(t, "S3", s.StopID)
	}
	assert.Len(t, filtered.Stops, 2)
	// StopTimes for T3 should be gone
	assert.Len(t, filtered.StopTimes, 4)
}

func TestFindBestWeekday(t *testing.T) {
	feed := makeTestFeed()
	dayName, refDate := FindBestWeekday(feed)
	assert.Contains(t, []string{"monday", "tuesday", "wednesday", "thursday", "friday"}, dayName)
	assert.False(t, refDate.IsZero())
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd go && go test ./internal/gtfs/ -run TestFilter -v
```

Expected: FAIL.

- [ ] **Step 3: Write filter.go**

Create `go/internal/gtfs/filter.go`:

```go
package gtfs

import (
	"fmt"
	"time"
)

var weekdays = []string{"monday", "tuesday", "wednesday", "thursday", "friday"}

// FindBestWeekday returns the weekday name and reference date with the most active trips.
func FindBestWeekday(feed *Feed) (string, time.Time) {
	bestDay := "wednesday"
	bestDate := time.Now()
	bestTrips := 0

	// Gather candidate dates from calendar range
	var candidates []time.Time
	for _, cal := range feed.Calendar {
		start, err1 := time.Parse("20060102", cal.StartDate)
		end, err2 := time.Parse("20060102", cal.EndDate)
		if err1 != nil || err2 != nil {
			continue
		}
		for d := start; !d.After(end) && len(candidates) < 100; d = d.AddDate(0, 0, 1) {
			if d.Weekday() >= time.Monday && d.Weekday() <= time.Friday {
				candidates = append(candidates, d)
			}
		}
	}

	// Also try calendar_dates
	for _, cd := range feed.CalendarDates {
		d, err := time.Parse("20060102", cd.Date)
		if err != nil {
			continue
		}
		if d.Weekday() >= time.Monday && d.Weekday() <= time.Friday {
			candidates = append(candidates, d)
		}
	}

	if len(candidates) == 0 {
		for i := 0; i < 7; i++ {
			d := time.Now().AddDate(0, 0, i)
			if d.Weekday() >= time.Monday && d.Weekday() <= time.Friday {
				candidates = append(candidates, d)
			}
		}
	}

	for _, d := range candidates {
		dayIdx := int(d.Weekday()) - 1 // Monday=0
		if dayIdx < 0 || dayIdx >= 5 {
			continue
		}
		dayName := weekdays[dayIdx]
		dStr := d.Format("20060102")

		activeServices := make(map[string]bool)

		// calendar.txt
		for _, cal := range feed.Calendar {
			if !calendarDayActive(cal, dayName) {
				continue
			}
			if cal.StartDate <= dStr && cal.EndDate >= dStr {
				activeServices[cal.ServiceID] = true
			}
		}

		// calendar_dates.txt exceptions
		for _, cd := range feed.CalendarDates {
			if cd.Date != dStr {
				continue
			}
			if cd.ExceptionType == 1 {
				activeServices[cd.ServiceID] = true
			} else if cd.ExceptionType == 2 {
				delete(activeServices, cd.ServiceID)
			}
		}

		nTrips := 0
		for _, trip := range feed.Trips {
			if activeServices[trip.ServiceID] {
				nTrips++
			}
		}
		if nTrips > bestTrips {
			bestTrips = nTrips
			bestDay = dayName
			bestDate = d
		}
	}

	return bestDay, bestDate
}

// FilterFeed filters the feed to only the given routes and a specific service day.
// If targetDay is empty, the best weekday is auto-selected.
func FilterFeed(feed *Feed, routes []string, targetDay string) (*Feed, error) {
	dayName := targetDay
	var refDate time.Time

	if dayName == "" {
		dayName, refDate = FindBestWeekday(feed)
		fmt.Printf("Auto-selected best weekday: %s (%s)\n", dayName, refDate.Format("2006-01-02"))
	} else {
		_, refDate = FindBestWeekday(feed)
	}

	// Resolve active services
	dStr := refDate.Format("20060102")
	activeServices := make(map[string]bool)

	for _, cal := range feed.Calendar {
		if !calendarDayActive(cal, dayName) {
			continue
		}
		if cal.StartDate <= dStr && cal.EndDate >= dStr {
			activeServices[cal.ServiceID] = true
		}
	}
	for _, cd := range feed.CalendarDates {
		if cd.Date != dStr {
			continue
		}
		if cd.ExceptionType == 1 {
			activeServices[cd.ServiceID] = true
		} else if cd.ExceptionType == 2 {
			delete(activeServices, cd.ServiceID)
		}
	}

	if len(activeServices) == 0 {
		return nil, fmt.Errorf("no active services for %s on %s", dayName, refDate.Format("2006-01-02"))
	}

	// Filter routes by short name
	routeSet := make(map[string]bool, len(routes))
	for _, r := range routes {
		routeSet[r] = true
	}
	routeIDSet := make(map[string]bool)
	var filteredRoutes []Route
	for _, r := range feed.Routes {
		if routeSet[r.RouteShortName] {
			filteredRoutes = append(filteredRoutes, r)
			routeIDSet[r.RouteID] = true
		}
	}

	// Filter trips
	tripIDSet := make(map[string]bool)
	var filteredTrips []Trip
	for _, t := range feed.Trips {
		if routeIDSet[t.RouteID] && activeServices[t.ServiceID] {
			filteredTrips = append(filteredTrips, t)
			tripIDSet[t.TripID] = true
		}
	}

	// Filter stop_times
	usedStopIDs := make(map[string]bool)
	var filteredStopTimes []StopTime
	for _, st := range feed.StopTimes {
		if tripIDSet[st.TripID] {
			filteredStopTimes = append(filteredStopTimes, st)
			usedStopIDs[st.StopID] = true
		}
	}

	// Filter stops
	var filteredStops []Stop
	for _, s := range feed.Stops {
		if usedStopIDs[s.StopID] {
			filteredStops = append(filteredStops, s)
		}
	}

	fmt.Printf("Filtered: %d routes, %d trips, %d stops\n",
		len(filteredRoutes), len(filteredTrips), len(filteredStops))

	return &Feed{
		Stops:         filteredStops,
		StopTimes:     filteredStopTimes,
		Trips:         filteredTrips,
		Routes:        filteredRoutes,
		Calendar:      feed.Calendar,
		CalendarDates: feed.CalendarDates,
		Shapes:        feed.Shapes,
	}, nil
}

func calendarDayActive(cal Calendar, day string) bool {
	switch day {
	case "monday":
		return cal.Monday
	case "tuesday":
		return cal.Tuesday
	case "wednesday":
		return cal.Wednesday
	case "thursday":
		return cal.Thursday
	case "friday":
		return cal.Friday
	case "saturday":
		return cal.Saturday
	case "sunday":
		return cal.Sunday
	}
	return false
}
```

- [ ] **Step 4: Run tests**

```bash
cd go && go test ./internal/gtfs/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add go/internal/gtfs/filter.go go/internal/gtfs/filter_test.go
git commit -m "feat: GTFS filtering by route and service day"
```

---

## Task 6: Grid Generation

**Files:**
- Create: `go/internal/grid/types.go`
- Create: `go/internal/grid/generate.go`
- Create: `go/internal/grid/boundary.go`
- Create: `go/internal/grid/generate_test.go`

- [ ] **Step 1: Write types**

Create `go/internal/grid/types.go`:

```go
package grid

// Point is a lat/lon coordinate in the analysis grid.
type Point struct {
	Lat float64
	Lon float64
}
```

- [ ] **Step 2: Write failing test**

Create `go/internal/grid/generate_test.go`:

```go
package grid

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestGenerateGrid(t *testing.T) {
	bboxSW := [2]float64{49.10, -122.00}
	bboxNE := [2]float64{49.15, -121.95}
	points := Generate(bboxSW, bboxNE, 250, "")

	assert.True(t, len(points) > 0)
	for _, p := range points {
		assert.True(t, p.Lat >= bboxSW[0] && p.Lat <= bboxNE[0])
		assert.True(t, p.Lon >= bboxSW[1] && p.Lon <= bboxNE[1])
	}
}

func TestGenerateGridSpacing(t *testing.T) {
	bboxSW := [2]float64{49.0, -122.0}
	bboxNE := [2]float64{49.1, -121.9}
	fine := Generate(bboxSW, bboxNE, 100, "")
	coarse := Generate(bboxSW, bboxNE, 500, "")
	assert.True(t, len(fine) > len(coarse))
}

func TestPointInPolygon(t *testing.T) {
	// Simple square polygon
	poly := [][]float64{
		{0, 0}, {0, 10}, {10, 10}, {10, 0}, {0, 0},
	}
	assert.True(t, PointInPolygon(5, 5, poly))
	assert.False(t, PointInPolygon(15, 5, poly))
	assert.False(t, PointInPolygon(-1, -1, poly))
}
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd go && go test ./internal/grid/ -v
```

Expected: FAIL.

- [ ] **Step 4: Write boundary.go**

Create `go/internal/grid/boundary.go`:

```go
package grid

import (
	"encoding/json"
	"os"
)

// GeoJSON structures (minimal, for reading boundary polygons)
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
// Returns nil if the file doesn't exist or can't be parsed.
// Each ring is [][]float64 where each point is [lon, lat].
func LoadBoundaryRings(path string) [][][]float64 {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var gj geoJSONFile
	if err := json.Unmarshal(data, &gj); err != nil || len(gj.Features) == 0 {
		return nil
	}

	geom := gj.Features[0].Geometry
	switch geom.Type {
	case "Polygon":
		var coords [][][]float64
		if err := json.Unmarshal(geom.Coordinates, &coords); err != nil {
			return nil
		}
		return coords
	case "MultiPolygon":
		var multi [][][][]float64
		if err := json.Unmarshal(geom.Coordinates, &multi); err != nil {
			return nil
		}
		// Flatten to rings (use outer rings only)
		var rings [][][]float64
		for _, poly := range multi {
			if len(poly) > 0 {
				rings = append(rings, poly[0])
			}
		}
		return rings
	}
	return nil
}

// PointInPolygon uses ray casting to test if (lon, lat) is inside a ring.
// Ring is [][]float64 where each point is [lon, lat] (or [x, y]).
func PointInPolygon(lon, lat float64, ring [][]float64) bool {
	n := len(ring)
	inside := false
	j := n - 1
	for i := 0; i < n; i++ {
		xi, yi := ring[i][0], ring[i][1]
		xj, yj := ring[j][0], ring[j][1]
		if ((yi > lat) != (yj > lat)) &&
			(lon < (xj-xi)*(lat-yi)/(yj-yi)+xi) {
			inside = !inside
		}
		j = i
	}
	return inside
}

// PointInBoundary tests if (lat, lon) is inside any of the boundary rings.
func PointInBoundary(lat, lon float64, rings [][][]float64) bool {
	for _, ring := range rings {
		if PointInPolygon(lon, lat, ring) {
			return true
		}
	}
	return false
}
```

- [ ] **Step 5: Write generate.go**

Create `go/internal/grid/generate.go`:

```go
package grid

import (
	"math"

	"github.com/jasondyck/chwk-tqi/internal/config"
)

// Generate creates a regular grid of lat/lon points at ~spacingM apart.
// If boundaryPath is non-empty and the file exists, clips to boundary polygon.
func Generate(bboxSW, bboxNE [2]float64, spacingM float64, boundaryPath string) []Point {
	centerLat := (bboxSW[0] + bboxNE[0]) / 2.0
	degPerMLat := 1.0 / (float64(config.EarthRadiusM) * math.Pi / 180.0)
	degPerMLon := 1.0 / (float64(config.EarthRadiusM) * math.Cos(centerLat*math.Pi/180.0) * math.Pi / 180.0)

	latStep := spacingM * degPerMLat
	lonStep := spacingM * degPerMLon

	var points []Point
	for lat := bboxSW[0]; lat < bboxNE[0]; lat += latStep {
		for lon := bboxSW[1]; lon < bboxNE[1]; lon += lonStep {
			points = append(points, Point{Lat: lat, Lon: lon})
		}
	}

	// Clip to boundary if provided
	if boundaryPath != "" {
		rings := LoadBoundaryRings(boundaryPath)
		if rings != nil {
			var clipped []Point
			for _, p := range points {
				if PointInBoundary(p.Lat, p.Lon, rings) {
					clipped = append(clipped, p)
				}
			}
			points = clipped
		}
	}

	return points
}
```

- [ ] **Step 6: Run tests**

```bash
cd go && go test ./internal/grid/ -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add go/internal/grid/
git commit -m "feat: grid generation with boundary clipping"
```

---

## Task 7: RAPTOR Types + Timetable Builder

**Files:**
- Create: `go/internal/raptor/types.go`
- Create: `go/internal/raptor/timetable.go`
- Create: `go/internal/raptor/timetable_test.go`

- [ ] **Step 1: Write types**

Create `go/internal/raptor/types.go`:

```go
package raptor

import "math"

const Inf = math.MaxFloat64

// Timetable holds pre-processed RAPTOR data structures.
type Timetable struct {
	NStops      int
	StopIDs     []string
	StopIDToIdx map[string]int

	NPatterns    int
	PatternStops [][]int                // pattern → list of stop indices
	PatternTrips []PatternTripData      // pattern → trip timetable

	StopToPatterns [][]StopPatternEntry // stop → list of (patternIdx, position)
	Transfers      [][]Transfer         // stop → list of transfer edges
}

// PatternTripData holds the trip times for a single pattern.
// Trips is [nTrips][nStops][2]int where [t][s][0]=arrival, [t][s][1]=departure (minutes).
type PatternTripData struct {
	NTrips int
	NStops int
	Data   []int // flat: [trip0_stop0_arr, trip0_stop0_dep, trip0_stop1_arr, ...]
}

// ArrivalAt returns the arrival time for trip t at stop position s.
func (p *PatternTripData) ArrivalAt(trip, stopPos int) int {
	return p.Data[(trip*p.NStops+stopPos)*2]
}

// DepartureAt returns the departure time for trip t at stop position s.
func (p *PatternTripData) DepartureAt(trip, stopPos int) int {
	return p.Data[(trip*p.NStops+stopPos)*2+1]
}

type StopPatternEntry struct {
	PatternIdx int
	Position   int
}

type Transfer struct {
	TargetIdx int
	WalkMin   float64
}

// FlatTimetable holds Numba-style flat arrays for the RAPTOR engine.
type FlatTimetable struct {
	NStops    int
	NPatterns int
	StopIDs   []string

	PSData    []int32   // pattern → stops (concatenated)
	PSOffsets []int32   // offsets into PSData

	TTData    []int32   // trip times (flat: arr, dep pairs)
	TTOffsets []int32   // offsets into TTData per pattern
	TTNTrips  []int32
	TTNStops  []int32

	SPData    [][2]int32 // stop → patterns: [patternIdx, position]
	SPOffsets []int32

	TRData    [][2]int32 // transfers: [targetStopIdx, walkMinX100]
	TROffsets []int32
}
```

- [ ] **Step 2: Write failing test**

Create `go/internal/raptor/timetable_test.go`:

```go
package raptor

import (
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/gtfs"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func makeTestFeed() *gtfs.Feed {
	return &gtfs.Feed{
		Stops: []gtfs.Stop{
			{StopID: "S1", StopLat: 49.168, StopLon: -121.951},
			{StopID: "S2", StopLat: 49.170, StopLon: -121.955},
			{StopID: "S3", StopLat: 49.175, StopLon: -121.960},
		},
		Routes: []gtfs.Route{
			{RouteID: "R1", RouteShortName: "51"},
		},
		Trips: []gtfs.Trip{
			{TripID: "T1", RouteID: "R1", ServiceID: "SVC1", DirectionID: "0"},
			{TripID: "T2", RouteID: "R1", ServiceID: "SVC1", DirectionID: "0"},
		},
		StopTimes: []gtfs.StopTime{
			{TripID: "T1", StopID: "S1", ArrivalMin: 480, DepartureMin: 481, StopSequence: 1},
			{TripID: "T1", StopID: "S2", ArrivalMin: 490, DepartureMin: 491, StopSequence: 2},
			{TripID: "T1", StopID: "S3", ArrivalMin: 500, DepartureMin: 501, StopSequence: 3},
			{TripID: "T2", StopID: "S1", ArrivalMin: 510, DepartureMin: 511, StopSequence: 1},
			{TripID: "T2", StopID: "S2", ArrivalMin: 520, DepartureMin: 521, StopSequence: 2},
			{TripID: "T2", StopID: "S3", ArrivalMin: 530, DepartureMin: 531, StopSequence: 3},
		},
	}
}

func TestBuildTimetable(t *testing.T) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)

	assert.Equal(t, 3, tt.NStops)
	assert.Equal(t, 1, tt.NPatterns) // both trips share same stop sequence
	assert.Len(t, tt.PatternStops[0], 3)
	assert.Equal(t, 2, tt.PatternTrips[0].NTrips)

	// Verify sorted by departure at first stop
	assert.Equal(t, 481, tt.PatternTrips[0].DepartureAt(0, 0))
	assert.Equal(t, 511, tt.PatternTrips[0].DepartureAt(1, 0))
}

func TestFlattenTimetable(t *testing.T) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)
	ft := Flatten(tt)

	require.Equal(t, tt.NStops, ft.NStops)
	require.Equal(t, tt.NPatterns, ft.NPatterns)
	assert.True(t, len(ft.PSData) > 0)
	assert.True(t, len(ft.TTData) > 0)
}
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd go && go test ./internal/raptor/ -v
```

Expected: FAIL.

- [ ] **Step 4: Write timetable.go**

Create `go/internal/raptor/timetable.go`:

```go
package raptor

import (
	"fmt"
	"math"
	"sort"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/gtfs"
)

// BuildTimetable converts a filtered GTFS feed into RAPTOR data structures.
func BuildTimetable(feed *gtfs.Feed) *Timetable {
	// Index stops
	stopIDs := make([]string, 0, len(feed.Stops))
	stopIDSet := make(map[string]bool)
	for _, s := range feed.Stops {
		if !stopIDSet[s.StopID] {
			stopIDs = append(stopIDs, s.StopID)
			stopIDSet[s.StopID] = true
		}
	}
	sort.Strings(stopIDs)
	stopIDToIdx := make(map[string]int, len(stopIDs))
	for i, sid := range stopIDs {
		stopIDToIdx[sid] = i
	}
	nStops := len(stopIDs)

	// Sort stop_times by trip, then sequence
	type stEntry struct {
		gtfs.StopTime
	}
	sortedST := make([]stEntry, len(feed.StopTimes))
	for i, st := range feed.StopTimes {
		sortedST[i] = stEntry{st}
	}
	sort.Slice(sortedST, func(i, j int) bool {
		if sortedST[i].TripID != sortedST[j].TripID {
			return sortedST[i].TripID < sortedST[j].TripID
		}
		return sortedST[i].StopSequence < sortedST[j].StopSequence
	})

	// Group by trip: trip → [(stopIdx, arrMin, depMin)]
	type tripStop struct {
		stopIdx, arrMin, depMin int
	}
	tripSeqs := make(map[string][]tripStop)
	for _, st := range sortedST {
		idx, ok := stopIDToIdx[st.StopID]
		if !ok {
			continue
		}
		tripSeqs[st.TripID] = append(tripSeqs[st.TripID], tripStop{idx, st.ArrivalMin, st.DepartureMin})
	}

	// Group trips into patterns (same sequence of stops)
	type patternKey string
	patternKeyToIdx := make(map[patternKey]int)
	var patternStops [][]int
	var patternTripRaw [][][]int // [pattern][trip][stop] → (arr, dep)

	for _, seq := range tripSeqs {
		// Build key from stop sequence
		key := ""
		for _, s := range seq {
			key += fmt.Sprintf("%d,", s.stopIdx)
		}
		pk := patternKey(key)

		pidx, exists := patternKeyToIdx[pk]
		if !exists {
			pidx = len(patternStops)
			patternKeyToIdx[pk] = pidx
			stops := make([]int, len(seq))
			for i, s := range seq {
				stops[i] = s.stopIdx
			}
			patternStops = append(patternStops, stops)
			patternTripRaw = append(patternTripRaw, nil)
		}

		tripData := make([]int, len(seq)*2)
		for i, s := range seq {
			tripData[i*2] = s.arrMin
			tripData[i*2+1] = s.depMin
		}
		patternTripRaw[pidx] = append(patternTripRaw[pidx], tripData)
	}

	// Sort trips within each pattern by departure at first stop, build PatternTripData
	patternTrips := make([]PatternTripData, len(patternStops))
	for pidx := range patternStops {
		nS := len(patternStops[pidx])
		trips := patternTripRaw[pidx]

		sort.Slice(trips, func(i, j int) bool {
			return trips[i][1] < trips[j][1] // departure at first stop
		})

		flat := make([]int, 0, len(trips)*nS*2)
		for _, t := range trips {
			flat = append(flat, t...)
		}
		patternTrips[pidx] = PatternTripData{
			NTrips: len(trips),
			NStops: nS,
			Data:   flat,
		}
	}

	nPatterns := len(patternStops)

	// Stop → patterns
	stopToPatterns := make([][]StopPatternEntry, nStops)
	for pidx, stops := range patternStops {
		for pos, sidx := range stops {
			stopToPatterns[sidx] = append(stopToPatterns[sidx], StopPatternEntry{pidx, pos})
		}
	}

	// Build transfer edges using KD-tree-like approach (brute force for small N)
	stopLats := make([]float64, nStops)
	stopLons := make([]float64, nStops)
	stopLookup := make(map[string]gtfs.Stop, len(feed.Stops))
	for _, s := range feed.Stops {
		stopLookup[s.StopID] = s
	}
	for i, sid := range stopIDs {
		s := stopLookup[sid]
		stopLats[i] = s.StopLat
		stopLons[i] = s.StopLon
	}

	centerLat := 0.0
	for _, lat := range stopLats {
		centerLat += lat
	}
	centerLat /= float64(nStops)
	centerLatRad := centerLat * math.Pi / 180.0

	stopXs, stopYs := geo.ProjectSliceToXY(stopLats, stopLons, centerLatRad)

	// Which patterns does each stop belong to?
	stopPatternSet := make([]map[int]bool, nStops)
	for i := range stopPatternSet {
		stopPatternSet[i] = make(map[int]bool)
	}
	for pidx, stops := range patternStops {
		for _, sidx := range stops {
			stopPatternSet[sidx][pidx] = true
		}
	}

	transfers := make([][]Transfer, nStops)
	maxDist := config.MaxTransferWalkM
	for i := 0; i < nStops; i++ {
		for j := 0; j < nStops; j++ {
			if i == j {
				continue
			}
			d := geo.Distance2D(stopXs[i], stopYs[i], stopXs[j], stopYs[j])
			if d > maxDist {
				continue
			}
			// Skip if same patterns
			if setsEqual(stopPatternSet[i], stopPatternSet[j]) {
				continue
			}
			walkMin := d / config.WalkSpeedMPerMin
			transfers[i] = append(transfers[i], Transfer{TargetIdx: j, WalkMin: walkMin})
		}
	}

	fmt.Printf("RAPTOR timetable: %d stops, %d patterns, %d trips\n",
		nStops, nPatterns, countTrips(patternTrips))

	return &Timetable{
		NStops:         nStops,
		StopIDs:        stopIDs,
		StopIDToIdx:    stopIDToIdx,
		NPatterns:      nPatterns,
		PatternStops:   patternStops,
		PatternTrips:   patternTrips,
		StopToPatterns: stopToPatterns,
		Transfers:      transfers,
	}
}

// Flatten converts a Timetable to flat arrays for the engine.
func Flatten(tt *Timetable) *FlatTimetable {
	// Pattern stops
	var psData []int32
	psOffsets := []int32{0}
	for _, stops := range tt.PatternStops {
		for _, s := range stops {
			psData = append(psData, int32(s))
		}
		psOffsets = append(psOffsets, int32(len(psData)))
	}

	// Trip times
	var ttData []int32
	ttOffsets := []int32{0}
	ttNTrips := make([]int32, tt.NPatterns)
	ttNStops := make([]int32, tt.NPatterns)
	for pidx, pt := range tt.PatternTrips {
		ttNTrips[pidx] = int32(pt.NTrips)
		ttNStops[pidx] = int32(pt.NStops)
		for _, v := range pt.Data {
			ttData = append(ttData, int32(v))
		}
		ttOffsets = append(ttOffsets, int32(len(ttData)))
	}

	// Stop → patterns
	var spData [][2]int32
	spOffsets := []int32{0}
	for _, entries := range tt.StopToPatterns {
		for _, e := range entries {
			spData = append(spData, [2]int32{int32(e.PatternIdx), int32(e.Position)})
		}
		spOffsets = append(spOffsets, int32(len(spData)))
	}

	// Transfers
	var trData [][2]int32
	trOffsets := []int32{0}
	for _, entries := range tt.Transfers {
		for _, tr := range entries {
			trData = append(trData, [2]int32{int32(tr.TargetIdx), int32(tr.WalkMin * 100)})
		}
		trOffsets = append(trOffsets, int32(len(trData)))
	}

	return &FlatTimetable{
		NStops:    tt.NStops,
		NPatterns: tt.NPatterns,
		StopIDs:   tt.StopIDs,
		PSData:    psData,
		PSOffsets: psOffsets,
		TTData:    ttData,
		TTOffsets: ttOffsets,
		TTNTrips:  ttNTrips,
		TTNStops:  ttNStops,
		SPData:    spData,
		SPOffsets: spOffsets,
		TRData:    trData,
		TROffsets: trOffsets,
	}
}

func setsEqual(a, b map[int]bool) bool {
	if len(a) != len(b) {
		return false
	}
	for k := range a {
		if !b[k] {
			return false
		}
	}
	return true
}

func countTrips(pts []PatternTripData) int {
	n := 0
	for _, pt := range pts {
		n += pt.NTrips
	}
	return n
}
```

- [ ] **Step 5: Run tests**

```bash
cd go && go test ./internal/raptor/ -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add go/internal/raptor/
git commit -m "feat: RAPTOR timetable builder with flat array conversion"
```

---

## Task 8: RAPTOR Engine

**Files:**
- Create: `go/internal/raptor/engine.go`
- Create: `go/internal/raptor/engine_test.go`

- [ ] **Step 1: Write failing test**

Create `go/internal/raptor/engine_test.go`:

```go
package raptor

import (
	"math"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestRaptorSimple(t *testing.T) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)
	ft := Flatten(tt)

	// Depart from S1 at 08:00 (480 min), walk time 0
	s1Idx := tt.StopIDToIdx["S1"]
	sources := []SourceStop{{StopIdx: s1Idx, ArrivalTime: 480}}

	best := RunRAPTOR(ft, sources, 2, 480+90)

	// S1 is source → arrival = 480
	assert.InDelta(t, 480, best[s1Idx], 0.01)

	// S2 should be reachable via T1: arrives at 490
	s2Idx := tt.StopIDToIdx["S2"]
	assert.InDelta(t, 490, best[s2Idx], 0.01)

	// S3 should be reachable via T1: arrives at 500
	s3Idx := tt.StopIDToIdx["S3"]
	assert.InDelta(t, 500, best[s3Idx], 0.01)
}

func TestRaptorMissedTrip(t *testing.T) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)
	ft := Flatten(tt)

	// Depart at 09:00 (540 min) — should catch T2 (departs 511 at S1)
	// Wait, T2 departs at 511 from S1. If we arrive at 540, we miss T2.
	// Both trips have already departed from S1 by 540. Unreachable.
	s1Idx := tt.StopIDToIdx["S1"]
	sources := []SourceStop{{StopIdx: s1Idx, ArrivalTime: 540}}

	best := RunRAPTOR(ft, sources, 2, 540+90)

	s3Idx := tt.StopIDToIdx["S3"]
	assert.Equal(t, Inf, best[s3Idx])
}

func TestRaptorNoSource(t *testing.T) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)
	ft := Flatten(tt)

	best := RunRAPTOR(ft, nil, 2, 570)
	for _, v := range best {
		assert.Equal(t, Inf, v)
	}
}

func TestRaptorWorkspace(t *testing.T) {
	ws := NewWorkspace(10)
	assert.Len(t, ws.Best, 10)
	assert.Equal(t, math.MaxFloat64, ws.Best[0])
	ws.Reset(10)
	assert.Equal(t, math.MaxFloat64, ws.Best[0])
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd go && go test ./internal/raptor/ -run TestRaptor -v
```

Expected: FAIL.

- [ ] **Step 3: Write engine.go**

Create `go/internal/raptor/engine.go`:

```go
package raptor

import "sort"

// SourceStop represents a stop reachable from the origin by walking.
type SourceStop struct {
	StopIdx     int
	ArrivalTime float64 // minutes since midnight
}

// Workspace holds pre-allocated working memory for RAPTOR.
// Reuse across calls to avoid allocations in hot loops.
type Workspace struct {
	Tau       [][]float64 // [K+1][nStops]
	Best      []float64   // [nStops]
	Marked    []bool      // [nStops]
	NewMarked []bool      // [nStops]
	PatBoard  []int32     // [nPatterns] earliest boarding position, -1 = not scanned
}

// NewWorkspace allocates RAPTOR working memory for nStops stops.
func NewWorkspace(nStops int) *Workspace {
	ws := &Workspace{}
	ws.init(nStops)
	return ws
}

func (ws *Workspace) init(nStops int) {
	maxK := 4 // MaxTransfers + 1 + 1, generous
	ws.Tau = make([][]float64, maxK)
	for k := range ws.Tau {
		ws.Tau[k] = make([]float64, nStops)
	}
	ws.Best = make([]float64, nStops)
	ws.Marked = make([]bool, nStops)
	ws.NewMarked = make([]bool, nStops)
	ws.PatBoard = nil // allocated per call based on nPatterns
	ws.Reset(nStops)
}

// Reset reinitializes all arrays to infinity/false.
func (ws *Workspace) Reset(nStops int) {
	if len(ws.Best) < nStops {
		ws.init(nStops)
		return
	}
	for k := range ws.Tau {
		for s := 0; s < nStops; s++ {
			ws.Tau[k][s] = Inf
		}
	}
	for s := 0; s < nStops; s++ {
		ws.Best[s] = Inf
		ws.Marked[s] = false
		ws.NewMarked[s] = false
	}
}

// RunRAPTOR executes the RAPTOR algorithm on a FlatTimetable.
// Returns earliest arrival time at each stop (Inf if unreachable).
func RunRAPTOR(ft *FlatTimetable, sources []SourceStop, maxTransfers int, maxTime float64) []float64 {
	ws := NewWorkspace(ft.NStops)
	RunRAPTORWithWorkspace(ft, sources, maxTransfers, maxTime, ws)
	result := make([]float64, ft.NStops)
	copy(result, ws.Best[:ft.NStops])
	return result
}

// RunRAPTORWithWorkspace runs RAPTOR using a pre-allocated workspace (zero alloc hot path).
func RunRAPTORWithWorkspace(ft *FlatTimetable, sources []SourceStop, maxTransfers int, maxTime float64, ws *Workspace) {
	nStops := ft.NStops
	nPatterns := ft.NPatterns
	K := maxTransfers + 1

	ws.Reset(nStops)

	// Ensure PatBoard is large enough
	if len(ws.PatBoard) < nPatterns {
		ws.PatBoard = make([]int32, nPatterns)
	}

	// Initialize sources
	for _, src := range sources {
		s := src.StopIdx
		t := src.ArrivalTime
		if t < ws.Tau[0][s] {
			ws.Tau[0][s] = t
			ws.Best[s] = t
			ws.Marked[s] = true
		}
	}

	// Initial transfers
	applyTransfers(ft, ws.Tau[0], ws.Best, ws.Marked, nStops, maxTime, ws.NewMarked, ft.TRData, ft.TROffsets)
	// Merge new marks
	for s := 0; s < nStops; s++ {
		if ws.NewMarked[s] {
			ws.Marked[s] = true
		}
		ws.NewMarked[s] = false
	}

	for k := 1; k <= K; k++ {
		// Copy previous round
		for s := 0; s < nStops; s++ {
			ws.Tau[k][s] = ws.Tau[k-1][s]
			ws.NewMarked[s] = false
		}

		// Collect patterns to scan
		for p := 0; p < nPatterns; p++ {
			ws.PatBoard[p] = -1
		}
		for s := 0; s < nStops; s++ {
			if !ws.Marked[s] {
				continue
			}
			spStart := int(ft.SPOffsets[s])
			spEnd := int(ft.SPOffsets[s+1])
			for j := spStart; j < spEnd; j++ {
				pidx := ft.SPData[j][0]
				pos := ft.SPData[j][1]
				if ws.PatBoard[pidx] < 0 || pos < ws.PatBoard[pidx] {
					ws.PatBoard[pidx] = pos
				}
			}
		}

		// Route scanning
		for pidx := 0; pidx < nPatterns; pidx++ {
			if ws.PatBoard[pidx] < 0 {
				continue
			}
			boardPos := int(ws.PatBoard[pidx])
			nT := int(ft.TTNTrips[pidx])
			nS := int(ft.TTNStops[pidx])
			if nT == 0 {
				continue
			}
			ttOff := int(ft.TTOffsets[pidx])
			currentTrip := -1

			for pos := boardPos; pos < nS; pos++ {
				stopIdx := int(ft.PSData[int(ft.PSOffsets[pidx])+pos])

				// Can current trip improve arrival?
				if currentTrip >= 0 {
					arrTime := float64(ft.TTData[ttOff+currentTrip*nS*2+pos*2])
					if arrTime < ws.Best[stopIdx] && arrTime <= maxTime {
						if arrTime < ws.Tau[k][stopIdx] {
							ws.Tau[k][stopIdx] = arrTime
						}
						if arrTime < ws.Best[stopIdx] {
							ws.Best[stopIdx] = arrTime
						}
						ws.NewMarked[stopIdx] = true
					}
				}

				// Can we board an earlier trip?
				earliestBoard := ws.Tau[k-1][stopIdx]
				if earliestBoard < Inf {
					// Binary search for earliest trip departing >= earliestBoard
					lo, hi := 0, nT
					for lo < hi {
						mid := (lo + hi) / 2
						dep := float64(ft.TTData[ttOff+mid*nS*2+pos*2+1])
						if dep < earliestBoard {
							lo = mid + 1
						} else {
							hi = mid
						}
					}
					if lo < nT {
						if currentTrip < 0 || lo < currentTrip {
							currentTrip = lo
						}
					}
				}
			}
		}

		// Transfer phase
		applyTransfers(ft, ws.Tau[k], ws.Best, ws.NewMarked, nStops, maxTime, ws.Marked, ft.TRData, ft.TROffsets)

		// Check convergence
		anyMarked := false
		for s := 0; s < nStops; s++ {
			ws.Marked[s] = ws.NewMarked[s]
			if ws.NewMarked[s] {
				anyMarked = true
			}
		}
		// Merge transfer marks into Marked
		// (applyTransfers wrote new marks into ws.Marked, merge them)
		for s := 0; s < nStops; s++ {
			if ws.NewMarked[s] {
				ws.Marked[s] = true
			}
		}
		if !anyMarked {
			break
		}
	}
}

func applyTransfers(ft *FlatTimetable, tau []float64, best []float64, marked []bool, nStops int, maxTime float64, newMarks []bool, trData [][2]int32, trOffsets []int32) {
	for s := 0; s < nStops; s++ {
		if !marked[s] {
			continue
		}
		trStart := int(trOffsets[s])
		trEnd := int(trOffsets[s+1])
		for j := trStart; j < trEnd; j++ {
			target := int(trData[j][0])
			walkMin := float64(trData[j][1]) / 100.0
			arr := tau[s] + walkMin
			if arr < tau[target] && arr <= maxTime {
				tau[target] = arr
				if arr < best[target] {
					best[target] = arr
				}
				newMarks[target] = true
			}
		}
	}
}

// EarliestTripDeparture finds the first trip in a sorted trip list departing >= minTime.
// Uses binary search. Returns index or -1 if no trip found.
func EarliestTripDeparture(departures []int, minTime int) int {
	idx := sort.SearchInts(departures, minTime)
	if idx >= len(departures) {
		return -1
	}
	return idx
}
```

- [ ] **Step 4: Run tests**

```bash
cd go && go test ./internal/raptor/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add go/internal/raptor/engine.go go/internal/raptor/engine_test.go
git commit -m "feat: RAPTOR engine with workspace reuse and binary search"
```

---

## Task 9: Scoring Module — TSR, Coverage, Speed, Reliability, Time Profile

**Files:**
- Create: `go/internal/scoring/types.go`
- Create: `go/internal/scoring/tsr.go`
- Create: `go/internal/scoring/coverage.go`
- Create: `go/internal/scoring/speed.go`
- Create: `go/internal/scoring/reliability.go`
- Create: `go/internal/scoring/time_profile.go`
- Create: `go/internal/scoring/tqi.go`
- Create: `go/internal/scoring/scoring_test.go`

- [ ] **Step 1: Write types.go**

Create `go/internal/scoring/types.go`:

```go
package scoring

import "math"

const InfFloat = math.MaxFloat64

// ODMetrics holds the travel time matrix results.
type ODMetrics struct {
	MeanTravelTime  [][]float64 // [origins][dests] — Inf if unreachable
	Reachability    [][]float64 // [origins][dests] — fraction of slots reachable
	TravelTimeStd   [][]float64 // [origins][dests]
	PerSlotCoverage []float64   // [nTimes]
	PerSlotMeanTSR  []float64   // [nTimes]
	DistancesKM     [][]float64 // [origins][dests]
}

// TQIResult holds the final TQI scores.
type TQIResult struct {
	TQI              float64
	CoverageScore    float64
	SpeedScore       float64
	TimeProfile      []TimeSlotScore
	ReliabilityCV    float64
	ReliabilityPerOrigin []float64
}

type TimeSlotScore struct {
	Label string
	Score float64
}
```

- [ ] **Step 2: Write failing test**

Create `go/internal/scoring/scoring_test.go`:

```go
package scoring

import (
	"math"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestComputeTSR(t *testing.T) {
	// 10 km in 30 min = 20 km/h
	tsr := ComputeTSR(10.0, 30.0)
	assert.InDelta(t, 20.0, tsr, 0.01)
}

func TestComputeTSRUnreachable(t *testing.T) {
	tsr := ComputeTSR(10.0, math.MaxFloat64)
	assert.Equal(t, 0.0, tsr)
}

func TestValidPairMask(t *testing.T) {
	assert.True(t, IsValidPair(1.0))
	assert.False(t, IsValidPair(0.3)) // < 0.5 km
}

func TestCoverageScore(t *testing.T) {
	// 2x2 matrix, all reachable at 0.5, distances > 0.5km
	reach := [][]float64{{0, 0.5}, {0.5, 0}}
	dist := [][]float64{{0, 2.0}, {2.0, 0}}
	score := ComputeCoverageScore(reach, dist)
	assert.InDelta(t, 50.0, score, 0.1) // mean of 0.5 for valid pairs = 50
}

func TestSpeedScore(t *testing.T) {
	// Distance 10km, travel time 30min = 20km/h TSR
	// Speed score = (20-5)/(40-5)*100 = 42.86
	dist := [][]float64{{0, 10.0}, {10.0, 0}}
	tt := [][]float64{{InfFloat, 30.0}, {30.0, InfFloat}}
	score := ComputeSpeedScore(dist, tt)
	assert.InDelta(t, 42.86, score, 0.5)
}

func TestComputeTQI(t *testing.T) {
	metrics := &ODMetrics{
		MeanTravelTime:  [][]float64{{InfFloat, 30.0}, {30.0, InfFloat}},
		Reachability:    [][]float64{{0, 0.8}, {0.8, 0}},
		TravelTimeStd:   [][]float64{{0, 5.0}, {5.0, 0}},
		PerSlotCoverage: []float64{0.5},
		PerSlotMeanTSR:  []float64{15.0},
		DistancesKM:     [][]float64{{0, 10.0}, {10.0, 0}},
	}
	result := ComputeTQI(metrics)
	assert.True(t, result.TQI > 0)
	assert.True(t, result.CoverageScore > 0)
	assert.True(t, result.SpeedScore > 0)
}
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd go && go test ./internal/scoring/ -v
```

Expected: FAIL.

- [ ] **Step 4: Write tsr.go**

Create `go/internal/scoring/tsr.go`:

```go
package scoring

import "github.com/jasondyck/chwk-tqi/internal/config"

// ComputeTSR returns the Transit Speed Ratio in km/h.
// Returns 0 if unreachable or zero travel time.
func ComputeTSR(distKM, travelTimeMin float64) float64 {
	if travelTimeMin >= InfFloat || travelTimeMin <= 0 {
		return 0.0
	}
	return distKM / (travelTimeMin / 60.0)
}

// IsValidPair returns true if the OD pair distance is >= MinODDistKM.
func IsValidPair(distKM float64) bool {
	return distKM >= config.MinODDistKM
}
```

- [ ] **Step 5: Write coverage.go**

Create `go/internal/scoring/coverage.go`:

```go
package scoring

// ComputeCoverageScore returns coverage as 0-100.
func ComputeCoverageScore(reachability, distancesKM [][]float64) float64 {
	sum := 0.0
	count := 0
	for i := range reachability {
		for j := range reachability[i] {
			if IsValidPair(distancesKM[i][j]) {
				sum += reachability[i][j]
				count++
			}
		}
	}
	if count == 0 {
		return 0.0
	}
	return sum / float64(count) * 100.0
}
```

- [ ] **Step 6: Write speed.go**

Create `go/internal/scoring/speed.go`:

```go
package scoring

import (
	"math"

	"github.com/jasondyck/chwk-tqi/internal/config"
)

// ComputeSpeedScore returns the speed score 0-100.
func ComputeSpeedScore(distancesKM, meanTravelTime [][]float64) float64 {
	sum := 0.0
	count := 0
	for i := range distancesKM {
		for j := range distancesKM[i] {
			if !IsValidPair(distancesKM[i][j]) || meanTravelTime[i][j] >= InfFloat {
				continue
			}
			tsr := ComputeTSR(distancesKM[i][j], meanTravelTime[i][j])
			sum += tsr
			count++
		}
	}
	if count == 0 {
		return 0.0
	}
	meanTSR := sum / float64(count)
	score := (meanTSR - config.TSRWalk) / (config.TSRCar - config.TSRWalk) * 100.0
	return math.Max(0, math.Min(100, score))
}
```

- [ ] **Step 7: Write reliability.go**

Create `go/internal/scoring/reliability.go`:

```go
package scoring

import "math"

// ComputeReliability returns (meanCV, perOriginCV).
func ComputeReliability(meanTT, ttStd, distKM [][]float64) (float64, []float64) {
	nOrigins := len(meanTT)
	perOrigin := make([]float64, nOrigins)
	totalCV := 0.0
	totalCount := 0

	for i := 0; i < nOrigins; i++ {
		rowSum := 0.0
		rowCount := 0
		for j := range meanTT[i] {
			if !IsValidPair(distKM[i][j]) || meanTT[i][j] >= InfFloat || meanTT[i][j] <= 0 {
				continue
			}
			cv := ttStd[i][j] / meanTT[i][j]
			if !math.IsNaN(cv) && !math.IsInf(cv, 0) {
				rowSum += cv
				rowCount++
			}
		}
		if rowCount > 0 {
			perOrigin[i] = rowSum / float64(rowCount)
			totalCV += rowSum
			totalCount += rowCount
		}
	}

	meanCV := 0.0
	if totalCount > 0 {
		meanCV = totalCV / float64(totalCount)
	}
	return meanCV, perOrigin
}
```

- [ ] **Step 8: Write time_profile.go**

Create `go/internal/scoring/time_profile.go`:

```go
package scoring

import (
	"fmt"
	"math"

	"github.com/jasondyck/chwk-tqi/internal/config"
)

// ComputeTimeProfile computes TQI for each departure time slot.
func ComputeTimeProfile(perSlotCoverage, perSlotMeanTSR []float64) []TimeSlotScore {
	depTimes := config.DepartureTimes()
	results := make([]TimeSlotScore, len(depTimes))
	for i, tMin := range depTimes {
		h := tMin / 60
		m := tMin % 60
		label := fmt.Sprintf("%02d:%02d", h, m)

		covScore := perSlotCoverage[i] * 100.0
		tsr := perSlotMeanTSR[i]
		spdScore := math.Max(0, math.Min(100,
			(tsr-config.TSRWalk)/(config.TSRCar-config.TSRWalk)*100.0))
		slotTQI := 0.5*covScore + 0.5*spdScore

		results[i] = TimeSlotScore{Label: label, Score: slotTQI}
	}
	return results
}
```

- [ ] **Step 9: Write tqi.go**

Create `go/internal/scoring/tqi.go`:

```go
package scoring

// ComputeTQI computes the overall Transit Quality Index.
func ComputeTQI(metrics *ODMetrics) *TQIResult {
	coverage := ComputeCoverageScore(metrics.Reachability, metrics.DistancesKM)
	speed := ComputeSpeedScore(metrics.DistancesKM, metrics.MeanTravelTime)
	tqi := 0.5*coverage + 0.5*speed

	timeProfile := ComputeTimeProfile(metrics.PerSlotCoverage, metrics.PerSlotMeanTSR)

	relCV, relPerOrigin := ComputeReliability(
		metrics.MeanTravelTime, metrics.TravelTimeStd, metrics.DistancesKM)

	return &TQIResult{
		TQI:                  tqi,
		CoverageScore:        coverage,
		SpeedScore:           speed,
		TimeProfile:          timeProfile,
		ReliabilityCV:        relCV,
		ReliabilityPerOrigin: relPerOrigin,
	}
}
```

- [ ] **Step 10: Run tests**

```bash
cd go && go test ./internal/scoring/ -v
```

Expected: all PASS.

- [ ] **Step 11: Commit**

```bash
git add go/internal/scoring/
git commit -m "feat: scoring modules — TSR, coverage, speed, reliability, time profile, TQI"
```

---

## Task 10: TCQSM + PTAL + Amenity Scoring

**Files:**
- Create: `go/internal/scoring/tcqsm.go`
- Create: `go/internal/scoring/ptal.go`
- Create: `go/internal/scoring/amenity.go`
- Create: `go/internal/scoring/tcqsm_test.go`

- [ ] **Step 1: Write failing test**

Create `go/internal/scoring/tcqsm_test.go`:

```go
package scoring

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHeadwayToLOS(t *testing.T) {
	grade, desc := HeadwayToLOS(8)
	assert.Equal(t, "A", grade)
	assert.Contains(t, desc, "schedule")

	grade, _ = HeadwayToLOS(25)
	assert.Equal(t, "D", grade)

	grade, _ = HeadwayToLOS(120)
	assert.Equal(t, "F", grade)
}

func TestPTALGrade(t *testing.T) {
	assert.Equal(t, "1a", PTALGradeFromAI(1.0))
	assert.Equal(t, "3", PTALGradeFromAI(12.0))
	assert.Equal(t, "6b", PTALGradeFromAI(50.0))
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd go && go test ./internal/scoring/ -run TestHeadway -v
```

Expected: FAIL.

- [ ] **Step 3: Write tcqsm.go**

Create `go/internal/scoring/tcqsm.go`:

```go
package scoring

import (
	"math"
	"sort"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/gtfs"
)

// RouteLOS holds TCQSM grading for a single route.
type RouteLOS struct {
	RouteName       string  `json:"route_name"`
	RouteLongName   string  `json:"route_long_name"`
	RouteID         string  `json:"route_id"`
	NTrips          int     `json:"trip_count"`
	MedianHeadway   float64 `json:"median_headway_min"`
	PeakHeadway     *float64 `json:"peak_headway_min"`
	LOSGrade        string  `json:"los_grade"`
	LOSDescription  string  `json:"los_description"`
}

// SystemLOSSummary aggregates LOS across all routes.
type SystemLOSSummary struct {
	NRoutes             int            `json:"n_routes"`
	GradeCounts         map[string]int `json:"grade_counts"`
	MedianSystemHeadway float64        `json:"median_headway"`
	BestGrade           string         `json:"best_grade"`
	WorstGrade          string         `json:"worst_grade"`
	PctLOSDOrWorse      float64        `json:"pct_los_d_or_worse"`
}

// HeadwayToLOS maps median headway to TCQSM LOS grade.
func HeadwayToLOS(headwayMin float64) (string, string) {
	for _, g := range config.TCQSMLOSGrades() {
		if headwayMin <= g.MaxHeadway {
			return g.Grade, g.Description
		}
	}
	return "F", "Service unattractive to all riders"
}

// ComputeRouteLOS computes TCQSM LOS for each route.
func ComputeRouteLOS(feed *gtfs.Feed) []RouteLOS {
	// Build route lookup
	routeLongNames := make(map[string]string)
	routeShortNames := make(map[string]string)
	for _, r := range feed.Routes {
		routeLongNames[r.RouteID] = r.RouteLongName
		routeShortNames[r.RouteID] = r.RouteShortName
	}

	// Build trip → route lookup
	tripRoute := make(map[string]string)
	tripDir := make(map[string]string)
	for _, t := range feed.Trips {
		tripRoute[t.TripID] = t.RouteID
		tripDir[t.TripID] = t.DirectionID
	}

	// Group stop_times by route+direction, get first departure per trip
	type routeDirKey struct {
		routeID, dirID string
	}
	tripStarts := make(map[routeDirKey][]float64)
	tripFirstDep := make(map[string]int) // tripID → min departure

	// Find first stop departure for each trip
	for _, st := range feed.StopTimes {
		if cur, ok := tripFirstDep[st.TripID]; !ok || st.StopSequence < cur {
			tripFirstDep[st.TripID] = st.StopSequence
		}
	}
	// Now get actual departure times at first stop
	tripFirstDepTime := make(map[string]float64)
	tripFirstSeq := make(map[string]int)
	for _, st := range feed.StopTimes {
		if _, ok := tripFirstSeq[st.TripID]; !ok {
			tripFirstSeq[st.TripID] = st.StopSequence
			tripFirstDepTime[st.TripID] = float64(st.DepartureMin)
		} else if st.StopSequence < tripFirstSeq[st.TripID] {
			tripFirstSeq[st.TripID] = st.StopSequence
			tripFirstDepTime[st.TripID] = float64(st.DepartureMin)
		}
	}

	for tripID, depTime := range tripFirstDepTime {
		rID := tripRoute[tripID]
		dID := tripDir[tripID]
		key := routeDirKey{rID, dID}
		tripStarts[key] = append(tripStarts[key], depTime)
	}

	// Compute headway per route (best direction)
	routeHeadways := make(map[string]float64)
	routeTripCounts := make(map[string]int)

	routeTripSet := make(map[string]map[string]bool)
	for _, t := range feed.Trips {
		if routeTripSet[t.RouteID] == nil {
			routeTripSet[t.RouteID] = make(map[string]bool)
		}
		routeTripSet[t.RouteID][t.TripID] = true
	}
	for rID, trips := range routeTripSet {
		routeTripCounts[rID] = len(trips)
	}

	for key, starts := range tripStarts {
		sort.Float64s(starts)
		if len(starts) < 2 {
			continue
		}
		var headways []float64
		for i := 1; i < len(starts); i++ {
			hw := starts[i] - starts[i-1]
			if hw > 0 {
				headways = append(headways, hw)
			}
		}
		if len(headways) == 0 {
			continue
		}
		sort.Float64s(headways)
		medHW := headways[len(headways)/2]

		cur, exists := routeHeadways[key.routeID]
		if !exists || medHW < cur {
			routeHeadways[key.routeID] = medHW
		}
	}

	var results []RouteLOS
	for _, r := range feed.Routes {
		hw, ok := routeHeadways[r.RouteID]
		if !ok {
			hw = 999.0
		}
		grade, desc := HeadwayToLOS(hw)
		results = append(results, RouteLOS{
			RouteName:      r.RouteShortName,
			RouteLongName:  r.RouteLongName,
			RouteID:        r.RouteID,
			NTrips:         routeTripCounts[r.RouteID],
			MedianHeadway:  math.Round(hw*10) / 10,
			LOSGrade:       grade,
			LOSDescription: desc,
		})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].RouteName < results[j].RouteName
	})
	return results
}

// ComputeSystemLOSSummary aggregates route-level LOS.
func ComputeSystemLOSSummary(routeLOS []RouteLOS) *SystemLOSSummary {
	gradeCounts := make(map[string]int)
	var headways []float64
	bestGrade := "F"
	worstGrade := "A"

	for _, r := range routeLOS {
		gradeCounts[r.LOSGrade]++
		if r.MedianHeadway < 999 {
			headways = append(headways, r.MedianHeadway)
		}
		if r.LOSGrade < bestGrade {
			bestGrade = r.LOSGrade
		}
		if r.LOSGrade > worstGrade {
			worstGrade = r.LOSGrade
		}
	}

	medHW := 0.0
	if len(headways) > 0 {
		sort.Float64s(headways)
		medHW = headways[len(headways)/2]
	}

	dOrWorse := 0
	for _, r := range routeLOS {
		if r.LOSGrade >= "D" {
			dOrWorse++
		}
	}
	pctDOrWorse := 0.0
	if len(routeLOS) > 0 {
		pctDOrWorse = float64(dOrWorse) / float64(len(routeLOS)) * 100
	}

	return &SystemLOSSummary{
		NRoutes:             len(routeLOS),
		GradeCounts:         gradeCounts,
		MedianSystemHeadway: medHW,
		BestGrade:           bestGrade,
		WorstGrade:          worstGrade,
		PctLOSDOrWorse:      pctDOrWorse,
	}
}
```

- [ ] **Step 4: Write ptal.go**

Create `go/internal/scoring/ptal.go`:

```go
package scoring

import (
	"math"
	"sort"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/gtfs"
)

// PTALGradeFromAI maps an Accessibility Index value to a PTAL grade.
func PTALGradeFromAI(ai float64) string {
	for _, g := range config.PTALGrades() {
		if ai <= g.MaxAI {
			return g.Grade
		}
	}
	return "6b"
}

// PTALResult holds per-grid-point PTAL values.
type PTALResult struct {
	Values []float64 // AI per grid point
	Grades []string  // grade per grid point
}

// ComputePTAL computes PTAL for each grid point.
func ComputePTAL(points []grid.Point, feed *gtfs.Feed) *PTALResult {
	nPoints := len(points)
	aiValues := make([]float64, nPoints)
	grades := make([]string, nPoints)

	// Build stop spatial data
	stopLats := make([]float64, len(feed.Stops))
	stopLons := make([]float64, len(feed.Stops))
	stopIDs := make([]string, len(feed.Stops))
	for i, s := range feed.Stops {
		stopLats[i] = s.StopLat
		stopLons[i] = s.StopLon
		stopIDs[i] = s.StopID
	}

	meanLat := 0.0
	for _, lat := range stopLats {
		meanLat += lat
	}
	meanLat /= float64(len(stopLats))
	centerLatRad := meanLat * math.Pi / 180.0

	stopXs, stopYs := geo.ProjectSliceToXY(stopLats, stopLons, centerLatRad)

	// Project grid
	gridLats := make([]float64, nPoints)
	gridLons := make([]float64, nPoints)
	for i, p := range points {
		gridLats[i] = p.Lat
		gridLons[i] = p.Lon
	}
	gridXs, gridYs := geo.ProjectSliceToXY(gridLats, gridLons, centerLatRad)

	// Build stop→route headways
	// trip → route short name
	tripRoute := make(map[string]string)
	for _, t := range feed.Trips {
		for _, r := range feed.Routes {
			if t.RouteID == r.RouteID {
				tripRoute[t.TripID] = r.RouteShortName
				break
			}
		}
	}

	// (stopID, routeName) → departure times
	type stopRouteKey struct {
		stopID, routeName string
	}
	stopRouteDeps := make(map[stopRouteKey][]float64)
	for _, st := range feed.StopTimes {
		rName := tripRoute[st.TripID]
		if rName == "" {
			continue
		}
		key := stopRouteKey{st.StopID, rName}
		stopRouteDeps[key] = append(stopRouteDeps[key], float64(st.DepartureMin))
	}

	// Compute headway per (stop, route)
	stopRouteHW := make(map[stopRouteKey]float64)
	for key, deps := range stopRouteDeps {
		sort.Float64s(deps)
		unique := uniqueFloat64s(deps)
		if len(unique) < 2 {
			stopRouteHW[key] = 120.0
			continue
		}
		var headways []float64
		for i := 1; i < len(unique); i++ {
			hw := unique[i] - unique[i-1]
			if hw > 0 {
				headways = append(headways, hw)
			}
		}
		if len(headways) == 0 {
			stopRouteHW[key] = 120.0
			continue
		}
		sort.Float64s(headways)
		stopRouteHW[key] = headways[len(headways)/2]
	}

	// Build stop → routes lookup
	stopRoutes := make(map[string][]struct{ name string; hw float64 })
	for key, hw := range stopRouteHW {
		stopRoutes[key.stopID] = append(stopRoutes[key.stopID], struct{ name string; hw float64 }{key.routeName, hw})
	}

	// Compute PTAL for each grid point
	catchment := float64(config.PTALBusCatchmentM)
	for i := 0; i < nPoints; i++ {
		gx, gy := gridXs[i], gridYs[i]

		routeBestEDF := make(map[string]float64)

		for si := 0; si < len(feed.Stops); si++ {
			d := geo.Distance2D(gx, gy, stopXs[si], stopYs[si])
			if d > catchment {
				continue
			}
			walkMin := d / config.PTALWalkSpeedMPerMin
			sid := stopIDs[si]
			routes := stopRoutes[sid]
			for _, rt := range routes {
				totalAccess := walkMin + rt.hw/2.0
				if totalAccess <= 0 {
					continue
				}
				edf := 30.0 / totalAccess
				if cur, ok := routeBestEDF[rt.name]; !ok || edf > cur {
					routeBestEDF[rt.name] = edf
				}
			}
		}

		if len(routeBestEDF) == 0 {
			grades[i] = PTALGradeFromAI(0)
			continue
		}

		edfs := make([]float64, 0, len(routeBestEDF))
		for _, v := range routeBestEDF {
			edfs = append(edfs, v)
		}
		sort.Sort(sort.Reverse(sort.Float64Slice(edfs)))

		ai := edfs[0]
		for _, edf := range edfs[1:] {
			ai += 0.5 * edf
		}
		aiValues[i] = ai
		grades[i] = PTALGradeFromAI(ai)
	}

	return &PTALResult{Values: aiValues, Grades: grades}
}

func uniqueFloat64s(s []float64) []float64 {
	if len(s) == 0 {
		return s
	}
	result := []float64{s[0]}
	for i := 1; i < len(s); i++ {
		if s[i] != s[i-1] {
			result = append(result, s[i])
		}
	}
	return result
}
```

- [ ] **Step 5: Write amenity.go**

Create `go/internal/scoring/amenity.go`:

```go
package scoring

import (
	"encoding/json"
	"math"
	"os"
	"sort"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/grid"
)

// Amenity represents a point of interest from amenities.json.
type Amenity struct {
	Name     string  `json:"name"`
	Lat      float64 `json:"lat"`
	Lon      float64 `json:"lon"`
	Category string  `json:"category"`
}

// AmenityResult holds accessibility stats for one amenity.
type AmenityResult struct {
	Name            string  `json:"name"`
	Category        string  `json:"category"`
	Lat             float64 `json:"lat"`
	Lon             float64 `json:"lon"`
	PctWithin30Min  float64 `json:"pct_within_30min"`
	PctWithin60Min  float64 `json:"pct_within_60min"`
	MeanTravelTime  float64 `json:"mean_travel_time_min"`
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

// ComputeAmenityAccessibility measures how reachable each amenity is from the grid.
func ComputeAmenityAccessibility(
	points []grid.Point,
	meanTravelTime [][]float64,
	distancesKM [][]float64,
	amenities []Amenity,
) []AmenityResult {
	nGrid := len(points)
	var results []AmenityResult

	for _, am := range amenities {
		// Find closest grid point to amenity
		minDist := math.MaxFloat64
		amenityIdx := 0
		for i, p := range points {
			d := geo.Haversine(am.Lat, am.Lon, p.Lat, p.Lon)
			if d < minDist {
				minDist = d
				amenityIdx = i
			}
		}

		// Travel times from all grid points to this amenity's grid point
		within30 := 0
		within60 := 0
		var reachableTimes []float64

		for i := 0; i < nGrid; i++ {
			tt := meanTravelTime[i][amenityIdx]
			walkTime := distancesKM[i][amenityIdx] / (config.WalkSpeedKMH / 60.0)

			// Only count if transit beats walking
			if tt >= InfFloat || tt >= walkTime {
				continue
			}
			reachableTimes = append(reachableTimes, tt)
			if tt <= 30 {
				within30++
			}
			if tt <= 60 {
				within60++
			}
		}

		meanTT := 0.0
		if len(reachableTimes) > 0 {
			sort.Float64s(reachableTimes)
			sum := 0.0
			for _, t := range reachableTimes {
				sum += t
			}
			meanTT = sum / float64(len(reachableTimes))
		}

		results = append(results, AmenityResult{
			Name:           am.Name,
			Category:       am.Category,
			Lat:            am.Lat,
			Lon:            am.Lon,
			PctWithin30Min: float64(within30) / float64(nGrid) * 100,
			PctWithin60Min: float64(within60) / float64(nGrid) * 100,
			MeanTravelTime: math.Round(meanTT*10) / 10,
		})
	}

	return results
}
```

- [ ] **Step 6: Run tests**

```bash
cd go && go test ./internal/scoring/ -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add go/internal/scoring/tcqsm.go go/internal/scoring/ptal.go go/internal/scoring/amenity.go go/internal/scoring/tcqsm_test.go
git commit -m "feat: TCQSM route grading, PTAL accessibility, amenity scoring"
```

---

## Task 11: Travel Time Matrix (Goroutine Pool)

**Files:**
- Create: `go/internal/raptor/matrix.go`
- Create: `go/internal/raptor/cache.go`
- Create: `go/internal/raptor/matrix_test.go`

- [ ] **Step 1: Write failing test**

Create `go/internal/raptor/matrix_test.go`:

```go
package raptor

import (
	"math"
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/scoring"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestComputeMatrix(t *testing.T) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)

	points := []grid.Point{
		{Lat: 49.168, Lon: -121.951},
		{Lat: 49.175, Lon: -121.960},
	}

	stopLats := []float64{49.168, 49.170, 49.175}
	stopLons := []float64{-121.951, -121.955, -121.960}

	metrics := ComputeMatrix(tt, points, stopLats, stopLons, []int{480}, 1, nil)
	require.NotNil(t, metrics)
	assert.Equal(t, 2, len(metrics.MeanTravelTime))
	assert.Equal(t, 2, len(metrics.MeanTravelTime[0]))
}

func TestComputeMatrixSelfDistance(t *testing.T) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)

	points := []grid.Point{
		{Lat: 49.168, Lon: -121.951},
	}
	stopLats := []float64{49.168, 49.170, 49.175}
	stopLons := []float64{-121.951, -121.955, -121.960}

	metrics := ComputeMatrix(tt, points, stopLats, stopLons, []int{480}, 1, nil)
	assert.Equal(t, 0.0, metrics.DistancesKM[0][0])
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd go && go test ./internal/raptor/ -run TestComputeMatrix -v
```

Expected: FAIL.

- [ ] **Step 3: Write matrix.go**

Create `go/internal/raptor/matrix.go`:

```go
package raptor

import (
	"fmt"
	"math"
	"runtime"
	"sync"
	"sync/atomic"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/scoring"
)

// ProgressFunc is called with (completed, total) origin counts.
type ProgressFunc func(completed, total int)

// ComputeMatrix runs RAPTOR for all origins × departure times.
func ComputeMatrix(
	tt *Timetable,
	points []grid.Point,
	stopLats, stopLons []float64,
	departureTimes []int,
	workers int,
	progressFn ProgressFunc,
) *scoring.ODMetrics {
	nOrigins := len(points)
	nDests := nOrigins
	nTimes := len(departureTimes)

	if workers <= 0 {
		workers = runtime.NumCPU()
	}

	// Project coordinates
	centerLat := 0.0
	for _, p := range points {
		centerLat += p.Lat
	}
	centerLat /= float64(nOrigins)
	centerLatRad := centerLat * math.Pi / 180.0

	stopXs, stopYs := geo.ProjectSliceToXY(stopLats, stopLons, centerLatRad)
	gridLats := make([]float64, nOrigins)
	gridLons := make([]float64, nOrigins)
	for i, p := range points {
		gridLats[i] = p.Lat
		gridLons[i] = p.Lon
	}
	gridXs, gridYs := geo.ProjectSliceToXY(gridLats, gridLons, centerLatRad)

	// Precompute nearby stops for each grid point
	type nearbyStop struct {
		stopIdx int
		walkMin float64
	}
	nearbyStops := make([][]nearbyStop, nOrigins)
	for i := 0; i < nOrigins; i++ {
		for si := 0; si < len(stopLats); si++ {
			d := geo.Distance2D(gridXs[i], gridYs[i], stopXs[si], stopYs[si])
			if d <= config.MaxWalkToStopM {
				nearbyStops[i] = append(nearbyStops[i], nearbyStop{si, d / config.WalkSpeedMPerMin})
			}
		}
	}

	// Pairwise distance matrix
	distKM := geo.HaversineMatrix(gridLats, gridLons)

	// Flatten timetable
	ft := Flatten(tt)

	// Allocate results
	meanTT := make([][]float64, nOrigins)
	reach := make([][]float64, nOrigins)
	ttStd := make([][]float64, nOrigins)
	for i := 0; i < nOrigins; i++ {
		meanTT[i] = make([]float64, nDests)
		reach[i] = make([]float64, nDests)
		ttStd[i] = make([]float64, nDests)
		for j := range meanTT[i] {
			meanTT[i][j] = math.MaxFloat64
		}
	}
	slotTSRSum := make([]float64, nTimes)
	slotReachCount := make([]float64, nTimes)
	var slotMu sync.Mutex

	fmt.Printf("Computing travel times: %d origins × %d slots = %d RAPTOR runs\n",
		nOrigins, nTimes, nOrigins*nTimes)
	fmt.Printf("Using %d workers\n", workers)

	var completed int64
	origins := make(chan int, nOrigins)
	var wg sync.WaitGroup

	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			ws := NewWorkspace(ft.NStops)
			travelTimes := make([][]float64, nTimes) // [time][dest]
			for ti := range travelTimes {
				travelTimes[ti] = make([]float64, nDests)
			}

			for oi := range origins {
				nearby := nearbyStops[oi]
				if len(nearby) == 0 {
					atomic.AddInt64(&completed, 1)
					continue
				}

				// Run RAPTOR for each departure time
				for ti := 0; ti < nTimes; ti++ {
					depTime := float64(departureTimes[ti])
					maxTime := depTime + config.MaxTripMin

					sources := make([]SourceStop, len(nearby))
					for j, ns := range nearby {
						sources[j] = SourceStop{StopIdx: ns.stopIdx, ArrivalTime: depTime + ns.walkMin}
					}

					RunRAPTORWithWorkspace(ft, sources, config.MaxTransfers, maxTime, ws)

					// Compute travel time to each destination
					for di := 0; di < nDests; di++ {
						bestArr := math.MaxFloat64
						destNearby := nearbyStops[di]
						for _, dns := range destNearby {
							total := ws.Best[dns.stopIdx] + dns.walkMin
							if total < bestArr {
								bestArr = total
							}
						}
						if bestArr < 1e17 {
							travelTimes[ti][di] = bestArr - depTime
						} else {
							travelTimes[ti][di] = math.MaxFloat64
						}
					}
				}

				// Walking competitor check
				for ti := 0; ti < nTimes; ti++ {
					for di := 0; di < nDests; di++ {
						if travelTimes[ti][di] < math.MaxFloat64 {
							walkDistKM := math.Sqrt(
								math.Pow(gridXs[di]-gridXs[oi], 2)+
									math.Pow(gridYs[di]-gridYs[oi], 2)) / 1000.0
							walkTimeMin := walkDistKM / (config.WalkSpeedKMH / 60.0)
							if travelTimes[ti][di] >= walkTimeMin {
								travelTimes[ti][di] = math.MaxFloat64
							}
						}
					}
				}

				// Aggregate across time slots
				localSlotTSR := make([]float64, nTimes)
				localSlotReach := make([]float64, nTimes)

				for di := 0; di < nDests; di++ {
					reachCount := 0
					sum := 0.0
					sumSq := 0.0
					for ti := 0; ti < nTimes; ti++ {
						tt := travelTimes[ti][di]
						if tt < math.MaxFloat64 {
							reachCount++
							sum += tt
							sumSq += tt * tt
						}
					}
					if reachCount > 0 {
						mean := sum / float64(reachCount)
						meanTT[oi][di] = mean
						reach[oi][di] = float64(reachCount) / float64(nTimes)
						variance := sumSq/float64(reachCount) - mean*mean
						if variance > 0 {
							ttStd[oi][di] = math.Sqrt(variance)
						}
					}

					// Per-slot TSR
					for ti := 0; ti < nTimes; ti++ {
						if travelTimes[ti][di] < math.MaxFloat64 && distKM[oi][di] >= config.MinODDistKM {
							tsr := distKM[oi][di] / (travelTimes[ti][di] / 60.0)
							localSlotTSR[ti] += tsr
							localSlotReach[ti]++
						}
					}
				}

				slotMu.Lock()
				for ti := 0; ti < nTimes; ti++ {
					slotTSRSum[ti] += localSlotTSR[ti]
					slotReachCount[ti] += localSlotReach[ti]
				}
				slotMu.Unlock()

				c := atomic.AddInt64(&completed, 1)
				if progressFn != nil && (int(c)%100 == 0 || int(c) == nOrigins) {
					progressFn(int(c), nOrigins)
				}
			}
		}()
	}

	for i := 0; i < nOrigins; i++ {
		origins <- i
	}
	close(origins)
	wg.Wait()

	// Per-slot aggregates
	perSlotCov := make([]float64, nTimes)
	perSlotTSR := make([]float64, nTimes)
	maxPairs := float64(nOrigins * nDests)
	for ti := 0; ti < nTimes; ti++ {
		if maxPairs > 0 {
			perSlotCov[ti] = slotReachCount[ti] / maxPairs
		}
		if slotReachCount[ti] > 0 {
			perSlotTSR[ti] = slotTSRSum[ti] / slotReachCount[ti]
		}
	}

	return &scoring.ODMetrics{
		MeanTravelTime:  meanTT,
		Reachability:    reach,
		TravelTimeStd:   ttStd,
		PerSlotCoverage: perSlotCov,
		PerSlotMeanTSR:  perSlotTSR,
		DistancesKM:     distKM,
	}
}
```

- [ ] **Step 4: Write cache.go**

Create `go/internal/raptor/cache.go`:

```go
package raptor

import (
	"encoding/gob"
	"fmt"
	"os"
	"path/filepath"

	"github.com/jasondyck/chwk-tqi/internal/scoring"
)

// SaveCache writes ODMetrics to a gob file.
func SaveCache(dir, feedHash string, nOrigins int, m *scoring.ODMetrics) error {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	path := filepath.Join(dir, fmt.Sprintf("od_metrics_%s_%d.gob", feedHash[:12], nOrigins))
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return gob.NewEncoder(f).Encode(m)
}

// LoadCache reads ODMetrics from a gob file.
func LoadCache(dir, feedHash string, nOrigins int) (*scoring.ODMetrics, error) {
	path := filepath.Join(dir, fmt.Sprintf("od_metrics_%s_%d.gob", feedHash[:12], nOrigins))
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var m scoring.ODMetrics
	if err := gob.NewDecoder(f).Decode(&m); err != nil {
		return nil, err
	}
	return &m, nil
}
```

- [ ] **Step 5: Run tests**

```bash
cd go && go test ./internal/raptor/ -v -timeout 60s
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add go/internal/raptor/matrix.go go/internal/raptor/cache.go go/internal/raptor/matrix_test.go
git commit -m "feat: travel time matrix with goroutine pool and gob cache"
```

---

## Task 12: API Server + SSE

**Files:**
- Create: `go/internal/api/server.go`
- Create: `go/internal/api/handlers.go`
- Create: `go/internal/api/sse.go`
- Create: `go/internal/api/server_test.go`

- [ ] **Step 1: Write failing test**

Create `go/internal/api/server_test.go`:

```go
package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestHealthEndpoint(t *testing.T) {
	srv := NewServer(8080)
	req := httptest.NewRequest("GET", "/api/health", nil)
	w := httptest.NewRecorder()
	srv.Mux.ServeHTTP(w, req)

	assert.Equal(t, 200, w.Code)
	var body map[string]string
	json.Unmarshal(w.Body.Bytes(), &body)
	assert.Equal(t, "ok", body["status"])
}

func TestResultsNotReady(t *testing.T) {
	srv := NewServer(8080)
	req := httptest.NewRequest("GET", "/api/results", nil)
	w := httptest.NewRecorder()
	srv.Mux.ServeHTTP(w, req)

	assert.Equal(t, 404, w.Code)
}

func TestConfigEndpoint(t *testing.T) {
	srv := NewServer(8080)
	req := httptest.NewRequest("GET", "/api/config", nil)
	w := httptest.NewRecorder()
	srv.Mux.ServeHTTP(w, req)

	assert.Equal(t, 200, w.Code)
}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd go && go test ./internal/api/ -v
```

Expected: FAIL.

- [ ] **Step 3: Write sse.go**

Create `go/internal/api/sse.go`:

```go
package api

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// SSEWriter wraps an http.ResponseWriter for Server-Sent Events.
type SSEWriter struct {
	w       http.ResponseWriter
	flusher http.Flusher
}

// NewSSEWriter sets headers and returns an SSEWriter.
func NewSSEWriter(w http.ResponseWriter) *SSEWriter {
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	flusher, _ := w.(http.Flusher)
	return &SSEWriter{w: w, flusher: flusher}
}

type ProgressEvent struct {
	Step    string `json:"step"`
	Pct     int    `json:"pct"`
	Message string `json:"message"`
}

type CompleteEvent struct {
	TQI         float64 `json:"tqi"`
	DurationSec float64 `json:"duration_sec"`
}

type ErrorEvent struct {
	Message string `json:"message"`
}

func (s *SSEWriter) SendProgress(step string, pct int, msg string) {
	data, _ := json.Marshal(ProgressEvent{Step: step, Pct: pct, Message: msg})
	fmt.Fprintf(s.w, "event: progress\ndata: %s\n\n", data)
	if s.flusher != nil {
		s.flusher.Flush()
	}
}

func (s *SSEWriter) SendComplete(tqi, durationSec float64) {
	data, _ := json.Marshal(CompleteEvent{TQI: tqi, DurationSec: durationSec})
	fmt.Fprintf(s.w, "event: complete\ndata: %s\n\n", data)
	if s.flusher != nil {
		s.flusher.Flush()
	}
}

func (s *SSEWriter) SendError(msg string) {
	data, _ := json.Marshal(ErrorEvent{Message: msg})
	fmt.Fprintf(s.w, "event: error\ndata: %s\n\n", data)
	if s.flusher != nil {
		s.flusher.Flush()
	}
}
```

- [ ] **Step 4: Write server.go**

Create `go/internal/api/server.go`:

```go
package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"sync"

	"github.com/jasondyck/chwk-tqi/internal/scoring"
)

// Server holds the HTTP server state and results.
type Server struct {
	Port    int
	Mux     *http.ServeMux
	mu      sync.RWMutex
	results *PipelineResults
	running bool
}

// PipelineResults holds all computed data from a pipeline run.
type PipelineResults struct {
	TQI         *scoring.TQIResult
	Metrics     *scoring.ODMetrics
	RouteLOS    []scoring.RouteLOS
	SystemLOS   *scoring.SystemLOSSummary
	PTAL        *scoring.PTALResult
	Amenities   []scoring.AmenityResult
	GridPoints  int
	NStops      int
}

// NewServer creates a configured HTTP server.
func NewServer(port int) *Server {
	s := &Server{Port: port, Mux: http.NewServeMux()}
	s.registerRoutes()
	return s
}

func (s *Server) registerRoutes() {
	s.Mux.HandleFunc("GET /api/health", s.handleHealth)
	s.Mux.HandleFunc("GET /api/config", s.handleConfig)
	s.Mux.HandleFunc("GET /api/results", s.handleResults)
	s.Mux.HandleFunc("GET /api/results/routes", s.handleRoutes)
	s.Mux.HandleFunc("GET /api/results/time-profile", s.handleTimeProfile)
	s.Mux.HandleFunc("GET /api/results/amenities", s.handleAmenities)
	s.Mux.HandleFunc("POST /api/run", s.handleRun)
}

// Start begins listening.
func (s *Server) Start() error {
	addr := fmt.Sprintf(":%d", s.Port)
	fmt.Printf("TQI server listening on http://localhost%s\n", addr)
	return http.ListenAndServe(addr, s.Mux)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, 200, map[string]string{"status": "ok"})
}

func (s *Server) handleConfig(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, 200, map[string]string{
		"mapbox_token": os.Getenv("MAPBOX_TOKEN"),
	})
}

func (s *Server) handleResults(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.results == nil {
		writeJSON(w, 404, map[string]string{"error": "no results available, run the pipeline first"})
		return
	}
	writeJSON(w, 200, s.results.TQI)
}

func (s *Server) handleRoutes(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.results == nil {
		writeJSON(w, 404, map[string]string{"error": "no results"})
		return
	}
	writeJSON(w, 200, s.results.RouteLOS)
}

func (s *Server) handleTimeProfile(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.results == nil {
		writeJSON(w, 404, map[string]string{"error": "no results"})
		return
	}
	writeJSON(w, 200, s.results.TQI.TimeProfile)
}

func (s *Server) handleAmenities(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.results == nil {
		writeJSON(w, 404, map[string]string{"error": "no results"})
		return
	}
	writeJSON(w, 200, s.results.Amenities)
}

func (s *Server) handleRun(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		writeJSON(w, 409, map[string]string{"error": "pipeline already running"})
		return
	}
	s.running = true
	s.mu.Unlock()

	sse := NewSSEWriter(w)
	sse.SendProgress("starting", 0, "Pipeline not yet implemented in serve mode")
	sse.SendError("Pipeline execution via API not yet wired up")

	s.mu.Lock()
	s.running = false
	s.mu.Unlock()
}

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
```

- [ ] **Step 5: Run tests**

```bash
cd go && go test ./internal/api/ -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add go/internal/api/
git commit -m "feat: API server with health, config, results, SSE endpoints"
```

---

## Task 13: Wire CLI Commands

**Files:**
- Modify: `go/cmd/tqi/main.go`

- [ ] **Step 1: Update main.go with real pipeline wiring**

Replace the placeholder commands in `go/cmd/tqi/main.go` with actual calls to the internal packages. This wires the `download`, `run`, `serve`, and `compare` commands to real implementations.

Update `go/cmd/tqi/main.go` — replace `newRunCmd` body:

```go
func newRunCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "run",
		Short: "Run the full TQI analysis pipeline",
		RunE: func(cmd *cobra.Command, args []string) error {
			noDownload, _ := cmd.Flags().GetBool("no-download")
			noCache, _ := cmd.Flags().GetBool("no-cache")
			workers, _ := cmd.Flags().GetInt("workers")
			outputDir, _ := cmd.Flags().GetString("output-dir")

			return runPipeline(!noDownload, !noCache, workers, outputDir)
		},
	}
	cmd.Flags().Bool("no-download", false, "Skip GTFS download")
	cmd.Flags().Bool("no-cache", false, "Ignore cached matrix")
	cmd.Flags().IntP("workers", "w", 0, "Number of parallel workers (0 = NumCPU)")
	cmd.Flags().Bool("equity", false, "Include census equity overlay")
	cmd.Flags().StringP("output-dir", "o", "output", "Output directory")
	return cmd
}
```

Add `runPipeline` function and imports. Full file replacement is needed — the task executor should write the complete updated `main.go` that imports all internal packages and calls them in sequence matching the Python CLI pipeline.

- [ ] **Step 2: Update download command**

Wire `newDownloadCmd` to call `gtfs.DownloadGTFS`.

- [ ] **Step 3: Update serve command**

Wire `newServeCmd` to call `api.NewServer(port).Start()`.

- [ ] **Step 4: Verify build**

```bash
cd go && go build ./cmd/tqi/
```

Expected: compiles with no errors.

- [ ] **Step 5: Commit**

```bash
git add go/cmd/tqi/main.go
git commit -m "feat: wire CLI commands to pipeline, download, and serve"
```

---

## Task 14: React Frontend Scaffold

**Files:**
- Create: `go/web/package.json`
- Create: `go/web/vite.config.ts`
- Create: `go/web/tsconfig.json`
- Create: `go/web/tailwind.config.ts`
- Create: `go/web/index.html`
- Create: `go/web/src/main.tsx`
- Create: `go/web/src/App.tsx`
- Create: `go/web/src/styles/globals.css`
- Create: `go/web/src/lib/types.ts`
- Create: `go/web/src/lib/api.ts`

- [ ] **Step 1: Initialize Vite React project**

```bash
cd go && npm create vite@latest web -- --template react-ts
cd go/web && npm install
```

- [ ] **Step 2: Install dependencies**

```bash
cd go/web && npm install react-router-dom @tanstack/react-query recharts react-map-gl mapbox-gl tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Vite with API proxy**

Write `go/web/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
})
```

- [ ] **Step 4: Write TypeScript types**

Write `go/web/src/lib/types.ts`:

```typescript
export interface TQIResponse {
  TQI: number
  CoverageScore: number
  SpeedScore: number
  TimeProfile: TimeSlotScore[]
  ReliabilityCV: number
}

export interface TimeSlotScore {
  Label: string
  Score: number
}

export interface RouteLOS {
  route_name: string
  route_long_name: string
  median_headway_min: number
  los_grade: string
  los_description: string
  trip_count: number
}

export interface AmenityResult {
  name: string
  category: string
  lat: number
  lon: number
  pct_within_30min: number
  pct_within_60min: number
  mean_travel_time_min: number
}

export interface CityComparison {
  city: string
  tqi: number
  coverage: number
  speed: number
  grid_points: number
  stops: number
  routes: number
}

export interface ProgressEvent {
  step: string
  pct: number
  message: string
}
```

- [ ] **Step 5: Write API client**

Write `go/web/src/lib/api.ts`:

```typescript
const BASE = ''

export async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function subscribeSSE(
  path: string,
  onProgress: (evt: { step: string; pct: number; message: string }) => void,
  onComplete: (evt: { tqi: number; duration_sec: number }) => void,
  onError: (evt: { message: string }) => void,
): () => void {
  const ctrl = new AbortController()

  fetch(`${BASE}${path}`, { method: 'POST', signal: ctrl.signal })
    .then(async (res) => {
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) return

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) eventType = line.slice(7)
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            if (eventType === 'progress') onProgress(data)
            if (eventType === 'complete') onComplete(data)
            if (eventType === 'error') onError(data)
          }
        }
      }
    })
    .catch(() => {})

  return () => ctrl.abort()
}
```

- [ ] **Step 6: Write globals.css**

Write `go/web/src/styles/globals.css`:

```css
@import "tailwindcss";
```

- [ ] **Step 7: Write App.tsx shell**

Write `go/web/src/App.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">
            Chilliwack Transit Quality Index
          </h1>
        </header>
        <main className="p-6">
          <p className="text-gray-600">Dashboard coming soon. Run the pipeline via the API to see results.</p>
        </main>
      </div>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 8: Update main.tsx**

Write `go/web/src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles/globals.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

- [ ] **Step 9: Verify build**

```bash
cd go/web && npm run build
```

Expected: builds to `go/web/dist/` with no errors.

- [ ] **Step 10: Commit**

```bash
git add go/web/
git commit -m "feat: React + TypeScript + Vite frontend scaffold with TanStack Query"
```

---

## Task 15: Frontend Dashboard Components

**Files:**
- Create: `go/web/src/hooks/useResults.ts`
- Create: `go/web/src/hooks/usePipeline.ts`
- Create: `go/web/src/components/dashboard/Dashboard.tsx`
- Create: `go/web/src/components/dashboard/ScoreCard.tsx`
- Create: `go/web/src/components/dashboard/ScoreBreakdown.tsx`
- Create: `go/web/src/components/dashboard/TimeProfile.tsx`
- Create: `go/web/src/components/routes/RouteTable.tsx`
- Modify: `go/web/src/App.tsx`

- [ ] **Step 1: Write query hooks**

Write `go/web/src/hooks/useResults.ts`:

```typescript
import { useQuery } from '@tanstack/react-query'
import { fetchJSON } from '../lib/api'
import type { TQIResponse, RouteLOS, AmenityResult } from '../lib/types'

export function useResults() {
  return useQuery({
    queryKey: ['results'],
    queryFn: () => fetchJSON<TQIResponse>('/api/results'),
    retry: false,
  })
}

export function useRoutes() {
  return useQuery({
    queryKey: ['routes'],
    queryFn: () => fetchJSON<RouteLOS[]>('/api/results/routes'),
    retry: false,
  })
}

export function useAmenities() {
  return useQuery({
    queryKey: ['amenities'],
    queryFn: () => fetchJSON<AmenityResult[]>('/api/results/amenities'),
    retry: false,
  })
}
```

Write `go/web/src/hooks/usePipeline.ts`:

```typescript
import { useState, useCallback } from 'react'
import { subscribeSSE } from '../lib/api'

interface PipelineState {
  running: boolean
  step: string
  pct: number
  message: string
  error: string | null
  tqi: number | null
}

export function usePipeline() {
  const [state, setState] = useState<PipelineState>({
    running: false, step: '', pct: 0, message: '', error: null, tqi: null,
  })

  const run = useCallback(() => {
    setState(s => ({ ...s, running: true, error: null, tqi: null }))
    subscribeSSE(
      '/api/run',
      (evt) => setState(s => ({ ...s, step: evt.step, pct: evt.pct, message: evt.message })),
      (evt) => setState({ running: false, step: 'complete', pct: 100, message: 'Done', error: null, tqi: evt.tqi }),
      (evt) => setState(s => ({ ...s, running: false, error: evt.message })),
    )
  }, [])

  return { ...state, run }
}
```

- [ ] **Step 2: Write ScoreCard**

Write `go/web/src/components/dashboard/ScoreCard.tsx`:

```tsx
interface Props {
  score: number
  label: string
}

export default function ScoreCard({ score, label }: Props) {
  const color = score >= 70 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : score >= 25 ? 'text-orange-500' : 'text-red-600'

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 text-center">
      <div className={`text-5xl font-bold ${color}`}>{score.toFixed(1)}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}
```

- [ ] **Step 3: Write ScoreBreakdown**

Write `go/web/src/components/dashboard/ScoreBreakdown.tsx`:

```tsx
interface Props {
  coverage: number
  speed: number
}

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{value.toFixed(1)}</span>
      </div>
      <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  )
}

export default function ScoreBreakdown({ coverage, speed }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
      <h3 className="font-semibold text-gray-900">Score Breakdown</h3>
      <Bar label="Coverage (50%)" value={coverage} color="bg-blue-500" />
      <Bar label="Speed (50%)" value={speed} color="bg-emerald-500" />
    </div>
  )
}
```

- [ ] **Step 4: Write TimeProfile chart**

Write `go/web/src/components/dashboard/TimeProfile.tsx`:

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { TimeSlotScore } from '../../lib/types'

interface Props {
  data: TimeSlotScore[]
}

export default function TimeProfile({ data }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h3 className="font-semibold text-gray-900 mb-4">Score by Time of Day</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="Label" tick={{ fontSize: 11 }} interval={3} />
          <YAxis domain={[0, 'auto']} />
          <Tooltip />
          <Line type="monotone" dataKey="Score" stroke="#3b82f6" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 5: Write RouteTable**

Write `go/web/src/components/routes/RouteTable.tsx`:

```tsx
import type { RouteLOS } from '../../lib/types'

const gradeColors: Record<string, string> = {
  A: 'bg-green-100 text-green-800',
  B: 'bg-green-50 text-green-700',
  C: 'bg-yellow-100 text-yellow-800',
  D: 'bg-orange-100 text-orange-800',
  E: 'bg-red-100 text-red-800',
  F: 'bg-red-200 text-red-900',
}

interface Props {
  routes: RouteLOS[]
}

export default function RouteTable({ routes }: Props) {
  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Route</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Name</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600">Headway</th>
            <th className="px-4 py-3 text-center font-medium text-gray-600">LOS</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600">Trips</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {routes.map((r) => (
            <tr key={r.route_name} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium">{r.route_name}</td>
              <td className="px-4 py-3 text-gray-600">{r.route_long_name}</td>
              <td className="px-4 py-3 text-right">{r.median_headway_min} min</td>
              <td className="px-4 py-3 text-center">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${gradeColors[r.los_grade] || ''}`}>
                  {r.los_grade}
                </span>
              </td>
              <td className="px-4 py-3 text-right">{r.trip_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 6: Write Dashboard (assembles panels)**

Write `go/web/src/components/dashboard/Dashboard.tsx`:

```tsx
import { useResults, useRoutes } from '../../hooks/useResults'
import { usePipeline } from '../../hooks/usePipeline'
import ScoreCard from './ScoreCard'
import ScoreBreakdown from './ScoreBreakdown'
import TimeProfile from './TimeProfile'
import RouteTable from '../routes/RouteTable'

export default function Dashboard() {
  const results = useResults()
  const routes = useRoutes()
  const pipeline = usePipeline()

  if (results.isLoading) return <p className="text-gray-500">Loading...</p>

  if (results.isError) {
    return (
      <div className="space-y-4">
        <p className="text-gray-600">No results yet. Run the analysis pipeline to get started.</p>
        <button
          onClick={pipeline.run}
          disabled={pipeline.running}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {pipeline.running ? `${pipeline.message} (${pipeline.pct}%)` : 'Run Analysis'}
        </button>
        {pipeline.error && <p className="text-red-600">{pipeline.error}</p>}
      </div>
    )
  }

  const data = results.data!

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ScoreCard score={data.TQI} label="Transit Quality Index" />
        <ScoreCard score={data.CoverageScore} label="Coverage Score" />
        <ScoreCard score={data.SpeedScore} label="Speed Score" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ScoreBreakdown coverage={data.CoverageScore} speed={data.SpeedScore} />
        <TimeProfile data={data.TimeProfile} />
      </div>

      {routes.data && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Route Level of Service (TCQSM)</h2>
          <RouteTable routes={routes.data} />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 7: Update App.tsx**

Replace `go/web/src/App.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './components/dashboard/Dashboard'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">
            Chilliwack Transit Quality Index
          </h1>
        </header>
        <main className="max-w-7xl mx-auto p-6">
          <Dashboard />
        </main>
      </div>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 8: Verify frontend builds**

```bash
cd go/web && npm run build
```

Expected: builds to `dist/` with no errors.

- [ ] **Step 9: Commit**

```bash
git add go/web/src/
git commit -m "feat: dashboard with score cards, time profile chart, route table"
```

---

## Task 16: Embed Frontend + Production Build

**Files:**
- Create: `go/internal/api/embed.go`
- Modify: `go/internal/api/server.go`

- [ ] **Step 1: Write embed.go**

Create `go/internal/api/embed.go`:

```go
package api

import (
	"embed"
	"io/fs"
	"net/http"
)

//go:embed all:../../web/dist
var webDist embed.FS

// WebFS returns the embedded frontend filesystem.
func WebFS() http.FileSystem {
	sub, _ := fs.Sub(webDist, "web/dist")
	return http.FS(sub)
}
```

- [ ] **Step 2: Add SPA catch-all route to server.go**

Add to `registerRoutes()` in `server.go`:

```go
// Serve embedded SPA — catch-all for non-API routes
webFS := WebFS()
s.Mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
    // Try to serve the file directly
    f, err := webFS.Open(r.URL.Path[1:]) // strip leading /
    if err != nil {
        // Fall back to index.html for SPA routing
        r.URL.Path = "/"
    } else {
        f.Close()
    }
    http.FileServer(webFS).ServeHTTP(w, r)
})
```

- [ ] **Step 3: Build production binary**

```bash
cd go/web && npm run build
cd go && go build -o bin/tqi ./cmd/tqi/
```

Expected: single `bin/tqi` binary. Running `./bin/tqi serve` and visiting localhost:8080 shows the React app.

- [ ] **Step 4: Commit**

```bash
git add go/internal/api/embed.go go/internal/api/server.go
git commit -m "feat: embed React frontend in Go binary"
```

---

## Task 17: Integration Test — Full Pipeline

**Files:**
- Create: `go/internal/integration_test.go`

- [ ] **Step 1: Write integration test**

Create `go/internal/integration_test.go`:

```go
package internal_test

import (
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/gtfs"
	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/raptor"
	"github.com/jasondyck/chwk-tqi/internal/scoring"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestFullPipelineSmall(t *testing.T) {
	// Small synthetic feed
	feed := &gtfs.Feed{
		Stops: []gtfs.Stop{
			{StopID: "S1", StopLat: 49.168, StopLon: -121.951},
			{StopID: "S2", StopLat: 49.170, StopLon: -121.955},
			{StopID: "S3", StopLat: 49.175, StopLon: -121.960},
		},
		Routes: []gtfs.Route{
			{RouteID: "R1", RouteShortName: "51", RouteLongName: "Downtown"},
		},
		Trips: []gtfs.Trip{
			{TripID: "T1", RouteID: "R1", ServiceID: "SVC1", DirectionID: "0"},
			{TripID: "T2", RouteID: "R1", ServiceID: "SVC1", DirectionID: "0"},
			{TripID: "T3", RouteID: "R1", ServiceID: "SVC1", DirectionID: "0"},
		},
		StopTimes: []gtfs.StopTime{
			{TripID: "T1", StopID: "S1", ArrivalMin: 480, DepartureMin: 481, StopSequence: 1},
			{TripID: "T1", StopID: "S2", ArrivalMin: 490, DepartureMin: 491, StopSequence: 2},
			{TripID: "T1", StopID: "S3", ArrivalMin: 500, DepartureMin: 501, StopSequence: 3},
			{TripID: "T2", StopID: "S1", ArrivalMin: 510, DepartureMin: 511, StopSequence: 1},
			{TripID: "T2", StopID: "S2", ArrivalMin: 520, DepartureMin: 521, StopSequence: 2},
			{TripID: "T2", StopID: "S3", ArrivalMin: 530, DepartureMin: 531, StopSequence: 3},
			{TripID: "T3", StopID: "S1", ArrivalMin: 540, DepartureMin: 541, StopSequence: 1},
			{TripID: "T3", StopID: "S2", ArrivalMin: 550, DepartureMin: 551, StopSequence: 2},
			{TripID: "T3", StopID: "S3", ArrivalMin: 560, DepartureMin: 561, StopSequence: 3},
		},
	}

	// Build timetable
	tt := raptor.BuildTimetable(feed)
	require.Equal(t, 3, tt.NStops)

	// Generate small grid
	points := []grid.Point{
		{Lat: 49.168, Lon: -121.951},
		{Lat: 49.175, Lon: -121.960},
	}

	stopLats := []float64{49.168, 49.170, 49.175}
	stopLons := []float64{-121.951, -121.955, -121.960}

	// Compute matrix
	metrics := raptor.ComputeMatrix(tt, points, stopLats, stopLons, []int{480, 510}, 1, nil)
	require.NotNil(t, metrics)

	// Compute TQI
	result := scoring.ComputeTQI(metrics)
	assert.True(t, result.TQI >= 0)
	assert.True(t, result.CoverageScore >= 0)
	t.Logf("TQI: %.1f, Coverage: %.1f, Speed: %.1f", result.TQI, result.CoverageScore, result.SpeedScore)
}
```

- [ ] **Step 2: Run integration test**

```bash
cd go && go test ./internal/ -v -run TestFullPipeline -timeout 30s
```

Expected: PASS with logged TQI scores.

- [ ] **Step 3: Commit**

```bash
git add go/internal/integration_test.go
git commit -m "test: integration test — synthetic GTFS through full pipeline"
```

---

## Task 18: RAPTOR Engine Benchmark

**Files:**
- Create: `go/internal/raptor/engine_bench_test.go`

- [ ] **Step 1: Write benchmark**

Create `go/internal/raptor/engine_bench_test.go`:

```go
package raptor

import "testing"

func BenchmarkRAPTOR(b *testing.B) {
	feed := makeTestFeed()
	tt := BuildTimetable(feed)
	ft := Flatten(tt)

	s1Idx := tt.StopIDToIdx["S1"]
	sources := []SourceStop{{StopIdx: s1Idx, ArrivalTime: 480}}
	ws := NewWorkspace(ft.NStops)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		RunRAPTORWithWorkspace(ft, sources, 2, 570, ws)
	}
}
```

- [ ] **Step 2: Run benchmark**

```bash
cd go && go test ./internal/raptor/ -bench=BenchmarkRAPTOR -benchmem
```

Expected: outputs ns/op and allocs/op. This baseline tracks performance.

- [ ] **Step 3: Commit**

```bash
git add go/internal/raptor/engine_bench_test.go
git commit -m "bench: RAPTOR engine benchmark"
```
