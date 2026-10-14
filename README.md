# Chilliwack Transit Quality Index (TQI)

A data-driven score (0–100) for how well public transit connects people to places in Chilliwack, BC.

**Live dashboard:** https://jasondyck.github.io/chilliwack-tqi/ — refreshed weekly from BC Transit's latest published schedule.

## How it works

1. Downloads the BC Transit GTFS feed for the Fraser Valley region (operator 13).
2. Picks a representative weekday from the feed. Every Mon–Fri is grouped by its set of active services, and the most common pattern wins, so statutory holidays and one-off service changes are skipped.
3. Lays a 250 m grid (~4,700 points) over the municipal boundary.
4. Runs RAPTOR transit routing from every point to every other point, at 64 departure times from 06:00 to 22:00.
5. Scores the result:
   - **TQI**: 50% coverage (share of trips transit can make at all) + 50% speed (how much faster than walking). Transit gets no credit where walking is faster.
   - **TCQSM Level of Service**: an A–F grade per route by headway (TCRP Report 165).
   - **PTAL**: Transport for London's Public Transport Accessibility Level.
   - **Amenity access**: travel times to the hospital, grocery stores, schools and other key destinations.
   - **Neighbourhood breakdown** and population-weighted score, when boundary data is present (see below).

A full run takes a few seconds. See [docs/methodology.md](docs/methodology.md) for the methodology.

## Quick start

Requires Go 1.25+ and Node 24+.

```bash
make serve           # build dashboard + CLI, run the analysis, serve at http://localhost:8080
```

Or step by step:

```bash
go run ./cmd/tqi run             # download GTFS, analyse, write output/tqi_results.json
go run ./cmd/tqi run --no-download --date 20261020   # reuse feed, pin a service date
go run ./cmd/tqi serve           # run analysis and serve API + dashboard
go run ./cmd/tqi compare --cities chilliwack,victoria,kelowna
```

Frontend development, with the API server running on :8080:

```bash
cd web && npm install && npm run dev
```

## Layout

```
cmd/tqi/          CLI entrypoint (run, serve, download, compare)
internal/
  gtfs/           feed download, parsing, service-date selection
  grid/           analysis grid + boundary clipping
  raptor/         RAPTOR engine and OD travel-time matrix
  scoring/        TQI, TCQSM, PTAL, amenities, reliability, time profile
  neighbourhood/  per-neighbourhood + population-weighted scores
  isochrone/      reachability from the downtown exchange
  equity/         optional census income overlay
  api/            HTTP API (also serves /results.json)
web/              React + TypeScript dashboard (Vite, Tailwind, Recharts, Leaflet)
data/             curated inputs (municipal boundary, amenities)
```

## Data

| Input | Source | In repo? |
|-------|--------|----------|
| GTFS schedule | [BC Transit open data](https://www.bctransit.com/open-data/), downloaded each run | no |
| Municipal boundary | [City of Chilliwack Open Data](https://www.chilliwack.com/opendata) | `data/chilliwack_boundary.geojson` |
| Amenities | Hand-curated | `data/amenities.json` |
| Neighbourhoods | [City of Chilliwack Open Data](https://www.chilliwack.com/opendata), Neighbourhoods layer (OCP 2050) | `data/neighbourhoods.geojson` |
| Census income (optional) | Statistics Canada 2021, Dissemination Areas | place under `data/census/` |

Optional inputs are skipped if missing. Without `neighbourhoods.geojson`, the headline score falls back to the plain grid average instead of the population-weighted one.

Contains information licensed under the [Open Data License – City of Chilliwack](https://opendata.chilliwack.com/Chilliwack_Open_Data_License/Open_Data_License-City_of_Chilliwack.pdf).

## Publishing

`.github/workflows/pages.yml` runs the analysis, copies `output/tqi_results.json` to `web/public/results.json`, builds the dashboard as a static site and deploys it to GitHub Pages. It runs on every push to `master`, weekly on Mondays, and on demand.

## Tests

```bash
make test        # go test + frontend lint
cd web && npm run e2e   # Playwright smoke + accessibility tests
```

## License

[MIT](LICENSE)
