package raptor

import "math"

// SourceStop represents a source stop with its initial arrival time.
type SourceStop struct {
	StopIdx     int
	ArrivalTime float64
}

// Workspace holds reusable working memory for the RAPTOR algorithm.
type Workspace struct {
	Tau       [][]float64 // [K+1][nStops]
	Best      []float64
	Marked    []bool
	NewMarked []bool
	PatBoard  []int32
}

// NewWorkspace allocates a new workspace for nStops stops.
// Default K+1 = 4 (MaxTransfers=2 -> K=3, tau has K+1=4 rows).
func NewWorkspace(nStops int) *Workspace {
	ws := &Workspace{}
	K := 4 // default: max_transfers(2) + 1 + 1
	ws.Tau = make([][]float64, K)
	for i := range ws.Tau {
		ws.Tau[i] = make([]float64, nStops)
	}
	ws.Best = make([]float64, nStops)
	ws.Marked = make([]bool, nStops)
	ws.NewMarked = make([]bool, nStops)
	ws.Reset(nStops)
	return ws
}

// Reset reinitializes all workspace arrays to their default (Inf/false) state.
func (ws *Workspace) Reset(nStops int) {
	for k := range ws.Tau {
		for i := 0; i < nStops; i++ {
			ws.Tau[k][i] = Inf
		}
	}
	for i := 0; i < nStops; i++ {
		ws.Best[i] = Inf
		ws.Marked[i] = false
		ws.NewMarked[i] = false
	}
}

// ensureCapacity grows the workspace if needed for the given parameters.
func (ws *Workspace) ensureCapacity(nStops, maxTransfers, nPatterns int) {
	K := maxTransfers + 2 // K+1 rows where K = maxTransfers+1
	if len(ws.Tau) < K {
		ws.Tau = make([][]float64, K)
		for i := range ws.Tau {
			ws.Tau[i] = make([]float64, nStops)
		}
	} else {
		for i := range ws.Tau {
			if len(ws.Tau[i]) < nStops {
				ws.Tau[i] = make([]float64, nStops)
			}
		}
	}
	if len(ws.Best) < nStops {
		ws.Best = make([]float64, nStops)
	}
	if len(ws.Marked) < nStops {
		ws.Marked = make([]bool, nStops)
	}
	if len(ws.NewMarked) < nStops {
		ws.NewMarked = make([]bool, nStops)
	}
	if len(ws.PatBoard) < nPatterns {
		ws.PatBoard = make([]int32, nPatterns)
	}
}

// RunRAPTOR runs the RAPTOR algorithm and returns a copy of the best arrival times.
func RunRAPTOR(ft *FlatTimetable, sources []SourceStop, maxTransfers int, maxTime float64) []float64 {
	ws := NewWorkspace(ft.NStops)
	ws.ensureCapacity(ft.NStops, maxTransfers, ft.NPatterns)
	RunRAPTORWithWorkspace(ft, sources, maxTransfers, maxTime, ws)
	result := make([]float64, ft.NStops)
	copy(result, ws.Best)
	return result
}

// RunRAPTORWithWorkspace runs the RAPTOR algorithm using a pre-allocated workspace.
func RunRAPTORWithWorkspace(ft *FlatTimetable, sources []SourceStop, maxTransfers int, maxTime float64, ws *Workspace) {
	nStops := ft.NStops
	nPatterns := ft.NPatterns
	K := maxTransfers + 1

	ws.ensureCapacity(nStops, maxTransfers, nPatterns)
	ws.Reset(nStops)

	// 1. Initialize source stops.
	for _, src := range sources {
		s := src.StopIdx
		t := src.ArrivalTime
		if t < ws.Tau[0][s] {
			ws.Tau[0][s] = t
			ws.Best[s] = t
			ws.Marked[s] = true
		}
	}

	// 2. Apply initial transfers from source stops.
	applyTransfers(ft, ws.Tau[0], ws.Best, ws.Marked, nStops, maxTime)

	// 3. Main rounds.
	for k := 1; k <= K; k++ {
		// Copy tau[k] = tau[k-1]
		copy(ws.Tau[k], ws.Tau[k-1])

		// Clear NewMarked.
		for i := 0; i < nStops; i++ {
			ws.NewMarked[i] = false
		}

		// Ensure PatBoard is large enough and reset.
		if ws.PatBoard == nil || len(ws.PatBoard) < nPatterns {
			ws.PatBoard = make([]int32, nPatterns)
		}
		for i := 0; i < nPatterns; i++ {
			ws.PatBoard[i] = -1
		}

		// Collect patterns containing marked stops.
		for s := 0; s < nStops; s++ {
			if !ws.Marked[s] {
				continue
			}
			for j := ft.SPOffsets[s]; j < ft.SPOffsets[s+1]; j++ {
				pidx := ft.SPData[j][0]
				pos := ft.SPData[j][1]
				if ws.PatBoard[pidx] < 0 || pos < ws.PatBoard[pidx] {
					ws.PatBoard[pidx] = pos
				}
			}
		}

		// Route scanning.
		for pidx := 0; pidx < nPatterns; pidx++ {
			if ws.PatBoard[pidx] < 0 {
				continue
			}

			boardPos := ws.PatBoard[pidx]
			nTrips := int(ft.TTNTrips[pidx])
			nS := int(ft.TTNStops[pidx])
			if nTrips == 0 {
				continue
			}

			ttOff := int(ft.TTOffsets[pidx])
			currentTrip := int32(-1)

			for pos := boardPos; pos < int32(nS); pos++ {
				stopIdx := int(ft.PSData[ft.PSOffsets[pidx]+pos])

				// Can current trip improve arrival at this stop?
				if currentTrip >= 0 {
					arrTime := float64(ft.TTData[ttOff+int(currentTrip)*nS*2+int(pos)*2])
					if arrTime < ws.Best[stopIdx] && arrTime <= maxTime {
						if arrTime < ws.Tau[k][stopIdx] {
							ws.Tau[k][stopIdx] = arrTime
						}
						if arrTime < ws.Best[stopIdx] {
							ws.Best[stopIdx] = arrTime
						}
						ws.NewMarked[stopIdx] = true
					}
				}

				// Can we board an earlier trip at this stop?
				earliestBoard := ws.Tau[k-1][stopIdx]
				if earliestBoard < math.MaxFloat64 {
					// Binary search for earliest trip with dep >= earliestBoard.
					lo, hi := 0, nTrips
					for lo < hi {
						mid := (lo + hi) / 2
						dep := float64(ft.TTData[ttOff+mid*nS*2+int(pos)*2+1])
						if dep < earliestBoard {
							lo = mid + 1
						} else {
							hi = mid
						}
					}
					if lo < nTrips {
						if currentTrip < 0 || int32(lo) < currentTrip {
							currentTrip = int32(lo)
						}
					}
				}
			}
		}

		// Transfer phase.
		applyTransfers(ft, ws.Tau[k], ws.Best, ws.NewMarked, nStops, maxTime)

		// Check convergence.
		anyMarked := false
		for s := 0; s < nStops; s++ {
			ws.Marked[s] = ws.NewMarked[s]
			if ws.NewMarked[s] {
				anyMarked = true
			}
		}
		if !anyMarked {
			break
		}
	}
}

// applyTransfers applies walking transfers from marked stops.
func applyTransfers(ft *FlatTimetable, tauK []float64, best []float64, marked []bool, nStops int, maxTime float64) {
	newMarks := make([]bool, nStops)

	for s := 0; s < nStops; s++ {
		if !marked[s] {
			continue
		}
		for j := ft.TROffsets[s]; j < ft.TROffsets[s+1]; j++ {
			target := int(ft.TRData[j][0])
			walkMin := float64(ft.TRData[j][1]) / 100.0
			arr := tauK[s] + walkMin
			if arr < tauK[target] && arr <= maxTime {
				tauK[target] = arr
				if arr < best[target] {
					best[target] = arr
				}
				newMarks[target] = true
			}
		}
	}

	// Merge new marks.
	for s := 0; s < nStops; s++ {
		if newMarks[s] {
			marked[s] = true
		}
	}
}
