"""Folium equity overlay map."""

import folium
import geopandas as gpd
import numpy as np
import pandas as pd


def create_equity_map(
    da_boundaries: gpd.GeoDataFrame,
    equity_data: pd.DataFrame,
    center: tuple[float, float] = (49.163, -121.940),
) -> folium.Map:
    """Create a folium map with choropleth layers for TQI and income."""
    m = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")

    # Merge equity data with boundaries
    merged = da_boundaries.merge(equity_data, on="DGUID", how="inner")

    if merged.empty:
        return m

    # TQI choropleth
    if "da_tqi" in merged.columns:
        tqi_layer = folium.FeatureGroup(name="Transit Quality (TQI)", show=True)
        _add_choropleth(tqi_layer, merged, "da_tqi", "TQI Score",
                       colormap=["#d32f2f", "#ff9800", "#4caf50"])
        tqi_layer.add_to(m)

    # Income choropleth
    income_col = None
    for col in ["median_after_tax_income", "median_income"]:
        if col in merged.columns:
            income_col = col
            break

    if income_col:
        income_layer = folium.FeatureGroup(name="Median Household Income", show=False)
        _add_choropleth(income_layer, merged, income_col, "Median Income ($)",
                       colormap=["#e8eaf6", "#3f51b5", "#1a237e"])
        income_layer.add_to(m)

    folium.LayerControl().add_to(m)
    return m


def _add_choropleth(
    layer: folium.FeatureGroup,
    gdf: gpd.GeoDataFrame,
    value_col: str,
    label: str,
    colormap: list[str],
) -> None:
    """Add coloured polygons to a feature group."""
    values = pd.to_numeric(gdf[value_col], errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return

    vmin, vmax = float(valid.min()), float(valid.max())
    if vmax == vmin:
        vmax = vmin + 1

    for _, row in gdf.iterrows():
        val = pd.to_numeric(row.get(value_col), errors="coerce")
        if pd.isna(val):
            continue

        norm = (val - vmin) / (vmax - vmin)
        # Interpolate between colormap entries
        idx = norm * (len(colormap) - 1)
        lower = int(idx)
        upper = min(lower + 1, len(colormap) - 1)
        colour = colormap[min(lower, len(colormap) - 1)]  # simplified

        popup_html = f"<b>DGUID:</b> {row.get('DGUID', 'N/A')}<br>"
        popup_html += f"<b>{label}:</b> {val:.1f}<br>"
        if "population" in row.index:
            popup_html += f"<b>Population:</b> {row.get('population', 'N/A')}<br>"

        folium.GeoJson(
            row["geometry"].__geo_interface__,
            style_function=lambda x, c=colour: {
                "fillColor": c,
                "color": "#666",
                "weight": 1,
                "fillOpacity": 0.6,
            },
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(layer)
