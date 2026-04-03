// Package config provides central configuration for the TQI analysis.
package config

import "math"

// ── GTFS source ──

const GTFSURL = "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=13"

// ── Chilliwack municipal boundary ──
// Bounding box derived from official municipal boundary polygon.

var (
	BBoxSW = [2]float64{49.045918, -122.124370}
	BBoxNE = [2]float64{49.225607, -121.777247}
)

// BoundaryGeoJSON is the relative path to the boundary file.
const BoundaryGeoJSON = "data/chilliwack_boundary.geojson"

// ── Chilliwack route short names (strings, as in GTFS) ──

var ChilliwackRoutes = []string{
	"51", "52", "53", "54", "55", "57", "58", "59", // Chilliwack local
	"66", // Fraser Valley Express
}

// ── Grid parameters ──

const GridSpacingM = 250

// ── Walking / routing parameters ──

const (
	WalkSpeedKMH      = 5.0
	WalkSpeedMPerMin  = WalkSpeedKMH * 1000.0 / 60.0 // 83.33 m/min
	MaxWalkToStopM    = 800
	MaxTransferWalkM  = 400
	MaxTripMin        = 90
	MaxTransfers      = 2
)

// ── Time window (minutes since midnight) ──

const (
	TimeStart = 6 * 60  // 06:00
	TimeEnd   = 22 * 60 // 22:00
	TimeStep  = 15      // 15-minute resolution
)

// DepartureTimes returns all departure times (minutes since midnight) in the analysis window.
func DepartureTimes() []int {
	times := make([]int, 0, (TimeEnd-TimeStart)/TimeStep)
	for t := TimeStart; t < TimeEnd; t += TimeStep {
		times = append(times, t)
	}
	return times
}

// ── Scoring normalisation ──

const (
	TSRWalk      = 5.0  // km/h — walking baseline (score = 0)
	TSRCar       = 40.0 // km/h — car baseline (score = 100)
	MinODDistKM  = 0.5  // exclude trivially walkable pairs
)

// ── Walk Score Transit Score ranges ──

// WalkScoreRange describes a Walk Score transit score band.
type WalkScoreRange struct {
	Min         int
	Max         int
	Label       string
	Description string
}

var WalkScoreRanges = []WalkScoreRange{
	{90, 100, "Rider's Paradise", "World-class public transportation"},
	{70, 89, "Excellent Transit", "Transit convenient for most trips"},
	{50, 69, "Good Transit", "Many nearby public transportation options"},
	{25, 49, "Some Transit", "A few nearby public transportation options"},
	{0, 24, "Minimal Transit", "It is possible to get on a bus"},
}

// WalkScoreCategory returns the label for a given score (0-100).
func WalkScoreCategory(score float64) string {
	for _, r := range WalkScoreRanges {
		if score >= float64(r.Min) && score <= float64(r.Max) {
			return r.Label
		}
	}
	return "Minimal Transit"
}

// WalkScoreDescription returns the description for a given score (0-100).
func WalkScoreDescription(score float64) string {
	for _, r := range WalkScoreRanges {
		if score >= float64(r.Min) && score <= float64(r.Max) {
			return r.Description
		}
	}
	return "It is possible to get on a bus"
}

// ── TCQSM LOS grades (TCRP Report 165, 3rd Edition) ──

// TCQSMLOSGrade describes a TCQSM level-of-service grade.
type TCQSMLOSGrade struct {
	MaxHeadwayMin int
	Grade         string
	Description   string
}

var TCQSMLOS = []TCQSMLOSGrade{
	{10, "A", "Passengers don't need schedules"},
	{14, "B", "Frequent service, passengers consult schedules"},
	{20, "C", "Maximum desirable wait if bus is missed"},
	{30, "D", "Service unattractive to choice riders"},
	{60, "E", "Service available during the hour"},
	{999, "F", "Service unattractive to all riders"},
}

// ── PTAL grade boundaries (TfL methodology) ──

// PTALGrade describes a PTAL accessibility index grade.
type PTALGrade struct {
	MaxAI float64
	Grade string
}

var PTALGrades = []PTALGrade{
	{2.5, "1a"},
	{5.0, "1b"},
	{10.0, "2"},
	{15.0, "3"},
	{20.0, "4"},
	{25.0, "5"},
	{40.0, "6a"},
	{math.Inf(1), "6b"},
}

const (
	PTALWalkSpeedMPerMin = 80.0 // PTAL standard: 80m/min (4.8 km/h)
	PTALBusCatchmentM    = 640  // 8 min walk at 80m/min
)

// ── Earth radius (metres) for spatial projections ──

const EarthRadiusM = 6_371_000

// ── Multi-city comparison configs (BC Transit operators) ──

// CityConfig holds per-city GTFS and spatial parameters.
type CityConfig struct {
	OperatorID int
	URL        string
	BBoxSW     [2]float64
	BBoxNE     [2]float64
	Routes     []string // nil means use all routes
}

var CityConfigs = map[string]CityConfig{
	"chilliwack": {
		OperatorID: 13,
		URL:        "https://bct.tmix.se/Tmix.Cap.TdExport.WebApi/gtfs/?operatorIds=13",
		BBoxSW:     [2]float64{49.045918, -122.124370},
		BBoxNE:     [2]float64{49.225607, -121.777247},
		Routes:     []string{"51", "52", "53", "54", "55", "57", "58", "59", "66"},
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
