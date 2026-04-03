package scoring

import (
	"math"
	"sort"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/gtfs"
)

// PTALResult holds PTAL accessibility indices and grades for a set of points.
type PTALResult struct {
	Values []float64
	Grades []string
}

// PTALGradeFromAI maps an accessibility index to a PTAL grade string.
func PTALGradeFromAI(ai float64) string {
	for _, g := range config.PTALGrades {
		if ai <= g.MaxAI {
			return g.Grade
		}
	}
	return "6b"
}

// ComputePTAL calculates PTAL using the TfL methodology.
// For each grid point, find stops within 640 m, compute EDF per (stop, route),
// then AI = bestEDF + 0.5 * sum(otherEDFs).
func ComputePTAL(points []grid.Point, feed *gtfs.Feed) *PTALResult {
	// Build trip -> route mapping.
	tripRoute := make(map[string]string, len(feed.Trips))
	for _, tr := range feed.Trips {
		tripRoute[tr.TripID] = tr.RouteID
	}

	// Collect first departure per trip.
	tripFirstDep := make(map[string]int)
	for _, st := range feed.StopTimes {
		if cur, ok := tripFirstDep[st.TripID]; !ok || st.DepartureMin < cur {
			tripFirstDep[st.TripID] = st.DepartureMin
		}
	}

	// Build stop -> set of routes and per-(stop, route) headways.
	type stopRouteKey struct{ stopID, routeID string }
	srTrips := make(map[stopRouteKey][]int) // departure minutes

	// Collect stop-level trips: for each stop_time, note which route serves that stop.
	stopTrips := make(map[string]map[string]bool) // stopID -> set of tripIDs
	for _, st := range feed.StopTimes {
		if stopTrips[st.StopID] == nil {
			stopTrips[st.StopID] = make(map[string]bool)
		}
		stopTrips[st.StopID][st.TripID] = true
	}

	for stopID, trips := range stopTrips {
		for tripID := range trips {
			routeID, ok := tripRoute[tripID]
			if !ok {
				continue
			}
			dep, ok := tripFirstDep[tripID]
			if !ok {
				continue
			}
			k := stopRouteKey{stopID, routeID}
			srTrips[k] = append(srTrips[k], dep)
		}
	}

	// Compute median headway per (stop, route).
	srHeadway := make(map[stopRouteKey]float64)
	for k, deps := range srTrips {
		if len(deps) < 2 {
			srHeadway[k] = 60.0 // default if only one trip
			continue
		}
		sort.Ints(deps)
		var headways []float64
		for i := 1; i < len(deps); i++ {
			hw := float64(deps[i] - deps[i-1])
			if hw > 0 {
				headways = append(headways, hw)
			}
		}
		if len(headways) == 0 {
			srHeadway[k] = 60.0
		} else {
			sort.Float64s(headways)
			srHeadway[k] = medianFloat(headways)
		}
	}

	// Build stop index.
	stopByID := make(map[string]*gtfs.Stop, len(feed.Stops))
	for i := range feed.Stops {
		stopByID[feed.Stops[i].StopID] = &feed.Stops[i]
	}

	// Collect unique routes per stop.
	stopRoutes := make(map[string]map[string]bool)
	for k := range srHeadway {
		if stopRoutes[k.stopID] == nil {
			stopRoutes[k.stopID] = make(map[string]bool)
		}
		stopRoutes[k.stopID][k.routeID] = true
	}

	result := &PTALResult{
		Values: make([]float64, len(points)),
		Grades: make([]string, len(points)),
	}

	for i, pt := range points {
		var edfs []float64

		for _, stop := range feed.Stops {
			distM := geo.Haversine(pt.Lat, pt.Lon, stop.StopLat, stop.StopLon) * 1000.0
			if distM > float64(config.PTALBusCatchmentM) {
				continue
			}

			walkTimeMin := distM / config.PTALWalkSpeedMPerMin

			routes, ok := stopRoutes[stop.StopID]
			if !ok {
				continue
			}

			for routeID := range routes {
				k := stopRouteKey{stop.StopID, routeID}
				hw, ok := srHeadway[k]
				if !ok {
					continue
				}
				edf := 30.0 / (walkTimeMin + hw/2.0)
				edfs = append(edfs, edf)
			}
		}

		if len(edfs) == 0 {
			result.Values[i] = 0
			result.Grades[i] = PTALGradeFromAI(0)
			continue
		}

		// Sort descending to get best EDF first.
		sort.Sort(sort.Reverse(sort.Float64Slice(edfs)))

		ai := edfs[0]
		for j := 1; j < len(edfs); j++ {
			ai += 0.5 * edfs[j]
		}

		if math.IsNaN(ai) || math.IsInf(ai, 0) {
			ai = 0
		}

		result.Values[i] = ai
		result.Grades[i] = PTALGradeFromAI(ai)
	}

	return result
}

func medianFloat(sorted []float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	if n%2 == 0 {
		return (sorted[n/2-1] + sorted[n/2]) / 2.0
	}
	return sorted[n/2]
}
