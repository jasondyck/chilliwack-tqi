package raptor

import (
	"encoding/gob"
	"fmt"
	"os"
	"path/filepath"

	"github.com/jasondyck/chwk-tqi/internal/scoring"
)

// cacheFilename returns the gob cache filename for the given parameters.
func cacheFilename(feedHash string, nOrigins int) string {
	h := feedHash
	if len(h) > 12 {
		h = h[:12]
	}
	return fmt.Sprintf("od_metrics_%s_%d.gob", h, nOrigins)
}

// SaveCache gob-encodes an ODMetrics to disk.
func SaveCache(dir, feedHash string, nOrigins int, m *scoring.ODMetrics) error {
	path := filepath.Join(dir, cacheFilename(feedHash, nOrigins))
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return gob.NewEncoder(f).Encode(m)
}

// LoadCache gob-decodes an ODMetrics from disk.
func LoadCache(dir, feedHash string, nOrigins int) (*scoring.ODMetrics, error) {
	path := filepath.Join(dir, cacheFilename(feedHash, nOrigins))
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var m scoring.ODMetrics
	if err := gob.NewDecoder(f).Decode(&m); err != nil {
		return nil, err
	}
	return &m, nil
}
