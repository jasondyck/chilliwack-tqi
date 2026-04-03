.PHONY: build-web build dev-api dev-web test lint clean

# Build the SvelteKit frontend (placeholder — requires web/ to exist)
build-web:
	@echo "build-web: not yet implemented (no web/ directory)"

# Build the Go CLI binary
build:
	go build -o bin/tqi ./cmd/tqi/

# Run the API server in dev mode
dev-api: build
	./bin/tqi serve --port 8080

# Run the SvelteKit dev server (placeholder)
dev-web:
	@echo "dev-web: not yet implemented (no web/ directory)"

# Run all Go tests
test:
	go test ./...

# Run linters
lint:
	go vet ./...
	@command -v staticcheck >/dev/null 2>&1 && staticcheck ./... || echo "staticcheck not installed, skipping"

# Remove build artifacts
clean:
	rm -rf bin/
