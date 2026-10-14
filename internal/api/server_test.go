package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHealthEndpoint(t *testing.T) {
	srv := NewServer(0)
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	w := httptest.NewRecorder()
	srv.Mux.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var body map[string]string
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.Equal(t, "ok", body["status"])
}

func TestResultsNotReady(t *testing.T) {
	srv := NewServer(0)
	req := httptest.NewRequest(http.MethodGet, "/api/results", nil)
	w := httptest.NewRecorder()
	srv.Mux.ServeHTTP(w, req)

	assert.Equal(t, http.StatusNotFound, w.Code)
}

func TestResultsJSONAlias(t *testing.T) {
	srv := NewServer(0)
	srv.SetResults(&PipelineResults{Meta: Meta{City: "chilliwack", ServiceDate: "20261013"}})
	req := httptest.NewRequest(http.MethodGet, "/results.json", nil)
	w := httptest.NewRecorder()
	srv.Mux.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)

	var body struct {
		Meta Meta `json:"meta"`
	}
	require.NoError(t, json.Unmarshal(w.Body.Bytes(), &body))
	assert.Equal(t, "20261013", body.Meta.ServiceDate)
}
