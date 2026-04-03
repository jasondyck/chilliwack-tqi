package gtfs

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func testFeed() *Feed {
	return &Feed{
		Routes: []Route{
			{RouteID: "R1", RouteShortName: "51", RouteLongName: "Vedder"},
			{RouteID: "R2", RouteShortName: "52", RouteLongName: "Yale"},
			{RouteID: "R3", RouteShortName: "99", RouteLongName: "Express"},
		},
		Trips: []Trip{
			{TripID: "T1", RouteID: "R1", ServiceID: "WD", ShapeID: "S1", DirectionID: "0"},
			{TripID: "T2", RouteID: "R2", ServiceID: "WD", ShapeID: "S2", DirectionID: "0"},
			{TripID: "T3", RouteID: "R3", ServiceID: "WD", ShapeID: "S3", DirectionID: "0"},
			{TripID: "T4", RouteID: "R1", ServiceID: "SAT", ShapeID: "S1", DirectionID: "1"},
		},
		StopTimes: []StopTime{
			{TripID: "T1", StopID: "ST1", ArrivalMin: 480, DepartureMin: 481, StopSequence: 1},
			{TripID: "T1", StopID: "ST2", ArrivalMin: 490, DepartureMin: 491, StopSequence: 2},
			{TripID: "T2", StopID: "ST2", ArrivalMin: 500, DepartureMin: 501, StopSequence: 1},
			{TripID: "T2", StopID: "ST3", ArrivalMin: 510, DepartureMin: 511, StopSequence: 2},
			{TripID: "T3", StopID: "ST1", ArrivalMin: 520, DepartureMin: 521, StopSequence: 1},
			{TripID: "T4", StopID: "ST1", ArrivalMin: 600, DepartureMin: 601, StopSequence: 1},
		},
		Stops: []Stop{
			{StopID: "ST1", StopName: "Main St", StopLat: 49.1, StopLon: -121.9},
			{StopID: "ST2", StopName: "Oak Ave", StopLat: 49.2, StopLon: -121.8},
			{StopID: "ST3", StopName: "Elm Rd", StopLat: 49.3, StopLon: -121.7},
			{StopID: "ST4", StopName: "Unused Stop", StopLat: 49.4, StopLon: -121.6},
		},
		Calendar: []Calendar{
			{
				ServiceID: "WD",
				Monday:    true, Tuesday: true, Wednesday: true, Thursday: true, Friday: true,
				Saturday: false, Sunday: false,
				StartDate: "20240101", EndDate: "20241231",
			},
			{
				ServiceID: "SAT",
				Monday:    false, Tuesday: false, Wednesday: false, Thursday: false, Friday: false,
				Saturday: true, Sunday: false,
				StartDate: "20240101", EndDate: "20241231",
			},
		},
		CalendarDates: []CalendarDate{},
	}
}

func TestFilterToRoutes(t *testing.T) {
	feed := testFeed()
	filtered, err := FilterFeed(feed, []string{"51", "52"}, "wednesday")
	require.NoError(t, err)

	// Should have only routes 51 and 52
	assert.Len(t, filtered.Routes, 2)
	shortNames := map[string]bool{}
	for _, r := range filtered.Routes {
		shortNames[r.RouteShortName] = true
	}
	assert.True(t, shortNames["51"])
	assert.True(t, shortNames["52"])
	assert.False(t, shortNames["99"])

	// Trips: T1 (R1/WD), T2 (R2/WD) — T3 is route 99, T4 is SAT service
	assert.Len(t, filtered.Trips, 2)

	// StopTimes: only for T1, T2
	assert.Len(t, filtered.StopTimes, 4)

	// Stops: ST1, ST2, ST3 used; ST4 unused
	assert.Len(t, filtered.Stops, 3)
	stopIDs := map[string]bool{}
	for _, s := range filtered.Stops {
		stopIDs[s.StopID] = true
	}
	assert.False(t, stopIDs["ST4"])
}

func TestFindBestWeekday(t *testing.T) {
	feed := testFeed()
	day, refDate := FindBestWeekday(feed)

	// WD service has 3 trips (T1, T2, T3) on weekdays vs SAT has 1 trip
	assert.Contains(t, []string{"monday", "tuesday", "wednesday", "thursday", "friday"}, day)
	assert.False(t, refDate.IsZero())
}
