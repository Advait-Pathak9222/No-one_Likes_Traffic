"""Evaluate recurrence, action, and operational ranking signals."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .evaluation import capture_at_k, ndcg_at_k


STATIC_SCORE_COLUMNS = {
    "final_tori": "TORI final score",
    "stable_tori": "TORI stable component",
    "exposure_adjusted_tori": "TORI exposure-adjusted",
    "violation_count_static": "Raw violation density",
    "weighted_violation_count": "Weighted obstruction density",
    "baseline_pred_next_weight": "Time-safe rolling baseline",
    "group_historical_mean_weight": "Time-safe historical mean",
}

ELRM_SCORE_COLUMNS = {
    "estimated_lane_recovery_minutes": "ELRM operational priority",
    "recovery_minutes_per_resource_hour": "ELRM resource efficiency",
}

OPERATIONAL_SCORE_COLUMNS = {
    "estimated_capacity_loss_minutes": "Capacity-loss minutes",
    "capacity_loss_pressure_0_100": "Capacity-loss pressure",
    "queue_spillback_risk_0_100": "Queue spillback risk",
    "operational_priority_score_0_100": "Operational priority score",
    "evidence_quality_score_0_100": "Evidence quality score",
}


def evaluate_tori_ranking() -> pd.DataFrame:
    """Compare recurrence/action rankings against future obstruction estimate.

    Notes:
    - TORI and operational columns are full-period static/modelled scores, so their
      comparison is a retrospective ranking diagnostic.
    - Rolling baseline columns are time-safe because they use lagged history.
    """
    tori = pd.read_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet")
    target = pd.read_parquet(config.PROCESSED_DIR / "forecast_target_table.parquet")
    target["created_date"] = pd.to_datetime(target["created_date"])
    target = target.dropna(subset=["next_day_total_tori_proxy"]).copy()

    max_date = target["created_date"].max()
    validation_start = max_date - pd.Timedelta(days=21)
    validation = target[target["created_date"] >= validation_start].copy()

    tori_cols = [
        "grid_id_250m",
        "station",
        "time_block",
        "centroid_lat",
        "centroid_lon",
        "final_tori",
        "stable_tori",
        "exposure_adjusted_tori",
        "violation_count",
        "weighted_violation_count",
    ]
    tori_features = tori[tori_cols].rename(
        columns={
            "violation_count": "violation_count_static",
            "centroid_lat": "tori_centroid_lat",
            "centroid_lon": "tori_centroid_lon",
        }
    )
    joined = validation.merge(
        tori_features,
        on=["grid_id_250m", "station", "time_block"],
        how="left",
    )

    impact_path = config.TABLES_DIR / "operational_impact_plan.csv"
    if impact_path.exists():
        impact = pd.read_csv(impact_path)
        if {"station", "time_block", "centroid_lat", "centroid_lon"}.issubset(impact.columns):
            joined["lat_key"] = joined["tori_centroid_lat"].round(5)
            joined["lon_key"] = joined["tori_centroid_lon"].round(5)
            impact = impact.copy()
            impact["lat_key"] = impact["centroid_lat"].round(5)
            impact["lon_key"] = impact["centroid_lon"].round(5)
            impact_cols = [
                "station",
                "time_block",
                "lat_key",
                "lon_key",
                "estimated_lane_recovery_minutes",
                "recovery_minutes_per_resource_hour",
                "estimated_capacity_loss_minutes",
                "capacity_loss_pressure_0_100",
                "queue_spillback_risk_0_100",
                "operational_priority_score_0_100",
                "evidence_quality_score_0_100",
            ]
            joined = joined.merge(
                impact[[col for col in impact_cols if col in impact.columns]],
                on=["station", "time_block", "lat_key", "lon_key"],
                how="left",
            )

    metric_rows = []
    target_col = "next_day_total_tori_proxy"
    score_columns = STATIC_SCORE_COLUMNS.copy()
    for score_col, method_name in ELRM_SCORE_COLUMNS.items():
        if score_col in joined.columns:
            score_columns[score_col] = method_name
    for score_col, method_name in OPERATIONAL_SCORE_COLUMNS.items():
        if score_col in joined.columns:
            score_columns[score_col] = method_name

    for score_col, method_name in score_columns.items():
        if score_col not in joined.columns:
            continue
        joined[score_col] = joined[score_col].fillna(0)
        for k in [10, 20, 50, 100]:
            captures = []
            ndcgs = []
            for _, day_frame in joined.groupby("created_date"):
                captures.append(capture_at_k(day_frame, score_col, target_col, k))
                ndcgs.append(ndcg_at_k(day_frame, score_col, target_col, k))
            metric_rows.append(
                {
                    "method": method_name,
                    "score_column": score_col,
                    "k": k,
                    "capture_at_k_mean": float(np.mean(captures)),
                    "capture_at_k_median": float(np.median(captures)),
                    "ndcg_at_k_mean": float(np.mean(ndcgs)),
                    "validation_days": int(joined["created_date"].nunique()),
                    "validation_start": str(validation_start.date()),
                    "validation_end": str(max_date.date()),
                    "diagnostic_type": (
                        "time_safe"
                        if score_col in {"baseline_pred_next_weight", "group_historical_mean_weight"}
                        else (
                            "retrospective_operational_proxy"
                            if score_col in ELRM_SCORE_COLUMNS or score_col in OPERATIONAL_SCORE_COLUMNS
                            else "retrospective_static"
                        )
                    ),
                }
            )
    return pd.DataFrame(metric_rows)


def main() -> None:
    config.ensure_directories()
    evaluation = evaluate_tori_ranking()
    evaluation.to_csv(config.TABLES_DIR / "tori_ranking_evaluation.csv", index=False)
    print(evaluation.to_string(index=False))


if __name__ == "__main__":
    main()
