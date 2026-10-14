//go:build !embed_frontend

package web

import "net/http"

// DistFS returns nil when built without the embedded frontend.
func DistFS() http.FileSystem {
	return nil
}
