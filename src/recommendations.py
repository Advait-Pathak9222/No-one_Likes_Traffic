"""Action recommendation layer for ParkPulse."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config


# Human-readable phrases for the operational time windows, used so reasoning
# never exposes raw codes like "09-12_commercial_morning_peak".
TIME_WINDOW_PHRASE = {
    "00-06_night_early_morning": "late-night (00:00–06:00)",
    "06-09_morning_buildup": "morning build-up (06:00–09:00)",
    "09-12_commercial_morning_peak": "commercial morning peak (09:00–12:00)",
    "12-15_market_midday_pressure": "market midday (12:00–15:00)",
    "15-18_school_evening_buildup": "school/evening build-up (15:00–18:00)",
    "18-22_evening_commercial_pressure": "evening commercial peak (18:00–22:00)",
    "22-24_late_night": "late-evening (22:00–24:00)",
}

_DROP_LOCATION_TOKENS = {"india", "karnataka", "bengaluru", "bangalore", ""}


def short_location_name(text: str) -> str:
    """Trim a long address to its 1–2 most specific parts (road / landmark).

    Drops city/state/pin/country noise so zone names stay legible in the UI.
    """
    cleaned = re.sub(r"\bPin[-\s]*\d+\b", "", str(text), flags=re.IGNORECASE)
    cleaned = re.sub(r"\(India\)", "", cleaned, flags=re.IGNORECASE)
    parts = [re.sub(r"\s+", " ", part.strip()) for part in cleaned.split(",")]
    parts = [
        part
        for part in parts
        if part.lower().strip(". ") not in _DROP_LOCATION_TOKENS
        and not re.fullmatch(r"\d{5,6}", part)
    ]
    if not parts:
        return cleaned.strip()[:48] or "Unnamed location"
    return " · ".join(parts[:2])[:52]


def clean_zone_name(row: pd.Series) -> str:
    """Create a readable hotspot name."""
    zone = str(row.get("zone_name", "") or "").strip()
    if zone and zone.upper() not in {"NO JUNCTION", "UNKNOWN", "NAN"}:
        return f"{zone} Cluster"
    location = str(row.get("location_mode", "") or "").strip()
    if location and location.upper() not in {"UNKNOWN", "NAN"}:
        return short_location_name(location)
    return f"{row.get('station', 'Unknown')} hotspot near {row.get('centroid_lat', 0):.4f}, {row.get('centroid_lon', 0):.4f}"


def recommend_action(row: pd.Series) -> str:
    """Map hotspot features to an operational action."""
    high_tori = row["final_tori_0_100"] >= 85
    medium_tori = row["final_tori_0_100"] >= 65
    high_obstruction = row["mean_vehicle_obstruction"] >= 1.15
    high_severity = row["mean_violation_severity"] >= 1.25
    peak_pressure = row["temporal_pressure"] >= 0.75
    persistent = row["persistence_score"] >= 0.70
    context = row["context_risk_score"] >= 0.70
    repeat_pressure = row.get("repeat_pressure_score_0_100", 0) >= 85
    chronic_share = row.get("chronic_vehicle_record_share", 0) >= 0.20
    patrol_gap = row.get("patrol_gap_score_0_100", 0) >= 85
    emerging = row.get("emerging_hotspot_score_0_100", 0) >= 85
    coverage_warning = row.get("time_window_reliability_score_0_100", 100) < 40

    if high_tori and high_obstruction and (repeat_pressure or chronic_share):
        return "Tow + fixed-window enforcement"
    if high_tori and high_obstruction and high_severity and peak_pressure:
        return "Tow + fixed-window enforcement"
    if high_tori and patrol_gap and persistent:
        return "Fixed-window enforcement"
    if emerging and high_tori and not coverage_warning:
        return "Targeted patrol"
    if persistent and context and row.get("main_road_share", 0) > 0.2:
        return "Engineering fix + targeted patrol"
    if persistent and (row.get("market_share", 0) > 0.1 or row.get("metro_share", 0) > 0.1):
        return "Metro/market spillover control"
    if persistent and row["violation_count"] >= 100:
        return "Fixed-window enforcement"
    if medium_tori:
        return "Targeted patrol"
    return "Watchlist monitoring"


def build_reasoning(row: pd.Series) -> str:
    """Build a short, plain-English explanation (no raw codes)."""
    reasons = []
    if row.get("hotspot_persistence_class"):
        reasons.append(str(row["hotspot_persistence_class"]).lower())
    if row.get("emerging_hotspot_score_0_100", 0) >= 85:
        reasons.append("recent pressure is rising against the prior baseline")
    if row.get("hidden_hotspot_score_0_100", 0) >= 85:
        reasons.append("possible hidden hotspot after correcting for station recording exposure")
    if row["persistence_score"] >= 0.70:
        reasons.append("repeats on many days")
    if row.get("repeat_pressure_score_0_100", 0) >= 85:
        reasons.append("same anonymized vehicles recur often enough to indicate chronic pressure")
    if row.get("repeat_vehicle_movement_score_0_100", 0) >= 85:
        reasons.append(str(row.get("repeat_vehicle_movement_pattern", "repeat-vehicle movement")).lower())
    if row.get("patrol_gap_score_0_100", 0) >= 85:
        reasons.append("risk remains high despite comparatively limited historical enforcement coverage")
    if row.get("time_window_reliability_score_0_100", 100) < 40:
        reasons.append("time-window evidence is sparse, so patrol audit is recommended before assuming low risk")
    if row["temporal_pressure"] >= 0.75:
        window = TIME_WINDOW_PHRASE.get(row["time_block"], str(row["time_block"]))
        reasons.append(f"concentrated in the {window} window")
    if row["mean_vehicle_obstruction"] >= 1.15:
        reasons.append("space-blocking vehicle mix (autos, cars or goods vehicles)")
    if row["mean_junction_criticality"] >= 1.30:
        reasons.append("sits near a junction, signal, market or metro")
    if row["exposure_adjusted_tori"] >= row["stable_tori"]:
        reasons.append("stays high-priority even after adjusting for enforcement attention")
    severity_signature = row.get("violation_text_severity_signature")
    if severity_signature and str(severity_signature) != "General parking pressure":
        reasons.append(str(severity_signature).lower())
    if not reasons:
        reasons.append("moderate recurring parking pressure")
    text = "; ".join(reasons)
    return text[0].upper() + text[1:] + "."


def add_resource_estimates(df: pd.DataFrame) -> pd.DataFrame:
    """Estimate patrol/tow hours and enforcement ROI."""
    out = df.copy()
    out["estimated_patrol_hours"] = np.select(
        [out["final_tori_0_100"] >= 90, out["final_tori_0_100"] >= 70],
        [4.0, 2.0],
        default=1.0,
    )
    out["estimated_tow_hours"] = np.where(
        out["recommended_action"].str.contains("Tow", case=False, na=False),
        2.0,
        0.0,
    )
    out["estimated_patrol_hours"] = (
        out["estimated_patrol_hours"]
        + np.where(out.get("patrol_gap_score_0_100", 0) >= 85, 0.5, 0.0)
        + np.where(out.get("repeat_pressure_score_0_100", 0) >= 90, 0.5, 0.0)
        + np.where(out.get("emerging_hotspot_score_0_100", 0) >= 90, 0.5, 0.0)
    )
    out["estimated_total_resource_hours"] = (
        out["estimated_patrol_hours"] + out["estimated_tow_hours"]
    )
    repeat_bonus = out.get("repeat_pressure_score_0_100", 0) / 100.0
    gap_bonus = out.get("patrol_gap_score_0_100", 0) / 100.0
    out["expected_impact_reduced"] = out["final_tori_0_100"] * (0.31 + 0.025 * repeat_bonus + 0.015 * gap_bonus)
    out["enforcement_roi"] = out["expected_impact_reduced"] / out[
        "estimated_total_resource_hours"
    ].clip(lower=1.0)
    return out


def add_station_load_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add station-level resource burden to each recommended row."""
    out = df.copy()
    station_load = (
        out.groupby("station", dropna=False)
        .agg(
            station_priority_zone_count=("rank", "count"),
            station_high_priority_zone_count=("final_tori_0_100", lambda s: int((s >= 85).sum())),
            station_patrol_hours_total=("estimated_patrol_hours", "sum"),
            station_tow_hours_total=("estimated_tow_hours", "sum"),
            station_avg_repeat_pressure=("repeat_pressure_score_0_100", "mean"),
            station_avg_patrol_gap=("patrol_gap_score_0_100", "mean"),
            station_avg_emerging_pressure=("emerging_hotspot_score_0_100", "mean"),
            station_avg_confidence_priority=("confidence_adjusted_priority_0_100", "mean"),
        )
        .reset_index()
    )
    station_load["station_enforcement_load_raw"] = (
        0.30 * percentile_like(station_load["station_priority_zone_count"])
        + 0.20 * percentile_like(station_load["station_high_priority_zone_count"])
        + 0.20 * percentile_like(station_load["station_patrol_hours_total"] + station_load["station_tow_hours_total"])
        + 0.15 * station_load["station_avg_repeat_pressure"].fillna(0) / 100.0
        + 0.15 * station_load["station_avg_patrol_gap"].fillna(0) / 100.0
    )
    station_load["station_enforcement_load_score_0_100"] = 100 * percentile_like(
        station_load["station_enforcement_load_raw"]
    )
    station_load["station_load_band"] = pd.cut(
        station_load["station_enforcement_load_score_0_100"],
        bins=[-0.01, 45, 70, 88, 100.01],
        labels=["Normal load", "Elevated load", "High load", "Critical load"],
    ).astype(str)
    return out.merge(station_load, on="station", how="left")


def percentile_like(series: pd.Series) -> pd.Series:
    """Small local percentile helper to avoid another import dependency."""
    return series.rank(method="average", pct=True).fillna(0.0)


def build_enforcement_plan(tori: pd.DataFrame, top_n: int = 100) -> pd.DataFrame:
    """Build a ranked operational enforcement table."""
    ranked = tori.sort_values(
        ["confidence_adjusted_priority_0_100", "final_tori_0_100"],
        ascending=False,
    ).copy()
    ranked["zone_name_readable"] = ranked.apply(clean_zone_name, axis=1)
    ranked["recommended_action"] = ranked.apply(recommend_action, axis=1)
    ranked["reasoning"] = ranked.apply(build_reasoning, axis=1)
    ranked = add_resource_estimates(ranked)
    ranked["rank"] = np.arange(1, len(ranked) + 1)
    selected = add_station_load_features(ranked.head(top_n).copy())
    cols = [
        "rank",
        "station",
        "zone_name_readable",
        "centroid_lat",
        "centroid_lon",
        "time_block",
        "violation_count",
        "final_tori_0_100",
        "stable_tori",
        "exposure_adjusted_tori",
        "confidence_adjusted_priority_0_100",
        "emerging_hotspot_score_0_100",
        "hidden_hotspot_score_0_100",
        "hidden_hotspot_flag",
        "recent_violation_rate",
        "prior_violation_rate",
        "recent_to_prior_pressure_ratio",
        "hotspot_persistence_class",
        "time_window_reliability_score_0_100",
        "time_window_reliability_band",
        "time_window_coverage_warning",
        "station_recording_bias_score_0_100",
        "station_recording_bias_band",
        "repeat_vehicle_movement_score_0_100",
        "repeat_vehicle_movement_pattern",
        "violation_text_severity_score_0_100",
        "violation_text_severity_signature",
        "repeat_vehicle_record_share",
        "chronic_vehicle_record_share",
        "multi_station_repeat_vehicle_share",
        "repeat_pressure_score_0_100",
        "chronic_vehicle_pressure_0_100",
        "patrol_gap_score_0_100",
        "patrol_gap_band",
        "confidence_band",
        "recommended_action",
        "reasoning",
        "estimated_patrol_hours",
        "estimated_tow_hours",
        "enforcement_roi",
        "station_priority_zone_count",
        "station_high_priority_zone_count",
        "station_patrol_hours_total",
        "station_tow_hours_total",
        "station_enforcement_load_score_0_100",
        "station_load_band",
    ]
    return selected[[col for col in cols if col in selected.columns]]


def build_operational_intelligence_summary(tori: pd.DataFrame, plan: pd.DataFrame) -> pd.DataFrame:
    """Summarize the eight judge-facing operational signals."""
    rows: list[dict[str, object]] = []

    def add(signal: str, scope: str, metric: str, value: object, note: str) -> None:
        rows.append(
            {
                "signal": signal,
                "scope": scope,
                "metric": metric,
                "value": value,
                "note": note,
            }
        )

    add(
        "Emerging Hotspot Index",
        "all hotspots",
        "score >= 85",
        int((tori["emerging_hotspot_score_0_100"] >= 85).sum()),
        "Recent 14-day pressure is high relative to prior 45-day pressure.",
    )
    add(
        "Station Recording Bias",
        "all hotspots",
        "high recording exposure",
        int((tori["station_recording_bias_score_0_100"] >= 75).sum()),
        "Station-level device/officer/activity exposure that can inflate raw density.",
    )
    add(
        "Repeat Vehicle Movement",
        "recommended plan",
        "movement pattern mix",
        "; ".join(f"{k}: {v}" for k, v in plan["repeat_vehicle_movement_pattern"].value_counts().items()),
        "Separates local repeaters, chronic repeaters and cross-station repeat movement.",
    )
    add(
        "Time-Window Reliability",
        "all hotspots",
        "coverage warnings",
        int((tori["time_window_reliability_score_0_100"] < 40).sum()),
        "Sparse time windows are flagged as coverage risk, not treated as zero demand.",
    )
    add(
        "Hotspot Persistence Class",
        "all hotspots",
        "class mix",
        "; ".join(f"{k}: {v}" for k, v in tori["hotspot_persistence_class"].value_counts().items()),
        "Classifies chronic, emerging, time-window persistent, one-off and coverage-risk hotspots.",
    )
    add(
        "Violation Text Severity Mining",
        "recommended plan",
        "top signatures",
        "; ".join(f"{k}: {v}" for k, v in plan["violation_text_severity_signature"].value_counts().head(5).items()),
        "Turns violation text into interpretable road-space severity signals.",
    )
    add(
        "Station-Level Enforcement Load",
        "recommended plan",
        "load band mix",
        "; ".join(f"{k}: {v}" for k, v in plan["station_load_band"].value_counts().items()),
        "Summarizes resource burden across priority zones per station.",
    )
    add(
        "Confidence-Aware Priority",
        "recommended plan",
        "median score",
        round(float(plan["confidence_adjusted_priority_0_100"].median()), 1),
        "Keeps final dispatch ranking sensitive to evidence quality and time-window reliability.",
    )
    return pd.DataFrame(rows)


def write_operational_intelligence_summary(tori: pd.DataFrame, plan: pd.DataFrame) -> pd.DataFrame:
    """Write operational signal summary for judges and QA."""
    summary = build_operational_intelligence_summary(tori, plan)
    summary.to_csv(config.TABLES_DIR / "operational_intelligence_summary.csv", index=False)
    return summary


def main() -> None:
    config.ensure_directories()
    tori = pd.read_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet")
    plan = build_enforcement_plan(tori, top_n=250)
    plan.to_csv(config.TABLES_DIR / "daily_enforcement_plan.csv", index=False)
    station_plan = plan.groupby("station").head(5)
    station_plan.to_csv(config.TABLES_DIR / "station_deployment_plan.csv", index=False)
    write_operational_intelligence_summary(tori, plan)
    print(f"Wrote enforcement plan with {len(plan):,} rows.")


if __name__ == "__main__":
    main()
