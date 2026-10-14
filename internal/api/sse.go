package api

import (
	"encoding/json"
	"fmt"
	"net/http"
)

// SSEWriter wraps an http.ResponseWriter with flushing support for
// Server-Sent Events.
type SSEWriter struct {
	w       http.ResponseWriter
	flusher http.Flusher
}

// NewSSEWriter creates an SSEWriter from an http.ResponseWriter.
// It returns nil if the ResponseWriter does not support flushing.
func NewSSEWriter(w http.ResponseWriter) *SSEWriter {
	f, ok := w.(http.Flusher)
	if !ok {
		return nil
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	return &SSEWriter{w: w, flusher: f}
}

// ProgressEvent is sent during pipeline execution to report progress.
type ProgressEvent struct {
	Step    string `json:"step"`
	Percent int    `json:"percent"`
	Message string `json:"message"`
}

// CompleteEvent is sent when the pipeline finishes successfully.
type CompleteEvent struct {
	TQI         float64 `json:"tqi"`
	DurationSec float64 `json:"duration_sec"`
}

// ErrorEvent is sent when the pipeline encounters an error.
type ErrorEvent struct {
	Message string `json:"message"`
}

// SendProgress emits an SSE progress event.
func (s *SSEWriter) SendProgress(step string, pct int, msg string) {
	s.send("progress", ProgressEvent{Step: step, Percent: pct, Message: msg})
}

// SendComplete emits an SSE complete event.
func (s *SSEWriter) SendComplete(tqi, durationSec float64) {
	s.send("complete", CompleteEvent{TQI: tqi, DurationSec: durationSec})
}

// SendError emits an SSE error event.
func (s *SSEWriter) SendError(msg string) {
	s.send("error", ErrorEvent{Message: msg})
}

func (s *SSEWriter) send(eventType string, v any) {
	data, err := json.Marshal(v)
	if err != nil {
		return
	}
	fmt.Fprintf(s.w, "event: %s\ndata: %s\n\n", eventType, data)
	s.flusher.Flush()
}
