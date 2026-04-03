package gtfs

import (
	"archive/zip"
	"bytes"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestDownloadGTFS(t *testing.T) {
	// Create a test zip in memory
	var buf bytes.Buffer
	zw := zip.NewWriter(&buf)
	for _, name := range []string{"stops.txt", "stop_times.txt", "trips.txt", "routes.txt"} {
		w, err := zw.Create(name)
		require.NoError(t, err)
		_, err = w.Write([]byte("header\nrow\n"))
		require.NoError(t, err)
	}
	require.NoError(t, zw.Close())

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/zip")
		w.Write(buf.Bytes())
	}))
	defer srv.Close()

	destDir := t.TempDir()
	hash, err := DownloadGTFS(srv.URL, destDir)
	require.NoError(t, err)
	assert.NotEmpty(t, hash)

	// Verify files were extracted
	for _, name := range ExpectedFiles {
		_, err := os.Stat(filepath.Join(destDir, name))
		assert.NoError(t, err, "expected file %s to exist", name)
	}

	// Verify hash file was written
	assert.Equal(t, hash, GetFeedHash(destDir))
}

func TestGetFeedHash(t *testing.T) {
	dir := t.TempDir()
	err := os.WriteFile(filepath.Join(dir, ".feed_hash"), []byte("abc123"), 0644)
	require.NoError(t, err)
	assert.Equal(t, "abc123", GetFeedHash(dir))
}

func TestGetFeedHashMissing(t *testing.T) {
	dir := t.TempDir()
	assert.Equal(t, "", GetFeedHash(dir))
}
