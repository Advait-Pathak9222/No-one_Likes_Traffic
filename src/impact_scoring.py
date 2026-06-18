"""TORI scoring for traffic obstruction risk."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .exposure import build_exposure_table, percentile_rank


def _mode_or_unknown(series: pd.Series) -> str:
    mode = series.dropna().astype(str).mode()
    return mode.iloc[0] if len(mode) else "Unknown"


def _add_vehicle_repeat_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add city-wide repeat/chronic vehicle signals to record-level data.

    The vehicle number is anonymized, but if the same anonymized id appears
    repeatedly it is still useful operational evidence: the hotspot may need
    fixed-window enforcement, repeat-offender follow-up, or towing rather than
    one-off challans.
    """
    out = df.copy()
    if "vehicle_number" not in out.columns:
        out["vehicle_key"] = np.nan
        out["vehicle_city_record_count"] = 0.0
        out["vehicle_city_station_count"] = 0.0
    else:
        vehicle = out["vehicle_number"].fillna("").astype(str).str.strip()
        invalid = vehicle.str.lower().isin({"", "nan", "none", "unknown", "na"})
        out["vehicle_key"] = vehicle.mask(invalid)
        out["vehicle_city_record_count"] = (
            out.groupby("vehicle_key", dropna=True)["violation_id"].transform("count").fillna(0.0)
        )
        out["vehicle_city_station_count"] = (
            out.groupby("vehicle_key", dropna=True)["station"].transform("nunique").fillna(0.0)
        )

    out["is_repeat_vehicle_record"] = out["vehicle_city_record_count"] >= 2
    out["is_chronic_vehicle_record"] = out["vehicle_city_record_count"] >= 3
    out["is_multi_station_repeat_vehicle_record"] = (
        out["is_repeat_vehicle_record"] & (out["vehicle_city_station_count"] >= 2)
    )
    out["repeat_vehicle_weight"] = out["record_weight"] * out["is_repeat_vehicle_record"].astype(float)
    out["chronic_vehicle_weight"] = out["record_weight"] * out["is_chronic_vehicle_record"].astype(float)
    out["multi_station_repeat_vehicle_weight"] = (
        out["record_weight"] * out["is_multi_station_repeat_vehicle_record"].astype(float)
    )
    return out


def build_hotspot_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate clean records into grid/station/time-block hotspot features."""
    df = _add_vehicle_repeat_features(df)
    group_cols = ["grid_id_250m", "station", "time_block"]
    hotspot = (
        df.groupby(group_cols, dropna=False)
        .agg(
            violation_count=("violation_id", "count"),
            weighted_violation_count=("record_weight", "sum"),
            mean_record_weight=("record_weight", "mean"),
            mean_violation_severity=("violation_severity", "mean"),
            mean_vehicle_obstruction=("vehicle_obstruction_weight", "mean"),
            mean_validation_confidence=("validation_confidence", "mean"),
            mean_junction_criticality=("junction_criticality", "mean"),
            active_days=("created_date", "nunique"),
            unique_vehicle_count=("vehicle_key", "nunique"),
            repeat_vehicle_record_share=("is_repeat_vehicle_record", "mean"),
            chronic_vehicle_record_share=("is_chronic_vehicle_record", "mean"),
            multi_station_repeat_vehicle_share=("is_multi_station_repeat_vehicle_record", "mean"),
            repeat_vehicle_weighted_count=("repeat_vehicle_weight", "sum"),
            chronic_vehicle_weighted_count=("chronic_vehicle_weight", "sum"),
            multi_station_repeat_vehicle_weighted_count=("multi_station_repeat_vehicle_weight", "sum"),
            mean_vehicle_city_record_count=("vehicle_city_record_count", "mean"),
            max_vehicle_city_record_count=("vehicle_city_record_count", "max"),
            centroid_lat=("lat", "mean"),
            centroid_lon=("lon", "mean"),
            zone_name=("junction", _mode_or_unknown),
            location_mode=("location_text", _mode_or_unknown),
            device_count=("device_id", "nunique"),
            created_by_count=("created_by_id", "nunique"),
            high_confidence_share=("is_high_confidence_record", "mean"),
            signal_share=("is_signal_area", "mean"),
            market_share=("is_market_area", "mean"),
            metro_share=("is_metro_area", "mean"),
            main_road_share=("has_main_road", "mean"),
            crossing_share=("has_crossing", "mean"),
            footpath_share=("has_footpath", "mean"),
        )
        .reset_index()
    )
    weighted_denominator = hotspot["weighted_violation_count"].clip(lower=1e-9)
    hotspot["repeat_vehicle_weighted_share"] = (
        hotspot["repeat_vehicle_weighted_count"] / weighted_denominator
    ).clip(0, 1)
    hotspot["chronic_vehicle_weighted_share"] = (
        hotspot["chronic_vehicle_weighted_count"] / weighted_denominator
    ).clip(0, 1)
    hotspot["multi_station_repeat_vehicle_weighted_share"] = (
        hotspot["multi_station_repeat_vehicle_weighted_count"] / weighted_denominator
    ).clip(0, 1)
    hotspot["repeat_vehicle_share"] = hotspot["repeat_vehicle_record_share"]
    hotspot["chronic_vehicle_share"] = hotspot["chronic_vehicle_record_share"]

    city_active_days = max(int(df["created_date"].nunique()), 1)
    hotspot["active_day_share"] = hotspot["active_days"] / city_active_days

    station_totals = df.groupby("station").size().rename("station_total_count")
    hotspot = hotspot.merge(station_totals, on="station", how="left")
    hotspot["station_normalized_pressure_raw"] = hotspot["violation_count"] / hotspot[
        "station_total_count"
    ].clip(lower=1)

    exposure = build_exposure_table(df)
    exposure_cols = [
        "grid_id_250m",
        "station",
        "time_block",
        "enforcement_exposure_raw",
        "enforcement_exposure_score",
        "exposure_adjusted_density",
        "exposure_adjusted_density_score",
    ]
    hotspot = hotspot.merge(exposure[exposure_cols], on=group_cols, how="left")
    return hotspot


def add_tori_scores(hotspot: pd.DataFrame) -> pd.DataFrame:
    """Add stable, emerging, and final TORI scores."""
    out = hotspot.copy()
    out["density_score"] = percentile_rank(np.log1p(out["violation_count"]))
    out["weighted_density_score"] = percentile_rank(np.log1p(out["weighted_violation_count"]))
    out["repeat_pressure_raw"] = (
        0.35 * out["repeat_vehicle_record_share"].fillna(0)
        + 0.35 * out["chronic_vehicle_record_share"].fillna(0)
        + 0.15 * out["repeat_vehicle_weighted_share"].fillna(0)
        + 0.15 * out["multi_station_repeat_vehicle_share"].fillna(0)
    ) * (0.75 + 0.25 * out["weighted_density_score"])
    out["repeat_pressure_score"] = percentile_rank(out["repeat_pressure_raw"])
    out["repeat_pressure_score_0_100"] = 100 * out["repeat_pressure_score"]
    out["chronic_vehicle_pressure_0_100"] = 100 * percentile_rank(
        (
            0.65 * out["chronic_vehicle_record_share"].fillna(0)
            + 0.35 * out["chronic_vehicle_weighted_share"].fillna(0)
        )
        * (0.75 + 0.25 * out["weighted_density_score"])
    )

    out["persistence_score"] = (
        0.45 * percentile_rank(out["active_day_share"])
        + 0.20 * percentile_rank(out["station_normalized_pressure_raw"])
        + 0.20 * out["repeat_pressure_score"]
        + 0.15 * percentile_rank(out["chronic_vehicle_record_share"])
    )
    out["temporal_pressure"] = out.groupby("station")["violation_count"].transform(
        lambda s: percentile_rank(s)
    )
    out["junction_criticality_score"] = percentile_rank(out["mean_junction_criticality"])
    out["violation_severity_score"] = percentile_rank(out["mean_violation_severity"])
    out["vehicle_obstruction_score"] = percentile_rank(out["mean_vehicle_obstruction"])
    out["validation_confidence_score"] = percentile_rank(out["mean_validation_confidence"])

    out["stable_tori"] = (
        0.25 * out["density_score"]
        + 0.20 * out["persistence_score"]
        + 0.15 * out["temporal_pressure"]
        + 0.15 * out["junction_criticality_score"]
        + 0.10 * out["violation_severity_score"]
        + 0.10 * out["vehicle_obstruction_score"]
        + 0.05 * out["validation_confidence_score"]
    )

    out["exposure_adjusted_tori"] = (
        0.40 * out["exposure_adjusted_density_score"].fillna(out["density_score"])
        + 0.20 * out["persistence_score"]
        + 0.15 * out["temporal_pressure"]
        + 0.10 * out["junction_criticality_score"]
        + 0.075 * out["violation_severity_score"]
        + 0.075 * out["vehicle_obstruction_score"]
    )

    out["context_risk_score"] = (
        0.25 * percentile_rank(out["signal_share"])
        + 0.20 * percentile_rank(out["crossing_share"])
        + 0.20 * percentile_rank(out["main_road_share"])
        + 0.15 * percentile_rank(out["market_share"])
        + 0.10 * percentile_rank(out["metro_share"])
        + 0.10 * percentile_rank(out["footpath_share"])
    )
    out["patrol_gap_raw"] = (
        out["exposure_adjusted_density_score"].fillna(out["density_score"])
        * (1 - out["enforcement_exposure_score"].fillna(0.5)).clip(lower=0, upper=1)
        * (0.50 + 0.50 * out["weighted_density_score"])
    )
    out["patrol_gap_score"] = percentile_rank(out["patrol_gap_raw"])
    out["patrol_gap_score_0_100"] = 100 * out["patrol_gap_score"]
    out["patrol_gap_band"] = pd.cut(
        out["patrol_gap_score_0_100"],
        bins=[-0.01, 50, 75, 90, 100.01],
        labels=["Covered", "Watch", "Gap", "Critical gap"],
    ).astype(str)

    out["final_tori"] = (
        0.66 * out["stable_tori"]
        + 0.16 * out["exposure_adjusted_tori"]
        + 0.08 * out["context_risk_score"]
        + 0.06 * out["repeat_pressure_score"]
        + 0.04 * out["patrol_gap_score"]
    )
    out["final_tori_0_100"] = 100 * percentile_rank(out["final_tori"])
    out["confidence_score"] = (
        0.45 * percentile_rank(out["violation_count"])
        + 0.25 * out["high_confidence_share"].fillna(0)
        + 0.20 * percentile_rank(out["active_days"])
        + 0.10 * (1 - out["enforcement_exposure_score"].fillna(0.5).sub(0.5).abs() * 2).clip(0, 1)
    )
    out["confidence_band"] = pd.cut(
        out["confidence_score"],
        bins=[-0.01, 0.45, 0.70, 1.01],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    return out


def build_tori_table(df: pd.DataFrame) -> pd.DataFrame:
    """Create the final hotspot TORI table."""
    hotspot = build_hotspot_feature_table(df)
    return add_tori_scores(hotspot)


def main() -> None:
    config.ensure_directories()
    df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")
    tori = build_tori_table(df)
    tori.to_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet", index=False)
    tori.sort_values("final_tori", ascending=False).head(250).to_csv(
        config.TABLES_DIR / "top_hotspots_by_tori.csv", index=False
    )
    tori.sort_values("violation_count", ascending=False).head(250).to_csv(
        config.TABLES_DIR / "top_hotspots_by_density.csv", index=False
    )
    tori.sort_values("exposure_adjusted_tori", ascending=False).head(250).to_csv(
        config.TABLES_DIR / "top_hotspots_by_exposure_adjusted_tori.csv", index=False
    )
    print(f"Wrote TORI table with {len(tori):,} hotspot rows.")


if __name__ == "__main__":
    main()
