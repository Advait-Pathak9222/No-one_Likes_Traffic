"""Build the canonical clean violation table."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config
from .data_loader import (
    build_column_audit,
    build_dataset_summary,
    load_raw_data,
    standardize_columns,
)
from .spatial_features import add_coordinate_features, add_grid_features
from .time_features import add_time_features
from .vehicle_normalizer import add_vehicle_features
from .violation_parser import add_violation_features


def _normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _normalize_bool(value: object) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def add_canonical_identity_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add stable aliases for key raw fields."""
    out = df.copy()
    out["violation_id"] = out.get("id", pd.Series(np.nan, index=out.index))
    out["station"] = out.get("police_station", pd.Series("Unknown", index=out.index)).map(
        lambda x: _normalize_text(x) or "Unknown"
    )
    out["junction"] = out.get("junction_name", pd.Series("Unknown", index=out.index)).map(
        lambda x: _normalize_text(x) or "Unknown"
    )
    out["location_text"] = out.get("location", pd.Series("", index=out.index)).map(
        _normalize_text
    )
    out["data_sent_to_scita_bool"] = out.get(
        "data_sent_to_scita", pd.Series(False, index=out.index)
    ).map(_normalize_bool)
    return out


def normalize_validation_status(value: object, sent_to_scita: bool) -> str:
    """Normalize validation status while accounting for missing status."""
    if pd.isna(value) or not str(value).strip():
        return "missing_sent_to_scita" if sent_to_scita else "missing_not_sent"
    text = str(value).strip().lower()
    if text in {"approved", "rejected", "duplicate", "created1", "processing", "pending"}:
        return text
    return "unknown"


def add_validation_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add validation status and confidence columns."""
    out = df.copy()
    raw_status = out.get("validation_status", pd.Series(np.nan, index=out.index))
    out["validation_status_norm"] = [
        normalize_validation_status(status, sent)
        for status, sent in zip(raw_status, out["data_sent_to_scita_bool"])
    ]
    out["validation_confidence"] = out["validation_status_norm"].map(
        config.VALIDATION_CONFIDENCE_WEIGHTS
    ).fillna(config.VALIDATION_CONFIDENCE_WEIGHTS["unknown"])
    out["is_high_confidence_record"] = out["validation_confidence"] >= 0.75
    return out


def add_road_context_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create road-context keyword features from location, junction, and violations."""
    out = df.copy()
    junction_text = out.get("junction", pd.Series("", index=out.index)).astype(str)
    named_junction_mask = ~junction_text.str.upper().isin(
        {"", "NO JUNCTION", "UNKNOWN", "NAN"}
    )
    # Do not let the literal value "No Junction" trigger the word "JUNCTION".
    # Only named junction strings are allowed to contribute road-context tokens.
    junction_context = junction_text.where(named_junction_mask, "")
    context = (
        out.get("location_text", "").astype(str)
        + " "
        + junction_context.astype(str)
        + " "
        + out.get("violation_type", "").astype(str)
    ).str.upper()

    out["is_named_junction"] = named_junction_mask
    out["is_metro_area"] = context.str.contains(r"\bMETRO\b", regex=True, na=False)
    out["is_market_area"] = context.str.contains(
        r"MARKET|BAZAAR|BAZAR|MANDI|KR MARKET|CITY MARKET", regex=True, na=False
    )
    out["is_bus_stop_area"] = context.str.contains(
        r"BUS\s*STOP|BUSTOP|BMTC", regex=True, na=False
    )
    out["is_school_hospital_area"] = context.str.contains(
        r"SCHOOL|COLLEGE|HOSPITAL|CLINIC", regex=True, na=False
    )
    out["is_main_road_context"] = context.str.contains(r"MAIN ROAD|MAIN RD", regex=True, na=False)
    out["is_crossing_context"] = context.str.contains(
        r"CROSSING|JUNCTION|CIRCLE", regex=True, na=False
    )
    out["is_signal_area"] = context.str.contains(
        r"SIGNAL|TRAFFIC LIGHT|ZEBRA", regex=True, na=False
    )
    out["is_footpath_context"] = context.str.contains(
        r"FOOTPATH|SIDEWALK", regex=True, na=False
    )
    out["is_commercial_area"] = context.str.contains(
        r"PLAZA|MALL|COMPLEX|THEATRE|MARKET|BAZAAR|BAZAR|MAIN ROAD|COMMERCIAL",
        regex=True,
        na=False,
    )
    return out


def add_junction_criticality(df: pd.DataFrame) -> pd.DataFrame:
    """Add max-applicable junction and road-context criticality weight."""
    out = df.copy()
    weights = np.full(len(out), config.JUNCTION_CRITICALITY_WEIGHTS["default"], dtype=float)
    weights = np.where(
        out["is_school_hospital_area"] | out["is_footpath_context"],
        np.maximum(weights, config.JUNCTION_CRITICALITY_WEIGHTS["school_hospital_footpath"]),
        weights,
    )
    weights = np.where(
        out["is_metro_area"] | out["is_bus_stop_area"] | out["is_market_area"],
        np.maximum(weights, config.JUNCTION_CRITICALITY_WEIGHTS["metro_bus_market"]),
        weights,
    )
    weights = np.where(
        out["is_named_junction"] | out["is_crossing_context"],
        np.maximum(weights, config.JUNCTION_CRITICALITY_WEIGHTS["crossing_or_named_junction"]),
        weights,
    )
    weights = np.where(
        out["is_signal_area"] | out["has_signal_or_zebra"],
        np.maximum(weights, config.JUNCTION_CRITICALITY_WEIGHTS["signal_or_zebra"]),
        weights,
    )
    out["junction_criticality"] = weights
    return out


def add_base_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add row-level obstruction and analytical weight proxies."""
    out = df.copy()
    out["base_obstruction_score"] = (
        out["violation_severity"]
        * out["vehicle_obstruction_weight"]
        * out["junction_criticality"]
    )
    out["record_weight"] = out["base_obstruction_score"] * out["validation_confidence"]
    return out


def write_quality_outputs(df: pd.DataFrame, raw_df: pd.DataFrame) -> None:
    """Write audit, distribution, and top-category tables."""
    config.ensure_directories()
    build_dataset_summary(raw_df).to_csv(
        config.TABLES_DIR / "raw_dataset_summary.csv", index=False
    )
    build_column_audit(raw_df).to_csv(
        config.TABLES_DIR / "raw_column_audit.csv", index=False
    )

    summary_rows = [
        {"metric": "rows", "value": len(df)},
        {"metric": "columns", "value": len(df.columns)},
        {"metric": "created_min_ist", "value": str(df["created_ts"].min())},
        {"metric": "created_max_ist", "value": str(df["created_ts"].max())},
        {"metric": "active_days", "value": int(pd.Series(df["created_date"]).nunique())},
        {"metric": "police_stations", "value": int(df["station"].nunique())},
        {"metric": "junctions", "value": int(df["junction"].nunique())},
        {"metric": "devices", "value": int(df.get("device_id", pd.Series()).nunique())},
        {"metric": "valid_coordinate_rows", "value": int(df["has_valid_coordinates"].sum())},
        {"metric": "within_bengaluru_rows", "value": int(df["is_within_bengaluru_bounds"].sum())},
        {"metric": "grid_100m_cells", "value": int(df["grid_id_100m"].nunique())},
        {"metric": "grid_250m_cells", "value": int(df["grid_id_250m"].nunique())},
        {"metric": "high_confidence_records", "value": int(df["is_high_confidence_record"].sum())},
    ]
    pd.DataFrame(summary_rows).to_csv(
        config.TABLES_DIR / "data_quality_summary.csv", index=False
    )

    table_specs = {
        "top_police_stations.csv": df["station"].value_counts(dropna=False).head(50),
        "top_junctions.csv": df["junction"].value_counts(dropna=False).head(50),
        "vehicle_type_norm_distribution.csv": df["vehicle_type_norm"].value_counts(dropna=False),
        "validation_status_distribution.csv": df["validation_status_norm"].value_counts(dropna=False),
        "hourly_distribution.csv": df["hour"].value_counts(dropna=False).sort_index(),
        "time_block_distribution.csv": df["time_block"].value_counts(dropna=False),
    }
    for filename, series in table_specs.items():
        series.rename_axis("category").reset_index(name="count").to_csv(
            config.TABLES_DIR / filename, index=False
        )

    atom_counts = (
        df["violation_atoms"]
        .str.split("; ")
        .explode()
        .replace("", np.nan)
        .dropna()
        .value_counts()
        .rename_axis("violation_atom")
        .reset_index(name="count")
    )
    atom_counts.to_csv(config.TABLES_DIR / "violation_atom_distribution.csv", index=False)


def build_clean_dataset(nrows: int | None = None) -> pd.DataFrame:
    """Load raw data and build the canonical clean table."""
    config.ensure_directories()
    raw_df = standardize_columns(load_raw_data(nrows=nrows))

    df = raw_df.copy()
    df = add_canonical_identity_columns(df)
    df = add_time_features(df)
    df = add_coordinate_features(df)
    df = add_grid_features(df)
    df = add_vehicle_features(df)
    df = add_violation_features(df)
    df = add_validation_features(df)
    df = add_road_context_features(df)
    df = add_junction_criticality(df)
    df = add_base_scores(df)

    output_path = config.PROCESSED_DIR / "violations_clean.parquet"
    df.to_parquet(output_path, index=False)
    write_quality_outputs(df, raw_df)
    return df


def main() -> None:
    df = build_clean_dataset()
    print(f"Wrote clean dataset with {len(df):,} rows to {config.PROCESSED_DIR}")
    print(f"Wrote quality tables to {config.TABLES_DIR}")


if __name__ == "__main__":
    main()
