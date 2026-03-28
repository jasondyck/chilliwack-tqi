"""Matplotlib charts for TQI analysis — modern, cohesive styling."""

import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np

# ── Global style ──
FONT_FAMILY = "sans-serif"
BG_COLOR = "#ffffff"
GRID_COLOR = "#e8e8e8"
TEXT_COLOR = "#2d2d2d"
TEXT_MUTED = "#888888"
ACCENT = "#3b82f6"      # blue
ACCENT2 = "#10b981"     # green
ACCENT3 = "#f59e0b"     # amber
ACCENT4 = "#8b5cf6"     # purple
DANGER = "#ef4444"

def _apply_style(ax, fig, title="", subtitle=""):
    """Apply consistent modern styling to an axes."""
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.grid(True, alpha=0.4, color=GRID_COLOR, linewidth=0.5)
    if title:
        ax.set_title(title, fontsize=13, fontweight="600", color=TEXT_COLOR,
                      pad=12, loc="left")
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9,
                color=TEXT_MUTED, va="bottom")


def plot_time_profile(
    time_labels: list[str],
    tqi_scores: list[float],
) -> plt.Figure:
    """Line chart of TQI by time of day."""
    fig, ax = plt.subplots(figsize=(13, 5))
    x = range(len(time_labels))

    # Gradient fill
    ax.fill_between(x, tqi_scores, alpha=0.08, color=ACCENT)
    ax.plot(x, tqi_scores, color=ACCENT, linewidth=2.5, solid_capstyle="round")
    ax.scatter(x, tqi_scores, color=ACCENT, s=12, zorder=5, edgecolors="white", linewidth=0.5)

    # Peak hour shading
    for start_h, end_h, label, c in [(7, 9, "AM Peak", "#fef3c7"), (16, 18, "PM Peak", "#fef3c7")]:
        s_idx = (start_h - 6) * 4
        e_idx = (end_h - 6) * 4
        if 0 <= s_idx < len(time_labels) and e_idx <= len(time_labels):
            ax.axvspan(s_idx, e_idx, alpha=0.5, color=c, label=label, zorder=0)

    ax.set_ylim(bottom=0)
    tick_pos = list(range(0, len(time_labels), 4))
    ax.set_xticks(tick_pos)
    ax.set_xticklabels([time_labels[i] for i in tick_pos], rotation=0, fontsize=9)
    ax.set_ylabel("TQI Score", fontsize=10)
    ax.legend(loc="upper right", framealpha=0.9, fontsize=8, edgecolor=GRID_COLOR)
    _apply_style(ax, fig, "Time-of-Day Profile")
    fig.tight_layout()
    return fig


def plot_score_breakdown(
    coverage: float,
    speed: float,
    tqi: float,
) -> plt.Figure:
    """Horizontal gauge-style bar chart for score breakdown."""
    fig, axes = plt.subplots(3, 1, figsize=(10, 4.5), gridspec_kw={"hspace": 0.6})

    items = [
        ("Overall TQI", tqi, ACCENT3),
        ("Coverage", coverage, ACCENT),
        ("Speed", speed, ACCENT2),
    ]

    for ax, (label, val, color) in zip(axes, items):
        # Background track
        ax.barh(0, 100, height=0.6, color="#f1f5f9", zorder=1)
        # Value bar
        ax.barh(0, val, height=0.6, color=color, zorder=2,
                left=0, alpha=0.85)
        # Score label
        ax.text(max(val + 1.5, 8), 0, f"{val:.1f}",
                va="center", fontsize=14, fontweight="700", color=TEXT_COLOR, zorder=3)
        ax.text(-1, 0, label, va="center", ha="right", fontsize=10,
                fontweight="500", color=TEXT_COLOR)
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(axis="x", labelsize=8, colors=TEXT_MUTED)
        ax.set_facecolor(BG_COLOR)
        ax.grid(False)

    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle("Score Breakdown", fontsize=13, fontweight="600",
                 color=TEXT_COLOR, x=0.12, ha="left", y=0.98)
    fig.subplots_adjust(left=0.18)
    return fig


def plot_reliability_histogram(cv_values: list[float]) -> plt.Figure:
    """Histogram of travel time coefficient of variation."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    valid = [v for v in cv_values if v > 0]
    if valid:
        n, bins, patches = ax.hist(valid, bins=25, color=ACCENT4, edgecolor="white",
                                    alpha=0.8, linewidth=0.5)
        # Gradient color by position
        for i, p in enumerate(patches):
            p.set_facecolor(plt.cm.Purples(0.3 + 0.5 * i / len(patches)))

    ax.set_xlabel("Coefficient of Variation", fontsize=10)
    ax.set_ylabel("Grid Points", fontsize=10)
    _apply_style(ax, fig, "Temporal Reliability",
                 "Lower CV = more predictable trip times")
    fig.tight_layout()
    return fig


def plot_tsr_distribution(
    slower_pct: float,
    band_5_10_pct: float,
    band_10_20_pct: float,
    band_20_plus_pct: float,
    mean_tsr: float,
    median_tsr: float,
) -> plt.Figure:
    """Stacked horizontal bar showing speed band breakdown."""
    fig, ax = plt.subplots(figsize=(12, 2.8))

    categories = ["< 5 km/h\nSlower than walking",
                  "5-10 km/h\nMarginal",
                  "10-20 km/h\nUseful",
                  "20+ km/h\nCompetitive"]
    values = [slower_pct, band_5_10_pct, band_10_20_pct, band_20_plus_pct]
    colours = [DANGER, ACCENT3, ACCENT2, "#059669"]

    # Single stacked horizontal bar
    left = 0
    for val, col, cat in zip(values, colours, categories):
        if val > 0:
            bar = ax.barh(0, val, left=left, color=col, height=0.5, edgecolor="white", linewidth=0.5)
            if val > 5:
                ax.text(left + val / 2, 0, f"{val:.0f}%",
                        ha="center", va="center", fontsize=10, fontweight="700",
                        color="white",
                        path_effects=[pe.withStroke(linewidth=2, foreground=col)])
            left += val

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, 0.6)
    ax.set_yticks([])
    ax.set_xlabel("% of Reachable Trips", fontsize=10)

    # Legend below
    legend_y = -0.55
    legend_x = 0
    for col, cat in zip(colours, categories):
        short = cat.split("\n")[1] if "\n" in cat else cat
        ax.plot(legend_x, legend_y, "s", color=col, markersize=8,
                transform=ax.transData, clip_on=False)
        ax.text(legend_x + 2, legend_y, short, fontsize=8, va="center",
                color=TEXT_COLOR, transform=ax.transData, clip_on=False)
        legend_x += 25

    _apply_style(ax, fig,
                 f"Transit Speed Distribution",
                 f"Mean {mean_tsr:.1f} km/h | Median {median_tsr:.1f} km/h | Walking = 5 km/h")
    ax.spines["left"].set_visible(False)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.3)
    return fig


def plot_travel_time_distribution(percentiles: dict[int, float]) -> plt.Figure:
    """Lollipop chart of travel time percentiles."""
    if not percentiles:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No reachable trips", ha="center", va="center",
                fontsize=14, color=TEXT_MUTED)
        ax.set_facecolor(BG_COLOR)
        return fig

    fig, ax = plt.subplots(figsize=(10, 4))
    pcts = sorted(percentiles.keys())
    labels = [f"P{p}" for p in pcts]
    values = [percentiles[p] for p in pcts]

    # Color gradient from green (fast) to red (slow)
    colors = [plt.cm.RdYlGn(1.0 - i / (len(values) - 1)) if len(values) > 1 else ACCENT
              for i in range(len(values))]

    # Lollipop stems
    for i, (lbl, val, col) in enumerate(zip(labels, values, colors)):
        ax.plot([i, i], [0, val], color=col, linewidth=2.5, solid_capstyle="round")
        ax.scatter(i, val, color=col, s=80, zorder=5, edgecolors="white", linewidth=1.5)
        ax.text(i, val + 1.5, f"{val:.0f}", ha="center", fontsize=10,
                fontweight="600", color=TEXT_COLOR)

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Minutes", fontsize=10)
    ax.set_ylim(bottom=0)
    _apply_style(ax, fig, "Travel Time Percentiles",
                 "How long reachable transit trips take")
    fig.tight_layout()
    return fig


def plot_route_los(route_los_list: list) -> plt.Figure:
    """Horizontal bar chart of routes colored by TCQSM LOS grade."""
    if not route_los_list:
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.text(0.5, 0.5, "No route data", ha="center", va="center", fontsize=14)
        return fig

    los_colors = {
        "A": "#059669", "B": "#10b981", "C": "#84cc16",
        "D": ACCENT3, "E": "#f97316", "F": DANGER,
    }

    labels = []
    for r in route_los_list:
        if r.route_long_name:
            labels.append(f"{r.route_name} {r.route_long_name}")
        else:
            labels.append(f"Route {r.route_name}")

    headways = [min(r.median_headway_min, 120) for r in route_los_list]
    grades = [r.los_grade for r in route_los_list]
    colours = [los_colors.get(g, "#999") for g in grades]

    fig, ax = plt.subplots(figsize=(13, max(3.5, len(labels) * 0.45)))
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, headways, color=colours, height=0.65,
                   edgecolor="white", linewidth=0.5)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Median Headway (minutes)", fontsize=10)
    ax.invert_yaxis()

    for bar, grade, hw in zip(bars, grades, headways):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"LOS {grade}", va="center", fontsize=9, fontweight="700",
                color=los_colors.get(grade, TEXT_COLOR))

    # LOS boundary reference lines
    for threshold, g in [(10, "A/B"), (20, "C/D"), (30, "D/E"), (60, "E/F")]:
        if threshold < max(headways) * 1.2:
            ax.axvline(x=threshold, color=GRID_COLOR, linestyle="--", linewidth=0.8, zorder=0)
            ax.text(threshold, -0.7, f"{threshold}m", ha="center", fontsize=7,
                    color=TEXT_MUTED, clip_on=False)

    ax.set_xlim(0, max(headways) * 1.2)
    _apply_style(ax, fig, "Route Service Frequency (TCQSM)")
    ax.grid(True, axis="x", alpha=0.3, color=GRID_COLOR)
    ax.grid(False, axis="y")
    fig.tight_layout()
    return fig


def plot_ptal_distribution(ptal_dist: dict) -> plt.Figure:
    """Bar chart of PTAL grade distribution across grid points."""
    if not ptal_dist:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No PTAL data", ha="center", va="center", fontsize=14)
        return fig

    grades = ["1a", "1b", "2", "3", "4", "5", "6a", "6b"]
    counts = [ptal_dist.get(g, 0) for g in grades]
    desc = ["Extremely\nPoor", "Very\nPoor", "Poor", "Moderate",
            "Good", "Very\nGood", "Excellent", "Excellent+"]
    grade_colors = [DANGER, "#f97316", ACCENT3, "#eab308",
                    "#84cc16", ACCENT2, "#059669", "#047857"]

    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(range(len(grades)), counts, color=grade_colors,
                  edgecolor="white", linewidth=0.5, width=0.7)

    # Count labels on bars
    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(counts) * 0.01,
                    f"{count:,}", ha="center", va="bottom", fontsize=10,
                    fontweight="600", color=TEXT_COLOR)

    # Two-line x labels: grade + description
    ax.set_xticks(range(len(grades)))
    combined = [f"{g}\n{d}" for g, d in zip(grades, desc)]
    ax.set_xticklabels(combined, fontsize=8, linespacing=1.4)
    ax.set_ylabel("Grid Points", fontsize=10)
    _apply_style(ax, fig, "PTAL Accessibility Distribution",
                 "Transport for London methodology applied to Chilliwack")
    fig.tight_layout()
    return fig


def fig_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64-encoded PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
