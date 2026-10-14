// Package geo provides geographic utility functions including haversine
// distance calculations, equirectangular projections, and Euclidean distance.
package geo

import "math"

const (
	// EarthRadiusKM is the mean radius of the Earth in kilometres.
	EarthRadiusKM = 6371.0
	// EarthRadiusM is the mean radius of the Earth in metres.
	EarthRadiusM = 6_371_000.0
)

// deg2rad converts degrees to radians.
func deg2rad(d float64) float64 {
	return d * math.Pi / 180.0
}

// Haversine returns the great-circle distance in kilometres between two points
// specified by latitude and longitude in decimal degrees.
func Haversine(lat1, lon1, lat2, lon2 float64) float64 {
	lat1R := deg2rad(lat1)
	lat2R := deg2rad(lat2)
	dLat := deg2rad(lat2 - lat1)
	dLon := deg2rad(lon2 - lon1)

	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1R)*math.Cos(lat2R)*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))

	return EarthRadiusKM * c
}

// HaversineMatrix returns a symmetric n x n matrix of pairwise haversine
// distances (in km) for the given latitude/longitude slices.
func HaversineMatrix(lats, lons []float64) [][]float64 {
	n := len(lats)
	mat := make([][]float64, n)
	for i := range mat {
		mat[i] = make([]float64, n)
	}
	for i := 0; i < n; i++ {
		for j := i + 1; j < n; j++ {
			d := Haversine(lats[i], lons[i], lats[j], lons[j])
			mat[i][j] = d
			mat[j][i] = d
		}
	}
	return mat
}

// ProjectToXY converts a (lat, lon) pair to (x, y) metres using an
// equirectangular projection centred at the given latitude (in radians).
func ProjectToXY(lat, lon, centerLatRad float64) (x, y float64) {
	latR := deg2rad(lat)
	lonR := deg2rad(lon)
	x = EarthRadiusM * lonR * math.Cos(centerLatRad)
	y = EarthRadiusM * latR
	return x, y
}

// ProjectSliceToXY applies ProjectToXY to each element in the lat/lon slices.
func ProjectSliceToXY(lats, lons []float64, centerLatRad float64) (xs, ys []float64) {
	n := len(lats)
	xs = make([]float64, n)
	ys = make([]float64, n)
	for i := 0; i < n; i++ {
		xs[i], ys[i] = ProjectToXY(lats[i], lons[i], centerLatRad)
	}
	return xs, ys
}

// Distance2D returns the Euclidean distance between two 2-D points.
func Distance2D(x1, y1, x2, y2 float64) float64 {
	dx := x2 - x1
	dy := y2 - y1
	return math.Sqrt(dx*dx + dy*dy)
}
