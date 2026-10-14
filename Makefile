.PHONY: all web build run serve dev-web test lint clean

all: build

# Build the React dashboard into web/dist
web:
	cd web && npm ci && npm run build

# Build the CLI with the dashboard embedded
build: web
	go build -tags embed_frontend -o bin/tqi ./cmd/tqi

# Run the analysis and write output/tqi_results.json
run:
	go run ./cmd/tqi run

# Run the analysis, then serve the dashboard at http://localhost:8080
serve: build
	./bin/tqi serve --port 8080

# Vite dev server (proxies data requests to `make serve` on :8080)
dev-web:
	cd web && npm run dev

test:
	go test ./...
	cd web && npm run lint

lint:
	go vet ./...
	@command -v staticcheck >/dev/null 2>&1 && staticcheck ./... || echo "staticcheck not installed, skipping"
	cd web && npm run lint

clean:
	rm -rf bin/ output/ web/dist/
