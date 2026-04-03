package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"sync"

	"github.com/jasondyck/chwk-tqi/internal/equity"
	"github.com/jasondyck/chwk-tqi/internal/isochrone"
	"github.com/jasondyck/chwk-tqi/internal/neighbourhood"
	"github.com/jasondyck/chwk-tqi/internal/scoring"
)

// GridScorePoint holds a single grid point with its composite score.
type GridScorePoint struct {
	Lat   float64 `json:"lat"`
	Lon   float64 `json:"lon"`
	Score float64 `json:"score"`
}

// PipelineResults holds the output of a completed pipeline run.
type PipelineResults struct {
	TQI               *scoring.TQIResult        `json:"tqi"`
	Metrics           *scoring.ODMetrics         `json:"-"`
	RouteLOS          []scoring.RouteLOS         `json:"route_los"`
	SystemLOS         *scoring.SystemLOSSummary  `json:"system_los"`
	PTAL              *scoring.PTALResult        `json:"ptal"`
	Amenities         []scoring.AmenityResult    `json:"amenities"`
	GridPoints        int                        `json:"grid_points"`
	NStops            int                        `json:"n_stops"`
	GridScores        []GridScorePoint           `json:"grid_scores,omitempty"`
	Narrative         []string                   `json:"narrative,omitempty"`
	WalkScoreCategory string                     `json:"walkscore_category"`
	WalkScoreDesc     string                     `json:"walkscore_desc"`
	DetailedAnalysis  *scoring.DetailedAnalysis   `json:"detailed_analysis,omitempty"`
	Isochrones        []isochrone.Result          `json:"isochrones,omitempty"`
	Equity                  *equity.Result              `json:"equity,omitempty"`
	NeighbourhoodScores     []neighbourhood.Score       `json:"neighbourhood_scores,omitempty"`
	NeighbourhoodBoundaries json.RawMessage             `json:"neighbourhood_boundaries,omitempty"`
}

// Server is the HTTP API server for the TQI pipeline.
type Server struct {
	Port    int
	Mux     *http.ServeMux
	WebFS   http.FileSystem // embedded frontend (nil = no SPA serving)
	mu      sync.RWMutex
	results *PipelineResults
	running bool
}

// NewServer creates a Server and registers all routes.
func NewServer(port int) *Server {
	s := &Server{
		Port: port,
		Mux:  http.NewServeMux(),
	}
	s.registerRoutes()
	return s
}

// Start begins listening on the configured port.
func (s *Server) Start() error {
	addr := fmt.Sprintf(":%d", s.Port)
	return http.ListenAndServe(addr, s.Mux)
}

// SetResults stores pipeline results (thread-safe).
func (s *Server) SetResults(r *PipelineResults) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.results = r
}

func (s *Server) registerRoutes() {
	s.Mux.HandleFunc("GET /api/health", s.handleHealth)
	s.Mux.HandleFunc("GET /api/config", s.handleConfig)
	s.Mux.HandleFunc("GET /api/results", s.handleResults)
	s.Mux.HandleFunc("GET /api/results/routes", s.handleResultsRoutes)
	s.Mux.HandleFunc("GET /api/results/time-profile", s.handleResultsTimeProfile)
	s.Mux.HandleFunc("GET /api/results/amenities", s.handleResultsAmenities)
	s.Mux.HandleFunc("GET /api/results/grid", s.handleResultsGrid)
	s.Mux.HandleFunc("GET /api/results/narrative", s.handleResultsNarrative)
	s.Mux.HandleFunc("GET /api/results/walkscore", s.handleResultsWalkScore)
	s.Mux.HandleFunc("POST /api/run", s.handleRun)

	// SPA catch-all: serve embedded frontend if available
	s.Mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if s.WebFS == nil {
			http.NotFound(w, r)
			return
		}
		// Try serving the exact file; fall back to index.html for SPA routing
		path := r.URL.Path
		if path == "/" {
			path = "/index.html"
		}
		f, err := s.WebFS.Open(path[1:])
		if err != nil {
			// SPA fallback: serve index.html
			r.URL.Path = "/"
		} else {
			f.Close()
		}
		http.FileServer(s.WebFS).ServeHTTP(w, r)
	})
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleConfig(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"mapbox_token": os.Getenv("MAPBOX_TOKEN"),
	})
}

func (s *Server) handleResults(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	res := s.results
	s.mu.RUnlock()

	if res == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no results available"})
		return
	}
	writeJSON(w, http.StatusOK, res)
}

func (s *Server) handleResultsRoutes(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	res := s.results
	s.mu.RUnlock()

	if res == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no results available"})
		return
	}
	writeJSON(w, http.StatusOK, res.RouteLOS)
}

func (s *Server) handleResultsTimeProfile(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	res := s.results
	s.mu.RUnlock()

	if res == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no results available"})
		return
	}
	if res.TQI == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no time profile available"})
		return
	}
	writeJSON(w, http.StatusOK, res.TQI.TimeProfile)
}

func (s *Server) handleResultsAmenities(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	res := s.results
	s.mu.RUnlock()

	if res == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no results available"})
		return
	}
	writeJSON(w, http.StatusOK, res.Amenities)
}

func (s *Server) handleResultsGrid(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	res := s.results
	s.mu.RUnlock()

	if res == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no results available"})
		return
	}
	writeJSON(w, http.StatusOK, res.GridScores)
}

func (s *Server) handleResultsNarrative(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	res := s.results
	s.mu.RUnlock()

	if res == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no results available"})
		return
	}
	writeJSON(w, http.StatusOK, res.Narrative)
}

func (s *Server) handleResultsWalkScore(w http.ResponseWriter, r *http.Request) {
	s.mu.RLock()
	res := s.results
	s.mu.RUnlock()

	if res == nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "no results available"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"category":    res.WalkScoreCategory,
		"description": res.WalkScoreDesc,
	})
}

func (s *Server) handleRun(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		writeJSON(w, http.StatusConflict, map[string]string{"error": "pipeline already running"})
		return
	}
	s.running = true
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		s.running = false
		s.mu.Unlock()
	}()

	sse := NewSSEWriter(w)
	if sse == nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "streaming not supported"})
		return
	}

	// Placeholder: will be wired to the pipeline in a later task.
	sse.SendProgress("init", 0, "pipeline started")
	sse.SendComplete(0, 0)
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}
