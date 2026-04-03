package scoring

import (
	"math"

	"github.com/jasondyck/chwk-tqi/internal/config"
)

// ComputeSpeedScore returns the normalised speed score (0-100).
// Mean TSR for reachable valid pairs is mapped to [0,100] using
// (TSR - TSRWalk) / (TSRCar - TSRWalk) * 100, clamped to [0,100].
func ComputeSpeedScore(distancesKM, meanTravelTime [][]float64) float64 {
	var tsrSum float64
	var count int

	n := len(distancesKM)
	for i := 0; i < n; i++ {
		for j := 0; j < len(distancesKM[i]); j++ {
			if i == j {
				continue
			}
			if !IsValidPair(distancesKM[i][j]) {
				continue
			}
			tsr := ComputeTSR(distancesKM[i][j], meanTravelTime[i][j])
			if tsr <= 0 {
				continue
			}
			tsrSum += tsr
			count++
		}
	}
	if count == 0 {
		return 0
	}
	meanTSR := tsrSum / float64(count)
	score := (meanTSR - config.TSRWalk) / (config.TSRCar - config.TSRWalk) * 100.0
	return math.Max(0, math.Min(100, score))
}
