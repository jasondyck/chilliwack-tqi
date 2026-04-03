package scoring

import "math"

// ComputeReliability returns the mean coefficient of variation (CV) across
// all valid reachable OD pairs and per-origin CVs.
func ComputeReliability(meanTT, ttStd, distKM [][]float64) (float64, []float64) {
	n := len(meanTT)
	perOrigin := make([]float64, n)

	var totalCV float64
	var totalCount int

	for i := 0; i < n; i++ {
		var originCV float64
		var originCount int

		for j := 0; j < len(meanTT[i]); j++ {
			if i == j {
				continue
			}
			if !IsValidPair(distKM[i][j]) {
				continue
			}
			if math.IsInf(meanTT[i][j], 1) || meanTT[i][j] >= InfFloat || meanTT[i][j] <= 0 {
				continue
			}
			cv := ttStd[i][j] / meanTT[i][j]
			originCV += cv
			originCount++
		}
		if originCount > 0 {
			perOrigin[i] = originCV / float64(originCount)
		}
		totalCV += originCV
		totalCount += originCount
	}

	var meanCV float64
	if totalCount > 0 {
		meanCV = totalCV / float64(totalCount)
	}
	return meanCV, perOrigin
}
