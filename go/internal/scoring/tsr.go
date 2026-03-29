package scoring

import (
	"math"

	"github.com/jasondyck/chwk-tqi/internal/config"
)

// ComputeTSR returns the transit speed ratio in km/h.
// TSR = distance / (time / 60). Returns 0 if unreachable.
func ComputeTSR(distKM, travelTimeMin float64) float64 {
	if math.IsInf(travelTimeMin, 1) || travelTimeMin >= InfFloat || travelTimeMin <= 0 {
		return 0
	}
	return distKM / (travelTimeMin / 60.0)
}

// IsValidPair returns true when the OD distance is at least MinODDistKM.
func IsValidPair(distKM float64) bool {
	return distKM >= config.MinODDistKM
}
