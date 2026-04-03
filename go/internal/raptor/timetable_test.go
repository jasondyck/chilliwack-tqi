package raptor

import (
	"testing"

	"github.com/jasondyck/chwk-tqi/internal/gtfs"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// testFeed creates a minimal GTFS feed with 3 stops, 1 route, 2 trips
// sharing the same stop pattern (S1 -> S2 -> S3).
// Trip T1: departs 480,490,500 (08:00, 08:10, 08:20)
// Trip T2: departs 510,520,530 (08:30, 08:40, 08:50)
func testFeed() *gtfs.Feed {
	return &gtfs.Feed{
		Stops: []gtfs.Stop{
			{StopID: "S1", StopLat: 49.15, StopLon: -121.95},
			{StopID: "S2", StopLat: 49.16, StopLon: -121.95},
			{StopID: "S3", StopLat: 49.17, StopLon: -121.95},
		},
		Routes: []gtfs.Route{
			{RouteID: "R1", RouteShortName: "1"},
		},
		Trips: []gtfs.Trip{
			{TripID: "T1", RouteID: "R1", ServiceID: "WD"},
			{TripID: "T2", RouteID: "R1", ServiceID: "WD"},
		},
		StopTimes: []gtfs.StopTime{
			{TripID: "T1", StopID: "S1", StopSequence: 1, ArrivalMin: 480, DepartureMin: 480},
			{TripID: "T1", StopID: "S2", StopSequence: 2, ArrivalMin: 490, DepartureMin: 490},
			{TripID: "T1", StopID: "S3", StopSequence: 3, ArrivalMin: 500, DepartureMin: 500},
			{TripID: "T2", StopID: "S1", StopSequence: 1, ArrivalMin: 510, DepartureMin: 510},
			{TripID: "T2", StopID: "S2", StopSequence: 2, ArrivalMin: 520, DepartureMin: 520},
			{TripID: "T2", StopID: "S3", StopSequence: 3, ArrivalMin: 530, DepartureMin: 530},
		},
	}
}

func TestBuildTimetable(t *testing.T) {
	feed := testFeed()
	tt := BuildTimetable(feed)

	assert.Equal(t, 3, tt.NStops)
	assert.Equal(t, 1, tt.NPatterns, "two trips with same stop sequence should form one pattern")

	// Verify stops are indexed (sorted)
	require.Len(t, tt.StopIDs, 3)
	assert.Equal(t, "S1", tt.StopIDs[0])
	assert.Equal(t, "S2", tt.StopIDs[1])
	assert.Equal(t, "S3", tt.StopIDs[2])

	// Verify pattern stops
	require.Len(t, tt.PatternStops, 1)
	assert.Equal(t, []int{tt.StopIDToIdx["S1"], tt.StopIDToIdx["S2"], tt.StopIDToIdx["S3"]}, tt.PatternStops[0])

	// Verify trips sorted by departure at first stop
	ptd := tt.PatternTrips[0]
	assert.Equal(t, 2, ptd.NTrips)
	assert.Equal(t, 3, ptd.NStops)
	// Trip 0 should depart first stop at 480 (T1)
	assert.Equal(t, 480, ptd.DepartureAt(0, 0))
	// Trip 1 should depart first stop at 510 (T2)
	assert.Equal(t, 510, ptd.DepartureAt(1, 0))

	// Verify arrival times
	assert.Equal(t, 490, ptd.ArrivalAt(0, 1)) // T1 at S2
	assert.Equal(t, 500, ptd.ArrivalAt(0, 2)) // T1 at S3

	// Verify stopToPatterns
	require.Len(t, tt.StopToPatterns, 3)
	for i := 0; i < 3; i++ {
		require.Len(t, tt.StopToPatterns[i], 1)
		assert.Equal(t, 0, tt.StopToPatterns[i][0].PatternIdx)
		assert.Equal(t, i, tt.StopToPatterns[i][0].Position)
	}
}

func TestFlattenTimetable(t *testing.T) {
	feed := testFeed()
	tt := BuildTimetable(feed)
	ft := Flatten(tt)

	assert.Equal(t, tt.NStops, ft.NStops)
	assert.Equal(t, tt.NPatterns, ft.NPatterns)
	assert.Equal(t, tt.StopIDs, ft.StopIDs)

	// Check PSData
	require.Len(t, ft.PSOffsets, tt.NPatterns+1)
	assert.Equal(t, int32(0), ft.PSOffsets[0])
	assert.Equal(t, int32(3), ft.PSOffsets[1])

	// Check TTData
	require.Len(t, ft.TTOffsets, tt.NPatterns+1)
	require.Len(t, ft.TTNTrips, tt.NPatterns)
	require.Len(t, ft.TTNStops, tt.NPatterns)
	assert.Equal(t, int32(2), ft.TTNTrips[0])
	assert.Equal(t, int32(3), ft.TTNStops[0])

	// Verify trip data matches: trip 0, stop 1 arrival = 490
	off := ft.TTOffsets[0]
	// trip0 stop1 arr = off + 0*3*2 + 1*2 + 0 = off + 2
	assert.Equal(t, int32(490), ft.TTData[off+2])

	// Check SPData
	require.Len(t, ft.SPOffsets, tt.NStops+1)

	// Check TRData
	require.Len(t, ft.TROffsets, tt.NStops+1)
}
