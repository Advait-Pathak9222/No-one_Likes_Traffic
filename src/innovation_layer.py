"""Innovation layer for ParkPulse — dataset-only, no external data.

Two extensions that go beyond hotspot ranking, both derived purely from the
provided enforcement records:

1. Obstruction-density heatmaps (kernel-style), overall and split by time-of-day,
   answering the Theme-1 ask for a heatmap and exposing how pressure shifts by hour.

2. A repeat-offender "circuit" network: enforcement zones (police stations) are
   linked when the SAME anonymized repeat vehicle is recorded in both. This uses the
   repeat-vehicle key — a signal most pipelines reduce to a simple count — to reveal
   that a share of offenders operate across multiple zones, which enables
   circuit-aware interception instead of single-spot enforcement.

Outputs:
    outputs/figures/violation_density_heatmap.png
    outputs/figures/violation_density_by_timeblock.png
    outputs/figures/repeat_offender_network.png
    outputs/tables/innovation_layer_summary.json
"""

from __future__ import annotations

import itertools
import json
from collections import Counter
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

from . import config


# ParkPulse dark palette (matches the dashboard branding).
BG = "#0b1220"
PANEL = "#0f1830"
INK = "#eaf1ff"
MUTED = "#9fb0c7"
ACCENT = "#2874F0"
HEAT_CMAP = "inferno"


def load_clean() -> pd.DataFrame:
    """Load the canonical clean table written by the pipeline."""
    return pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")


def _clean_vehicle_key(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA, "NA": pd.NA})
    )


def _bounds(df: pd.DataFrame, pad: float = 0.01) -> tuple[float, float, float, float]:
    lon, lat = df["lon"], df["lat"]
    return (
        float(lon.quantile(0.001)) - pad,
        float(lon.quantile(0.999)) + pad,
        float(lat.quantile(0.001)) - pad,
        float(lat.quantile(0.999)) + pad,
    )


def _density_grid(
    lon: np.ndarray,
    lat: np.ndarray,
    weight: np.ndarray,
    bounds: tuple[float, float, float, float],
    bins: int = 260,
    smooth: float = 3.2,
) -> np.ndarray:
    lon_min, lon_max, lat_min, lat_max = bounds
    grid, _, _ = np.histogram2d(
        lon, lat, bins=bins, range=[[lon_min, lon_max], [lat_min, lat_max]], weights=weight
    )
    grid = gaussian_filter(grid, sigma=smooth)
    if grid.max() > 0:
        # Mild gamma so dense cores do not wash out the mid-tier corridors.
        grid = np.power(grid / grid.max(), 0.55)
    return grid.T


def _style_geo_axis(ax: plt.Axes, bounds: tuple[float, float, float, float]) -> None:
    lon_min, lon_max, lat_min, lat_max = bounds
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    mean_lat = (lat_min + lat_max) / 2
    ax.set_aspect(1.0 / np.cos(np.radians(mean_lat)))
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def render_density_heatmap(df: pd.DataFrame, out_path) -> None:
    """Hero obstruction-density heatmap for the whole city."""
    bounds = _bounds(df)
    weight = df["record_weight"].to_numpy(dtype=float)
    grid = _density_grid(df["lon"].to_numpy(), df["lat"].to_numpy(), weight, bounds)

    fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    extent = [bounds[0], bounds[1], bounds[2], bounds[3]]
    image = ax.imshow(grid, extent=extent, origin="lower", cmap=HEAT_CMAP, interpolation="bilinear")
    _style_geo_axis(ax, bounds)

    ax.set_title(
        "Illegal-Parking Obstruction Density — Bengaluru",
        color=INK,
        fontsize=18,
        fontweight="bold",
        loc="left",
        pad=34,
    )
    ax.text(
        0.0,
        1.012,
        f"{len(df):,} enforcement records · weighted by obstruction · kernel-smoothed",
        transform=ax.transAxes,
        color=MUTED,
        fontsize=11,
    )
    cbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Relative obstruction intensity", color=MUTED, fontsize=10)
    cbar.ax.yaxis.set_tick_params(color=MUTED)
    cbar.outline.set_visible(False)
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color=MUTED)
    fig.text(
        0.012,
        0.012,
        "ParkPulse · derived only from the provided violation dataset — not live vehicle speed.",
        color=MUTED,
        fontsize=9,
    )
    fig.savefig(out_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def render_density_by_timeblock(df: pd.DataFrame, out_path) -> None:
    """Small-multiples heatmap showing how obstruction shifts by time of day."""
    bounds = _bounds(df)
    blocks = [b for b in config.TIME_BLOCK_LABELS if b in set(df["time_block"].dropna().unique())]
    blocks = blocks[:4] if len(blocks) >= 4 else blocks
    cols = 2
    rows = int(np.ceil(len(blocks) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(11.5, 5.6 * rows), dpi=200)
    fig.patch.set_facecolor(BG)
    axes = np.atleast_1d(axes).ravel()

    for idx, block in enumerate(blocks):
        ax = axes[idx]
        ax.set_facecolor(BG)
        part = df[df["time_block"] == block]
        grid = _density_grid(
            part["lon"].to_numpy(),
            part["lat"].to_numpy(),
            part["record_weight"].to_numpy(dtype=float),
            bounds,
            bins=200,
            smooth=3.0,
        )
        ax.imshow(grid, extent=[bounds[0], bounds[1], bounds[2], bounds[3]], origin="lower", cmap=HEAT_CMAP, interpolation="bilinear")
        _style_geo_axis(ax, bounds)
        pretty = str(block).replace("_", " ").title()
        ax.set_title(f"{pretty}\n{len(part):,} records", color=INK, fontsize=11.5, fontweight="bold", loc="left", pad=8)

    for j in range(len(blocks), len(axes)):
        axes[j].set_visible(False)

    fig.subplots_adjust(wspace=0.05, hspace=0.28, top=0.9)

    fig.suptitle(
        "Obstruction Density Shifts by Time of Day",
        color=INK,
        fontsize=18,
        fontweight="bold",
        x=0.012,
        ha="left",
        y=0.995,
    )
    fig.text(
        0.012,
        0.006,
        "ParkPulse · same data, split by time window — enforcement timing matters, not just location.",
        color=MUTED,
        fontsize=9,
    )
    fig.savefig(out_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def build_offender_network(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    """Build the repeat-offender zone-link network and headline statistics."""
    frame = df.copy()
    frame["vehicle_key"] = _clean_vehicle_key(frame["vehicle_number"])
    known = frame[frame["vehicle_key"].notna() & frame["station"].notna()].copy()

    vehicle_stats = (
        known.groupby("vehicle_key")
        .agg(
            record_count=("violation_id", "count"),
            station_count=("station", "nunique"),
            active_days=("created_date", "nunique"),
            time_block_count=("time_block", "nunique"),
        )
        .reset_index()
    )
    distinct_vehicles = int(len(vehicle_stats))
    repeat = vehicle_stats[vehicle_stats["record_count"] >= 2]
    chronic = vehicle_stats[vehicle_stats["record_count"] >= 3]
    multi_station = repeat[repeat["station_count"] >= 2]

    # Station node positions and repeat-offender volume.
    station_pos = (
        known.groupby("station").agg(lat=("lat", "mean"), lon=("lon", "mean"), records=("violation_id", "count")).reset_index()
    )
    repeat_keys = set(repeat["vehicle_key"])
    known["is_repeat"] = known["vehicle_key"].isin(repeat_keys)
    repeat_volume = known[known["is_repeat"]].groupby("station")["violation_id"].count()
    station_pos["repeat_records"] = station_pos["station"].map(repeat_volume).fillna(0).astype(int)

    # Edges: stations linked by shared repeat (multi-station) vehicles.
    multi_keys = set(multi_station["vehicle_key"])
    vehicle_to_stations = (
        known[known["vehicle_key"].isin(multi_keys)]
        .groupby("vehicle_key")["station"]
        .apply(lambda s: sorted(set(s)))
    )
    edge_counter: Counter[tuple[str, str]] = Counter()
    for stations in vehicle_to_stations:
        if len(stations) > 8:  # cap pathological fan-out for the pairing step
            stations = stations[:8]
        for a, b in itertools.combinations(stations, 2):
            edge_counter[(a, b)] += 1

    edges = [
        {"a": a, "b": b, "shared_vehicles": int(w)}
        for (a, b), w in edge_counter.items()
        if w >= 2
    ]
    edges.sort(key=lambda e: e["shared_vehicles"], reverse=True)

    top_pair = edges[0] if edges else None
    most_mobile = vehicle_stats.sort_values("station_count", ascending=False).iloc[0] if distinct_vehicles else None

    stats: dict[str, Any] = {
        "total_records": int(len(df)),
        "known_vehicle_records": int(len(known)),
        "known_vehicle_share": round(float(len(known) / max(len(df), 1)), 4),
        "distinct_vehicles": distinct_vehicles,
        "repeat_vehicles": int(len(repeat)),
        "repeat_vehicle_share_of_known": round(float(len(repeat) / max(distinct_vehicles, 1)), 4),
        "repeat_record_share": round(float(known["is_repeat"].mean()), 4),
        "chronic_vehicles_3plus": int(len(chronic)),
        "multi_station_vehicles": int(len(multi_station)),
        "multi_station_share_of_repeat": round(float(len(multi_station) / max(len(repeat), 1)), 4),
        "max_stations_single_vehicle": int(vehicle_stats["station_count"].max()) if distinct_vehicles else 0,
        "max_records_single_vehicle": int(vehicle_stats["record_count"].max()) if distinct_vehicles else 0,
        "max_active_days_single_vehicle": int(vehicle_stats["active_days"].max()) if distinct_vehicles else 0,
        "zone_links_2plus_shared": int(len(edges)),
        "top_offender_circuit": (
            {
                "station_a": top_pair["a"],
                "station_b": top_pair["b"],
                "shared_vehicles": top_pair["shared_vehicles"],
            }
            if top_pair
            else None
        ),
        "most_mobile_offender": (
            {
                "stations": int(most_mobile["station_count"]),
                "records": int(most_mobile["record_count"]),
                "active_days": int(most_mobile["active_days"]),
            }
            if most_mobile is not None
            else None
        ),
    }
    return station_pos, edges, stats


def render_offender_network(station_pos: pd.DataFrame, edges: list[dict[str, Any]], out_path, max_edges: int = 90) -> None:
    """Geographic network of enforcement zones linked by shared repeat offenders."""
    fig, ax = plt.subplots(figsize=(10.8, 9.4), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    pos = {row.station: (row.lon, row.lat) for row in station_pos.itertuples()}
    drawn = edges[:max_edges]
    max_w = max((e["shared_vehicles"] for e in drawn), default=1)
    cmap = plt.get_cmap("inferno")

    for edge in drawn:
        if edge["a"] not in pos or edge["b"] not in pos:
            continue
        (x1, y1), (x2, y2) = pos[edge["a"]], pos[edge["b"]]
        frac = edge["shared_vehicles"] / max_w
        ax.plot(
            [x1, x2],
            [y1, y2],
            color=cmap(0.35 + 0.6 * frac),
            linewidth=0.6 + 3.4 * frac,
            alpha=0.25 + 0.55 * frac,
            solid_capstyle="round",
            zorder=1,
        )

    sizes = 30 + 320 * (station_pos["repeat_records"] / max(station_pos["repeat_records"].max(), 1))
    ax.scatter(
        station_pos["lon"], station_pos["lat"], s=sizes, c="#5ea0ff", edgecolors="white", linewidths=0.6, zorder=3, alpha=0.95
    )

    # Label the busiest repeat-offender zones.
    for row in station_pos.sort_values("repeat_records", ascending=False).head(12).itertuples():
        ax.annotate(
            str(row.station)[:22],
            (row.lon, row.lat),
            color=INK,
            fontsize=8.5,
            fontweight="bold",
            xytext=(4, 4),
            textcoords="offset points",
            zorder=4,
        )

    mean_lat = float(station_pos["lat"].mean())
    ax.set_aspect(1.0 / np.cos(np.radians(mean_lat)))
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title(
        "Repeat-Offender Circuits Across Enforcement Zones",
        color=INK,
        fontsize=18,
        fontweight="bold",
        loc="left",
        pad=34,
    )
    ax.text(
        0.0,
        1.012,
        "Police stations linked when the same anonymized repeat vehicle offends in both",
        transform=ax.transAxes,
        color=MUTED,
        fontsize=11,
    )
    fig.text(
        0.012,
        0.012,
        "ParkPulse · node size = repeat-offender volume · link width = shared offenders · dataset-only.",
        color=MUTED,
        fontsize=9,
    )
    fig.savefig(out_path, facecolor=BG, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    config.ensure_directories()
    df = load_clean()

    heatmap_path = config.FIGURES_DIR / "violation_density_heatmap.png"
    timeblock_path = config.FIGURES_DIR / "violation_density_by_timeblock.png"
    network_path = config.FIGURES_DIR / "repeat_offender_network.png"

    render_density_heatmap(df, heatmap_path)
    render_density_by_timeblock(df, timeblock_path)
    station_pos, edges, stats = build_offender_network(df)
    render_offender_network(station_pos, edges, network_path)

    summary_path = config.TABLES_DIR / "innovation_layer_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2, ensure_ascii=False)

    print("Innovation layer written:")
    print(f"  {heatmap_path}")
    print(f"  {timeblock_path}")
    print(f"  {network_path}")
    print(f"  {summary_path}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
