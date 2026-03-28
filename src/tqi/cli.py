"""CLI entry point for the Chilliwack TQI."""

import json
from pathlib import Path

import click
import numpy as np

from tqi.config import OUTPUT_DIR


@click.group()
def main():
    """Chilliwack Transit Quality Index — measure how well transit connects the city."""
    pass


@main.command()
def download():
    """Download GTFS data from BC Transit."""
    from tqi.gtfs.download import download_gtfs
    download_gtfs()


@main.command()
@click.option("--download/--no-download", "do_download", default=True,
              help="Download fresh GTFS data.")
@click.option("--use-cache/--no-cache", default=True,
              help="Use cached travel time matrix if available.")
@click.option("--parallel/--no-parallel", default=True,
              help="Parallelise RAPTOR runs.")
@click.option("--workers", default=None, type=int,
              help="Number of parallel workers.")
@click.option("--equity/--no-equity", default=False,
              help="Include census equity overlay (downloads ~150MB boundary file).")
@click.option("--output-dir", default=str(OUTPUT_DIR), type=click.Path(),
              help="Output directory.")
def run(do_download, use_cache, parallel, workers, equity, output_dir):
    """Run the full TQI analysis pipeline."""
    from tqi.gtfs.download import download_gtfs, get_feed_hash
    from tqi.gtfs.parse import load_gtfs
    from tqi.gtfs.filter import filter_to_chilliwack
    from tqi.grid.generate import generate_grid
    from tqi.raptor.timetable import build_raptor_timetable
    from tqi.raptor.matrix import compute_matrix
    from tqi.scoring.tqi import compute_tqi, compute_detailed_analysis
    from tqi.viz.heatmap import create_heatmap
    from tqi.viz.report import generate_report
    from tqi.scoring.tsr import compute_tsr_matrix, valid_pair_mask

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 1: GTFS
    if do_download:
        download_gtfs()
    feed_hash = get_feed_hash()

    print("\n── Parsing GTFS ──")
    feed = load_gtfs()

    print("\n── Filtering to Chilliwack ──")
    feed = filter_to_chilliwack(feed)

    print("\n── Building RAPTOR timetable ──")
    timetable = build_raptor_timetable(feed)

    print("\n── Generating analysis grid ──")
    grid = generate_grid()
    print(f"Grid: {len(grid)} points")

    # Extract stop coordinates indexed by timetable stop order
    stop_lats = np.array([
        feed.stops.loc[feed.stops["stop_id"] == sid, "stop_lat"].iloc[0]
        for sid in timetable.stop_ids
    ])
    stop_lons = np.array([
        feed.stops.loc[feed.stops["stop_id"] == sid, "stop_lon"].iloc[0]
        for sid in timetable.stop_ids
    ])

    print("\n── Computing travel time matrix ──")
    metrics = compute_matrix(
        timetable, grid, stop_lats, stop_lons,
        parallel=parallel,
        workers=workers,
        feed_hash=feed_hash if use_cache else None,
    )

    print("\n── Computing route-level LOS (TCQSM) ──")
    from tqi.scoring.tcqsm import compute_route_los, compute_system_los_summary
    route_los = compute_route_los(feed)
    system_los = compute_system_los_summary(route_los)
    for r in route_los:
        long = f" ({r.route_long_name})" if r.route_long_name else ""
        print(f"  Route {r.route_name:>3s}{long}: {r.median_headway_min:5.0f} min headway → LOS {r.los_grade}")

    print("\n── Computing PTAL accessibility index ──")
    from tqi.scoring.ptal import compute_ptal
    ptal_values, ptal_grades = compute_ptal(grid, feed)
    ptal_nonzero = ptal_values[ptal_values > 0]
    print(f"  {len(ptal_nonzero)}/{len(grid)} points with PTAL > 0")

    print("\n── Computing TQI scores ──")
    result = compute_tqi(metrics)
    detailed = compute_detailed_analysis(
        metrics, result, grid, len(feed.stops),
        route_los=route_los,
        system_los_summary=system_los,
        ptal_values=ptal_values,
        ptal_grades=ptal_grades,
    )

    print(f"\n{'='*50}")
    print(f"  Chilliwack Transit Quality Index: {result.tqi:.1f} / 100")
    print(f"  Coverage score: {result.coverage_score:.1f}")
    print(f"  Speed score:    {result.speed_score:.1f}")
    print(f"  Reliability CV: {result.reliability_mean_cv:.3f}")
    print(f"{'='*50}\n")

    # Spatial scores: per-origin outbound TQI
    INF = float("inf")
    tsr = compute_tsr_matrix(metrics.distances_km, metrics.mean_travel_time)
    mask = valid_pair_mask(metrics.distances_km) & (metrics.mean_travel_time < INF)
    with np.errstate(divide="ignore", invalid="ignore"):
        origin_tsr = np.where(
            mask.sum(axis=1) > 0,
            np.nanmean(np.where(mask, tsr, np.nan), axis=1),
            0.0,
        )
    origin_reach = np.mean(
        np.where(valid_pair_mask(metrics.distances_km), metrics.reachability, np.nan),
        axis=1,
    )
    origin_reach = np.nan_to_num(origin_reach, nan=0.0)
    origin_speed = np.clip((origin_tsr - 5) / 35 * 100, 0, 100)
    grid_scores = 0.5 * (origin_reach * 100) + 0.5 * origin_speed

    print("── Generating visualisations ──")
    heatmap = create_heatmap(
        grid, grid_scores, feed.stops,
        shapes_df=feed.shapes,
        trips_df=feed.trips,
        routes_df=feed.routes,
    )
    heatmap.save(str(output_path / "heatmap.html"))
    print(f"Heat map saved: {output_path / 'heatmap.html'}")

    # Isochrone from downtown exchange
    print("── Generating isochrone maps ──")
    from tqi.viz.isochrone import compute_isochrone_times, create_isochrone_map
    from tqi.raptor.timetable import flatten_timetable
    ft = flatten_timetable(timetable)

    exchange_lat, exchange_lon = 49.1680, -121.9510
    for dep_time, dep_label in [(8*60, "08:00 AM Peak"), (12*60, "12:00 Midday")]:
        iso_times = compute_isochrone_times(
            exchange_lat, exchange_lon, grid, timetable, ft,
            stop_lats, stop_lons, dep_time,
        )
        iso_map = create_isochrone_map(
            exchange_lat, exchange_lon, grid, iso_times,
            label=f"Downtown Exchange ({dep_label})",
        )
        safe_label = dep_label.replace(" ", "_").replace(":", "")
        iso_map.save(str(output_path / f"isochrone_{safe_label}.html"))
        reachable = (iso_times < float("inf")).sum()
        print(f"  Isochrone {dep_label}: {reachable}/{len(grid)} reachable")

    # Amenity accessibility
    print("── Computing amenity accessibility ──")
    from tqi.scoring.amenity import load_amenities, compute_amenity_accessibility
    amenities = load_amenities()
    if amenities:
        amenity_results = compute_amenity_accessibility(
            grid, metrics.mean_travel_time, metrics.distances_km, amenities,
        )
        for a in amenity_results:
            print(f"  {a['name']}: {a['pct_within_30min']:.0f}% within 30 min, "
                  f"{a['pct_within_60min']:.0f}% within 60 min")
    else:
        amenity_results = []

    # Equity overlay
    has_equity = False
    tqi_income_corr = None
    if equity:
        try:
            from tqi.equity.census import download_da_boundaries, download_census_profile, parse_census_profile
            from tqi.equity.boundaries import load_da_boundaries
            from tqi.equity.overlay import compute_equity_overlay
            from tqi.viz.equity_map import create_equity_map

            print("\n── Census equity overlay ──")
            shp_path = download_da_boundaries()
            csv_path = download_census_profile()
            da_boundaries = load_da_boundaries(shp_path)
            census_data = parse_census_profile(csv_path)

            equity_df = compute_equity_overlay(grid, grid_scores, da_boundaries, census_data)

            if "median_after_tax_income" in equity_df.columns:
                valid_eq = equity_df.dropna(subset=["da_tqi", "median_after_tax_income"])
                if len(valid_eq) > 2:
                    tqi_income_corr = float(valid_eq["da_tqi"].corr(valid_eq["median_after_tax_income"]))

            equity_map = create_equity_map(da_boundaries, equity_df)
            equity_map.save(str(output_path / "equity_map.html"))
            has_equity = True
            print(f"Equity map saved: {output_path / 'equity_map.html'}")
        except Exception as e:
            print(f"Warning: Equity overlay failed: {e}")
            print("Continuing without equity analysis.")

    # Report
    report_path = generate_report(
        result,
        output_dir=output_path,
        has_equity=has_equity,
        tqi_income_corr=tqi_income_corr,
        detailed=detailed,
        amenity_results=amenity_results if amenities else None,
    )

    # JSON results (include detailed stats)
    results_json = {
        "tqi": result.tqi,
        "coverage_score": result.coverage_score,
        "speed_score": result.speed_score,
        "reliability_mean_cv": result.reliability_mean_cv,
        "time_profile": {t: s for t, s in result.time_profile},
        "grid_points": len(grid),
        "stops": len(feed.stops),
        "detailed": {
            "transit_desert_pct": detailed.transit_desert_pct,
            "origins_with_service": detailed.n_origins_with_service,
            "reachability_rate_pct": detailed.reachability_rate_pct,
            "mean_tsr_kmh": detailed.mean_tsr,
            "median_tsr_kmh": detailed.median_tsr,
            "trips_slower_than_walking_pct": detailed.tsr_slower_than_walking_pct,
            "mean_travel_time_min": detailed.mean_travel_time_min,
            "median_travel_time_min": detailed.median_travel_time_min,
            "max_origin_reachability_pct": detailed.max_origin_reachability_pct,
        },
    }
    json_path = output_path / "tqi_results.json"
    json_path.write_text(json.dumps(results_json, indent=2))
    print(f"Results JSON: {json_path}")

    print(f"\nDone! Open {report_path} in a browser to view the full report.")


@main.command()
@click.option("--cities", default="chilliwack,victoria,kelowna",
              help="Comma-separated list of cities to compare.")
@click.option("--parallel/--no-parallel", default=True)
@click.option("--workers", default=None, type=int)
def compare(cities, parallel, workers):
    """Compare TQI across multiple BC Transit cities."""
    from tqi.config import CITY_CONFIGS, DEPARTURE_TIMES
    from tqi.gtfs.download import download_gtfs
    from tqi.gtfs.parse import load_gtfs
    from tqi.gtfs.filter import filter_to_chilliwack, _resolve_active_services, _find_reference_date
    from tqi.grid.generate import generate_grid
    from tqi.raptor.timetable import build_raptor_timetable
    from tqi.raptor.matrix import compute_matrix
    from tqi.scoring.tqi import compute_tqi

    city_list = [c.strip().lower() for c in cities.split(",")]
    results = {}

    for city_name in city_list:
        if city_name not in CITY_CONFIGS:
            print(f"Unknown city: {city_name}. Available: {list(CITY_CONFIGS.keys())}")
            continue

        cfg = CITY_CONFIGS[city_name]
        print(f"\n{'='*50}")
        print(f"  Processing: {city_name.upper()}")
        print(f"{'='*50}")

        # Download
        from pathlib import Path
        city_gtfs_dir = Path(f"data/gtfs_{city_name}")
        download_gtfs(url=cfg["url"], dest_dir=city_gtfs_dir)

        # Parse
        feed = load_gtfs(gtfs_dir=city_gtfs_dir)

        # Filter (if routes specified, otherwise use all)
        if cfg["routes"]:
            feed = filter_to_chilliwack(feed, routes=cfg["routes"])
        else:
            # Use all routes — just filter by active service day
            ref_date = _find_reference_date(feed.calendar, "wednesday")
            active = _resolve_active_services(feed.calendar, feed.calendar_dates, "wednesday", ref_date)
            trip_mask = feed.trips["service_id"].isin(active)
            feed.trips = feed.trips[trip_mask].reset_index(drop=True)
            trip_ids = set(feed.trips["trip_id"])
            feed.stop_times = feed.stop_times[feed.stop_times["trip_id"].isin(trip_ids)].reset_index(drop=True)
            used_stops = set(feed.stop_times["stop_id"])
            feed.stops = feed.stops[feed.stops["stop_id"].isin(used_stops)].reset_index(drop=True)
            print(f"All routes: {len(feed.routes)} routes, {len(feed.trips)} trips, {len(feed.stops)} stops")

        # Build timetable
        timetable = build_raptor_timetable(feed)

        # Generate grid (no boundary clipping for peer cities)
        grid = generate_grid(
            bbox_sw=cfg["bbox_sw"],
            bbox_ne=cfg["bbox_ne"],
            clip_to_boundary=False,
        )
        print(f"Grid: {len(grid)} points")

        # Stop coordinates
        stop_lats = np.array([
            feed.stops.loc[feed.stops["stop_id"] == sid, "stop_lat"].iloc[0]
            for sid in timetable.stop_ids
        ])
        stop_lons = np.array([
            feed.stops.loc[feed.stops["stop_id"] == sid, "stop_lon"].iloc[0]
            for sid in timetable.stop_ids
        ])

        # Compute matrix
        metrics = compute_matrix(
            timetable, grid, stop_lats, stop_lons,
            parallel=parallel, workers=workers,
        )

        # Score
        result = compute_tqi(metrics)
        results[city_name] = {
            "tqi": result.tqi,
            "coverage": result.coverage_score,
            "speed": result.speed_score,
            "grid_points": len(grid),
            "stops": len(feed.stops),
            "routes": len(feed.routes),
        }

        print(f"  TQI: {result.tqi:.1f} | Coverage: {result.coverage_score:.1f} | Speed: {result.speed_score:.1f}")

    # Summary table
    print(f"\n{'='*70}")
    print(f"  {'City':<15} {'TQI':>6} {'Coverage':>10} {'Speed':>8} {'Stops':>7} {'Routes':>8}")
    print(f"  {'-'*55}")
    for city, r in sorted(results.items(), key=lambda x: -x[1]["tqi"]):
        print(f"  {city:<15} {r['tqi']:>6.1f} {r['coverage']:>10.1f} {r['speed']:>8.1f} "
              f"{r['stops']:>7} {r['routes']:>8}")
    print(f"{'='*70}")

    # Save comparison JSON
    from pathlib import Path
    comp_path = Path("output/comparison.json")
    comp_path.parent.mkdir(parents=True, exist_ok=True)
    comp_path.write_text(json.dumps(results, indent=2))
    print(f"\nComparison saved: {comp_path}")
