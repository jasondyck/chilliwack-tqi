package scoring

// ComputeTQI calculates the Transit Quality Index from OD metrics.
// TQI = 0.5 * coverage + 0.5 * speed, plus time profile and reliability.
func ComputeTQI(metrics *ODMetrics) *TQIResult {
	cov := ComputeCoverageScore(metrics.Reachability, metrics.DistancesKM)
	spd := ComputeSpeedScore(metrics.DistancesKM, metrics.MeanTravelTime)
	tqi := 0.5*cov + 0.5*spd

	tp := ComputeTimeProfile(metrics.PerSlotCoverage, metrics.PerSlotMeanTSR)
	relCV, relPerOrigin := ComputeReliability(metrics.MeanTravelTime, metrics.TravelTimeStd, metrics.DistancesKM)

	return &TQIResult{
		TQI:                  tqi,
		CoverageScore:        cov,
		SpeedScore:           spd,
		TimeProfile:          tp,
		ReliabilityCV:        relCV,
		ReliabilityPerOrigin: relPerOrigin,
	}
}
