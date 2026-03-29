package raptor

import (
	"math"
	"runtime"
	"sync"

	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/geo"
	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/scoring"
)

// ProgressFunc is called to report progress during matrix computation.
type ProgressFunc func(completed, total int)

// nearbyStop records a transit stop near a grid point with the walk time to reach it.
type nearbyStop struct {
	stopIdx  int
	walkMin  float64
}

// ComputeMatrix computes pairwise travel time metrics between all grid points
// using the RAPTOR algorithm with a goroutine worker pool.
func ComputeMatrix(tt *Timetable, points []grid.Point, stopLats, stopLons []float64, departureTimes []int, workers int, progressFn ProgressFunc) *scoring.ODMetrics {
	if workers <= 0 {
		workers = runtime.NumCPU()
	}

	nPoints := len(points)
	nSlots := len(departureTimes)

	// 1. Project all coordinates to XY.
	allLats := make([]float64, nPoints)
	allLons := make([]float64, nPoints)
	for i, p := range points {
		allLats[i] = p.Lat
		allLons[i] = p.Lon
	}

	meanLat := 0.0
	for _, lat := range allLats {
		meanLat += lat
	}
	if nPoints > 0 {
		meanLat /= float64(nPoints)
	}
	centerLatRad := meanLat * math.Pi / 180.0

	pointXs, pointYs := geo.ProjectSliceToXY(allLats, allLons, centerLatRad)
	stopXs, stopYs := geo.ProjectSliceToXY(stopLats, stopLons, centerLatRad)

	// 2. Precompute nearby stops for each grid point (within MaxWalkToStopM).
	maxWalkM := float64(config.MaxWalkToStopM)
	walkSpeedMPerMin := config.WalkSpeedMPerMin

	nearbyStops := make([][]nearbyStop, nPoints)
	for i := 0; i < nPoints; i++ {
		for j := 0; j < len(stopLats); j++ {
			dist := geo.Distance2D(pointXs[i], pointYs[i], stopXs[j], stopYs[j])
			if dist <= maxWalkM {
				nearbyStops[i] = append(nearbyStops[i], nearbyStop{
					stopIdx: j,
					walkMin: dist / walkSpeedMPerMin,
				})
			}
		}
	}

	// 3. Compute pairwise distance matrix using HaversineMatrix.
	distKM := geo.HaversineMatrix(allLats, allLons)

	// 4. Flatten timetable.
	ft := Flatten(tt)

	// 5. Allocate result matrices.
	meanTravelTime := make([][]float64, nPoints)
	reachability := make([][]float64, nPoints)
	travelTimeStd := make([][]float64, nPoints)
	for i := 0; i < nPoints; i++ {
		meanTravelTime[i] = make([]float64, nPoints)
		reachability[i] = make([]float64, nPoints)
		travelTimeStd[i] = make([]float64, nPoints)
	}

	perSlotTSRSum := make([]float64, nSlots)
	perSlotTSRCount := make([]int, nSlots)
	perSlotReachable := make([]int, nSlots)
	perSlotTotal := make([]int, nSlots)
	var mu sync.Mutex

	// Walking speed in km per minute.
	walkSpeedKMPerMin := config.WalkSpeedKMH / 60.0

	// 6. Launch worker goroutines.
	originCh := make(chan int, nPoints)
	for i := 0; i < nPoints; i++ {
		originCh <- i
	}
	close(originCh)

	var wg sync.WaitGroup
	var completed int64
	var completedMu sync.Mutex

	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			ws := NewWorkspace(ft.NStops)

			// Per-origin temporary storage for per-slot results.
			// slotTimes[slot][dest] = travel time for this origin in this slot
			slotTimes := make([][]float64, nSlots)
			for s := 0; s < nSlots; s++ {
				slotTimes[s] = make([]float64, nPoints)
			}

			// Local accumulators for per-slot TSR (reduce lock contention).
			localTSRSum := make([]float64, nSlots)
			localTSRCount := make([]int, nSlots)
			localReachable := make([]int, nSlots)
			localTotal := make([]int, nSlots)

			for orig := range originCh {
				origNearby := nearbyStops[orig]

				// Reset local accumulators for this origin.
				for s := range localTSRSum {
					localTSRSum[s] = 0
					localTSRCount[s] = 0
					localReachable[s] = 0
					localTotal[s] = 0
				}

				for slotIdx, depTime := range departureTimes {
					// Build sources from nearby stops.
					sources := make([]SourceStop, 0, len(origNearby))
					for _, ns := range origNearby {
						sources = append(sources, SourceStop{
							StopIdx:     ns.stopIdx,
							ArrivalTime: float64(depTime) + ns.walkMin,
						})
					}

					// Run RAPTOR.
					ws.Reset(ft.NStops)
					if len(sources) > 0 {
						RunRAPTORWithWorkspace(ft, sources, config.MaxTransfers, float64(depTime+config.MaxTripMin), ws)
					}

					// Compute travel time to each destination via its nearby stops.
					for dest := 0; dest < nPoints; dest++ {
						bestTime := math.MaxFloat64
						for _, ns := range nearbyStops[dest] {
							arrAtStop := ws.Best[ns.stopIdx]
							if arrAtStop < math.MaxFloat64 {
								totalTime := (arrAtStop + ns.walkMin) - float64(depTime)
								if totalTime < bestTime {
									bestTime = totalTime
								}
							}
						}

						// Walking competitor: if transit time >= walking time, mark as Inf.
						if bestTime < math.MaxFloat64 {
							walkTime := distKM[orig][dest] / walkSpeedKMPerMin
							if bestTime >= walkTime {
								bestTime = math.MaxFloat64
							}
						}

						slotTimes[slotIdx][dest] = bestTime

						// Per-slot TSR accumulation.
						if scoring.IsValidPair(distKM[orig][dest]) {
							localTotal[slotIdx]++
							if bestTime < math.MaxFloat64 {
								localReachable[slotIdx]++
								tsr := scoring.ComputeTSR(distKM[orig][dest], bestTime)
								localTSRSum[slotIdx] += tsr
								localTSRCount[slotIdx]++
							}
						}
					}
				}

				// Aggregate across time slots for this origin.
				for dest := 0; dest < nPoints; dest++ {
					sumTime := 0.0
					reachCount := 0
					for s := 0; s < nSlots; s++ {
						if slotTimes[s][dest] < math.MaxFloat64 {
							sumTime += slotTimes[s][dest]
							reachCount++
						}
					}

					if reachCount > 0 {
						mean := sumTime / float64(reachCount)
						meanTravelTime[orig][dest] = mean
						reachability[orig][dest] = float64(reachCount) / float64(nSlots)

						// Std dev.
						if reachCount > 1 {
							sumSq := 0.0
							for s := 0; s < nSlots; s++ {
								if slotTimes[s][dest] < math.MaxFloat64 {
									diff := slotTimes[s][dest] - mean
									sumSq += diff * diff
								}
							}
							travelTimeStd[orig][dest] = math.Sqrt(sumSq / float64(reachCount))
						}
					} else {
						meanTravelTime[orig][dest] = math.MaxFloat64
						reachability[orig][dest] = 0
						travelTimeStd[orig][dest] = 0
					}
				}

				// Flush local per-slot accumulators under mutex.
				mu.Lock()
				for s := 0; s < nSlots; s++ {
					perSlotTSRSum[s] += localTSRSum[s]
					perSlotTSRCount[s] += localTSRCount[s]
					perSlotReachable[s] += localReachable[s]
					perSlotTotal[s] += localTotal[s]
				}
				mu.Unlock()

				// Progress reporting.
				completedMu.Lock()
				completed++
				c := int(completed)
				completedMu.Unlock()
				if progressFn != nil && (c%100 == 0 || c == nPoints) {
					progressFn(c, nPoints)
				}
			}
		}()
	}

	wg.Wait()

	// 7. Compute perSlotCoverage and perSlotMeanTSR.
	perSlotCoverage := make([]float64, nSlots)
	perSlotMeanTSR := make([]float64, nSlots)
	for s := 0; s < nSlots; s++ {
		if perSlotTotal[s] > 0 {
			perSlotCoverage[s] = float64(perSlotReachable[s]) / float64(perSlotTotal[s])
		}
		if perSlotTSRCount[s] > 0 {
			perSlotMeanTSR[s] = perSlotTSRSum[s] / float64(perSlotTSRCount[s])
		}
	}

	return &scoring.ODMetrics{
		MeanTravelTime:  meanTravelTime,
		Reachability:    reachability,
		TravelTimeStd:   travelTimeStd,
		PerSlotCoverage: perSlotCoverage,
		PerSlotMeanTSR:  perSlotMeanTSR,
		DistancesKM:     distKM,
	}
}
