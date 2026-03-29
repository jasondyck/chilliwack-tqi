package gtfs

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestParseTime(t *testing.T) {
	tests := []struct {
		input    string
		expected int
	}{
		{"08:00:00", 480},
		{"25:30:00", 1530},
		{"00:00:00", 0},
		{"12:30:00", 750},
		{"23:59:00", 1439},
	}
	for _, tc := range tests {
		t.Run(tc.input, func(t *testing.T) {
			got := ParseTime(tc.input)
			assert.Equal(t, tc.expected, got)
		})
	}
}

func TestLoadGTFS(t *testing.T) {
	dir := t.TempDir()

	// stops.txt
	writeFile(t, dir, "stops.txt", `stop_id,stop_name,stop_lat,stop_lon
S1,Main St,49.1,-121.9
S2,Oak Ave,49.2,-121.8
`)

	// routes.txt
	writeFile(t, dir, "routes.txt", `route_id,route_short_name,route_long_name
R1,51,Vedder
R2,52,Yale
`)

	// trips.txt
	writeFile(t, dir, "trips.txt", `trip_id,route_id,service_id,shape_id,direction_id
T1,R1,WD,SH1,0
T2,R2,WD,SH2,1
`)

	// stop_times.txt
	writeFile(t, dir, "stop_times.txt", `trip_id,stop_id,arrival_time,departure_time,stop_sequence
T1,S1,08:00:00,08:01:00,1
T1,S2,08:10:00,08:11:00,2
T2,S1,09:00:00,09:01:00,1
`)

	// calendar.txt (optional but provided)
	writeFile(t, dir, "calendar.txt", `service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
WD,1,1,1,1,1,0,0,20240101,20241231
`)

	// calendar_dates.txt (optional but provided)
	writeFile(t, dir, "calendar_dates.txt", `service_id,date,exception_type
WD,20240101,2
`)

	feed, err := LoadGTFS(dir)
	require.NoError(t, err)

	assert.Len(t, feed.Stops, 2)
	assert.Equal(t, "S1", feed.Stops[0].StopID)
	assert.Equal(t, "Main St", feed.Stops[0].StopName)
	assert.InDelta(t, 49.1, feed.Stops[0].StopLat, 0.001)

	assert.Len(t, feed.Routes, 2)
	assert.Equal(t, "51", feed.Routes[0].RouteShortName)

	assert.Len(t, feed.Trips, 2)
	assert.Equal(t, "T1", feed.Trips[0].TripID)

	assert.Len(t, feed.StopTimes, 3)
	assert.Equal(t, 480, feed.StopTimes[0].ArrivalMin)
	assert.Equal(t, 481, feed.StopTimes[0].DepartureMin)
	assert.Equal(t, 1, feed.StopTimes[0].StopSequence)

	assert.Len(t, feed.Calendar, 1)
	assert.True(t, feed.Calendar[0].Monday)
	assert.False(t, feed.Calendar[0].Saturday)

	assert.Len(t, feed.CalendarDates, 1)
	assert.Equal(t, 2, feed.CalendarDates[0].ExceptionType)
}

func TestLoadGTFS_OptionalFilesMissing(t *testing.T) {
	dir := t.TempDir()

	writeFile(t, dir, "stops.txt", `stop_id,stop_name,stop_lat,stop_lon
S1,Main St,49.1,-121.9
`)
	writeFile(t, dir, "routes.txt", `route_id,route_short_name,route_long_name
R1,51,Vedder
`)
	writeFile(t, dir, "trips.txt", `trip_id,route_id,service_id,shape_id,direction_id
T1,R1,WD,SH1,0
`)
	writeFile(t, dir, "stop_times.txt", `trip_id,stop_id,arrival_time,departure_time,stop_sequence
T1,S1,08:00:00,08:01:00,1
`)

	feed, err := LoadGTFS(dir)
	require.NoError(t, err)
	assert.Len(t, feed.Stops, 1)
	assert.Empty(t, feed.Calendar)
	assert.Empty(t, feed.CalendarDates)
	assert.Empty(t, feed.Shapes)
}

func writeFile(t *testing.T, dir, name, content string) {
	t.Helper()
	err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0644)
	require.NoError(t, err)
}
