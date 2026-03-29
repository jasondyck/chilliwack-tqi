package scoring

import (
	"fmt"
	"math"
	"sort"

	"github.com/jasondyck/chwk-tqi/internal/grid"
)

// haversineKM returns the great-circle distance in kilometres between two
// lat/lon points (in degrees).
func haversineKM(lat1, lon1, lat2, lon2 float64) float64 {
	const earthRadiusKM = 6371.0
	dLat := (lat2 - lat1) * math.Pi / 180.0
	dLon := (lon2 - lon1) * math.Pi / 180.0
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*math.Pi/180.0)*math.Cos(lat2*math.Pi/180.0)*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return earthRadiusKM * c
}

// mean returns the arithmetic mean of a float64 slice. Returns 0 for empty input.
func mean(vals []float64) float64 {
	if len(vals) == 0 {
		return 0
	}
	var sum float64
	for _, v := range vals {
		sum += v
	}
	return sum / float64(len(vals))
}

// percentile returns the interpolated p-th percentile (0–100) of a sorted slice.
func percentile(sorted []float64, p float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	if n == 1 {
		return sorted[0]
	}
	rank := (p / 100.0) * float64(n-1)
	lo := int(math.Floor(rank))
	hi := lo + 1
	if hi >= n {
		return sorted[n-1]
	}
	frac := rank - float64(lo)
	return sorted[lo]*(1-frac) + sorted[hi]*frac
}

// ComputeDetailedAnalysis derives dashboard metrics from OD matrices and
// related pipeline outputs.
func ComputeDetailedAnalysis(
	points []grid.Point,
	metrics *ODMetrics,
	tqi *TQIResult,
	ptal *PTALResult,
	stopLats, stopLons []float64,
) *DetailedAnalysis {
	nOrigins := len(points)
	nDests := nOrigins // square matrix

	// --- Coverage: origins within 800 m of any stop ---
	const serviceRadiusKM = 0.8
	nWithService := 0
	for _, pt := range points {
		near := false
		for k := 0; k < len(stopLats); k++ {
			if haversineKM(pt.Lat, pt.Lon, stopLats[k], stopLons[k]) <= serviceRadiusKM {
				near = true
				break
			}
		}
		if near {
			nWithService++
		}
	}
	nDesert := nOrigins - nWithService
	desertPct := 0.0
	if nOrigins > 0 {
		desertPct = float64(nDesert) / float64(nOrigins) * 100.0
	}

	// --- OD pair counts, TSR, travel times ---
	var nValid, nReachable int
	var tsrVals []float64
	var ttVals []float64

	// Per-origin reachability counts (number of reachable destinations).
	originReach := make([]int, nOrigins)

	for i := 0; i < nOrigins; i++ {
		if i >= len(metrics.MeanTravelTime) {
			continue
		}
		for j := 0; j < nDests; j++ {
			if i == j {
				continue
			}
			if j >= len(metrics.MeanTravelTime[i]) {
				continue
			}
			tt := metrics.MeanTravelTime[i][j]
			if tt > 0 && tt <= 90 {
				nValid++
				if i < len(metrics.Reachability) && j < len(metrics.Reachability[i]) && metrics.Reachability[i][j] > 0 {
					nReachable++
					originReach[i]++
					ttVals = append(ttVals, tt)

					// TSR = distance_km / (travel_time_min / 60) = km/h
					if i < len(metrics.DistancesKM) && j < len(metrics.DistancesKM[i]) {
						dist := metrics.DistancesKM[i][j]
						if dist > 0 && tt > 0 {
							tsr := dist / (tt / 60.0)
							tsrVals = append(tsrVals, tsr)
						}
					}
				}
			}
		}
	}

	reachRate := 0.0
	if nValid > 0 {
		reachRate = float64(nReachable) / float64(nValid) * 100.0
	}

	// Max origin reachability %.
	maxOriginReach := 0.0
	for i, cnt := range originReach {
		possibleDests := nDests - 1 // exclude self
		if possibleDests <= 0 {
			continue
		}
		_ = i
		pct := float64(cnt) / float64(possibleDests) * 100.0
		if pct > maxOriginReach {
			maxOriginReach = pct
		}
	}

	// --- TSR stats ---
	sort.Float64s(tsrVals)
	meanTSR := mean(tsrVals)
	medianTSR := percentile(tsrVals, 50)

	tsrPctiles := map[string]float64{}
	for _, p := range []float64{10, 25, 50, 75, 90, 95, 99} {
		tsrPctiles[fmt.Sprintf("p%d", int(p))] = percentile(tsrVals, p)
	}

	// Speed bands.
	var nSlowWalk, n5to10, n10to20, n20plus int
	for _, v := range tsrVals {
		switch {
		case v < 5:
			nSlowWalk++
		case v < 10:
			n5to10++
		case v < 20:
			n10to20++
		default:
			n20plus++
		}
	}
	tsrTotal := float64(len(tsrVals))
	pctOf := func(n int) float64 {
		if tsrTotal == 0 {
			return 0
		}
		return float64(n) / tsrTotal * 100.0
	}

	// --- Travel time stats ---
	sort.Float64s(ttVals)
	meanTT := mean(ttVals)
	medianTT := percentile(ttVals, 50)
	ttPctiles := map[string]float64{}
	for _, p := range []float64{10, 25, 50, 75, 90} {
		ttPctiles[fmt.Sprintf("p%d", int(p))] = percentile(ttVals, p)
	}

	// --- Peak / lowest time slot ---
	peakSlot, lowestSlot := "", ""
	peakTQI, lowestTQI := -1.0, math.MaxFloat64
	for _, ts := range tqi.TimeProfile {
		if ts.Score > peakTQI {
			peakTQI = ts.Score
			peakSlot = ts.Label
		}
		if ts.Score < lowestTQI {
			lowestTQI = ts.Score
			lowestSlot = ts.Label
		}
	}
	if len(tqi.TimeProfile) == 0 {
		peakTQI = 0
		lowestTQI = 0
	}

	// --- Top origins by reachability ---
	type indexedReach struct {
		idx  int
		cnt  int
		pct  float64
	}
	ranked := make([]indexedReach, nOrigins)
	for i := 0; i < nOrigins; i++ {
		possibleDests := nDests - 1
		pct := 0.0
		if possibleDests > 0 {
			pct = float64(originReach[i]) / float64(possibleDests) * 100.0
		}
		ranked[i] = indexedReach{idx: i, cnt: originReach[i], pct: pct}
	}
	sort.Slice(ranked, func(a, b int) bool {
		return ranked[a].cnt > ranked[b].cnt
	})
	topN := 10
	if nOrigins < topN {
		topN = nOrigins
	}
	topOrigins := make([]TopOrigin, topN)
	for k := 0; k < topN; k++ {
		topOrigins[k] = TopOrigin{
			Lat:             points[ranked[k].idx].Lat,
			Lon:             points[ranked[k].idx].Lon,
			ReachabilityPct: ranked[k].pct,
		}
	}

	// --- Reliability histogram (25 bins) ---
	reliHist := buildReliabilityHistogram(tqi.ReliabilityPerOrigin, 25)

	// --- PTAL distribution ---
	ptalDist := map[string]int{}
	if ptal != nil {
		for _, g := range ptal.Grades {
			ptalDist[g]++
		}
	}

	return &DetailedAnalysis{
		NOriginsWithService:      nWithService,
		NTransitDesertOrigins:    nDesert,
		TransitDesertPct:         desertPct,
		NValidPairs:              nValid,
		NReachablePairs:          nReachable,
		ReachabilityRatePct:      reachRate,
		MaxOriginReachabilityPct: maxOriginReach,

		MeanTSR:                 meanTSR,
		MedianTSR:               medianTSR,
		TSRPercentiles:          tsrPctiles,
		TSRSlowerThanWalkingPct: pctOf(nSlowWalk),
		TSR5To10Pct:             pctOf(n5to10),
		TSR10To20Pct:            pctOf(n10to20),
		TSR20PlusPct:            pctOf(n20plus),

		MeanTravelTimeMin:     meanTT,
		MedianTravelTimeMin:   medianTT,
		TravelTimePercentiles: ttPctiles,

		PeakSlot:   peakSlot,
		PeakTQI:    peakTQI,
		LowestSlot: lowestSlot,
		LowestTQI:  lowestTQI,

		TopOrigins:           topOrigins,
		ReliabilityHistogram: reliHist,
		PTALDistribution:     ptalDist,
	}
}

// buildReliabilityHistogram bins reliability values into nBins equal-width bins
// spanning [0, max].
func buildReliabilityHistogram(values []float64, nBins int) HistogramData {
	if len(values) == 0 || nBins <= 0 {
		return HistogramData{Labels: []string{}, Counts: []int{}}
	}

	maxVal := 0.0
	for _, v := range values {
		if v > maxVal {
			maxVal = v
		}
	}
	if maxVal == 0 {
		// All zeros — single bin.
		return HistogramData{
			Labels: []string{"0.00-0.00"},
			Counts: []int{len(values)},
		}
	}

	binWidth := maxVal / float64(nBins)
	counts := make([]int, nBins)
	for _, v := range values {
		bin := int(v / binWidth)
		if bin >= nBins {
			bin = nBins - 1
		}
		counts[bin]++
	}

	labels := make([]string, nBins)
	for i := 0; i < nBins; i++ {
		lo := float64(i) * binWidth
		hi := float64(i+1) * binWidth
		labels[i] = fmt.Sprintf("%.2f-%.2f", lo, hi)
	}

	return HistogramData{Labels: labels, Counts: counts}
}
