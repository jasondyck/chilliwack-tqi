"""Spatial heat map of per-grid-point transit quality."""

import numpy as np
import pandas as pd
import folium


# Distinct colors for up to 30 routes
ROUTE_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#fffac8", "#800000", "#aaffc3",
    "#808000", "#ffd8b1", "#000075", "#a9a9a9", "#000000",
    "#e6beff", "#1abc9c", "#7f8c8d", "#2ecc71", "#e74c3c",
    "#3498db", "#9b59b6", "#f39c12", "#1abc9c", "#d35400",
]


def create_heatmap(
    grid_points: np.ndarray,
    grid_scores: np.ndarray,
    stops_df=None,
    shapes_df=None,
    trips_df=None,
    routes_df=None,
    center: tuple[float, float] = (49.140, -121.940),
) -> folium.Map:
    """Create a folium heat map of transit quality with route overlays."""
    m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")

    # Normalise scores
    valid = grid_scores[grid_scores > 0]
    if len(valid) == 0:
        vmin, vmax = 0, 1
    else:
        vmin, vmax = float(valid.min()), float(valid.max())
    if vmax == vmin:
        vmax = vmin + 1

    # Grid point circles
    grid_group = folium.FeatureGroup(name="TQI Grid", show=True)
    for i in range(len(grid_points)):
        lat, lon = float(grid_points[i, 0]), float(grid_points[i, 1])
        score = float(grid_scores[i])
        norm = max(0.0, min(1.0, (score - vmin) / (vmax - vmin)))

        if norm < 0.5:
            r, g = 255, int(255 * norm * 2)
        else:
            r, g = int(255 * (1 - norm) * 2), 255
        colour = f"#{r:02x}{g:02x}00"
        opacity = 0.25 + 0.35 * norm

        folium.CircleMarker(
            location=[lat, lon],
            radius=2,
            color=colour,
            weight=0,
            fill=True,
            fill_color=colour,
            fill_opacity=opacity,
            popup=f"TQI: {score:.1f}",
        ).add_to(grid_group)
    grid_group.add_to(m)

    # Route geometry overlay from shapes.txt
    if shapes_df is not None and trips_df is not None and routes_df is not None:
        _add_route_lines(m, shapes_df, trips_df, routes_df)

    # Stop markers
    if stops_df is not None:
        stop_group = folium.FeatureGroup(name="Transit Stops", show=False)
        for _, stop in stops_df.iterrows():
            name = stop.get("stop_name", stop.get("stop_id", ""))
            folium.CircleMarker(
                location=[float(stop["stop_lat"]), float(stop["stop_lon"])],
                radius=2,
                color="#1a237e",
                weight=1,
                fill=True,
                fill_color="#1a237e",
                fill_opacity=0.8,
                popup=str(name),
            ).add_to(stop_group)
        stop_group.add_to(m)

    folium.LayerControl().add_to(m)
    return m


def _add_route_lines(m, shapes_df, trips_df, routes_df):
    """Draw route geometry lines from GTFS shapes.txt."""
    # Map shape_id → route names via trips
    if "shape_id" not in trips_df.columns:
        return

    route_cols = ["route_id", "route_short_name"]
    if "route_long_name" in routes_df.columns:
        route_cols.append("route_long_name")

    shape_route = trips_df[["shape_id", "route_id"]].drop_duplicates()
    shape_route = shape_route.merge(routes_df[route_cols], on="route_id")

    # Get unique shape_ids per route + long name lookup
    route_shapes: dict[str, list[str]] = {}
    route_long_names: dict[str, str] = {}
    for _, row in shape_route.iterrows():
        rname = str(row["route_short_name"])
        sid = str(row["shape_id"])
        if rname not in route_shapes:
            route_shapes[rname] = []
        if sid not in route_shapes[rname]:
            route_shapes[rname].append(sid)
        if "route_long_name" in row.index and row["route_long_name"]:
            route_long_names[rname] = str(row["route_long_name"])

    route_group = folium.FeatureGroup(name="Bus Routes", show=True)

    # Parse shape coordinates
    shapes_df = shapes_df.copy()
    shapes_df["shape_pt_lat"] = pd.to_numeric(shapes_df["shape_pt_lat"], errors="coerce")
    shapes_df["shape_pt_lon"] = pd.to_numeric(shapes_df["shape_pt_lon"], errors="coerce")
    shapes_df["shape_pt_sequence"] = pd.to_numeric(shapes_df["shape_pt_sequence"], errors="coerce")

    sorted_routes = sorted(route_shapes.keys(), key=lambda x: x.zfill(5))

    for i, rname in enumerate(sorted_routes):
        color = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        for shape_id in route_shapes[rname][:1]:  # one shape per route (first direction)
            pts = shapes_df[shapes_df["shape_id"] == shape_id].sort_values("shape_pt_sequence")
            if pts.empty:
                continue
            coords = list(zip(pts["shape_pt_lat"].values, pts["shape_pt_lon"].values))
            long = route_long_names.get(rname, "")
            popup_text = f"Route {rname} — {long}" if long else f"Route {rname}"
            folium.PolyLine(
                coords,
                color=color,
                weight=3,
                opacity=0.7,
                popup=popup_text,
            ).add_to(route_group)

    route_group.add_to(m)
