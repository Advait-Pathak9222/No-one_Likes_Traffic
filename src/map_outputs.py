"""Generate lightweight Folium map artifacts."""

from __future__ import annotations

import pandas as pd

from . import config


def _import_folium():
    import folium
    from folium.plugins import HeatMap

    return folium, HeatMap


def generate_maps() -> None:
    """Generate HTML maps for raw density and action-priority hotspots."""
    config.ensure_directories()
    folium, HeatMap = _import_folium()

    clean_cols = ["grid_id_250m", "lat", "lon", "violation_id"]
    df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet", columns=clean_cols)
    grid = (
        df.groupby("grid_id_250m")
        .agg(lat=("lat", "mean"), lon=("lon", "mean"), count=("violation_id", "count"))
        .reset_index()
    )
    center = [float(grid["lat"].mean()), float(grid["lon"].mean())]

    raw_map = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")
    heat_data = grid[["lat", "lon", "count"]].dropna().values.tolist()
    HeatMap(heat_data, radius=13, blur=18, min_opacity=0.25, max_zoom=15).add_to(raw_map)
    raw_map.save(config.MAPS_DIR / "raw_violation_heatmap.html")

    tori = pd.read_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet")
    top = tori.sort_values("final_tori", ascending=False).head(150)
    tori_map = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")
    for _, row in top.iterrows():
        score = float(row["final_tori_0_100"])
        radius = 4 + score / 8
        color = "#FB641B" if score >= 90 else "#2874F0"
        popup = (
            f"<b>{row['station']}</b><br>"
            f"Zone: {row['zone_name']}<br>"
            f"Time: {row['time_block']}<br>"
            f"Violations: {int(row['violation_count'])}<br>"
            f"TORI: {score:.2f}<br>"
            f"Confidence: {row['confidence_band']}"
        )
        folium.CircleMarker(
            location=[row["centroid_lat"], row["centroid_lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.65,
            popup=popup,
        ).add_to(tori_map)
    tori_map.save(config.MAPS_DIR / "tori_priority_hotspots.html")


def main() -> None:
    generate_maps()
    print(f"Wrote maps to {config.MAPS_DIR}")


if __name__ == "__main__":
    main()
