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
	// Create synthetic feed: 3 stops, 1 route, 3 trips
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

	// 2 grid points
	points := []grid.Point{
		{Lat: 49.168, Lon: -121.951},
		{Lat: 49.175, Lon: -121.960},
	}

	stopLats := []float64{49.168, 49.170, 49.175}
	stopLons := []float64{-121.951, -121.955, -121.960}

	// Compute matrix with 2 departure times
	metrics := raptor.ComputeMatrix(tt, points, stopLats, stopLons, []int{480, 510}, 1, nil)
	require.NotNil(t, metrics)

	// Compute TQI
	result := scoring.ComputeTQI(metrics)
	assert.True(t, result.TQI >= 0)
	assert.True(t, result.CoverageScore >= 0)
	t.Logf("TQI: %.1f, Coverage: %.1f, Speed: %.1f", result.TQI, result.CoverageScore, result.SpeedScore)
}
