"""Publication-style obstruction-density heatmaps for ParkPulse (dataset-only).

Generates two figures from the cleaned violation records — no external data:

    heatmaps/heatmap_city.png          city-wide obstruction density
    heatmaps/heatmap_by_timeofday.png  2x2 panel by time-of-day window (shared scale)

White background, lat/lon axes, titles and a labelled colorbar (proper graphs),
weighted by obstruction and kernel-smoothed.

Run:  python -m src.build_heatmaps      (or:  python src/build_heatmaps.py)
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from matplotlib.ticker import FuncFormatter, MaxNLocator
from scipy.ndimage import gaussian_filter

try:
    from . import config
except ImportError:  # allow running as a plain script
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "heatmaps"
CMAP = "inferno"
MIN_RECORDS_PER_PANEL = 20000  # skip near-empty time windows
TIME_LABELS = {
    "00-06_night_early_morning": "Night / Early Morning  (00–06)",
    "06-09_morning_buildup": "Morning Build-up  (06–09)",
    "09-12_commercial_morning_peak": "Commercial Morning Peak  (09–12)",
    "12-15_market_midday_pressure": "Market Midday Pressure  (12–15)",
}

_LON_FMT = FuncFormatter(lambda v, _: f"{v:.2f}°E")
_LAT_FMT = FuncFormatter(lambda v, _: f"{v:.2f}°N")


def load_clean() -> pd.DataFrame:
    return pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")


def _bounds(lon: np.ndarray, lat: np.ndarray) -> tuple[float, float, float, float]:
    return (
        np.quantile(lon, 0.003) - 0.006,
        np.quantile(lon, 0.997) + 0.006,
        np.quantile(lat, 0.003) - 0.006,
        np.quantile(lat, 0.997) + 0.006,
    )


def _density(lo, la, wt, bounds, bins=420, smooth=7.5) -> np.ndarray:
    x0, x1, y0, y1 = bounds
    grid, _, _ = np.histogram2d(lo, la, bins=bins, range=[[x0, x1], [y0, y1]], weights=wt)
    return gaussian_filter(grid, sigma=smooth).T


def _style_axis(ax, bounds, aspect, xlab=True, ylab=True):
    x0, x1, y0, y1 = bounds
    ax.set_aspect(aspect)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.xaxis.set_major_formatter(_LON_FMT)
    ax.yaxis.set_major_formatter(_LAT_FMT)
    ax.tick_params(labelsize=8)
    if xlab:
        ax.set_xlabel("Longitude", fontsize=9)
    else:
        ax.set_xticklabels([])
    if ylab:
        ax.set_ylabel("Latitude", fontsize=9)
    else:
        ax.set_yticklabels([])


def render_city(df: pd.DataFrame, bounds, aspect, out_path) -> None:
    d = _density(df["lon"].to_numpy(float), df["lat"].to_numpy(float), df["record_weight"].to_numpy(float), bounds)
    ref = np.percentile(d[d > 0], 99.5)
    dn = np.clip(d / ref, 0, 1) if ref > 0 else d
    fig, ax = plt.subplots(figsize=(7.4, 8.4), dpi=300)
    fig.patch.set_facecolor("white")
    im = ax.imshow(dn, extent=list(bounds), origin="lower", cmap=CMAP,
                   norm=PowerNorm(gamma=0.5, vmin=0, vmax=1), interpolation="bicubic")
    _style_axis(ax, bounds, aspect)
    ax.set_title("Illegal-Parking Obstruction Density — Bengaluru", fontsize=14, fontweight="bold", pad=10, loc="left")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label("Relative obstruction density", fontsize=9)
    cb.ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(out_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def render_by_timeofday(df: pd.DataFrame, bounds, aspect, out_path) -> None:
    present = set(df["time_block"].dropna().unique())
    blocks = [b for b in config.TIME_BLOCK_LABELS if b in TIME_LABELS and b in present
              and len(df[df.time_block == b]) >= MIN_RECORDS_PER_PANEL]
    dens = [_density(df[df.time_block == b]["lon"].to_numpy(float),
                     df[df.time_block == b]["lat"].to_numpy(float),
                     df[df.time_block == b]["record_weight"].to_numpy(float), bounds, smooth=8.0)
            for b in blocks]
    ref = max(np.percentile(g[g > 0], 99.5) for g in dens)  # shared scale -> comparable panels
    fig, axes = plt.subplots(2, 2, figsize=(11, 11.6), dpi=300)
    fig.patch.set_facecolor("white")
    axes = axes.ravel()
    im = None
    for i, (b, g) in enumerate(zip(blocks, dens)):
        ax = axes[i]
        gn = np.clip(g / ref, 0, 1)
        im = ax.imshow(gn, extent=list(bounds), origin="lower", cmap=CMAP,
                       norm=PowerNorm(gamma=0.5, vmin=0, vmax=1), interpolation="bicubic")
        _style_axis(ax, bounds, aspect, xlab=(i >= 2), ylab=(i % 2 == 0))
        ax.set_title(TIME_LABELS[b], fontsize=11, fontweight="bold", pad=6, loc="left")
    for j in range(len(blocks), len(axes)):
        axes[j].set_visible(False)
    fig.suptitle("Obstruction Density by Time of Day — Bengaluru", fontsize=15, fontweight="bold", x=0.02, ha="left", y=0.98)
    fig.subplots_adjust(left=0.06, right=0.88, top=0.92, bottom=0.06, wspace=0.08, hspace=0.16)
    cax = fig.add_axes([0.9, 0.12, 0.02, 0.74])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("Relative obstruction density (shared scale)", fontsize=10)
    cb.ax.tick_params(labelsize=8)
    fig.savefig(out_path, facecolor="white")
    plt.close(fig)


def main() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "axes.edgecolor": "#33415c", "axes.linewidth": 0.8,
        "text.color": "#0f172a", "axes.labelcolor": "#0f172a", "xtick.color": "#475569", "ytick.color": "#475569",
    })
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_clean()
    lon, lat = df["lon"].to_numpy(float), df["lat"].to_numpy(float)
    bounds = _bounds(lon, lat)
    aspect = 1.0 / np.cos(np.radians((bounds[2] + bounds[3]) / 2))
    render_city(df, bounds, aspect, OUT_DIR / "heatmap_city.png")
    render_by_timeofday(df, bounds, aspect, OUT_DIR / "heatmap_by_timeofday.png")
    print(f"Heatmaps written to {OUT_DIR}/")
    for f in sorted(os.listdir(OUT_DIR)):
        print("  ", f)


if __name__ == "__main__":
    main()
