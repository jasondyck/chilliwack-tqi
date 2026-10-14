package gtfs

import (
	"archive/zip"
	"crypto/sha256"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

// ExpectedFiles lists the required GTFS files.
var ExpectedFiles = []string{"stops.txt", "stop_times.txt", "trips.txt", "routes.txt"}

// DownloadGTFS downloads a GTFS zip from url, extracts it to destDir,
// and returns the SHA-256 hash of the zip file.
func DownloadGTFS(url, destDir string) (string, error) {
	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("downloading GTFS: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("downloading GTFS: HTTP %d", resp.StatusCode)
	}

	// Read entire body to compute hash and extract
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("reading GTFS response: %w", err)
	}

	// Compute hash
	h := sha256.Sum256(body)
	hash := fmt.Sprintf("%x", h)

	// Extract zip
	zr, err := zip.NewReader(strings.NewReader(string(body)), int64(len(body)))
	if err != nil {
		return "", fmt.Errorf("opening zip: %w", err)
	}

	if err := os.MkdirAll(destDir, 0755); err != nil {
		return "", fmt.Errorf("creating dest dir: %w", err)
	}

	for _, f := range zr.File {
		// Skip directories and files with path separators (security)
		name := filepath.Base(f.Name)
		if f.FileInfo().IsDir() || name == "" {
			continue
		}

		outPath := filepath.Join(destDir, name)
		rc, err := f.Open()
		if err != nil {
			return "", fmt.Errorf("opening zip entry %s: %w", f.Name, err)
		}

		outFile, err := os.Create(outPath)
		if err != nil {
			rc.Close()
			return "", fmt.Errorf("creating %s: %w", outPath, err)
		}

		_, err = io.Copy(outFile, rc)
		rc.Close()
		outFile.Close()
		if err != nil {
			return "", fmt.Errorf("extracting %s: %w", f.Name, err)
		}
	}

	// Write hash file
	hashPath := filepath.Join(destDir, ".feed_hash")
	if err := os.WriteFile(hashPath, []byte(hash), 0644); err != nil {
		return "", fmt.Errorf("writing hash file: %w", err)
	}

	return hash, nil
}

// GetFeedHash reads the .feed_hash file from a GTFS directory, or returns ""
// if not found.
func GetFeedHash(gtfsDir string) string {
	data, err := os.ReadFile(filepath.Join(gtfsDir, ".feed_hash"))
	if err != nil {
		return ""
	}
	return string(data)
}
