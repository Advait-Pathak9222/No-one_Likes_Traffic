"""Corridor and bottleneck intelligence for ParkPulse.

Every signal in this module is derived only from the provided violation dataset
and the already-computed road-space estimate table. No external road network, GIS,
basemap, or map-matching service is used. Corridor geometry and corridor links
are *inferred* from the spatial distribution of recorded violations, not from
surveyed road centerlines.

This module exists to strengthen the road-network story honestly:

- ``classify_bottleneck`` labels how a hotspot most likely chokes the carriageway,
- ``junction_sensitivity`` flags signal/crossing-approach exposure,
- ``enrich_roadspace`` attaches corridor linkage to each hotspot,
- ``build_corridor_summary`` rolls hotspots up into inferred corridors.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from . import config
from .roadspace_intelligence import clean_value, normalize_records, write_frontend_json


BOTTLENECK_CLASSES = [
    "Double-park lane squeeze",
    "Signal-approach blocker",
    "Junction-mouth blocker",
    "Arterial kerb-lane choke",
    "Metro feeder spillover",
    "Market/commercial spillover",
    "Footpath-displacement",
    "Heavy-vehicle width loss",
    "Recurring kerbside pressure",
]


def classify_bottleneck(lane_context: Any, dominant_issue: Any, recommended_action: Any = "") -> str:
    """Label the dominant way this hotspot likely removes carriageway capacity.

    Derived purely from the dataset-driven lane-context and dominant-issue text;
    it is an explanation label, not a measured throughput effect.
    """
    text = f"{lane_context or ''} {dominant_issue or ''} {recommended_action or ''}".lower()
    if "double" in text:
        return "Double-park lane squeeze"
    if any(token in text for token in ["signal", "zebra", "stop-line", "stop line"]):
        return "Signal-approach blocker"
    if any(token in text for token in ["junction", "crossing"]):
        return "Junction-mouth blocker"
    if any(token in text for token in ["main-road", "kerb", "running lane", "carriageway"]):
        return "Arterial kerb-lane choke"
    if "metro" in text:
        return "Metro feeder spillover"
    if any(token in text for token in ["market", "commercial"]):
        return "Market/commercial spillover"
    if "footpath" in text:
        return "Footpath-displacement"
    if any(token in text for token in ["large-vehicle", "heavy", "goods"]):
        return "Heavy-vehicle width loss"
    return "Recurring kerbside pressure"


def junction_sensitivity(signal_zebra_share: Any, crossing_share: Any) -> tuple[str, str]:
    """Return a junction-sensitivity (band, label) from observed approach context."""
    score = float(signal_zebra_share or 0.0) + float(crossing_share or 0.0)
    if score >= 0.08:
        return "High", "High junction sensitivity: strong signal/crossing-approach context observed"
    if score >= 0.03:
        return "Medium", "Moderate junction sensitivity: some signal/crossing-approach context observed"
    return "Low", "Low junction sensitivity: little signal/crossing-approach context observed"


def infer_corridor_name(row: pd.Series) -> str:
    """Infer a road/corridor label from available address text (dataset-only).

    Moved here so both the overlay and corridor roll-ups share one naming rule.
    """
    text = str(row.get("dominant_location_text") or row.get("zone_name_readable") or "")
    text = re.sub(r"\bPin[-\s]*\d+\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(India\)", "", text, flags=re.IGNORECASE)
    parts = [re.sub(r"\s+", " ", part.strip()) for part in text.split(",")]
    parts = [part for part in parts if part and part.lower() not in {"india", "karnataka", "bengaluru"}]

    road_patterns = re.compile(
        r"\b(road|rd|street|st|main|cross|ring|orr|flyover|junction|circle|metro|market|layout)\b",
        flags=re.IGNORECASE,
    )
    for part in parts[:4]:
        if "unnamed road" not in part.lower() and road_patterns.search(part):
            return part[:80]
    for part in parts[:2]:
        if "unnamed road" not in part.lower():
            return part[:80]
    return f"{row.get('station', 'Unknown')} local corridor"


def _corridor_length_m(lats: np.ndarray, lons: np.ndarray) -> float:
    """Approximate corridor length from the principal-axis span of its points."""
    lats = np.asarray(lats, dtype=float)
    lons = np.asarray(lons, dtype=float)
    if len(lats) < 2:
        return 0.0
    lat0 = float(np.mean(lats))
    x = (lons - float(np.mean(lons))) * np.cos(np.radians(lat0)) * 111320.0
    y = (lats - float(np.mean(lats))) * 110540.0
    pts = np.column_stack([x, y])
    shifted = pts - pts.mean(axis=0)
    try:
        _, _, vh = np.linalg.svd(shifted, full_matrices=False)
        projection = shifted @ vh[0]
        return float(projection.max() - projection.min())
    except np.linalg.LinAlgError:
        return float(np.hypot(x.max() - x.min(), y.max() - y.min()))


def enrich_roadspace(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach corridor name, bottleneck class, junction sensitivity, and corridor
    linkage to each road-space hotspot. Additive columns only."""
    out = frame.copy()
    out["corridor_name"] = out.apply(infer_corridor_name, axis=1)
    out["bottleneck_class"] = [
        classify_bottleneck(lane_context, dominant_issue, action)
        for lane_context, dominant_issue, action in zip(
            out["lane_context"], out["dominant_lane_issue"], out["recommended_action"]
        )
    ]
    sensitivity = [
        junction_sensitivity(signal_share, crossing_share)
        for signal_share, crossing_share in zip(
            out.get("signal_zebra_share_observed", pd.Series(0.0, index=out.index)).fillna(0.0),
            out.get("crossing_share_observed", pd.Series(0.0, index=out.index)).fillna(0.0),
        )
    ]
    out["junction_sensitivity_band"] = [band for band, _ in sensitivity]
    out["junction_sensitivity_label"] = [label for _, label in sensitivity]

    out["corridor_linked_hotspots"] = (
        out.groupby(["station", "corridor_name"])["zone_id"].transform("count").astype(int)
    )
    lengths: dict[tuple[Any, Any], float] = {}
    for key, group in out.groupby(["station", "corridor_name"]):
        lengths[key] = _corridor_length_m(
            group["centroid_lat"].to_numpy(dtype=float),
            group["centroid_lon"].to_numpy(dtype=float),
        )
    out["corridor_length_m"] = [
        round(lengths[(station, corridor)], 1)
        for station, corridor in zip(out["station"], out["corridor_name"])
    ]
    out["corridor_length_km"] = (out["corridor_length_m"] / 1000.0).round(2)
    return out


def build_corridor_summary(
    roadspace: pd.DataFrame,
    min_hotspots: int = 2,
    top_n: int = 150,
) -> pd.DataFrame:
    """Roll linked hotspots up into inferred corridor records."""
    df = roadspace.copy()
    if "corridor_name" not in df.columns:
        df["corridor_name"] = df.apply(infer_corridor_name, axis=1)
    if "bottleneck_class" not in df.columns:
        df["bottleneck_class"] = [
            classify_bottleneck(lane_context, dominant_issue, action)
            for lane_context, dominant_issue, action in zip(
                df["lane_context"], df["dominant_lane_issue"], df["recommended_action"]
            )
        ]

    rows: list[dict[str, Any]] = []
    for (station, corridor), group in df.groupby(["station", "corridor_name"], dropna=False):
        if len(group) < min_hotspots:
            continue
        length_m = _corridor_length_m(
            group["centroid_lat"].to_numpy(dtype=float),
            group["centroid_lon"].to_numpy(dtype=float),
        )
        bottleneck_mode = group["bottleneck_class"].mode()
        window_mode = group["time_window_readable"].mode()
        rows.append(
            {
                "corridor_id": f"{station}|{corridor}",
                "station": station,
                "corridor_name": corridor,
                "linked_hotspots": int(len(group)),
                "total_violations": int(group["violation_count"].sum()),
                "approx_length_m": round(length_m, 1),
                "approx_length_km": round(length_m / 1000.0, 2),
                "max_tori": round(float(group["final_tori_0_100"].max()), 1),
                "mean_obstruction": round(float(group["lane_obstruction_proxy_0_100"].mean()), 1),
                "dominant_bottleneck": bottleneck_mode.iloc[0] if len(bottleneck_mode) else "Recurring kerbside pressure",
                "peak_window": window_mode.iloc[0] if len(window_mode) else "—",
                "centroid_lat": round(float(group["centroid_lat"].mean()), 6),
                "centroid_lon": round(float(group["centroid_lon"].mean()), 6),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["corridor_priority"] = out["total_violations"] * np.log1p(out["mean_obstruction"])
    out = out.sort_values("corridor_priority", ascending=False).head(top_n).reset_index(drop=True)
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    return out


def export_corridor_summary(roadspace: pd.DataFrame) -> pd.DataFrame:
    """Write corridor roll-up artifacts for tables and the frontend."""
    config.ensure_directories()
    summary = build_corridor_summary(roadspace)
    summary.to_csv(config.TABLES_DIR / "corridor_summary.csv", index=False)
    write_frontend_json("corridor_summary.json", normalize_records(summary))
    return summary


def main() -> None:
    """Build corridor intelligence from existing pipeline outputs."""
    import pandas as pd  # local import keeps module import light

    config.ensure_directories()
    roadspace = pd.read_csv(config.TABLES_DIR / "roadspace_intelligence_plan.csv")
    roadspace = enrich_roadspace(roadspace)
    summary = export_corridor_summary(roadspace)
    print(f"Wrote corridor summary with {len(summary):,} inferred corridors.")


if __name__ == "__main__":
    main()
