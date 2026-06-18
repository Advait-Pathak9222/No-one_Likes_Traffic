"""Enforcement exposure adjustment features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def percentile_rank(series: pd.Series) -> pd.Series:
    """Return percentile ranks with zero fallback."""
    if series.empty:
        return series
    return series.rank(method="average", pct=True).fillna(0.0)


def build_exposure_table(df: pd.DataFrame) -> pd.DataFrame:
    """Estimate recording/enforcement exposure by grid, station, and time block."""
    group_cols = ["grid_id_250m", "station", "time_block"]
    exposure = (
        df.groupby(group_cols, dropna=False)
        .agg(
            violation_count=("violation_id", "count"),
            unique_devices=("device_id", "nunique"),
            unique_created_by_ids=("created_by_id", "nunique"),
            active_recording_days=("created_date", "nunique"),
            station_total_records=("station", "size"),
            mean_record_weight=("record_weight", "mean"),
            mean_validation_confidence=("validation_confidence", "mean"),
        )
        .reset_index()
    )
    exposure["enforcement_exposure_raw"] = (
        exposure["unique_devices"].clip(lower=1)
        * exposure["unique_created_by_ids"].clip(lower=1)
        * exposure["active_recording_days"].clip(lower=1)
        * np.log1p(exposure["station_total_records"].clip(lower=1))
    )
    exposure["enforcement_exposure_score"] = percentile_rank(
        np.log1p(exposure["enforcement_exposure_raw"])
    )
    exposure["exposure_adjusted_density"] = exposure["violation_count"] / np.log1p(
        exposure["enforcement_exposure_raw"].clip(lower=1)
    )
    exposure["exposure_adjusted_density_score"] = percentile_rank(
        np.log1p(exposure["exposure_adjusted_density"])
    )
    return exposure


def main() -> None:
    df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")
    exposure = build_exposure_table(df)
    config.ensure_directories()
    exposure.to_parquet(config.PROCESSED_DIR / "exposure_table.parquet", index=False)
    exposure.sort_values("exposure_adjusted_density", ascending=False).head(200).to_csv(
        config.TABLES_DIR / "top_hotspots_exposure_adjusted.csv", index=False
    )
    print(f"Wrote exposure table with {len(exposure):,} rows.")


if __name__ == "__main__":
    main()

