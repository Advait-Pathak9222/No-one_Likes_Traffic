"""Leakage-safe forecasting and hotspot-capture evaluation."""

from __future__ import annotations

import os
import warnings
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[1] / "outputs" / ".matplotlib"),
)

import ctypes

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from . import config
from .evaluation import capture_at_k, ndcg_at_k


FEATURE_COLUMNS = [
    "grid_code",
    "station_code",
    "time_block_code",
    "weekday",
    "is_weekend",
    "day_index",
    "lagged_3d_count_mean",
    "lagged_7d_count_mean",
    "lagged_14d_count_mean",
    "lagged_28d_count_mean",
    "lagged_3d_weight_mean",
    "lagged_7d_weight_mean",
    "lagged_14d_weight_mean",
    "lagged_28d_weight_mean",
    "group_historical_mean_count",
    "group_historical_mean_weight",
]

OPENMP_LIBRARY_CANDIDATES = [
    Path("/Users/advaitpathak/anaconda3/lib/libomp.dylib"),
    Path("/opt/homebrew/opt/libomp/lib/libomp.dylib"),
    Path("/opt/local/lib/libomp/libomp.dylib"),
]


def build_observed_cell_date_timeblock_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build observed grid-date-time-block rows before panel expansion."""
    group_cols = ["grid_id_250m", "station", "created_date", "time_block"]
    return (
        df.groupby(group_cols, dropna=False)
        .agg(
            violation_count=("violation_id", "count"),
            total_record_weight=("record_weight", "sum"),
            mean_violation_severity=("violation_severity", "mean"),
            mean_vehicle_obstruction=("vehicle_obstruction_weight", "mean"),
            mean_validation_confidence=("validation_confidence", "mean"),
            centroid_lat=("lat", "mean"),
            centroid_lon=("lon", "mean"),
        )
        .reset_index()
    )


def build_cell_date_timeblock_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a full leakage-safe grid-date-time-block panel.

    Missing cell/date/time-block combinations are real zeros: no recorded
    violation pressure for that operational bucket.
    """
    observed = build_observed_cell_date_timeblock_table(df)
    observed["created_date"] = pd.to_datetime(observed["created_date"])

    key_cols = ["grid_id_250m", "station", "time_block"]
    keys = observed[key_cols + ["centroid_lat", "centroid_lon"]].drop_duplicates(key_cols)
    dates = pd.DataFrame(
        {
            "created_date": pd.date_range(
                observed["created_date"].min(), observed["created_date"].max(), freq="D"
            )
        }
    )

    keys["_join_key"] = 1
    dates["_join_key"] = 1
    panel = keys.merge(dates, on="_join_key").drop(columns="_join_key")
    daily = panel.merge(observed, on=key_cols + ["created_date"], how="left", suffixes=("", "_obs"))

    for col in [
        "violation_count",
        "total_record_weight",
        "mean_violation_severity",
        "mean_vehicle_obstruction",
        "mean_validation_confidence",
    ]:
        daily[col] = daily[col].fillna(0)

    daily = daily.sort_values(key_cols + ["created_date"]).reset_index(drop=True)
    first_date = daily["created_date"].min()
    daily["weekday"] = daily["created_date"].dt.weekday
    daily["is_weekend"] = daily["weekday"].isin([5, 6]).astype(int)
    daily["day_index"] = (daily["created_date"] - first_date).dt.days

    daily["grid_code"] = pd.factorize(daily["grid_id_250m"])[0].astype("int32")
    daily["station_code"] = pd.factorize(daily["station"])[0].astype("int16")
    daily["time_block_code"] = pd.factorize(daily["time_block"])[0].astype("int8")

    for window in [3, 7, 14, 28]:
        daily[f"lagged_{window}d_count_mean"] = (
            daily.groupby(key_cols)["violation_count"]
            .transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
            .fillna(0)
        )
        daily[f"lagged_{window}d_weight_mean"] = (
            daily.groupby(key_cols)["total_record_weight"]
            .transform(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
            .fillna(0)
        )

    daily["group_historical_mean_count"] = (
        daily.groupby(key_cols)["violation_count"]
        .transform(lambda s: s.shift(1).expanding(min_periods=1).mean())
        .fillna(0)
    )
    daily["group_historical_mean_weight"] = (
        daily.groupby(key_cols)["total_record_weight"]
        .transform(lambda s: s.shift(1).expanding(min_periods=1).mean())
        .fillna(0)
    )

    daily["next_day_violation_count"] = daily.groupby(key_cols)["violation_count"].shift(-1)
    daily["next_day_total_tori_proxy"] = daily.groupby(key_cols)["total_record_weight"].shift(-1)
    daily["baseline_pred_next_weight"] = daily["lagged_7d_weight_mean"]
    return daily


def preload_openmp_runtime() -> bool:
    """Load OpenMP before importing native boosting libraries when available."""
    for library_path in OPENMP_LIBRARY_CANDIDATES:
        if library_path.exists():
            try:
                ctypes.CDLL(str(library_path), mode=ctypes.RTLD_GLOBAL)
                return True
            except OSError:
                continue
    return False


def _try_lightgbm():
    preload_openmp_runtime()
    try:
        from lightgbm import LGBMRegressor

        return LGBMRegressor
    except Exception:
        return None


def _try_xgboost():
    preload_openmp_runtime()
    try:
        from xgboost import XGBRegressor

        return XGBRegressor
    except Exception:
        return None


def build_model_candidates() -> list[tuple[str, object]]:
    """Return available forecasting models in a robust preference ladder."""
    candidates: list[tuple[str, object]] = []

    LGBMRegressor = _try_lightgbm()
    if LGBMRegressor is not None:
        candidates.append(
            (
                "lightgbm",
                LGBMRegressor(
                    objective="regression",
                    n_estimators=500,
                    learning_rate=0.035,
                    num_leaves=63,
                    min_child_samples=80,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_alpha=0.25,
                    reg_lambda=1.00,
                    random_state=42,
                    n_jobs=4,
                    verbose=-1,
                ),
            )
        )

    XGBRegressor = _try_xgboost()
    if XGBRegressor is not None:
        candidates.append(
            (
                "xgboost",
                XGBRegressor(
                    objective="reg:squarederror",
                    n_estimators=280,
                    learning_rate=0.045,
                    max_depth=6,
                    min_child_weight=8,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    reg_alpha=0.15,
                    reg_lambda=1.50,
                    tree_method="hist",
                    random_state=42,
                    n_jobs=4,
                ),
            )
        )

    candidates.append(
        (
            "hist_gradient_boosting",
            HistGradientBoostingRegressor(
                loss="squared_error",
                learning_rate=0.06,
                max_iter=220,
                max_leaf_nodes=31,
                l2_regularization=0.10,
                random_state=42,
            ),
        )
    )
    return candidates


def train_forecast_model(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train baseline and ML forecast models with a final-period time split."""
    data = table.dropna(subset=["next_day_total_tori_proxy"]).copy()
    max_date = data["created_date"].max()
    validation_start = max_date - pd.Timedelta(days=21)
    train = data[data["created_date"] < validation_start].copy()
    valid = data[data["created_date"] >= validation_start].copy()

    feature_cols = [col for col in FEATURE_COLUMNS if col in data.columns]
    target = "next_day_total_tori_proxy"

    if train.empty or valid.empty:
        raise ValueError("Not enough rows for time-based train/validation split.")

    valid["pred_baseline"] = valid["baseline_pred_next_weight"]

    trained_model_names = []
    for model_name, model in build_model_candidates():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(train[feature_cols], np.log1p(train[target]))
        valid[f"pred_{model_name}"] = np.expm1(model.predict(valid[feature_cols])).clip(min=0)
        trained_model_names.append(model_name)

    metric_rows = []
    score_columns = [("pred_baseline", "rolling_7d_baseline")] + [
        (f"pred_{name}", name) for name in trained_model_names
    ]
    for score_col, name in score_columns:
        for k in [10, 20, 50, 100]:
            captures = []
            ndcgs = []
            for _, day_frame in valid.groupby("created_date"):
                captures.append(capture_at_k(day_frame, score_col, target, k))
                ndcgs.append(ndcg_at_k(day_frame, score_col, target, k))
            metric_rows.append(
                {
                    "model": name,
                    "k": k,
                    "capture_at_k_mean": float(np.mean(captures)),
                    "capture_at_k_median": float(np.median(captures)),
                    "ndcg_at_k_mean": float(np.mean(ndcgs)),
                    "validation_days": int(valid["created_date"].nunique()),
                    "train_rows": int(len(train)),
                    "valid_rows": int(len(valid)),
                    "validation_start": str(validation_start.date()),
                    "validation_end": str(max_date.date()),
                }
            )
    metrics = pd.DataFrame(metric_rows)

    selection_pool = metrics[(metrics["k"] == 20) & (metrics["model"] != "rolling_7d_baseline")]
    if selection_pool.empty:
        selected_model = "rolling_7d_baseline"
        selected_score_col = "pred_baseline"
    else:
        selected_row = selection_pool.sort_values(
            ["capture_at_k_mean", "ndcg_at_k_mean"], ascending=False
        ).iloc[0]
        selected_model = str(selected_row["model"])
        selected_score_col = f"pred_{selected_model}"

    valid["selected_model"] = selected_model
    valid["pred_selected"] = valid[selected_score_col]
    metrics["selected_for_predictions"] = metrics["model"].eq(selected_model)
    predictions = valid.sort_values(["created_date", "pred_selected"], ascending=[True, False])
    return metrics, predictions


def main() -> None:
    config.ensure_directories()
    df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")
    table = build_cell_date_timeblock_table(df)
    table.to_parquet(config.PROCESSED_DIR / "forecast_target_table.parquet", index=False)
    metrics, predictions = train_forecast_model(table)
    metrics.to_csv(config.TABLES_DIR / "forecast_validation_metrics.csv", index=False)
    predictions.groupby("created_date").head(50).to_csv(
        config.TABLES_DIR / "next_day_hotspot_predictions.csv", index=False
    )
    print(f"Wrote forecast target table with {len(table):,} rows.")
    print("Forecast validation:")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
