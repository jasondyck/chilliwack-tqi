package scoring

import (
	"math"
	"sort"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/gtfs"
)

// RouteLOS holds the level-of-service grading for a single route.
type RouteLOS struct {
	RouteName     string   `json:"route_name"`
	RouteLongName string   `json:"route_long_name"`
	RouteID       string   `json:"route_id"`
	NTrips        int      `json:"n_trips"`
	MedianHeadway float64  `json:"median_headway"`
	PeakHeadway   *float64 `json:"peak_headway"`
	LOSGrade      string   `json:"los_grade"`
	LOSDescription string  `json:"los_description"`
}

// SystemLOSSummary summarises the LOS across all routes.
type SystemLOSSummary struct {
	NRoutes             int                `json:"n_routes"`
	GradeCounts         map[string]int     `json:"grade_counts"`
	MedianSystemHeadway float64            `json:"median_system_headway"`
	BestGrade           string             `json:"best_grade"`
	WorstGrade          string             `json:"worst_grade"`
	PctLOSDOrWorse      float64            `json:"pct_los_d_or_worse"`
}

// HeadwayToLOS maps a headway (minutes) to a TCQSM grade and description.
func HeadwayToLOS(headwayMin float64) (string, string) {
	for _, g := range config.TCQSMLOS {
		if headwayMin <= float64(g.MaxHeadwayMin) {
			return g.Grade, g.Description
		}
	}
	return "F", "Service unattractive to all riders"
}

// ComputeRouteLOS grades each route in the feed by its median headway
// per direction.
func ComputeRouteLOS(feed *gtfs.Feed) []RouteLOS {
	// Build lookup maps.
	tripByID := make(map[string]*gtfs.Trip, len(feed.Trips))
	for i := range feed.Trips {
		tripByID[feed.Trips[i].TripID] = &feed.Trips[i]
	}
	routeByID := make(map[string]*gtfs.Route, len(feed.Routes))
	for i := range feed.Routes {
		routeByID[feed.Routes[i].RouteID] = &feed.Routes[i]
	}

	// Collect first departure per trip.
	tripFirstDep := make(map[string]int)
	for _, st := range feed.StopTimes {
		if st.StopSequence == 1 {
			tripFirstDep[st.TripID] = st.DepartureMin
		} else if cur, ok := tripFirstDep[st.TripID]; !ok || st.DepartureMin < cur {
			tripFirstDep[st.TripID] = st.DepartureMin
		}
	}

	// Group trips by (routeID, directionID).
	type dirKey struct{ routeID, dir string }
	dirTrips := make(map[dirKey][]int) // departure minutes
	for tripID, dep := range tripFirstDep {
		tr, ok := tripByID[tripID]
		if !ok {
			continue
		}
		k := dirKey{tr.RouteID, tr.DirectionID}
		dirTrips[k] = append(dirTrips[k], dep)
	}

	// Compute headways per direction, take median.
	type routeResult struct {
		routeID   string
		nTrips    int
		headways  []float64
	}
	routeResults := make(map[string]*routeResult)

	for k, deps := range dirTrips {
		sort.Ints(deps)
		for i := 1; i < len(deps); i++ {
			hw := float64(deps[i] - deps[i-1])
			if hw <= 0 {
				continue
			}
			rr, ok := routeResults[k.routeID]
			if !ok {
				rr = &routeResult{routeID: k.routeID}
				routeResults[k.routeID] = rr
			}
			rr.headways = append(rr.headways, hw)
		}
		if rr, ok := routeResults[k.routeID]; ok {
			rr.nTrips += len(deps)
		} else {
			routeResults[k.routeID] = &routeResult{routeID: k.routeID, nTrips: len(deps)}
		}
	}

	var results []RouteLOS
	for routeID, rr := range routeResults {
		rt := routeByID[routeID]
		if rt == nil {
			continue
		}

		var medHW float64
		if len(rr.headways) > 0 {
			sort.Float64s(rr.headways)
			medHW = median(rr.headways)
		} else {
			medHW = math.Inf(1)
		}

		grade, desc := HeadwayToLOS(medHW)
		results = append(results, RouteLOS{
			RouteName:      rt.RouteShortName,
			RouteLongName:  rt.RouteLongName,
			RouteID:        routeID,
			NTrips:         rr.nTrips,
			MedianHeadway:  medHW,
			LOSGrade:       grade,
			LOSDescription: desc,
		})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].RouteName < results[j].RouteName
	})
	return results
}

// ComputeSystemLOSSummary aggregates route-level LOS into a system summary.
func ComputeSystemLOSSummary(routeLOS []RouteLOS) *SystemLOSSummary {
	summary := &SystemLOSSummary{
		NRoutes:     len(routeLOS),
		GradeCounts: make(map[string]int),
	}
	if len(routeLOS) == 0 {
		return summary
	}

	gradeOrder := map[string]int{"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}
	bestIdx := 5
	worstIdx := 0

	var headways []float64
	var dOrWorse int

	for _, r := range routeLOS {
		summary.GradeCounts[r.LOSGrade]++
		if !math.IsInf(r.MedianHeadway, 1) {
			headways = append(headways, r.MedianHeadway)
		}
		if idx, ok := gradeOrder[r.LOSGrade]; ok {
			if idx < bestIdx {
				bestIdx = idx
			}
			if idx > worstIdx {
				worstIdx = idx
			}
			if idx >= 3 { // D=3, E=4, F=5
				dOrWorse++
			}
		}
	}

	gradeNames := []string{"A", "B", "C", "D", "E", "F"}
	summary.BestGrade = gradeNames[bestIdx]
	summary.WorstGrade = gradeNames[worstIdx]

	if len(headways) > 0 {
		sort.Float64s(headways)
		summary.MedianSystemHeadway = median(headways)
	}

	summary.PctLOSDOrWorse = float64(dOrWorse) / float64(len(routeLOS)) * 100.0

	return summary
}

func median(sorted []float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	if n%2 == 0 {
		return (sorted[n/2-1] + sorted[n/2]) / 2.0
	}
	return sorted[n/2]
}
