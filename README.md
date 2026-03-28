# Chilliwack Transit Quality Index (TQI)

A data-driven analysis of public transit quality in Chilliwack, BC — scoring the city 0–100 based on how well buses connect people to destinations.

## What it does

- Downloads BC Transit GTFS schedule data for the Fraser Valley
- Generates a ~4,700 point analysis grid clipped to Chilliwack's municipal boundary
- Runs ~300,000 RAPTOR pathfinding operations across 64 departure times (6 AM – 10 PM)
- Computes a Transit Quality Index using coverage and speed metrics
- Grades every route using TCQSM Level of Service (TCRP Report 165)
- Computes PTAL accessibility scores (Transport for London methodology)
- Measures access to essential amenities (hospital, grocery, schools)
- Generates an HTML report with interactive maps, isochrones, and charts

## Quick start

```bash
uv sync --all-extras
uv run tqi run              # full pipeline (downloads GTFS, computes, generates report)
uv run tqi run --no-download  # re-run without re-downloading GTFS
```

Open `output/report.html` in a browser.

## CLI commands

```bash
uv run tqi run [OPTIONS]       # full analysis pipeline
  --download/--no-download     # download fresh GTFS data (default: yes)
  --use-cache/--no-cache       # use cached travel time matrix (default: yes)
  --parallel/--no-parallel     # parallelise RAPTOR runs (default: yes)
  --workers N                  # number of parallel workers
  --equity/--no-equity         # include census equity overlay
  --output-dir PATH            # output directory

uv run tqi download            # download GTFS data only

uv run tqi compare             # compare TQI across BC Transit cities
  --cities chilliwack,victoria,kelowna
```

## Output

| File | Description |
|------|-------------|
| `output/report.html` | Full HTML report with all analysis |
| `output/heatmap.html` | Interactive spatial heat map with route overlays |
| `output/isochrone_*.html` | Isochrone maps from downtown exchange |
| `output/tqi_results.json` | Machine-readable results |

## Established frameworks used

- **Walk Score Transit Score** — 0–100 interpretation scale (walkscore.com)
- **TCQSM Level of Service** — route grading A–F by headway (TCRP Report 165, Transportation Research Board)
- **PTAL** — Public Transport Accessibility Level (Transport for London methodology)
- **RAPTOR** — Round-Based Public Transit Routing algorithm (Delling et al., 2012)

## Data sources

- **GTFS**: BC Transit, Operator 13 (Fraser Valley Region) — [bctransit.com/open-data](https://www.bctransit.com/open-data/)
- **Municipal boundary**: City of Chilliwack Open Data — [chilliwack.com](https://www.chilliwack.com/main/page.cfm?id=2331)
- **Census data** (optional): Statistics Canada 2021 Census, Dissemination Area level

## Methodology

See [transit-quality-index.md](transit-quality-index.md) for the full methodology design document.

**TL;DR**: For every pair of points in the city, at every 15-minute interval throughout the day, find the fastest transit trip (RAPTOR algorithm). Compare transit speed against walking speed. The TQI is 50% coverage (what fraction of trips are possible) + 50% speed (how fast transit is vs walking). Trips where walking is faster than transit are excluded — transit only gets credit when it actually helps.

## Running tests

```bash
uv run pytest -v
```

## License

MIT
