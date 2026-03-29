package raptor

import (
	"math"
	"sort"
	"strings"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/gtfs"
)

type stopEntry struct {
	stopIdx int
	arrMin  int
	depMin  int
}

// BuildTimetable converts a GTFS feed into a RAPTOR timetable.
func BuildTimetable(feed *gtfs.Feed) *Timetable {
	// 1. Index stops: collect unique stop IDs from stop_times, sort, create map.
	stopSet := make(map[string]struct{})
	for i := range feed.StopTimes {
		stopSet[feed.StopTimes[i].StopID] = struct{}{}
	}
	stopIDs := make([]string, 0, len(stopSet))
	for id := range stopSet {
		stopIDs = append(stopIDs, id)
	}
	sort.Strings(stopIDs)

	stopIDToIdx := make(map[string]int, len(stopIDs))
	for i, id := range stopIDs {
		stopIDToIdx[id] = i
	}
	nStops := len(stopIDs)

	// 2. Sort stop_times by trip_id then stop_sequence.
	stCopy := make([]gtfs.StopTime, len(feed.StopTimes))
	copy(stCopy, feed.StopTimes)
	sort.Slice(stCopy, func(i, j int) bool {
		if stCopy[i].TripID != stCopy[j].TripID {
			return stCopy[i].TripID < stCopy[j].TripID
		}
		return stCopy[i].StopSequence < stCopy[j].StopSequence
	})

	// 3. Group by trip: trip -> [(stopIdx, arrMin, depMin)]
	tripStops := make(map[string][]stopEntry)
	for _, st := range stCopy {
		idx, ok := stopIDToIdx[st.StopID]
		if !ok {
			continue
		}
		tripStops[st.TripID] = append(tripStops[st.TripID], stopEntry{
			stopIdx: idx,
			arrMin:  st.ArrivalMin,
			depMin:  st.DepartureMin,
		})
	}

	// 4. Group trips into patterns (same sequence of stop indices).
	//    Pattern key = comma-separated stop indices.
	type tripData struct {
		tripID string
		stops  []stopEntry
	}

	patternMap := make(map[string][]tripData)
	for tripID, stops := range tripStops {
		key := patternKey(stops)
		patternMap[key] = append(patternMap[key], tripData{tripID: tripID, stops: stops})
	}

	// Sort pattern keys for deterministic output.
	patternKeys := make([]string, 0, len(patternMap))
	for k := range patternMap {
		patternKeys = append(patternKeys, k)
	}
	sort.Strings(patternKeys)

	nPatterns := len(patternKeys)
	patternStops := make([][]int, nPatterns)
	patternTrips := make([]PatternTripData, nPatterns)

	for pi, key := range patternKeys {
		trips := patternMap[key]
		nStopsInPattern := len(trips[0].stops)

		// Build stop index list for this pattern.
		ps := make([]int, nStopsInPattern)
		for j, se := range trips[0].stops {
			ps[j] = se.stopIdx
		}
		patternStops[pi] = ps

		// 5. Sort trips within each pattern by departure at first stop.
		sort.Slice(trips, func(a, b int) bool {
			return trips[a].stops[0].depMin < trips[b].stops[0].depMin
		})

		// Build flat trip data.
		ptd := PatternTripData{
			NTrips: len(trips),
			NStops: nStopsInPattern,
			Data:   make([]int, len(trips)*nStopsInPattern*2),
		}
		for ti, td := range trips {
			for si, se := range td.stops {
				ptd.Data[(ti*nStopsInPattern+si)*2] = se.arrMin
				ptd.Data[(ti*nStopsInPattern+si)*2+1] = se.depMin
			}
		}
		patternTrips[pi] = ptd
	}

	// 6. Build stopToPatterns.
	stopToPatterns := make([][]StopPatternEntry, nStops)
	for pi, ps := range patternStops {
		for pos, stopIdx := range ps {
			stopToPatterns[stopIdx] = append(stopToPatterns[stopIdx], StopPatternEntry{
				PatternIdx: pi,
				Position:   pos,
			})
		}
	}

	// 7. Build transfers.
	transfers := buildTransfers(feed, stopIDs, stopIDToIdx, nStops)

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

// patternKey creates a string key from a sequence of stop entries.
func patternKey(stops []stopEntry) string {
	parts := make([]string, len(stops))
	for i, s := range stops {
		parts[i] = strings.Repeat("0", 6) // placeholder
		// Use a simple int-to-string for the key.
		parts[i] = intToStr(s.stopIdx)
	}
	return strings.Join(parts, ",")
}

func intToStr(n int) string {
	if n == 0 {
		return "0"
	}
	s := ""
	neg := n < 0
	if neg {
		n = -n
	}
	for n > 0 {
		s = string(rune('0'+n%10)) + s
		n /= 10
	}
	if neg {
		s = "-" + s
	}
	return s
}

// buildTransfers creates walking transfers between nearby stops.
func buildTransfers(feed *gtfs.Feed, stopIDs []string, stopIDToIdx map[string]int, nStops int) [][]Transfer {
	transfers := make([][]Transfer, nStops)

	if nStops == 0 {
		return transfers
	}

	// Build lat/lon arrays indexed by our stop index.
	stopByID := make(map[string]*gtfs.Stop, len(feed.Stops))
	for i := range feed.Stops {
		stopByID[feed.Stops[i].StopID] = &feed.Stops[i]
	}

	lats := make([]float64, nStops)
	lons := make([]float64, nStops)
	for i, id := range stopIDs {
		s, ok := stopByID[id]
		if ok {
			lats[i] = s.StopLat
			lons[i] = s.StopLon
		}
	}

	// Project to XY.
	meanLat := 0.0
	for _, lat := range lats {
		meanLat += lat
	}
	meanLat /= float64(nStops)
	centerLatRad := meanLat * math.Pi / 180.0

	xs, ys := geo.ProjectSliceToXY(lats, lons, centerLatRad)

	// Build set of patterns each stop belongs to (for same-pattern-set filtering).
	// We skip transfers between stops that share exactly the same set of patterns,
	// as they're already connected by routes.

	maxDist := float64(config.MaxTransferWalkM)
	walkSpeed := config.WalkSpeedMPerMin

	for i := 0; i < nStops; i++ {
		for j := 0; j < nStops; j++ {
			if i == j {
				continue
			}
			dist := geo.Distance2D(xs[i], ys[i], xs[j], ys[j])
			if dist <= maxDist {
				walkMin := dist / walkSpeed
				transfers[i] = append(transfers[i], Transfer{
					TargetIdx: j,
					WalkMin:   walkMin,
				})
			}
		}
	}

	return transfers
}

// Flatten converts a Timetable into a FlatTimetable with contiguous arrays.
func Flatten(tt *Timetable) *FlatTimetable {
	ft := &FlatTimetable{
		NStops:    tt.NStops,
		NPatterns: tt.NPatterns,
		StopIDs:   tt.StopIDs,
	}

	// Flatten PatternStops -> PSData + PSOffsets
	ft.PSOffsets = make([]int32, tt.NPatterns+1)
	for pi, ps := range tt.PatternStops {
		ft.PSOffsets[pi+1] = ft.PSOffsets[pi] + int32(len(ps))
	}
	ft.PSData = make([]int32, ft.PSOffsets[tt.NPatterns])
	for pi, ps := range tt.PatternStops {
		off := ft.PSOffsets[pi]
		for j, idx := range ps {
			ft.PSData[off+int32(j)] = int32(idx)
		}
	}

	// Flatten PatternTrips -> TTData + TTOffsets + TTNTrips + TTNStops
	ft.TTOffsets = make([]int32, tt.NPatterns+1)
	ft.TTNTrips = make([]int32, tt.NPatterns)
	ft.TTNStops = make([]int32, tt.NPatterns)
	for pi, ptd := range tt.PatternTrips {
		ft.TTNTrips[pi] = int32(ptd.NTrips)
		ft.TTNStops[pi] = int32(ptd.NStops)
		ft.TTOffsets[pi+1] = ft.TTOffsets[pi] + int32(len(ptd.Data))
	}
	ft.TTData = make([]int32, ft.TTOffsets[tt.NPatterns])
	for pi, ptd := range tt.PatternTrips {
		off := ft.TTOffsets[pi]
		for j, v := range ptd.Data {
			ft.TTData[off+int32(j)] = int32(v)
		}
	}

	// Flatten StopToPatterns -> SPData + SPOffsets
	ft.SPOffsets = make([]int32, tt.NStops+1)
	for si, entries := range tt.StopToPatterns {
		ft.SPOffsets[si+1] = ft.SPOffsets[si] + int32(len(entries))
	}
	ft.SPData = make([][2]int32, ft.SPOffsets[tt.NStops])
	for si, entries := range tt.StopToPatterns {
		off := ft.SPOffsets[si]
		for j, e := range entries {
			ft.SPData[off+int32(j)] = [2]int32{int32(e.PatternIdx), int32(e.Position)}
		}
	}

	// Flatten Transfers -> TRData + TROffsets
	ft.TROffsets = make([]int32, tt.NStops+1)
	for si, trs := range tt.Transfers {
		ft.TROffsets[si+1] = ft.TROffsets[si] + int32(len(trs))
	}
	ft.TRData = make([][2]int32, ft.TROffsets[tt.NStops])
	for si, trs := range tt.Transfers {
		off := ft.TROffsets[si]
		for j, tr := range trs {
			ft.TRData[off+int32(j)] = [2]int32{int32(tr.TargetIdx), int32(tr.WalkMin * 100)}
		}
	}

	return ft
}
