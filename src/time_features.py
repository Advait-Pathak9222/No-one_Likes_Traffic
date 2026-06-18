"""Time parsing and operational time-window features."""

from __future__ import annotations

import pandas as pd

from . import config


def parse_timestamp(series: pd.Series, timezone: str = config.DEFAULT_TIMEZONE) -> pd.Series:
    """Parse a timestamp series as UTC and convert to local timezone."""
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.tz_convert(timezone)


def assign_time_block(hour: int | float | None) -> str:
    """Map an hour to an operational time block label."""
    if pd.isna(hour):
        return "unknown"
    hour_int = int(hour)
    if 0 <= hour_int < 6:
        return "00-06_night_early_morning"
    if 6 <= hour_int < 9:
        return "06-09_morning_buildup"
    if 9 <= hour_int < 12:
        return "09-12_commercial_morning_peak"
    if 12 <= hour_int < 15:
        return "12-15_market_midday_pressure"
    if 15 <= hour_int < 18:
        return "15-18_school_evening_buildup"
    if 18 <= hour_int < 22:
        return "18-22_evening_commercial_pressure"
    if 22 <= hour_int < 24:
        return "22-24_late_night"
    return "unknown"


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add parsed timestamps and calendar features."""
    out = df.copy()
    if "created_datetime" not in out.columns:
        raise KeyError("created_datetime column is required.")

    out["created_ts"] = parse_timestamp(out["created_datetime"])
    if "modified_datetime" in out.columns:
        out["modified_ts"] = parse_timestamp(out["modified_datetime"])
    if "validation_timestamp" in out.columns:
        out["validation_ts"] = parse_timestamp(out["validation_timestamp"])

    out["created_date"] = out["created_ts"].dt.date
    out["created_hour"] = out["created_ts"].dt.hour.astype("Int64")
    out["hour"] = out["created_hour"]
    out["weekday"] = out["created_ts"].dt.weekday.astype("Int64")
    out["weekday_name"] = out["created_ts"].dt.day_name()
    out["is_weekend"] = out["weekday"].isin([5, 6])
    out["month"] = out["created_ts"].dt.month.astype("Int64")
    out["week"] = out["created_ts"].dt.isocalendar().week.astype("Int64")
    out["time_block"] = out["hour"].map(assign_time_block)
    min_date = pd.to_datetime(out["created_date"], errors="coerce").min()
    out["day_index"] = (
        pd.to_datetime(out["created_date"], errors="coerce") - min_date
    ).dt.days.astype("Int64")

    if "validation_ts" in out.columns:
        out["validation_lag_hours"] = (
            (out["validation_ts"] - out["created_ts"]).dt.total_seconds() / 3600
        )
    if "modified_ts" in out.columns:
        out["modified_lag_hours"] = (
            (out["modified_ts"] - out["created_ts"]).dt.total_seconds() / 3600
        )
    return out

