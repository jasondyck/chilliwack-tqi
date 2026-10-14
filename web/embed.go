//go:build embed_frontend

package web

import (
	"embed"
	"io/fs"
	"net/http"
)

//go:embed all:dist
var dist embed.FS

// DistFS returns the embedded frontend build as an http.FileSystem.
func DistFS() http.FileSystem {
	sub, _ := fs.Sub(dist, "dist")
	return http.FS(sub)
}
