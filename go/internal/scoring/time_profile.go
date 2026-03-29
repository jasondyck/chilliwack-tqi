package scoring

import (
	"fmt"
	"math"

	"github.com/jasondyck/chwk-tqi/internal/config"
)

// ComputeTimeProfile returns the TQI for each departure time slot.
func ComputeTimeProfile(perSlotCoverage, perSlotMeanTSR []float64) []TimeSlotScore {
	departures := config.DepartureTimes()
	n := len(perSlotCoverage)
	if n > len(departures) {
		n = len(departures)
	}

	profile := make([]TimeSlotScore, n)
	for i := 0; i < n; i++ {
		cov := perSlotCoverage[i] * 100.0

		speedNorm := (perSlotMeanTSR[i] - config.TSRWalk) / (config.TSRCar - config.TSRWalk) * 100.0
		speedNorm = math.Max(0, math.Min(100, speedNorm))

		tqi := 0.5*cov + 0.5*speedNorm

		h := departures[i] / 60
		m := departures[i] % 60
		label := fmt.Sprintf("%02d:%02d", h, m)

		profile[i] = TimeSlotScore{Label: label, Score: tqi}
	}
	return profile
}
