"""Robustness checks for noisy enforcement/validation data."""

from __future__ import annotations

import pandas as pd

from . import config
from .impact_scoring import build_tori_table


def topk_overlap(left: pd.DataFrame, right: pd.DataFrame, k: int) -> float:
    """Compute overlap share between two top-k hotspot rankings."""
    key_cols = ["grid_id_250m", "station", "time_block"]
    left_keys = set(map(tuple, left.head(k)[key_cols].to_numpy()))
    right_keys = set(map(tuple, right.head(k)[key_cols].to_numpy()))
    if not left_keys or not right_keys:
        return 0.0
    return len(left_keys & right_keys) / k


def build_all_vs_high_confidence_report(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare all-record and high-confidence hotspot rankings."""
    all_tori = build_tori_table(df).sort_values("final_tori", ascending=False)
    high_df = df[df["is_high_confidence_record"]].copy()
    high_tori = build_tori_table(high_df).sort_values("final_tori", ascending=False)

    rows = []
    for k in [10, 20, 50, 100, 200]:
        rows.append(
            {
                "k": k,
                "topk_overlap_share": topk_overlap(all_tori, high_tori, k),
                "all_records_rows": len(df),
                "high_confidence_rows": len(high_df),
                "all_hotspot_rows": len(all_tori),
                "high_confidence_hotspot_rows": len(high_tori),
            }
        )
    overlap_report = pd.DataFrame(rows)

    key_cols = ["grid_id_250m", "station", "time_block"]
    comparison = all_tori.head(250)[
        key_cols + ["violation_count", "final_tori_0_100", "confidence_band"]
    ].merge(
        high_tori[key_cols + ["violation_count", "final_tori_0_100", "confidence_band"]],
        on=key_cols,
        how="left",
        suffixes=("_all_records", "_high_confidence"),
    )
    comparison["appears_in_high_confidence_view"] = comparison[
        "final_tori_0_100_high_confidence"
    ].notna()
    return overlap_report, comparison


def main() -> None:
    config.ensure_directories()
    df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")
    overlap, comparison = build_all_vs_high_confidence_report(df)
    overlap.to_csv(config.TABLES_DIR / "robust_topk_overlap_all_vs_high_confidence.csv", index=False)
    comparison.to_csv(config.TABLES_DIR / "robust_hotspots_all_vs_high_confidence.csv", index=False)
    print("Robustness overlap:")
    print(overlap.to_string(index=False))


if __name__ == "__main__":
    main()

