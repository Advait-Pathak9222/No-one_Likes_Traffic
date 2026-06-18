"""Road-space and lane-obstruction intelligence for Theme 1.

The provided dataset has exact violation coordinates and rich violation context,
but it does not include lane geometry, signal-health telemetry, or live police
roster feeds. This module therefore separates evidence into three levels:

1. observed in the violation data,
2. proxy inferred from repeated enforcement/recording patterns,
3. external feed required.

That distinction is important for a judge-facing system: ParkPulse should be
ambitious without pretending to have data that is not present.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

import folium
import numpy as np
import pandas as pd
from folium.plugins import Fullscreen, MarkerCluster

from . import config
from .exposure import percentile_rank


FRONTEND_OUTPUT_DIR = config.OUTPUT_DIR / "frontend"
FRONTEND_PUBLIC_DATA_DIR = config.PROJECT_DIR / "frontend" / "public" / "data"

TIME_BLOCK_LABELS = {
    "00-06_night_early_morning": "00:00–06:00 Night",
    "06-09_morning_buildup": "06:00–09:00 AM build-up",
    "09-12_commercial_morning_peak": "09:00–12:00 AM peak",
    "12-15_market_midday_pressure": "12:00–15:00 Midday",
    "15-18_school_evening_buildup": "15:00–18:00 PM build-up",
    "18-22_evening_commercial_pressure": "18:00–22:00 PM peak",
    "22-24_late_night": "22:00–24:00 Late",
}


def clean_value(value: Any) -> Any:
    """Convert numpy/pandas values into JSON-safe scalars."""
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and (math.isnan(float(value)) or math.isinf(float(value))):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def write_json(path: Path, data: Any) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=clean_value)


def write_frontend_json(filename: str, data: Any) -> None:
    """Write a JSON artifact to pipeline outputs and React public data."""
    write_json(FRONTEND_OUTPUT_DIR / filename, data)
    write_json(FRONTEND_PUBLIC_DATA_DIR / filename, data)


def make_zone_id(station: str, time_block: str, lat: float, lon: float) -> str:
    """Create a stable zone id matching the frontend convention."""
    station_part = str(station).lower().replace(" ", "_").replace("/", "_")
    time_part = str(time_block).split("_")[0]
    return f"{station_part}_{time_part}_{lat:.5f}_{lon:.5f}"


def _mode_or_unknown(series: pd.Series) -> str:
    mode = series.dropna().astype(str).mode()
    return mode.iloc[0] if len(mode) else "Unknown"


def _share(series: pd.Series) -> float:
    return float(series.fillna(False).mean()) if len(series) else 0.0


def _contains(series: pd.Series, pattern: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(pattern, case=False, regex=True)


def build_reason_aggregates(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate violation evidence needed for road-space explanations."""
    df = clean_df.copy()
    atoms = df["violation_atoms"].fillna("").astype(str)
    raw_violation = df.get("violation_type", pd.Series("", index=df.index)).fillna("").astype(str)

    df["wrong_parking_hit"] = _contains(atoms, r"\bwrong parking\b")
    df["no_parking_hit"] = _contains(atoms, r"\bno parking\b")
    df["main_road_hit"] = df.get("has_main_road", False)
    df["double_parking_hit"] = _contains(atoms, r"\bdouble parking\b")
    df["footpath_hit"] = df.get("has_footpath", False)
    df["crossing_hit"] = df.get("has_crossing", False)
    df["signal_zebra_hit"] = df.get("has_signal_or_zebra", False) | df.get("is_signal_area", False)
    df["bus_stop_school_hospital_hit"] = df.get("has_bus_stop_school_hospital", False)
    df["wrong_side_hit"] = _contains(atoms + " " + raw_violation, r"against one way|no entry|wrong side")
    df["lane_discipline_hit"] = _contains(atoms + " " + raw_violation, r"lane disipline|lane discipline")
    df["heavy_or_goods_hit"] = df["vehicle_type_norm"].isin(["heavy", "goods_light"])
    df["auto_cab_hit"] = df["vehicle_type_norm"].eq("auto_cab")
    df["car_hit"] = df["vehicle_type_norm"].eq("car")
    df["two_wheeler_hit"] = df["vehicle_type_norm"].eq("two_wheeler")

    group_cols = ["grid_id_250m", "station", "time_block"]
    return (
        df.groupby(group_cols, dropna=False)
        .agg(
            exact_violation_rows=("violation_id", "count"),
            observed_lat_min=("lat", "min"),
            observed_lat_max=("lat", "max"),
            observed_lon_min=("lon", "min"),
            observed_lon_max=("lon", "max"),
            dominant_location_text=("location_text", _mode_or_unknown),
            wrong_parking_share=("wrong_parking_hit", _share),
            no_parking_share=("no_parking_hit", _share),
            main_road_share_observed=("main_road_hit", _share),
            double_parking_share=("double_parking_hit", _share),
            footpath_share_observed=("footpath_hit", _share),
            crossing_share_observed=("crossing_hit", _share),
            signal_zebra_share_observed=("signal_zebra_hit", _share),
            bus_stop_school_hospital_share=("bus_stop_school_hospital_hit", _share),
            wrong_side_share=("wrong_side_hit", _share),
            lane_discipline_share=("lane_discipline_hit", _share),
            heavy_or_goods_share=("heavy_or_goods_hit", _share),
            auto_cab_share=("auto_cab_hit", _share),
            car_share=("car_hit", _share),
            two_wheeler_share=("two_wheeler_hit", _share),
            historical_recording_devices=("device_id", "nunique"),
            historical_recording_officer_ids=("created_by_id", "nunique"),
            active_recording_days=("created_date", "nunique"),
        )
        .reset_index()
    )


def add_lane_obstruction_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Add lane/road-space obstruction proxy scores."""
    out = frame.copy()
    out["kerbside_illegal_parking_share"] = (
        out["wrong_parking_share"].fillna(0)
        + out["no_parking_share"].fillna(0)
        + out["double_parking_share"].fillna(0)
    ).clip(0, 1)
    out["junction_conflict_share"] = (
        out["crossing_share_observed"].fillna(0)
        + out["signal_zebra_share_observed"].fillna(0)
        + out["bus_stop_school_hospital_share"].fillna(0)
    ).clip(0, 1)
    out["large_vehicle_space_share"] = (
        out["heavy_or_goods_share"].fillna(0) + 0.5 * out["auto_cab_share"].fillna(0)
    ).clip(0, 1)

    out["lane_obstruction_raw"] = (
        0.24 * out["kerbside_illegal_parking_share"]
        + 0.18 * out["main_road_share_observed"].fillna(out.get("main_road_share", 0)).fillna(0)
        + 0.16 * out["junction_conflict_share"]
        + 0.14 * out["large_vehicle_space_share"]
        + 0.12 * out["footpath_share_observed"].fillna(out.get("footpath_share", 0)).fillna(0)
        + 0.10 * out["vehicle_obstruction_score"].fillna(0)
        + 0.06 * out["violation_severity_score"].fillna(0)
    ) * np.log1p(out["violation_count"].clip(lower=0))
    out["lane_obstruction_proxy_0_100"] = 100 * percentile_rank(out["lane_obstruction_raw"])
    out["workforce_presence_proxy_0_100"] = 100 * percentile_rank(
        np.log1p(out["historical_recording_officer_ids"].clip(lower=0))
        + np.log1p(out["historical_recording_devices"].clip(lower=0))
        + np.log1p(out["active_recording_days"].clip(lower=0))
    )
    out["lane_obstruction_band"] = pd.cut(
        out["lane_obstruction_proxy_0_100"],
        bins=[-0.01, 50, 75, 90, 100.01],
        labels=["Watch", "Moderate", "High", "Critical"],
    ).astype(str)
    out["workforce_presence_band"] = pd.cut(
        out["workforce_presence_proxy_0_100"],
        bins=[-0.01, 40, 70, 100.01],
        labels=["Low historical coverage", "Medium historical coverage", "High historical coverage"],
    ).astype(str)
    return out


def infer_dominant_lane_issue(row: pd.Series) -> str:
    """Return the primary road-space issue visible from the dataset."""
    if row["double_parking_share"] >= 0.08:
        return "Double-parking likely narrowing an active running lane"
    if row["main_road_share_observed"] >= 0.12:
        return "Main-road illegal parking likely occupying the kerb-side running lane"
    if row["signal_zebra_share_observed"] >= 0.03:
        return "Signal/zebra-crossing approach obstruction"
    if row["crossing_share_observed"] >= 0.03:
        return "Junction-mouth or road-crossing obstruction"
    if row["footpath_share_observed"] >= 0.03:
        return "Footpath parking spillover pushing pedestrians into carriageway"
    if row["large_vehicle_space_share"] >= 0.18:
        return "Large-vehicle road-space footprint amplifying congestion"
    return "Recurring kerbside illegal-parking pressure"


def infer_lane_context(row: pd.Series) -> str:
    """Return a practical lane/corridor context label."""
    if row["main_road_share_observed"] >= 0.10:
        return "Main-road kerb lane"
    if row["signal_zebra_share_observed"] >= 0.03:
        return "Signal approach / stop-line zone"
    if row["crossing_share_observed"] >= 0.03:
        return "Junction approach"
    if row["footpath_share_observed"] >= 0.03:
        return "Footpath-adjacent edge lane"
    if row["market_share"] >= 0.10:
        return "Market/commercial access lane"
    if row["metro_share"] >= 0.10:
        return "Metro feeder access lane"
    return "Local carriageway edge"


def build_reason_codes(row: pd.Series) -> list[dict[str, Any]]:
    """Build transparent hotspot reasons with evidence level."""
    reasons: list[dict[str, Any]] = []
    if row["kerbside_illegal_parking_share"] >= 0.25:
        reasons.append(
            {
                "reason": "Illegal parking is repeatedly present at this location",
                "evidence": f"{row['kerbside_illegal_parking_share']:.0%} of records include wrong/no/double parking.",
                "support_level": "observed",
            }
        )
    if row["main_road_share_observed"] >= 0.05:
        reasons.append(
            {
                "reason": "Running-lane capacity is likely reduced",
                "evidence": f"{row['main_road_share_observed']:.0%} of records mention main-road parking context.",
                "support_level": "observed",
            }
        )
    if row["large_vehicle_space_share"] >= 0.12:
        reasons.append(
            {
                "reason": "Vehicle footprint can choke carriageway width",
                "evidence": f"{row['large_vehicle_space_share']:.0%} heavy/goods/auto-cab road-space mix.",
                "support_level": "observed",
            }
        )
    if row["junction_conflict_share"] >= 0.04:
        reasons.append(
            {
                "reason": "Intersection or pedestrian-crossing conflict",
                "evidence": f"{row['junction_conflict_share']:.0%} crossing, signal, zebra, bus-stop, school or hospital context.",
                "support_level": "observed",
            }
        )
    if row["wrong_side_share"] > 0 or row["lane_discipline_share"] > 0:
        reasons.append(
            {
                "reason": "Non-parking traffic violation signal is present but sparse",
                "evidence": f"{row['wrong_side_share']:.1%} wrong-side/no-entry and {row['lane_discipline_share']:.1%} lane-discipline records in this hotspot.",
                "support_level": "observed-low-volume",
            }
        )
    if row.get("repeat_pressure_score_0_100", 0) >= 80:
        reasons.append(
            {
                "reason": "Chronic repeat-vehicle pressure is present",
                "evidence": (
                    f"{row.get('repeat_vehicle_record_share', 0):.0%} repeat-vehicle records and "
                    f"{row.get('chronic_vehicle_record_share', 0):.0%} chronic-vehicle records."
                ),
                "support_level": "observed",
            }
        )
    if row.get("patrol_gap_score_0_100", 0) >= 80:
        reasons.append(
            {
                "reason": "Patrol-gap opportunity: high risk with lower historical coverage",
                "evidence": (
                    f"Patrol-gap score {row.get('patrol_gap_score_0_100', 0):.1f}; "
                    f"{row.get('workforce_presence_band', 'coverage proxy unavailable')}."
                ),
                "support_level": "proxy",
            }
        )
    if row["workforce_presence_proxy_0_100"] >= 75:
        reasons.append(
            {
                "reason": "High historical police/enforcement recording presence",
                "evidence": f"{int(row['historical_recording_officer_ids'])} officer IDs, {int(row['historical_recording_devices'])} devices, {int(row['active_recording_days'])} active days.",
                "support_level": "proxy",
            }
        )
    else:
        reasons.append(
            {
                "reason": "Limited historical enforcement coverage relative to risk",
                "evidence": f"{row['workforce_presence_band']} compared with TORI {row['final_tori_0_100']:.1f}.",
                "support_level": "proxy",
            }
        )

    reasons.append(
        {
            "reason": "Broken traffic-light status is not directly observable",
            "evidence": "The current dataset has signal/zebra parking context, but no signal-health telemetry.",
            "support_level": "external-feed-required",
        }
    )
    return reasons


def build_mitigation_plan(row: pd.Series) -> list[dict[str, str]]:
    """Build field-ready mitigation steps."""
    action = str(row["recommended_action"]).lower()
    plan: list[dict[str, str]] = []

    if "tow" in action:
        plan.append(
            {
                "phase": "0-30 min",
                "step": "Pre-position tow vehicle and one patrol unit at the hotspot before the peak window.",
            }
        )
        plan.append(
            {
                "phase": "30-90 min",
                "step": "Clear kerb-side obstruction and record repeat vehicle numbers for repeat-offender tracking.",
            }
        )
    elif "engineering" in action:
        plan.append(
            {
                "phase": "Today",
                "step": "Run targeted patrol during the peak window and capture photo evidence of the obstruction pattern.",
            }
        )
        plan.append(
            {
                "phase": "7-day fix",
                "step": "Audit no-parking boards, kerb paint, bollards/delineators, and loading-bay design.",
            }
        )
    elif "metro" in action or "market" in action:
        plan.append(
            {
                "phase": "Peak window",
                "step": "Deploy one marshal/patrol unit for pick-up/drop-off discipline and vendor/loading spillover control.",
            }
        )
        plan.append(
            {
                "phase": "Policy",
                "step": "Create timed loading/unloading slots and marked short-stop bays away from the running lane.",
            }
        )
    elif "fixed" in action:
        plan.append(
            {
                "phase": "Peak window",
                "step": "Assign a fixed-window patrol at the same time block for three consecutive active days.",
            }
        )
    else:
        plan.append(
            {
                "phase": "Watchlist",
                "step": "Monitor recurrence and deploy patrol only when the hotspot enters a high-TORI time window.",
            }
        )

    if row["signal_zebra_share_observed"] >= 0.03:
        plan.append(
            {
                "phase": "Signal approach",
                "step": "Keep 30m approach to signal/zebra-crossing clear; add barricade cones during the peak window.",
            }
        )
    if row["main_road_share_observed"] >= 0.05:
        plan.append(
            {
                "phase": "Carriageway",
                "step": "Protect the kerb-side running lane with temporary cones or flexible delineators.",
            }
        )
    if row.get("repeat_pressure_score_0_100", 0) >= 85:
        plan.append(
            {
                "phase": "Repeat-offender follow-up",
                "step": "Use the anonymized repeat-vehicle watchlist for the zone and prioritize towing/escalation for vehicles seen again in the same window.",
            }
        )
    if row.get("patrol_gap_score_0_100", 0) >= 85:
        plan.append(
            {
                "phase": "Coverage gap",
                "step": "Schedule a fixed patrol beat for this window because risk is high relative to historical enforcement presence.",
            }
        )
    if row["workforce_presence_proxy_0_100"] < 45 and row["final_tori_0_100"] >= 85:
        plan.append(
            {
                "phase": "Deployment",
                "step": "Escalate to station-level priority because risk is high but historical enforcement presence is low.",
            }
        )
    return plan


def make_officer_brief(row: pd.Series) -> str:
    """Create a concise field brief for police personnel."""
    return (
        f"{row['station']} | {TIME_BLOCK_LABELS.get(row['time_block'], row['time_block'])}: "
        f"{row['dominant_lane_issue']}. TORI {row['final_tori_0_100']:.1f}, "
        f"lane-obstruction proxy {row['lane_obstruction_proxy_0_100']:.1f}, "
        f"repeat pressure {row.get('repeat_pressure_score_0_100', 0):.1f}, "
        f"patrol gap {row.get('patrol_gap_score_0_100', 0):.1f}. "
        f"Recommended action: {row['recommended_action']}."
    )


def build_roadspace_intelligence(
    clean_df: pd.DataFrame,
    tori: pd.DataFrame,
    plan: pd.DataFrame,
    top_n: int = 500,
) -> pd.DataFrame:
    """Build hotspot-level road-space intelligence records."""
    reasons = build_reason_aggregates(clean_df)
    frame = tori.merge(reasons, on=["grid_id_250m", "station", "time_block"], how="left")
    plan_small = plan[
        [
            "station",
            "time_block",
            "centroid_lat",
            "centroid_lon",
            "recommended_action",
            "reasoning",
            "estimated_patrol_hours",
            "estimated_tow_hours",
            "enforcement_roi",
        ]
    ].copy()
    plan_small["lat_key"] = plan_small["centroid_lat"].round(6)
    plan_small["lon_key"] = plan_small["centroid_lon"].round(6)
    frame["lat_key"] = frame["centroid_lat"].round(6)
    frame["lon_key"] = frame["centroid_lon"].round(6)
    frame = frame.merge(
        plan_small.drop(columns=["centroid_lat", "centroid_lon"]),
        on=["station", "time_block", "lat_key", "lon_key"],
        how="left",
    )
    frame["recommended_action"] = frame["recommended_action"].fillna("Targeted patrol")
    frame["reasoning"] = frame["reasoning"].fillna("High road-space obstruction risk based on repeated illegal parking evidence.")
    frame["estimated_patrol_hours"] = frame["estimated_patrol_hours"].fillna(2.0)
    frame["estimated_tow_hours"] = frame["estimated_tow_hours"].fillna(0.0)
    frame["enforcement_roi"] = frame["enforcement_roi"].fillna(0.0)
    frame = add_lane_obstruction_scores(frame)
    frame["zone_id"] = [
        make_zone_id(row.station, row.time_block, row.centroid_lat, row.centroid_lon)
        for row in frame.itertuples()
    ]
    from .recommendations import short_location_name

    frame["zone_name_readable"] = np.where(
        ~frame["zone_name"].astype(str).str.upper().isin(["NO JUNCTION", "UNKNOWN", "NAN", ""]),
        frame["zone_name"].astype(str) + " Cluster",
        frame["location_mode"].astype(str).map(short_location_name),
    )
    frame["time_window_readable"] = frame["time_block"].map(TIME_BLOCK_LABELS).fillna(frame["time_block"])
    frame["lane_context"] = frame.apply(infer_lane_context, axis=1)
    frame["dominant_lane_issue"] = frame.apply(infer_dominant_lane_issue, axis=1)
    frame["reason_codes"] = frame.apply(build_reason_codes, axis=1)
    frame["mitigation_plan"] = frame.apply(build_mitigation_plan, axis=1)
    frame["officer_brief"] = frame.apply(make_officer_brief, axis=1)
    frame["exact_location_note"] = (
        "Exact centroid from violation coordinates; lane geometry is a road-space proxy, not surveyed lane GIS."
    )
    frame["signal_health_status"] = np.where(
        frame["signal_zebra_share_observed"] >= 0.03,
        "Signal/zebra context observed; broken-signal status requires signal asset feed",
        "No signal-health evidence in current dataset",
    )
    frame["live_workforce_status"] = "External feed required: integrate duty roster / GPS patrol availability"
    frame["historical_workforce_proxy"] = (
        frame["historical_recording_officer_ids"].fillna(0).astype(int).astype(str)
        + " officer IDs, "
        + frame["historical_recording_devices"].fillna(0).astype(int).astype(str)
        + " devices historically recorded here"
    )

    selected_columns = [
        "zone_id",
        "zone_name_readable",
        "station",
        "time_block",
        "time_window_readable",
        "centroid_lat",
        "centroid_lon",
        "observed_lat_min",
        "observed_lat_max",
        "observed_lon_min",
        "observed_lon_max",
        "lane_context",
        "dominant_lane_issue",
        "lane_obstruction_proxy_0_100",
        "lane_obstruction_band",
        "final_tori_0_100",
        "violation_count",
        "weighted_violation_count",
        "repeat_vehicle_record_share",
        "chronic_vehicle_record_share",
        "multi_station_repeat_vehicle_share",
        "repeat_pressure_score_0_100",
        "chronic_vehicle_pressure_0_100",
        "patrol_gap_score_0_100",
        "patrol_gap_band",
        "confidence_band",
        "recommended_action",
        "estimated_patrol_hours",
        "estimated_tow_hours",
        "enforcement_roi",
        "workforce_presence_proxy_0_100",
        "workforce_presence_band",
        "historical_workforce_proxy",
        "signal_health_status",
        "live_workforce_status",
        "wrong_parking_share",
        "no_parking_share",
        "main_road_share_observed",
        "double_parking_share",
        "footpath_share_observed",
        "crossing_share_observed",
        "signal_zebra_share_observed",
        "wrong_side_share",
        "lane_discipline_share",
        "large_vehicle_space_share",
        "dominant_location_text",
        "reason_codes",
        "mitigation_plan",
        "officer_brief",
        "exact_location_note",
    ]
    return (
        frame.sort_values(["final_tori_0_100", "lane_obstruction_proxy_0_100"], ascending=False)
        .head(top_n)
        .reset_index(drop=True)[selected_columns]
    )


def normalize_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to JSON-safe records."""
    records = []
    for row in frame.to_dict(orient="records"):
        records.append({key: clean_value(value) for key, value in row.items()})
    return records


def build_lane_hotspots_geojson(frame: pd.DataFrame) -> dict[str, Any]:
    """Create GeoJSON with exact hotspot coordinates and road-space properties."""
    features = []
    for row in frame.itertuples(index=False):
        properties = {
            "zone_id": row.zone_id,
            "zone_name": row.zone_name_readable,
            "police_station": row.station,
            "time_window": row.time_window_readable,
            "lane_context": row.lane_context,
            "dominant_lane_issue": row.dominant_lane_issue,
            "lane_obstruction_proxy_0_100": row.lane_obstruction_proxy_0_100,
            "lane_obstruction_band": row.lane_obstruction_band,
            "final_tori_0_100": row.final_tori_0_100,
            "violation_count": row.violation_count,
            "confidence_band": row.confidence_band,
            "recommended_action": row.recommended_action,
            "repeat_pressure_score_0_100": getattr(row, "repeat_pressure_score_0_100", None),
            "chronic_vehicle_pressure_0_100": getattr(row, "chronic_vehicle_pressure_0_100", None),
            "patrol_gap_score_0_100": getattr(row, "patrol_gap_score_0_100", None),
            "patrol_gap_band": getattr(row, "patrol_gap_band", None),
            "bottleneck_class": getattr(row, "bottleneck_class", None),
            "junction_sensitivity_band": getattr(row, "junction_sensitivity_band", None),
            "corridor_name": getattr(row, "corridor_name", None),
            "corridor_linked_hotspots": getattr(row, "corridor_linked_hotspots", None),
            "corridor_length_km": getattr(row, "corridor_length_km", None),
            "mitigation_plan": row.mitigation_plan,
            "reason_codes": row.reason_codes,
            "officer_brief": row.officer_brief,
            "historical_workforce_proxy": row.historical_workforce_proxy,
            "signal_health_status": row.signal_health_status,
            "live_workforce_status": row.live_workforce_status,
            "exact_location_note": row.exact_location_note,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [clean_value(row.centroid_lon), clean_value(row.centroid_lat)],
                },
                "properties": {key: clean_value(value) for key, value in properties.items()},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _band_color(band: str) -> str:
    if band == "Critical":
        return "#c81e1e"
    if band == "High":
        return "#fb641b"
    if band == "Moderate":
        return "#2874f0"
    return "#5f6c7b"


def generate_lane_hotspot_map(frame: pd.DataFrame, output_path: Path) -> None:
    """Generate a high-quality interactive HTML map using OpenStreetMap tiles."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    center = [float(frame["centroid_lat"].median()), float(frame["centroid_lon"].median())]
    fmap = folium.Map(
        location=center,
        zoom_start=11,
        tiles="CartoDB positron",
        control_scale=True,
        prefer_canvas=True,
    )
    Fullscreen(position="topright").add_to(fmap)
    cluster = MarkerCluster(name="Lane obstruction hotspot intelligence").add_to(fmap)

    for row in frame.head(500).itertuples(index=False):
        reasons = "; ".join(
            f"{item['reason']} ({item['support_level']})" for item in row.reason_codes[:3]
        )
        mitigation = "; ".join(f"{item['phase']}: {item['step']}" for item in row.mitigation_plan[:3])
        popup_html = f"""
        <div style="width: 360px; font-family: Inter, Arial, sans-serif;">
          <h3 style="margin:0 0 6px;">{html.escape(str(row.zone_name_readable))}</h3>
          <b>Station:</b> {html.escape(str(row.station))}<br/>
          <b>Window:</b> {html.escape(str(row.time_window_readable))}<br/>
          <b>Lane context:</b> {html.escape(str(row.lane_context))}<br/>
          <b>Primary issue:</b> {html.escape(str(row.dominant_lane_issue))}<br/>
          <b>TORI:</b> {row.final_tori_0_100:.1f} |
          <b>Lane obstruction:</b> {row.lane_obstruction_proxy_0_100:.1f} ({html.escape(str(row.lane_obstruction_band))})<br/>
          <b>Action:</b> {html.escape(str(row.recommended_action))}<br/>
          <b>Reasons:</b> {html.escape(reasons)}<br/>
          <b>Mitigation:</b> {html.escape(mitigation)}<br/>
          <small>{html.escape(str(row.exact_location_note))}</small>
        </div>
        """
        folium.CircleMarker(
            location=[row.centroid_lat, row.centroid_lon],
            radius=max(5, min(16, row.lane_obstruction_proxy_0_100 / 8)),
            color=_band_color(row.lane_obstruction_band),
            fill=True,
            fill_color=_band_color(row.lane_obstruction_band),
            fill_opacity=0.72,
            weight=2,
            tooltip=f"{row.station} | {row.lane_obstruction_band} | TORI {row.final_tori_0_100:.1f}",
            popup=folium.Popup(popup_html, max_width=420),
        ).add_to(cluster)

    folium.LayerControl().add_to(fmap)
    fmap.save(str(output_path))


def export_roadspace_intelligence(frame: pd.DataFrame) -> None:
    """Write CSV, JSON, GeoJSON and HTML map artifacts."""
    csv_frame = frame.copy()
    csv_frame["reason_codes"] = csv_frame["reason_codes"].map(lambda value: json.dumps(value, ensure_ascii=False))
    csv_frame["mitigation_plan"] = csv_frame["mitigation_plan"].map(lambda value: json.dumps(value, ensure_ascii=False))
    csv_frame.to_csv(config.TABLES_DIR / "roadspace_intelligence_plan.csv", index=False)

    records = normalize_records(frame)
    geojson = build_lane_hotspots_geojson(frame)
    write_frontend_json("roadspace_intelligence.json", records)
    write_frontend_json("lane_hotspots.geojson", geojson)
    generate_lane_hotspot_map(frame, config.MAPS_DIR / "lane_hotspot_intelligence.html")


def main() -> None:
    """Build and export road-space intelligence from existing pipeline outputs."""
    config.ensure_directories()
    clean_df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")
    tori = pd.read_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet")
    plan = pd.read_csv(config.TABLES_DIR / "daily_enforcement_plan.csv")
    frame = build_roadspace_intelligence(clean_df, tori, plan, top_n=500)
    export_roadspace_intelligence(frame)
    print(f"Wrote road-space intelligence for {len(frame):,} hotspots.")


if __name__ == "__main__":
    main()
