"""Generate Google-Maps-style obstruction-risk overlays.

The Theme 1 dataset does not contain live traffic speed, vehicle probe traces,
or official road centerline geometry. What it does contain is enough to build a
traffic-style *risk overlay*: road/corridor segments inferred from repeated
hotspot coordinates, colored by illegal-parking obstruction risk.

Color semantics:

- blue: low obstruction risk, likely free-flow from the parking perspective;
- yellow: moderate obstruction risk;
- red: severe obstruction risk, likely carriageway capacity loss.

This should be presented as "parking obstruction risk", not live congestion.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

import folium
import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from folium.plugins import Fullscreen

from . import config
from .corridor_intelligence import classify_bottleneck, infer_corridor_name
from .roadspace_intelligence import (
    build_roadspace_intelligence,
    clean_value,
    write_frontend_json,
)


RISK_COLORS = {
    "low": "#2874F0",
    "moderate": "#F4C430",
    "severe": "#D93025",
}

RISK_LABELS = {
    "low": "Blue: low obstruction risk",
    "moderate": "Yellow: moderate obstruction risk",
    "severe": "Red: severe obstruction risk",
}


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance between two WGS84 points in meters."""
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def risk_band(score: float) -> str:
    """Map obstruction risk score to blue/yellow/red band."""
    if score < 50:
        return "low"
    if score < 75:
        return "moderate"
    return "severe"


def aggregate_corridor_points(roadspace: pd.DataFrame) -> pd.DataFrame:
    """Aggregate repeated time-window rows into corridor points."""
    frame = roadspace.copy()
    frame["corridor_name"] = frame.apply(infer_corridor_name, axis=1)
    frame["lat_key"] = frame["centroid_lat"].round(5)
    frame["lon_key"] = frame["centroid_lon"].round(5)

    point = (
        frame.groupby(["station", "corridor_name", "lat_key", "lon_key"], dropna=False)
        .agg(
            centroid_lat=("centroid_lat", "mean"),
            centroid_lon=("centroid_lon", "mean"),
            max_obstruction_score=("lane_obstruction_proxy_0_100", "max"),
            mean_obstruction_score=("lane_obstruction_proxy_0_100", "mean"),
            max_tori=("final_tori_0_100", "max"),
            total_violations=("violation_count", "sum"),
            top_time_window=("time_window_readable", lambda s: s.mode().iloc[0] if len(s.mode()) else "All"),
            lane_context=("lane_context", lambda s: s.mode().iloc[0] if len(s.mode()) else "Road segment"),
            dominant_issue=("dominant_lane_issue", lambda s: s.mode().iloc[0] if len(s.mode()) else "Parking obstruction risk"),
            recommended_action=("recommended_action", lambda s: s.mode().iloc[0] if len(s.mode()) else "Targeted patrol"),
        )
        .reset_index()
    )
    point["point_id"] = np.arange(len(point))
    return point


def _sort_points_along_axis(group: pd.DataFrame) -> pd.DataFrame:
    """Sort corridor points along the dominant spatial axis."""
    lon_range = float(group["centroid_lon"].max() - group["centroid_lon"].min())
    lat_range = float(group["centroid_lat"].max() - group["centroid_lat"].min())
    sort_col = "centroid_lon" if lon_range >= lat_range else "centroid_lat"
    return group.sort_values(sort_col)


def _local_principal_curve(points: np.ndarray, window: int = 4, smooth_passes: int = 2) -> np.ndarray:
    """Approximate a principal curve for ordered points via local PCA projection.

    Each point is projected onto a line fitted to its local neighbourhood, then
    the pass is repeated. Unlike a single global axis, this de-noises the trace
    while preserving large-scale curvature, so the inferred corridor bends with
    the point cloud instead of collapsing to one straight chord. It is still an
    inference from violation coordinates, not a surveyed road centerline.
    """
    pts = np.asarray(points, dtype=float).copy()
    count = len(pts)
    if count < 3:
        return pts
    for _ in range(smooth_passes):
        updated = pts.copy()
        for index in range(count):
            low = max(0, index - window)
            high = min(count, index + window + 1)
            local = pts[low:high]
            local_center = local.mean(axis=0)
            shifted_local = local - local_center
            try:
                _, _, vh = np.linalg.svd(shifted_local, full_matrices=False)
            except np.linalg.LinAlgError:
                continue
            axis = vh[0]
            offset = (pts[index] - local_center) @ axis
            updated[index] = local_center + offset * axis
        pts = updated
    return pts


def _snap_group_to_centerline(group: pd.DataFrame) -> pd.DataFrame:
    """Project corridor points onto a data-inferred local centerline.

    We do not have surveyed road centerline GIS, so we infer a stable directional
    trace from the spatial distribution of repeated violations belonging to the
    same corridor, then smooth it into a gently curving centerline.
    """
    if len(group) < 3:
        out = group.copy()
        out["snap_lat"] = out["centroid_lat"]
        out["snap_lon"] = out["centroid_lon"]
        out["snap_method"] = "raw-hotspot-points"
        out["snap_progress"] = np.arange(len(out), dtype=float)
        return out

    out = group.copy()
    coords = out[["centroid_lon", "centroid_lat"]].to_numpy(dtype=float)
    center = coords.mean(axis=0)
    shifted = coords - center
    _, _, vh = np.linalg.svd(shifted, full_matrices=False)
    axis = vh[0]
    progress = shifted @ axis
    order = np.argsort(progress)

    out = out.iloc[order].reset_index(drop=True)
    ordered_coords = coords[order]
    smoothed = _local_principal_curve(ordered_coords)
    out["snap_lon"] = smoothed[:, 0]
    out["snap_lat"] = smoothed[:, 1]
    out["snap_method"] = "data-inferred-corridor-centerline"
    out["snap_progress"] = progress[order]
    return out


def build_congestion_segments(
    roadspace: pd.DataFrame,
    max_segment_meters: float = 900.0,
    max_segments: int = 3000,
) -> pd.DataFrame:
    """Build colored corridor segments from hotspot points."""
    points = aggregate_corridor_points(roadspace)
    segments: list[dict[str, Any]] = []
    seen_pairs: set[tuple[int, int]] = set()

    def add_segments(group: pd.DataFrame, source: str) -> None:
        ordered = _snap_group_to_centerline(group)
        if len(ordered) < 2:
            return
        rows = list(ordered.itertuples(index=False))
        for first, second in zip(rows, rows[1:]):
            pair = tuple(sorted((int(first.point_id), int(second.point_id))))
            if pair in seen_pairs:
                continue
            distance = haversine_meters(
                float(first.snap_lat),
                float(first.snap_lon),
                float(second.snap_lat),
                float(second.snap_lon),
            )
            if distance < 20 or distance > max_segment_meters:
                continue
            score = float(max(first.max_obstruction_score, second.max_obstruction_score))
            band = risk_band(score)
            seen_pairs.add(pair)
            segments.append(
                {
                    "segment_id": f"seg_{len(segments) + 1:05d}",
                    "station": first.station,
                    "corridor_name": first.corridor_name,
                    "source": source,
                    "snap_method": first.snap_method,
                    "start_lat": float(first.snap_lat),
                    "start_lon": float(first.snap_lon),
                    "end_lat": float(second.snap_lat),
                    "end_lon": float(second.snap_lon),
                    "distance_meters": distance,
                    "obstruction_score": score,
                    "risk_band": band,
                    "risk_label": RISK_LABELS[band],
                    "color": RISK_COLORS[band],
                    "max_tori": float(max(first.max_tori, second.max_tori)),
                    "total_violations": int(first.total_violations + second.total_violations),
                    "top_time_window": first.top_time_window,
                    "lane_context": first.lane_context,
                    "dominant_issue": first.dominant_issue,
                    "recommended_action": first.recommended_action,
                    "bottleneck_class": classify_bottleneck(
                        first.lane_context, first.dominant_issue, first.recommended_action
                    ),
                }
            )

    for _, group in points.groupby(["station", "corridor_name"], dropna=False):
        add_segments(group, "same-road-corridor")

    if len(segments) < 800:
        for _, group in points.groupby(["station", "lane_context"], dropna=False):
            add_segments(group, "same-station-lane-context")

    out = pd.DataFrame(segments)
    if out.empty:
        return out
    out["priority"] = out["obstruction_score"] * np.log1p(out["total_violations"])
    out = out.sort_values(["priority", "distance_meters"], ascending=[False, True])

    # Preserve the Google-Maps-like visual language. A pure top-N sample would
    # keep mostly red corridors and hide the blue/yellow contrast.
    budgets = {
        "severe": int(max_segments * 0.45),
        "moderate": int(max_segments * 0.35),
        "low": max_segments - int(max_segments * 0.45) - int(max_segments * 0.35),
    }
    selected_parts = []
    selected_index: set[int] = set()
    for band, budget in budgets.items():
        part = out[out["risk_band"] == band].head(budget)
        selected_parts.append(part)
        selected_index.update(part.index.tolist())

    remaining_slots = max_segments - sum(len(part) for part in selected_parts)
    if remaining_slots > 0:
        selected_parts.append(out[~out.index.isin(selected_index)].head(remaining_slots))

    return pd.concat(selected_parts, ignore_index=True).sort_values(
        ["risk_band", "priority"], ascending=[False, False]
    ).reset_index(drop=True)


def segments_to_geojson(segments: pd.DataFrame) -> dict[str, Any]:
    """Convert segment table to LineString GeoJSON."""
    features = []
    for row in segments.itertuples(index=False):
        properties = {
            "segment_id": row.segment_id,
            "station": row.station,
            "corridor_name": row.corridor_name,
            "source": row.source,
            "snap_method": getattr(row, "snap_method", None),
            "distance_meters": row.distance_meters,
            "obstruction_score": row.obstruction_score,
            "risk_band": row.risk_band,
            "risk_label": row.risk_label,
            "color": row.color,
            "max_tori": row.max_tori,
            "total_violations": row.total_violations,
            "top_time_window": row.top_time_window,
            "lane_context": row.lane_context,
            "dominant_issue": row.dominant_issue,
            "bottleneck_class": getattr(row, "bottleneck_class", None),
            "recommended_action": row.recommended_action,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [clean_value(row.start_lon), clean_value(row.start_lat)],
                        [clean_value(row.end_lon), clean_value(row.end_lat)],
                    ],
                },
                "properties": {key: clean_value(value) for key, value in properties.items()},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def export_segment_artifacts(segments: pd.DataFrame) -> None:
    """Write CSV and GeoJSON artifacts for the overlay."""
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    segments.to_csv(config.TABLES_DIR / "congestion_risk_segments.csv", index=False)
    write_frontend_json("congestion_risk_segments.geojson", segments_to_geojson(segments))


def generate_congestion_overlay_map(segments: pd.DataFrame, output_path: Path) -> None:
    """Generate high-quality interactive HTML overlay."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    center = [
        float(pd.concat([segments["start_lat"], segments["end_lat"]]).median()),
        float(pd.concat([segments["start_lon"], segments["end_lon"]]).median()),
    ]
    fmap = folium.Map(
        location=center,
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )
    Fullscreen(position="topright").add_to(fmap)

    groups = {
        "low": folium.FeatureGroup(name="Blue: low parking obstruction risk", show=True),
        "moderate": folium.FeatureGroup(name="Yellow: moderate parking obstruction risk", show=True),
        "severe": folium.FeatureGroup(name="Red: severe parking obstruction risk", show=True),
    }
    for group in groups.values():
        group.add_to(fmap)

    for row in segments.itertuples(index=False):
        popup_html = f"""
        <div style="width: 340px; font-family: Inter, Arial, sans-serif;">
          <h3 style="margin:0 0 6px;">{html.escape(str(row.corridor_name))}</h3>
          <b>Station:</b> {html.escape(str(row.station))}<br/>
          <b>Risk:</b> {html.escape(str(row.risk_label))}<br/>
          <b>Obstruction score:</b> {row.obstruction_score:.1f}<br/>
          <b>Window:</b> {html.escape(str(row.top_time_window))}<br/>
          <b>Lane context:</b> {html.escape(str(row.lane_context))}<br/>
          <b>Reason:</b> {html.escape(str(row.dominant_issue))}<br/>
          <b>Plan:</b> {html.escape(str(row.recommended_action))}<br/>
          <small>Generated from violation hotspot coordinates; not live vehicle-speed data.</small>
        </div>
        """
        folium.PolyLine(
            locations=[[row.start_lat, row.start_lon], [row.end_lat, row.end_lon]],
            color=row.color,
            weight=3.0 + min(5.0, row.obstruction_score / 22.0),
            opacity=0.82,
            tooltip=f"{row.risk_label} | {row.corridor_name} | {row.obstruction_score:.1f}",
            popup=folium.Popup(popup_html, max_width=390),
        ).add_to(groups[row.risk_band])

    legend_html = """
    <div style="
      position: fixed; bottom: 28px; left: 28px; z-index: 9999;
      background: white; padding: 14px 16px; border-radius: 14px;
      border: 1px solid #d8e3f2; box-shadow: 0 10px 28px rgba(0,0,0,.16);
      font-family: Inter, Arial, sans-serif; font-size: 13px;">
      <b>ParkPulse Obstruction Overlay</b><br/>
      <span style="color:#2874F0;font-weight:800;">━</span> Blue: low obstruction risk<br/>
      <span style="color:#F4C430;font-weight:800;">━</span> Yellow: moderate obstruction risk<br/>
      <span style="color:#D93025;font-weight:800;">━</span> Red: severe obstruction risk<br/>
      <small>Modelled estimate from illegal-parking hotspot data, not live speed.</small>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl().add_to(fmap)
    fmap.save(str(output_path))


def generate_congestion_overlay_png(segments: pd.DataFrame, output_path: Path) -> None:
    """Generate static PNG suitable for reports/decks."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.5, 10.0), dpi=180)
    ax.set_facecolor("#f4f7fb")
    fig.patch.set_facecolor("#f4f7fb")

    for band in ["low", "moderate", "severe"]:
        subset = segments[segments["risk_band"] == band]
        for row in subset.itertuples(index=False):
            ax.plot(
                [row.start_lon, row.end_lon],
                [row.start_lat, row.end_lat],
                color=RISK_COLORS[band],
                linewidth=1.0 + min(4.0, row.obstruction_score / 25.0),
                alpha=0.72 if band != "low" else 0.55,
                solid_capstyle="round",
            )

    severe = segments[segments["risk_band"] == "severe"].head(180)
    ax.scatter(
        pd.concat([severe["start_lon"], severe["end_lon"]]),
        pd.concat([severe["start_lat"], severe["end_lat"]]),
        s=9,
        color=RISK_COLORS["severe"],
        alpha=0.35,
        edgecolors="none",
    )

    handles = [
        plt.Line2D([0], [0], color=RISK_COLORS["low"], lw=5, label="Blue: low obstruction risk"),
        plt.Line2D([0], [0], color=RISK_COLORS["moderate"], lw=5, label="Yellow: moderate obstruction risk"),
        plt.Line2D([0], [0], color=RISK_COLORS["severe"], lw=5, label="Red: severe obstruction risk"),
    ]
    ax.legend(handles=handles, loc="lower left", frameon=True, facecolor="white", framealpha=0.96)
    ax.set_title(
        "ParkPulse Bengaluru: Parking Obstruction Risk Overlay",
        fontsize=18,
        fontweight="bold",
        color="#172337",
        pad=16,
    )
    ax.text(
        0.01,
        0.98,
        "Generated from illegal-parking hotspot coordinates and lane-obstruction estimate. Not live speed data.",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=10,
        color="#5f6c7b",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": "#d8e3f2"},
    )
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def build_and_export_congestion_overlay(
    clean_df: pd.DataFrame,
    tori: pd.DataFrame,
    plan: pd.DataFrame,
) -> pd.DataFrame:
    """Build full obstruction overlay and write all artifacts."""
    roadspace = build_roadspace_intelligence(clean_df, tori, plan, top_n=len(tori))
    segments = build_congestion_segments(roadspace)
    export_segment_artifacts(segments)
    generate_congestion_overlay_map(segments, config.MAPS_DIR / "congestion_risk_overlay.html")
    generate_congestion_overlay_png(segments, config.FIGURES_DIR / "congestion_risk_overlay.png")
    return segments


def main() -> None:
    """CLI entry point."""
    config.ensure_directories()
    clean_df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")
    tori = pd.read_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet")
    plan = pd.read_csv(config.TABLES_DIR / "daily_enforcement_plan.csv")
    segments = build_and_export_congestion_overlay(clean_df, tori, plan)
    print(f"Wrote congestion-risk overlay with {len(segments):,} inferred corridor segments.")


if __name__ == "__main__":
    main()
