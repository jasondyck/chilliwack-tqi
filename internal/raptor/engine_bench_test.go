package raptor

import "testing"

func BenchmarkRAPTOR(b *testing.B) {
	feed := testFeed()
	tt := BuildTimetable(feed)
	ft := Flatten(tt)

	s1Idx := tt.StopIDToIdx["S1"]
	sources := []SourceStop{{StopIdx: s1Idx, ArrivalTime: 480}}
	ws := NewWorkspace(ft.NStops)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		RunRAPTORWithWorkspace(ft, sources, 2, 570, ws)
	}
}
