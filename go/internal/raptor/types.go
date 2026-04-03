package raptor

import "math"

const Inf = math.MaxFloat64

// Timetable holds the structured RAPTOR timetable.
type Timetable struct {
	NStops         int
	StopIDs        []string
	StopIDToIdx    map[string]int
	NPatterns      int
	PatternStops   [][]int
	PatternTrips   []PatternTripData
	StopToPatterns [][]StopPatternEntry
	Transfers      [][]Transfer
}

// PatternTripData holds trip times for a single route pattern as a flat array.
// Layout: [trip0_stop0_arr, trip0_stop0_dep, trip0_stop1_arr, trip0_stop1_dep, ...]
type PatternTripData struct {
	NTrips int
	NStops int
	Data   []int // flat: (trip*NStops+stopPos)*2 + 0=arr, +1=dep
}

// ArrivalAt returns the arrival time for a given trip and stop position.
func (p *PatternTripData) ArrivalAt(trip, stopPos int) int {
	return p.Data[(trip*p.NStops+stopPos)*2]
}

// DepartureAt returns the departure time for a given trip and stop position.
func (p *PatternTripData) DepartureAt(trip, stopPos int) int {
	return p.Data[(trip*p.NStops+stopPos)*2+1]
}

// StopPatternEntry records that a stop appears at a given position in a pattern.
type StopPatternEntry struct {
	PatternIdx int
	Position   int
}

// Transfer represents a walking transfer to another stop.
type Transfer struct {
	TargetIdx int
	WalkMin   float64
}

// FlatTimetable holds the RAPTOR timetable as contiguous flat arrays
// suitable for high-performance scanning.
type FlatTimetable struct {
	NStops    int
	NPatterns int
	StopIDs   []string
	PSData    []int32   // pattern stop indices, concatenated
	PSOffsets []int32   // PSData[PSOffsets[p]..PSOffsets[p+1]] = stops of pattern p
	TTData    []int32   // trip times, concatenated: arr/dep pairs
	TTOffsets []int32   // TTData offset per pattern
	TTNTrips  []int32   // number of trips per pattern
	TTNStops  []int32   // number of stops per pattern
	SPData    [][2]int32 // (patternIdx, position) per stop, concatenated
	SPOffsets []int32    // SPData offset per stop
	TRData    [][2]int32 // (targetStopIdx, walkMin*100) per stop, concatenated
	TROffsets []int32    // TRData offset per stop
}
