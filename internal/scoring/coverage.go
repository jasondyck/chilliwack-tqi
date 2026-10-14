package scoring

// ComputeCoverageScore returns the mean reachability for valid OD pairs,
// scaled to 0-100.
func ComputeCoverageScore(reachability, distancesKM [][]float64) float64 {
	var sum float64
	var count int

	n := len(reachability)
	for i := 0; i < n; i++ {
		for j := 0; j < len(reachability[i]); j++ {
			if i == j {
				continue
			}
			if !IsValidPair(distancesKM[i][j]) {
				continue
			}
			sum += reachability[i][j]
			count++
		}
	}
	if count == 0 {
		return 0
	}
	return (sum / float64(count)) * 100.0
}
