"""Theme-1 signal EDA for ParkPulse.

This module answers a specific hackathon question:

    From the data we were actually given, what signals can support illegal
    parking hotspot detection, traffic-impact approximation, and enforcement
    prioritisation?

It deliberately separates:
- strong dataset-backed signals,
- weak-but-useful inferred signals,
- and signals that are not supported by this dataset.
"""

from __future__ import annotations

import json
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config
from .time_features import parse_timestamp


TIME_BLOCK_ORDER = config.TIME_BLOCK_LABELS
CORE_RAW_COLUMNS = [
    "id",
    "latitude",
    "longitude",
    "location",
    "vehicle_number",
    "vehicle_type",
    "updated_vehicle_number",
    "updated_vehicle_type",
    "violation_type",
    "offence_code",
    "created_datetime",
    "closed_datetime",
    "modified_datetime",
    "device_id",
    "created_by_id",
    "center_code",
    "police_station",
    "data_sent_to_scita",
    "junction_name",
    "action_taken_timestamp",
    "data_sent_to_scita_timestamp",
    "validation_status",
    "validation_timestamp",
]


def _pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{100 * float(value):.1f}%"


def _clean_id(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    )


def _safe_quantiles(series: pd.Series) -> dict[str, float | None]:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return {"p50": None, "p75": None, "p90": None, "p95": None}
    return {
        "p50": round(float(values.quantile(0.50)), 2),
        "p75": round(float(values.quantile(0.75)), 2),
        "p90": round(float(values.quantile(0.90)), 2),
        "p95": round(float(values.quantile(0.95)), 2),
    }


def _write_json(path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_clean() -> pd.DataFrame:
    """Load the canonical clean table."""
    return pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")


def build_missingness_table(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise raw-column completeness."""
    rows = []
    for col in CORE_RAW_COLUMNS:
        if col not in df.columns:
            continue
        missing_share = float(df[col].isna().mean())
        rows.append(
            {
                "column": col,
                "available_rows": int(df[col].notna().sum()),
                "missing_rows": int(df[col].isna().sum()),
                "available_share": round(1.0 - missing_share, 5),
                "missing_share": round(missing_share, 5),
                "unique_values": int(df[col].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows).sort_values("available_share", ascending=True)


def build_timestamp_signal_table(df: pd.DataFrame) -> pd.DataFrame:
    """Check which lifecycle timestamps are actually usable."""
    created = df["created_ts"]
    timestamp_specs = {
        "modified_ts": df.get("modified_ts"),
        "validation_ts": df.get("validation_ts"),
        "closed_ts": parse_timestamp(df["closed_datetime"]) if "closed_datetime" in df.columns else None,
        "action_taken_ts": parse_timestamp(df["action_taken_timestamp"]) if "action_taken_timestamp" in df.columns else None,
        "data_sent_to_scita_ts": (
            parse_timestamp(df["data_sent_to_scita_timestamp"])
            if "data_sent_to_scita_timestamp" in df.columns
            else None
        ),
    }
    rows = []
    for name, ts in timestamp_specs.items():
        if ts is None:
            continue
        available = ts.notna()
        lag_hours = (ts - created).dt.total_seconds() / 3600
        quantiles = _safe_quantiles(lag_hours[available])
        rows.append(
            {
                "timestamp": name,
                "available_rows": int(available.sum()),
                "available_share": round(float(available.mean()), 5),
                "negative_lag_rows": int((lag_hours < 0).sum()),
                "lag_p50_hours": quantiles["p50"],
                "lag_p75_hours": quantiles["p75"],
                "lag_p90_hours": quantiles["p90"],
                "lag_p95_hours": quantiles["p95"],
            }
        )
    return pd.DataFrame(rows)


def build_repeat_vehicle_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Analyse chronic/repeat vehicle signal."""
    vehicle = _clean_id(df["vehicle_number"])
    frame = df.copy()
    frame["vehicle_key"] = vehicle
    frame["created_date_eda"] = pd.to_datetime(frame["created_date"], errors="coerce")
    known = frame[frame["vehicle_key"].notna()].copy()
    vehicle_stats = (
        known.groupby("vehicle_key")
        .agg(
            record_count=("violation_id", "count"),
            active_days=("created_date", "nunique"),
            station_count=("station", "nunique"),
            time_block_count=("time_block", "nunique"),
            weighted_obstruction=("record_weight", "sum"),
            first_seen=("created_date_eda", "min"),
            last_seen=("created_date_eda", "max"),
        )
        .reset_index()
    )
    vehicle_stats["is_repeat_vehicle"] = vehicle_stats["record_count"] >= 2
    vehicle_stats["is_chronic_vehicle_3plus"] = vehicle_stats["record_count"] >= 3
    vehicle_stats["is_multi_station_vehicle"] = vehicle_stats["station_count"] >= 2

    repeat_lookup = vehicle_stats.set_index("vehicle_key")["record_count"]
    known["vehicle_record_count"] = known["vehicle_key"].map(repeat_lookup)
    station_repeat = (
        known.assign(is_repeat_record=known["vehicle_record_count"] >= 2)
        .groupby(["station", "time_block"], dropna=False)
        .agg(
            records=("violation_id", "count"),
            repeat_vehicle_records=("is_repeat_record", "sum"),
            weighted_obstruction=("record_weight", "sum"),
        )
        .reset_index()
    )
    station_repeat["repeat_vehicle_record_share"] = (
        station_repeat["repeat_vehicle_records"] / station_repeat["records"].clip(lower=1)
    ).round(5)
    return vehicle_stats.sort_values("record_count", ascending=False), station_repeat.sort_values(
        "repeat_vehicle_record_share", ascending=False
    )


def build_station_time_signal(df: pd.DataFrame) -> pd.DataFrame:
    """Station×time-block signal table for deployment planning."""
    vehicle_counts = _clean_id(df["vehicle_number"]).value_counts()
    repeat_vehicles = set(vehicle_counts[vehicle_counts >= 2].index)
    frame = df.copy()
    frame["is_repeat_vehicle_record"] = _clean_id(frame["vehicle_number"]).isin(repeat_vehicles)
    station_time = (
        frame.groupby(["station", "time_block"], dropna=False)
        .agg(
            records=("violation_id", "count"),
            weighted_obstruction=("record_weight", "sum"),
            active_days=("created_date", "nunique"),
            unique_devices=("device_id", "nunique"),
            unique_officers=("created_by_id", "nunique"),
            high_confidence_share=("is_high_confidence_record", "mean"),
            sent_to_scita_share=("data_sent_to_scita_bool", "mean"),
            repeat_vehicle_record_share=("is_repeat_vehicle_record", "mean"),
            main_road_share=("has_main_road", "mean"),
            crossing_share=("has_crossing", "mean"),
            signal_zebra_share=("has_signal_or_zebra", "mean"),
            footpath_share=("has_footpath", "mean"),
            double_parking_share=("has_double_parking", "mean"),
            large_vehicle_share=("vehicle_obstruction_weight", lambda s: float((s >= 1.15).mean())),
        )
        .reset_index()
    )
    station_time["records_per_active_day"] = (
        station_time["records"] / station_time["active_days"].clip(lower=1)
    ).round(2)
    station_time["weighted_per_officer"] = (
        station_time["weighted_obstruction"] / station_time["unique_officers"].clip(lower=1)
    ).round(2)
    station_time["exposure_gap_score"] = (
        station_time["weighted_obstruction"]
        / np.log1p(station_time["unique_devices"].clip(lower=1) * station_time["unique_officers"].clip(lower=1))
    ).round(2)
    return station_time.sort_values("weighted_obstruction", ascending=False)


def build_context_signal(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise road/user-context signals from text and parsed violation atoms."""
    context_specs = {
        "main road / running lane": df["has_main_road"] | df["is_main_road_context"],
        "crossing / named junction": df["has_crossing"] | df["is_named_junction"],
        "signal / zebra": df["has_signal_or_zebra"] | df["is_signal_area"],
        "metro area": df["is_metro_area"],
        "market / commercial": df["is_market_area"] | df["is_commercial_area"],
        "bus stop": df["is_bus_stop_area"],
        "school / hospital": df["is_school_hospital_area"],
        "footpath / pedestrian edge": df["has_footpath"] | df["is_footpath_context"],
        "double parking": df["has_double_parking"],
        "large vehicle footprint": df["vehicle_obstruction_weight"] >= 1.15,
        "high-confidence record": df["is_high_confidence_record"],
        "sent to SCITA": df["data_sent_to_scita_bool"],
    }
    rows = []
    for label, mask in context_specs.items():
        part = df[mask.fillna(False)]
        rows.append(
            {
                "context_signal": label,
                "records": int(len(part)),
                "record_share": round(float(len(part) / len(df)), 5),
                "weighted_obstruction": round(float(part["record_weight"].sum()), 2),
                "weighted_share": round(float(part["record_weight"].sum() / df["record_weight"].sum()), 5),
                "mean_record_weight": round(float(part["record_weight"].mean()) if len(part) else 0.0, 4),
                "unique_stations": int(part["station"].nunique()) if len(part) else 0,
                "unique_250m_cells": int(part["grid_id_250m"].nunique()) if len(part) else 0,
            }
        )
    return pd.DataFrame(rows).sort_values("weighted_obstruction", ascending=False)


def build_spatial_concentration(df: pd.DataFrame) -> pd.DataFrame:
    """How concentrated is obstruction in a small number of grid cells?"""
    grid = (
        df.groupby("grid_id_250m")
        .agg(records=("violation_id", "count"), weighted_obstruction=("record_weight", "sum"))
        .sort_values("weighted_obstruction", ascending=False)
        .reset_index()
    )
    total_cells = len(grid)
    total_records = float(grid["records"].sum())
    total_weight = float(grid["weighted_obstruction"].sum())
    rows = []
    for label, n in [
        ("top_20_cells", 20),
        ("top_50_cells", 50),
        ("top_100_cells", 100),
        ("top_1pct_cells", max(1, int(round(total_cells * 0.01)))),
        ("top_5pct_cells", max(1, int(round(total_cells * 0.05)))),
        ("top_10pct_cells", max(1, int(round(total_cells * 0.10)))),
    ]:
        top = grid.head(n)
        rows.append(
            {
                "segment": label,
                "cell_count": int(n),
                "cell_share": round(float(n / total_cells), 5),
                "record_share": round(float(top["records"].sum() / total_records), 5),
                "weighted_obstruction_share": round(float(top["weighted_obstruction"].sum() / total_weight), 5),
            }
        )
    grid["cum_cell_share"] = (np.arange(len(grid)) + 1) / len(grid)
    grid["cum_weighted_share"] = grid["weighted_obstruction"].cumsum() / total_weight
    grid.to_csv(config.TABLES_DIR / "theme_signal_grid_concentration_curve.csv", index=False)
    return pd.DataFrame(rows)


def build_exposure_bias_signal() -> pd.DataFrame:
    """Summarise patrol/recording exposure bias from the exposure table."""
    path = config.PROCESSED_DIR / "exposure_table.parquet"
    if not path.exists():
        return pd.DataFrame()
    exposure = pd.read_parquet(path)
    metric_cols = [
        "violation_count",
        "unique_devices",
        "unique_created_by_ids",
        "active_recording_days",
        "enforcement_exposure_raw",
        "exposure_adjusted_density",
    ]
    corr = exposure[metric_cols].corr(numeric_only=True)["violation_count"].rename("correlation_with_raw_count")
    rows = corr.reset_index().rename(columns={"index": "metric"})
    rows["interpretation"] = np.where(
        rows["metric"].isin(["unique_devices", "unique_created_by_ids", "active_recording_days", "enforcement_exposure_raw"]),
        "High correlation means raw counts are partly exposure/recording intensity, not only true parking pressure.",
        "Core density metric.",
    )
    top_exposure_gap = exposure.sort_values("exposure_adjusted_density", ascending=False).head(100)
    top_exposure_gap.to_csv(config.TABLES_DIR / "theme_signal_top_exposure_adjusted_zones.csv", index=False)
    return rows


def build_weekday_timeblock_table(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise weekday/time-block pressure by number of active calendar days."""
    dates = df[["created_date", "weekday_name", "is_weekend"]].drop_duplicates()
    day_counts = dates.groupby(["weekday_name", "is_weekend"]).size().rename("active_calendar_days").reset_index()
    grouped = (
        df.groupby(["weekday_name", "is_weekend", "time_block"])
        .agg(records=("violation_id", "count"), weighted_obstruction=("record_weight", "sum"))
        .reset_index()
        .merge(day_counts, on=["weekday_name", "is_weekend"], how="left")
    )
    grouped["records_per_calendar_day"] = (
        grouped["records"] / grouped["active_calendar_days"].clip(lower=1)
    ).round(2)
    grouped["weighted_per_calendar_day"] = (
        grouped["weighted_obstruction"] / grouped["active_calendar_days"].clip(lower=1)
    ).round(2)
    return grouped.sort_values("weighted_per_calendar_day", ascending=False)


def build_signal_summary(
    df: pd.DataFrame,
    timestamp_signal: pd.DataFrame,
    repeat_vehicle: pd.DataFrame,
    spatial_concentration: pd.DataFrame,
    context_signal: pd.DataFrame,
    exposure_bias: pd.DataFrame,
) -> pd.DataFrame:
    """Create judge-facing EDA findings and backend opportunities."""
    known_vehicle_rows = int(_clean_id(df["vehicle_number"]).notna().sum())
    repeat_vehicle_records = int(
        repeat_vehicle.loc[repeat_vehicle["record_count"] >= 2, "record_count"].sum()
    )
    chronic_vehicle_records = int(
        repeat_vehicle.loc[repeat_vehicle["record_count"] >= 3, "record_count"].sum()
    )
    validation_row = timestamp_signal[timestamp_signal["timestamp"] == "validation_ts"]
    action_row = timestamp_signal[timestamp_signal["timestamp"] == "action_taken_ts"]
    closed_row = timestamp_signal[timestamp_signal["timestamp"] == "closed_ts"]
    validation_share = float(validation_row["available_share"].iloc[0]) if not validation_row.empty else 0.0
    action_share = float(action_row["available_share"].iloc[0]) if not action_row.empty else 0.0
    closed_share = float(closed_row["available_share"].iloc[0]) if not closed_row.empty else 0.0
    top5 = spatial_concentration[spatial_concentration["segment"] == "top_5pct_cells"]
    top5_weight = float(top5["weighted_obstruction_share"].iloc[0]) if not top5.empty else 0.0
    exposure_corr = exposure_bias[exposure_bias["metric"] == "enforcement_exposure_raw"]
    exposure_corr_value = float(exposure_corr["correlation_with_raw_count"].iloc[0]) if not exposure_corr.empty else None

    context_lookup = context_signal.set_index("context_signal")
    mainroad_share = float(context_lookup.loc["main road / running lane", "record_share"])
    large_vehicle_share = float(context_lookup.loc["large vehicle footprint", "record_share"])
    signal_share = float(context_lookup.loc["signal / zebra", "record_share"])

    rows = [
        {
            "signal": "Micro-hotspot concentration",
            "finding": f"Top 5% of 250m cells capture {_pct(top5_weight)} of weighted obstruction.",
            "support_level": "strong",
            "theme_use": "Targeted enforcement zones instead of broad patrol beats.",
            "backend_upgrade": "Use concentration curve to choose station-specific top-K deployment caps.",
        },
        {
            "signal": "Repeat / chronic vehicles",
            "finding": (
                f"{_pct(repeat_vehicle_records / max(1, known_vehicle_rows))} of known-vehicle records are repeat vehicles; "
                f"{_pct(chronic_vehicle_records / max(1, known_vehicle_rows))} are 3+ repeat records."
            ),
            "support_level": "strong",
            "theme_use": "Repeat-offender enforcement and tow/watchlist prioritisation.",
            "backend_upgrade": "Add chronic-repeat pressure and multi-station repeat flags to action rules.",
        },
        {
            "signal": "Road-space obstruction context",
            "finding": (
                f"Main-road context appears in {_pct(mainroad_share)} of records; large-footprint vehicle context appears in {_pct(large_vehicle_share)}."
            ),
            "support_level": "strong",
            "theme_use": "Quantify likely carriageway blockage from violation text and vehicle type.",
            "backend_upgrade": "Refine capacity-loss pressure with station-specific main-road/large-vehicle mixes.",
        },
        {
            "signal": "Signal/zebra/junction conflict",
            "finding": f"Signal/zebra context appears in {_pct(signal_share)} of records; named junctions are separately available.",
            "support_level": "medium",
            "theme_use": "Queue-spillback and junction-mouth clearance prioritisation.",
            "backend_upgrade": "Create a dedicated junction-mouth blocker class with higher SLA urgency.",
        },
        {
            "signal": "Recording/exposure bias",
            "finding": (
                f"Raw count correlation with enforcement exposure is {exposure_corr_value:.2f}."
                if exposure_corr_value is not None
                else "Exposure table unavailable."
            ),
            "support_level": "strong",
            "theme_use": "Avoid simply sending police to already-policed zones.",
            "backend_upgrade": "Keep exposure-adjusted density; add patrol-gap candidates where pressure is high despite low device/officer coverage.",
        },
        {
            "signal": "Validation and evidence latency",
            "finding": f"Validation timestamp availability is {_pct(validation_share)}.",
            "support_level": "medium",
            "theme_use": "Evidence-quality scoring and backend workflow SLA.",
            "backend_upgrade": "Add validation-lag penalties for stale evidence; show station evidence backlog.",
        },
        {
            "signal": "Action/closure outcome data",
            "finding": f"Action timestamp availability is {_pct(action_share)}; closed timestamp availability is {_pct(closed_share)}.",
            "support_level": "weak",
            "theme_use": "Cannot reliably learn true enforcement outcome or before/after congestion from current fields.",
            "backend_upgrade": "Do not train outcome claims from these fields; ask for live closure/tow workflow in production.",
        },
        {
            "signal": "SCITA transfer flag",
            "finding": f"SCITA transfer flag is available for {_pct(df['data_sent_to_scita_bool'].notna().mean())} of records and true for {_pct(df['data_sent_to_scita_bool'].mean())}.",
            "support_level": "medium",
            "theme_use": "Integration/evidence workflow signal, not direct traffic impact.",
            "backend_upgrade": "Use SCITA transfer as evidence-routing status and operational workflow readiness.",
        },
    ]
    return pd.DataFrame(rows)


def generate_theme_signal_plots(
    df: pd.DataFrame,
    station_time: pd.DataFrame,
    repeat_vehicle: pd.DataFrame,
    context_signal: pd.DataFrame,
) -> None:
    """Write Theme-1 EDA plots."""
    config.ensure_directories()

    top_stations = station_time.groupby("station")["weighted_obstruction"].sum().nlargest(14).index
    heat = (
        station_time[station_time["station"].isin(top_stations)]
        .pivot_table(index="station", columns="time_block", values="weighted_obstruction", fill_value=0)
        .reindex(columns=TIME_BLOCK_ORDER)
    )
    fig, ax = plt.subplots(figsize=(13, 7))
    im = ax.imshow(heat.values, aspect="auto", cmap="YlOrRd")
    ax.set_title("Theme Signal: Station × Time-Block Weighted Obstruction")
    ax.set_xticks(range(len(heat.columns)))
    ax.set_xticklabels(heat.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(heat.index)))
    ax.set_yticklabels(heat.index)
    fig.colorbar(im, ax=ax, label="weighted obstruction")
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "theme_station_timeblock_heatmap.png", dpi=160)
    plt.close(fig)

    counts = repeat_vehicle["record_count"].clip(upper=20)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(counts, bins=range(1, 22), color="#2874F0", edgecolor="white")
    ax.set_yscale("log")
    ax.set_title("Theme Signal: Repeat Vehicle Frequency")
    ax.set_xlabel("records per anonymised vehicle, clipped at 20")
    ax.set_ylabel("vehicles, log scale")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "theme_repeat_vehicle_frequency.png", dpi=160)
    plt.close(fig)

    top_context = context_signal.sort_values("weighted_obstruction", ascending=True).tail(10)
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(top_context["context_signal"], top_context["weighted_obstruction"], color="#FB641B")
    ax.set_title("Theme Signal: Context Features by Weighted Obstruction")
    ax.set_xlabel("weighted obstruction")
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(config.FIGURES_DIR / "theme_context_signal_weighted_obstruction.png", dpi=160)
    plt.close(fig)

    curve_path = config.TABLES_DIR / "theme_signal_grid_concentration_curve.csv"
    if curve_path.exists():
        curve = pd.read_csv(curve_path)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(curve["cum_cell_share"] * 100, curve["cum_weighted_share"] * 100, color="#2874F0", linewidth=2.5)
        ax.plot([0, 100], [0, 100], color="#94A3B8", linestyle="--", linewidth=1)
        ax.set_title("Theme Signal: Spatial Concentration of Weighted Obstruction")
        ax.set_xlabel("250m grid cells included (%)")
        ax.set_ylabel("weighted obstruction captured (%)")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(config.FIGURES_DIR / "theme_spatial_concentration_curve.png", dpi=160)
        plt.close(fig)


def export_theme_signal_eda() -> dict[str, Any]:
    """Run Theme-1 EDA and write tables/plots."""
    config.ensure_directories()
    df = load_clean()

    missingness = build_missingness_table(df)
    timestamp_signal = build_timestamp_signal_table(df)
    repeat_vehicle, repeat_station_time = build_repeat_vehicle_tables(df)
    station_time = build_station_time_signal(df)
    context_signal = build_context_signal(df)
    spatial_concentration = build_spatial_concentration(df)
    exposure_bias = build_exposure_bias_signal()
    weekday_timeblock = build_weekday_timeblock_table(df)
    summary = build_signal_summary(
        df,
        timestamp_signal,
        repeat_vehicle,
        spatial_concentration,
        context_signal,
        exposure_bias,
    )

    outputs = {
        "theme_signal_missingness.csv": missingness,
        "theme_signal_timestamp_lifecycle.csv": timestamp_signal,
        "theme_signal_repeat_vehicle_top.csv": repeat_vehicle.head(300),
        "theme_signal_repeat_vehicle_station_time.csv": repeat_station_time.head(300),
        "theme_signal_station_timeblock.csv": station_time,
        "theme_signal_context_features.csv": context_signal,
        "theme_signal_spatial_concentration.csv": spatial_concentration,
        "theme_signal_exposure_bias.csv": exposure_bias,
        "theme_signal_weekday_timeblock.csv": weekday_timeblock,
        "theme_signal_summary.csv": summary,
    }
    for filename, table in outputs.items():
        table.to_csv(config.TABLES_DIR / filename, index=False)

    generate_theme_signal_plots(df, station_time, repeat_vehicle, context_signal)

    payload = {
        "rows": int(len(df)),
        "active_days": int(df["created_date"].nunique()),
        "stations": int(df["station"].nunique()),
        "grid_250m_cells": int(df["grid_id_250m"].nunique()),
        "summary_rows": int(len(summary)),
        "top_summary_signals": summary["signal"].tolist(),
    }
    _write_json(config.TABLES_DIR / "theme_signal_eda_summary.json", payload)
    return payload


def main() -> None:
    payload = export_theme_signal_eda()
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
