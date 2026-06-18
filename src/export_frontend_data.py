"""Export compact JSON/GeoJSON artifacts for the React frontend."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import config


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
    """Convert pandas/numpy values into JSON-safe values."""
    if value is None:
        return None
    if isinstance(value, (float, np.floating)) and (math.isnan(float(value)) or math.isinf(float(value))):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def write_json(path: Path, data: Any) -> None:
    """Write pretty JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=clean_value)


def write_frontend_json(filename: str, data: Any) -> None:
    """Write frontend data to pipeline outputs and Vite public directory."""
    write_json(FRONTEND_OUTPUT_DIR / filename, data)
    write_json(FRONTEND_PUBLIC_DATA_DIR / filename, data)


def normalize_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert DataFrame rows to JSON-safe dicts."""
    records = []
    for row in frame.to_dict(orient="records"):
        records.append({key: clean_value(value) for key, value in row.items()})
    return records


def make_zone_id(station: str, time_block: str, lat: float, lon: float) -> str:
    """Create a stable frontend zone id."""
    station_part = str(station).lower().replace(" ", "_").replace("/", "_")
    time_part = str(time_block).split("_")[0]
    return f"{station_part}_{time_part}_{lat:.5f}_{lon:.5f}"


def load_outputs() -> dict[str, pd.DataFrame]:
    """Load available pipeline outputs."""
    tables: dict[str, pd.DataFrame] = {}
    tables["plan"] = pd.read_csv(config.TABLES_DIR / "daily_enforcement_plan.csv")
    tables["tori"] = pd.read_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet")
    tables["clean"] = pd.read_parquet(
        config.PROCESSED_DIR / "violations_clean.parquet",
        columns=[
            "violation_id",
            "created_date",
            "hour",
            "weekday_name",
            "station",
            "grid_id_250m",
            "vehicle_type_norm",
            "validation_status_norm",
            "violation_atoms",
            "record_weight",
            "lat",
            "lon",
        ],
    )
    optional_csvs = {
        "forecast_metrics": config.TABLES_DIR / "forecast_validation_metrics.csv",
        "tori_eval": config.TABLES_DIR / "tori_ranking_evaluation.csv",
        "robust": config.TABLES_DIR / "robust_topk_overlap_all_vs_high_confidence.csv",
        "forecast_predictions": config.TABLES_DIR / "next_day_hotspot_predictions.csv",
        "operational_impact": config.TABLES_DIR / "operational_impact_plan.csv",
    }
    for name, path in optional_csvs.items():
        tables[name] = pd.read_csv(path) if path.exists() else pd.DataFrame()
    return tables


def load_strategy_summary() -> dict[str, Any]:
    """Load judge-facing strategy validation summary if present."""
    path = config.TABLES_DIR / "strategy_validation_summary.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_policy_summary() -> dict[str, Any]:
    """Load deployment policy simulation summary if present."""
    path = config.TABLES_DIR / "deployment_policy_summary.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def enrich_plan(plan: pd.DataFrame) -> pd.DataFrame:
    """Add frontend-friendly aliases to enforcement plan."""
    out = plan.copy()
    out["zone_id"] = [
        make_zone_id(row.station, row.time_block, row.centroid_lat, row.centroid_lon)
        for row in out.itertuples()
    ]
    out["zone_name"] = out["zone_name_readable"]
    out["police_station"] = out["station"]
    out["best_time_window"] = out["time_block"].map(TIME_BLOCK_LABELS).fillna(out["time_block"])
    out["expected_violations"] = out["violation_count"]
    out["expected_impact_score"] = out["final_tori_0_100"]
    out["final_priority_score"] = out["final_tori_0_100"]
    out["stable_pcis"] = out["stable_tori"]
    out["emerging_score"] = 0.0
    return out


def export_enforcement_plan(plan: pd.DataFrame, operational_impact: pd.DataFrame) -> pd.DataFrame:
    """Export enforcement plan JSON."""
    enriched = enrich_plan(plan)
    if not operational_impact.empty:
        impact_cols = [
            "zone_id",
            "estimated_capacity_loss_minutes",
            "capacity_loss_pressure_0_100",
            "queue_spillback_risk_0_100",
            "clearance_sla_minutes",
            "clearance_decision_band",
            "evidence_quality_score_0_100",
            "operational_priority_score_0_100",
            "estimated_lane_recovery_minutes",
            "estimated_lane_recovery_minutes_low",
            "estimated_lane_recovery_minutes_high",
            "recovery_minutes_per_resource_hour",
            "carriageway_recovery_class",
            "junction_clearance_bonus",
            "impact_confidence_note",
        ]
        enriched = enriched.merge(
            operational_impact[[col for col in impact_cols if col in operational_impact.columns]],
            on="zone_id",
            how="left",
        )
    else:
        enriched["estimated_lane_recovery_minutes"] = 0.0
        enriched["estimated_lane_recovery_minutes_low"] = 0.0
        enriched["estimated_lane_recovery_minutes_high"] = 0.0
        enriched["recovery_minutes_per_resource_hour"] = 0.0
        enriched["estimated_capacity_loss_minutes"] = 0.0
        enriched["capacity_loss_pressure_0_100"] = 0.0
        enriched["queue_spillback_risk_0_100"] = 0.0
        enriched["clearance_sla_minutes"] = 120
        enriched["clearance_decision_band"] = "Watchlist / routine patrol"
        enriched["evidence_quality_score_0_100"] = 0.0
        enriched["operational_priority_score_0_100"] = 0.0
        enriched["carriageway_recovery_class"] = "Unclassified carriageway"
        enriched["junction_clearance_bonus"] = 0.0
        enriched["impact_confidence_note"] = "Operational impact table not generated"
    sort_col = (
        "operational_priority_score_0_100"
        if "operational_priority_score_0_100" in enriched.columns
        else "final_priority_score"
    )
    enriched = enriched.sort_values(sort_col, ascending=False).reset_index(drop=True)
    enriched["rank"] = np.arange(1, len(enriched) + 1)
    columns = [
        "rank",
        "zone_id",
        "zone_name",
        "police_station",
        "best_time_window",
        "expected_violations",
        "expected_impact_score",
        "final_priority_score",
        "stable_pcis",
        "emerging_score",
        "confidence_band",
        "recommended_action",
        "reasoning",
        "repeat_vehicle_record_share",
        "chronic_vehicle_record_share",
        "multi_station_repeat_vehicle_share",
        "repeat_pressure_score_0_100",
        "chronic_vehicle_pressure_0_100",
        "patrol_gap_score_0_100",
        "patrol_gap_band",
        "estimated_patrol_hours",
        "estimated_tow_hours",
        "enforcement_roi",
        "estimated_capacity_loss_minutes",
        "capacity_loss_pressure_0_100",
        "queue_spillback_risk_0_100",
        "clearance_sla_minutes",
        "clearance_decision_band",
        "evidence_quality_score_0_100",
        "operational_priority_score_0_100",
        "estimated_lane_recovery_minutes",
        "estimated_lane_recovery_minutes_low",
        "estimated_lane_recovery_minutes_high",
        "recovery_minutes_per_resource_hour",
        "carriageway_recovery_class",
        "junction_clearance_bonus",
        "impact_confidence_note",
        "centroid_lat",
        "centroid_lon",
    ]
    columns = [col for col in columns if col in enriched.columns]
    write_frontend_json("enforcement_plan.json", normalize_records(enriched[columns]))
    return enriched


def export_hotspots_geojson(tori: pd.DataFrame, plan: pd.DataFrame) -> None:
    """Export hotspot point GeoJSON."""
    plan_lookup = enrich_plan(plan)[
        [
            "zone_id",
            "station",
            "time_block",
            "centroid_lat",
            "centroid_lon",
            "recommended_action",
            "reasoning",
            "enforcement_roi",
        ]
    ].copy()
    plan_lookup["lat_key"] = plan_lookup["centroid_lat"].round(6)
    plan_lookup["lon_key"] = plan_lookup["centroid_lon"].round(6)

    hotspots = tori.sort_values("final_tori", ascending=False).head(2500).copy()
    hotspots["lat_key"] = hotspots["centroid_lat"].round(6)
    hotspots["lon_key"] = hotspots["centroid_lon"].round(6)
    hotspots = hotspots.merge(
        plan_lookup.drop(columns=["centroid_lat", "centroid_lon"]),
        on=["station", "time_block", "lat_key", "lon_key"],
        how="left",
    )
    hotspots["zone_id"] = hotspots.apply(
        lambda row: row["zone_id"]
        if pd.notna(row.get("zone_id"))
        else make_zone_id(row["station"], row["time_block"], row["centroid_lat"], row["centroid_lon"]),
        axis=1,
    )
    hotspots["zone_name"] = hotspots["zone_name"].where(
        ~hotspots["zone_name"].astype(str).str.upper().isin(["NO JUNCTION", "UNKNOWN", "NAN"]),
        hotspots["location_mode"].astype(str).str.slice(0, 80),
    )
    hotspots["recommended_action"] = hotspots["recommended_action"].fillna("Targeted patrol")
    hotspots["reasoning"] = hotspots["reasoning"].fillna(
        "High-priority hotspot based on traffic obstruction risk components."
    )
    hotspots["enforcement_roi"] = hotspots["enforcement_roi"].fillna(0)

    features = []
    for row in hotspots.itertuples(index=False):
        properties = {
            "zone_id": row.zone_id,
            "zone_name": row.zone_name,
            "police_station": row.station,
            "centroid_lat": row.centroid_lat,
            "centroid_lon": row.centroid_lon,
            "tori_score": row.final_tori_0_100,
            "stable_pcis": row.stable_tori,
            "emerging_score": 0,
            "final_priority_score": row.final_tori_0_100,
            "recommended_action": row.recommended_action,
            "confidence_band": row.confidence_band,
            "best_time_window": TIME_BLOCK_LABELS.get(row.time_block, row.time_block),
            "expected_violations": row.violation_count,
            "expected_impact_score": row.final_tori_0_100,
            "enforcement_roi": row.enforcement_roi,
            "reasoning": row.reasoning,
            "repeat_pressure_score_0_100": getattr(row, "repeat_pressure_score_0_100", None),
            "chronic_vehicle_pressure_0_100": getattr(row, "chronic_vehicle_pressure_0_100", None),
            "patrol_gap_score_0_100": getattr(row, "patrol_gap_score_0_100", None),
            "patrol_gap_band": getattr(row, "patrol_gap_band", None),
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
    write_frontend_json(
        "hotspots.geojson",
        {"type": "FeatureCollection", "features": features},
    )


def export_station_summary(tori: pd.DataFrame, plan: pd.DataFrame, operational_impact: pd.DataFrame) -> None:
    """Export station-level summary."""
    station = (
        tori.groupby("station")
        .agg(
            total_violations=("violation_count", "sum"),
            high_impact_hotspots=("final_tori_0_100", lambda s: int((s >= 90).sum())),
            avg_priority_score=("final_tori_0_100", "mean"),
            peak_time_window=("time_block", lambda s: s.mode().iloc[0] if len(s.mode()) else "Unknown"),
            confidence_score=("confidence_score", "mean"),
            avg_repeat_pressure=("repeat_pressure_score_0_100", "mean"),
            avg_patrol_gap=("patrol_gap_score_0_100", "mean"),
        )
        .reset_index()
    )
    plan_station = (
        enrich_plan(plan)
        .groupby("station")
        .agg(
            top_action=("recommended_action", lambda s: s.mode().iloc[0] if len(s.mode()) else "Targeted patrol"),
            patrol_hours_required=("estimated_patrol_hours", "sum"),
            tow_hours_required=("estimated_tow_hours", "sum"),
        )
        .reset_index()
    )
    station = station.merge(plan_station, on="station", how="left").fillna(
        {"top_action": "Targeted patrol", "patrol_hours_required": 0, "tow_hours_required": 0}
    )
    if not operational_impact.empty:
        impact_station = (
            operational_impact.groupby("station")
            .agg(
                recoverable_lane_minutes=("estimated_lane_recovery_minutes", "sum"),
                recovery_minutes_per_resource_hour=("recovery_minutes_per_resource_hour", "mean"),
            )
            .reset_index()
        )
        station = station.merge(impact_station, on="station", how="left")
    else:
        station["recoverable_lane_minutes"] = 0.0
        station["recovery_minutes_per_resource_hour"] = 0.0
    station["police_station"] = station["station"]
    station["peak_time_window"] = station["peak_time_window"].map(TIME_BLOCK_LABELS).fillna(station["peak_time_window"])
    station["confidence_band"] = pd.cut(
        station["confidence_score"],
        bins=[-0.1, 0.45, 0.70, 1.1],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    columns = [
        "police_station",
        "total_violations",
        "high_impact_hotspots",
        "avg_priority_score",
        "peak_time_window",
        "top_action",
        "confidence_band",
        "patrol_hours_required",
        "tow_hours_required",
        "recoverable_lane_minutes",
        "recovery_minutes_per_resource_hour",
        "avg_repeat_pressure",
        "avg_patrol_gap",
    ]
    write_frontend_json("station_summary.json", normalize_records(station[columns]))


def export_forecast_summary(forecast_predictions: pd.DataFrame, plan: pd.DataFrame) -> None:
    """Export forecast summary if available."""
    if forecast_predictions.empty:
        write_frontend_json("forecast_summary.json", [])
        return
    frame = forecast_predictions.head(500).copy()
    frame["zone_id"] = [
        make_zone_id(row.station, row.time_block, row.centroid_lat, row.centroid_lon)
        for row in frame.itertuples()
    ]
    frame["best_time_window"] = frame["time_block"].map(TIME_BLOCK_LABELS).fillna(frame["time_block"])
    frame["zone_name"] = frame["grid_id_250m"]
    frame["police_station"] = frame["station"]
    frame["predicted_impact_score"] = frame.get("pred_selected", frame.get("pred_baseline", 0))
    frame["predicted_violation_count"] = frame.get("next_day_violation_count", 0)
    frame["emerging_score"] = 0
    frame["confidence_band"] = "Medium"
    columns = [
        "created_date",
        "best_time_window",
        "zone_id",
        "zone_name",
        "police_station",
        "predicted_impact_score",
        "predicted_violation_count",
        "emerging_score",
        "confidence_band",
    ]
    write_frontend_json("forecast_summary.json", normalize_records(frame[columns]))


def export_metrics(
    plan: pd.DataFrame,
    tori: pd.DataFrame,
    clean: pd.DataFrame,
    forecast_metrics: pd.DataFrame,
    tori_eval: pd.DataFrame,
    robust: pd.DataFrame,
    operational_impact: pd.DataFrame,
    strategy_summary: dict[str, Any],
    policy_summary: dict[str, Any],
) -> None:
    """Export dashboard-level metrics."""
    selected_forecast = forecast_metrics[forecast_metrics.get("selected_for_predictions", False) == True] if not forecast_metrics.empty else pd.DataFrame()
    selected_20 = selected_forecast[selected_forecast["k"] == 20].iloc[0] if not selected_forecast.empty and not selected_forecast[selected_forecast["k"] == 20].empty else {}
    raw_20 = tori_eval[(tori_eval["method"] == "Raw violation density") & (tori_eval["k"] == 20)].iloc[0] if not tori_eval.empty and not tori_eval[(tori_eval["method"] == "Raw violation density") & (tori_eval["k"] == 20)].empty else {}
    robust_20 = robust[robust["k"] == 20].iloc[0] if not robust.empty and not robust[robust["k"] == 20].empty else {}
    impact_top20 = operational_impact.head(20) if not operational_impact.empty else pd.DataFrame()

    metrics = {
        "total_violations": int(len(clean)),
        "total_hotspots": int(len(tori)),
        "high_impact_hotspots": int((tori["final_tori_0_100"] >= 90).sum()),
        "predicted_risk_tomorrow": clean_value(selected_20.get("capture_at_k_mean")) if isinstance(selected_20, pd.Series) else None,
        "tow_priority_zones": int(plan["recommended_action"].str.contains("Tow", case=False, na=False).sum()),
        "average_confidence": float(tori["confidence_score"].mean()),
        "capture_at_10": clean_value(selected_forecast[selected_forecast["k"] == 10]["capture_at_k_mean"].iloc[0]) if not selected_forecast.empty and not selected_forecast[selected_forecast["k"] == 10].empty else None,
        "capture_at_20": clean_value(selected_20.get("capture_at_k_mean")) if isinstance(selected_20, pd.Series) else None,
        "precision_at_10": None,
        "precision_at_20": None,
        "raw_count_baseline_capture_at_20": clean_value(raw_20.get("capture_at_k_mean")) if isinstance(raw_20, pd.Series) else None,
        "parkpulse_capture_at_20": clean_value(selected_20.get("capture_at_k_mean")) if isinstance(selected_20, pd.Series) else None,
        "robust_top20_overlap": clean_value(robust_20.get("topk_overlap_share")) if isinstance(robust_20, pd.Series) else None,
        "headline_recurrence_signal": strategy_summary.get("headline_recurrence_signal"),
        "headline_recurrence_capture_at_20": clean_value(strategy_summary.get("headline_recurrence_capture_at_20")),
        "selected_forecast_model": strategy_summary.get("selected_forecast_model"),
        "selected_forecast_capture_at_20": clean_value(strategy_summary.get("selected_forecast_capture_at_20")),
        "weighted_obstruction_capture_at_20": clean_value(strategy_summary.get("weighted_obstruction_capture_at_20")),
        "time_safe_historical_capture_at_20": clean_value(strategy_summary.get("time_safe_historical_capture_at_20")),
        "tori_capture_at_20": clean_value(strategy_summary.get("tori_capture_at_20")),
        "elrm_capture_at_20": clean_value(strategy_summary.get("elrm_capture_at_20")),
        "elrm_efficiency_capture_at_20": clean_value(strategy_summary.get("elrm_efficiency_capture_at_20")),
        "capacity_loss_capture_at_20": clean_value(strategy_summary.get("capacity_loss_capture_at_20")),
        "spillback_risk_capture_at_20": clean_value(strategy_summary.get("spillback_risk_capture_at_20")),
        "operational_priority_capture_at_20": clean_value(strategy_summary.get("operational_priority_capture_at_20")),
        "evidence_quality_capture_at_20": clean_value(strategy_summary.get("evidence_quality_capture_at_20")),
        "best_validation_method_at_20": strategy_summary.get("best_validation_method_at_20"),
        "best_validation_capture_at_20": clean_value(strategy_summary.get("best_validation_capture_at_20")),
        "evening_records": clean_value(strategy_summary.get("evening_records")),
        "night_records": clean_value(strategy_summary.get("night_records")),
        "evening_to_night_record_ratio": clean_value(strategy_summary.get("evening_to_night_record_ratio")),
        "evening_window_quality_note": strategy_summary.get("evening_window_quality_note"),
        "judge_positioning": strategy_summary.get("judge_positioning"),
        "top20_lane_recovery_minutes": round(float(impact_top20["estimated_lane_recovery_minutes"].sum()), 1) if not impact_top20.empty else None,
        "top20_lane_recovery_minutes_low": round(float(impact_top20["estimated_lane_recovery_minutes_low"].sum()), 1) if not impact_top20.empty and "estimated_lane_recovery_minutes_low" in impact_top20.columns else None,
        "top20_lane_recovery_minutes_high": round(float(impact_top20["estimated_lane_recovery_minutes_high"].sum()), 1) if not impact_top20.empty and "estimated_lane_recovery_minutes_high" in impact_top20.columns else None,
        "top20_capacity_loss_minutes": round(float(impact_top20["estimated_capacity_loss_minutes"].sum()), 1) if not impact_top20.empty and "estimated_capacity_loss_minutes" in impact_top20.columns else None,
        "top20_mean_spillback_risk": round(float(impact_top20["queue_spillback_risk_0_100"].mean()), 1) if not impact_top20.empty and "queue_spillback_risk_0_100" in impact_top20.columns else None,
        "top20_mean_evidence_quality": round(float(impact_top20["evidence_quality_score_0_100"].mean()), 1) if not impact_top20.empty and "evidence_quality_score_0_100" in impact_top20.columns else None,
        "top20_mean_repeat_pressure": round(float(impact_top20["repeat_pressure_score_0_100"].mean()), 1) if not impact_top20.empty and "repeat_pressure_score_0_100" in impact_top20.columns else None,
        "top20_mean_patrol_gap": round(float(impact_top20["patrol_gap_score_0_100"].mean()), 1) if not impact_top20.empty and "patrol_gap_score_0_100" in impact_top20.columns else None,
        "plan_lane_recovery_minutes": round(float(operational_impact["estimated_lane_recovery_minutes"].sum()), 1) if not operational_impact.empty else None,
        "plan_capacity_loss_minutes": round(float(operational_impact["estimated_capacity_loss_minutes"].sum()), 1) if not operational_impact.empty and "estimated_capacity_loss_minutes" in operational_impact.columns else None,
        "high_spillback_risk_zones": int((operational_impact["queue_spillback_risk_0_100"] >= 70).sum()) if not operational_impact.empty and "queue_spillback_risk_0_100" in operational_impact.columns else None,
        "chronic_repeat_priority_zones": int((operational_impact["repeat_pressure_score_0_100"] >= 85).sum()) if not operational_impact.empty and "repeat_pressure_score_0_100" in operational_impact.columns else None,
        "patrol_gap_priority_zones": int((operational_impact["patrol_gap_score_0_100"] >= 85).sum()) if not operational_impact.empty and "patrol_gap_score_0_100" in operational_impact.columns else None,
        "immediate_clearance_zones": int((operational_impact["clearance_sla_minutes"] <= 30).sum()) if not operational_impact.empty and "clearance_sla_minutes" in operational_impact.columns else None,
        "median_clearance_sla_minutes": int(operational_impact["clearance_sla_minutes"].median()) if not operational_impact.empty and "clearance_sla_minutes" in operational_impact.columns else None,
        "avg_evidence_quality_score": round(float(operational_impact["evidence_quality_score_0_100"].mean()), 1) if not operational_impact.empty and "evidence_quality_score_0_100" in operational_impact.columns else None,
        "recovery_minutes_per_resource_hour": round(float(operational_impact["recovery_minutes_per_resource_hour"].mean()), 1) if not operational_impact.empty else None,
        "best_station_for_recovery": (
            operational_impact.groupby("station")["estimated_lane_recovery_minutes"].sum().sort_values(ascending=False).index[0]
            if not operational_impact.empty
            else None
        ),
        "standard_budget_policy": policy_summary.get("standard_budget_policy"),
        "standard_budget_best_recovery_policy": policy_summary.get("standard_budget_best_recovery_policy"),
        "standard_budget_recovery_minutes": clean_value(policy_summary.get("standard_budget_recovery_minutes")),
        "standard_budget_capacity_loss_minutes": clean_value(policy_summary.get("standard_budget_capacity_loss_minutes")),
        "standard_budget_high_spillback_zones": clean_value(policy_summary.get("standard_budget_high_spillback_zones")),
        "standard_budget_immediate_clearance_zones": clean_value(policy_summary.get("standard_budget_immediate_clearance_zones")),
        "standard_budget_recovery_per_resource_hour": clean_value(policy_summary.get("standard_budget_recovery_per_resource_hour")),
        "standard_budget_mean_evidence_quality": clean_value(policy_summary.get("standard_budget_mean_evidence_quality")),
        "parkpulse_vs_tori_recovery_uplift_pct": clean_value(policy_summary.get("parkpulse_vs_tori_recovery_uplift_pct")),
        "parkpulse_vs_density_recovery_uplift_pct": clean_value(policy_summary.get("parkpulse_vs_density_recovery_uplift_pct")),
        "policy_lab_note": policy_summary.get("policy_lab_note"),
    }
    write_frontend_json("metrics.json", metrics)


def top_n_counts(series: pd.Series, n: int = 8) -> list[dict[str, Any]]:
    """Return top value counts as chart records."""
    return normalize_records(series.value_counts().head(n).rename_axis("name").reset_index(name="value"))


def export_hotspot_drilldown(clean: pd.DataFrame, tori: pd.DataFrame, plan: pd.DataFrame) -> None:
    """Export compact drilldown data for top enforcement zones."""
    enriched = enrich_plan(plan).head(80)
    tori_lookup = tori.copy()
    tori_lookup["lat_key"] = tori_lookup["centroid_lat"].round(6)
    tori_lookup["lon_key"] = tori_lookup["centroid_lon"].round(6)
    records = []
    for row in enriched.itertuples(index=False):
        matches = tori_lookup[
            (tori_lookup["station"] == row.station)
            & (tori_lookup["time_block"] == row.time_block)
            & (tori_lookup["lat_key"] == round(row.centroid_lat, 6))
            & (tori_lookup["lon_key"] == round(row.centroid_lon, 6))
        ]
        grid_id = matches["grid_id_250m"].iloc[0] if not matches.empty else None
        zone_data = clean[clean["grid_id_250m"] == grid_id].copy() if grid_id else clean.iloc[0:0].copy()
        zone_data["created_date"] = pd.to_datetime(zone_data["created_date"], errors="coerce")
        hourly = (
            zone_data.groupby("hour").size().reindex(range(24), fill_value=0).rename_axis("hour").reset_index(name="value")
            if not zone_data.empty
            else pd.DataFrame({"hour": list(range(24)), "value": [0] * 24})
        )
        recurrence = (
            zone_data.groupby(zone_data["created_date"].dt.strftime("%Y-%m-%d")).size().tail(45).rename_axis("date").reset_index(name="value")
            if not zone_data.empty
            else pd.DataFrame(columns=["date", "value"])
        )
        records.append(
            {
                "zone_id": row.zone_id,
                "zone_name": row.zone_name,
                "hourly_pattern": normalize_records(hourly),
                "weekday_pattern": top_n_counts(zone_data["weekday_name"]) if not zone_data.empty else [],
                "violation_mix": top_n_counts(zone_data["violation_atoms"]) if not zone_data.empty else [],
                "vehicle_mix": top_n_counts(zone_data["vehicle_type_norm"]) if not zone_data.empty else [],
                "validation_status_mix": top_n_counts(zone_data["validation_status_norm"]) if not zone_data.empty else [],
                "recurrence_trend": normalize_records(recurrence),
                "explanation": row.reasoning,
            }
        )
    write_frontend_json("hotspot_drilldown.json", records)


def main() -> None:
    config.ensure_directories()
    FRONTEND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tables = load_outputs()
    strategy_summary = load_strategy_summary()
    policy_summary = load_policy_summary()
    write_frontend_json("strategy_validation_summary.json", strategy_summary)
    write_frontend_json("deployment_policy_summary.json", policy_summary)
    enriched_plan = export_enforcement_plan(tables["plan"], tables["operational_impact"])
    export_hotspots_geojson(tables["tori"], tables["plan"])
    export_station_summary(tables["tori"], tables["plan"], tables["operational_impact"])
    export_forecast_summary(tables["forecast_predictions"], tables["plan"])
    export_metrics(
        enriched_plan,
        tables["tori"],
        tables["clean"],
        tables["forecast_metrics"],
        tables["tori_eval"],
        tables["robust"],
        tables["operational_impact"],
        strategy_summary,
        policy_summary,
    )
    export_hotspot_drilldown(tables["clean"], tables["tori"], tables["plan"])
    print(f"Wrote frontend artifacts to {FRONTEND_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
