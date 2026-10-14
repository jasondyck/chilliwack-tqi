package raptor

import (
	"math"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func testFlatTimetable() *FlatTimetable {
	feed := testFeed()
	tt := BuildTimetable(feed)
	return Flatten(tt)
}

func TestRaptorSimple(t *testing.T) {
	ft := testFlatTimetable()

	// Depart S1 at 480 -> catch T1 -> S2@490, S3@500
	sources := []SourceStop{{StopIdx: 0, ArrivalTime: 480}}
	best := RunRAPTOR(ft, sources, 2, 1440)

	assert.Equal(t, 480.0, best[0], "S1 should be 480")
	assert.Equal(t, 490.0, best[1], "S2 should be 490")
	assert.Equal(t, 500.0, best[2], "S3 should be 500")
}

func TestRaptorMissedTrip(t *testing.T) {
	ft := testFlatTimetable()

	// Depart S1 at 540 -> both trips already departed -> unreachable
	sources := []SourceStop{{StopIdx: 0, ArrivalTime: 540}}
	best := RunRAPTOR(ft, sources, 2, 1440)

	assert.Equal(t, 540.0, best[0], "S1 should be 540")
	assert.Equal(t, math.MaxFloat64, best[1], "S2 should be Inf (missed)")
	assert.Equal(t, math.MaxFloat64, best[2], "S3 should be Inf (missed)")
}

func TestRaptorNoSource(t *testing.T) {
	ft := testFlatTimetable()

	best := RunRAPTOR(ft, nil, 2, 1440)

	for i := range best {
		assert.Equal(t, math.MaxFloat64, best[i], "all stops should be Inf with no source")
	}
}

func TestRaptorWorkspace(t *testing.T) {
	ws := NewWorkspace(5)
	require.Len(t, ws.Best, 5)
	require.Len(t, ws.Marked, 5)
	require.Len(t, ws.Tau, 4) // MaxTransfers(2)+1+1 = default 4

	// Verify initial state
	for i := 0; i < 5; i++ {
		assert.Equal(t, math.MaxFloat64, ws.Best[i])
		assert.False(t, ws.Marked[i])
	}

	// Mutate and reset
	ws.Best[0] = 100
	ws.Marked[0] = true
	ws.Reset(5)
	assert.Equal(t, math.MaxFloat64, ws.Best[0])
	assert.False(t, ws.Marked[0])
}
