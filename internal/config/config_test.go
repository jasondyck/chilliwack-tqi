package config

import "testing"

func TestWalkScoreCategory(t *testing.T) {
	for score, want := range map[float64]string{
		0:    "Minimal Transit",
		3.3:  "Minimal Transit",
		24.6: "Minimal Transit",
		25:   "Some Transit",
		49.5: "Some Transit",
		69.9: "Good Transit",
		70:   "Excellent Transit",
		95:   "Rider's Paradise",
		100:  "Rider's Paradise",
	} {
		if got := WalkScoreCategory(score); got != want {
			t.Errorf("WalkScoreCategory(%v) = %q, want %q", score, got, want)
		}
	}
}
