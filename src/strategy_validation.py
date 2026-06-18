"""Judge-facing validation summary for ParkPulse strategy.

This module resolves the main narrative risk:

- use validated density/history/model signals to predict recurrence;
- use TORI to explain obstruction severity and choose the action;
- use ELRM to compare operational payoff.

The output is intentionally small and readable because it is meant to feed the
dashboard, deck, and judge Q&A.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from . import config


def _metric_row(frame: pd.DataFrame, method: str, k: int = 20) -> pd.Series | None:
    if frame.empty:
        return None
    rows = frame[(frame["method"] == method) & (frame["k"] == k)]
    return rows.iloc[0] if not rows.empty else None


def _selected_forecast_row(frame: pd.DataFrame, k: int = 20) -> pd.Series | None:
    if frame.empty:
        return None
    rows = frame[(frame["selected_for_predictions"] == True) & (frame["k"] == k)]  # noqa: E712
    return rows.iloc[0] if not rows.empty else None


def _clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_strategy_validation_summary() -> dict[str, Any]:
    """Build a compact summary of what each score is responsible for."""
    tori_eval_path = config.TABLES_DIR / "tori_ranking_evaluation.csv"
    forecast_path = config.TABLES_DIR / "forecast_validation_metrics.csv"
    clean_path = config.PROCESSED_DIR / "violations_clean.parquet"

    tori_eval = pd.read_csv(tori_eval_path) if tori_eval_path.exists() else pd.DataFrame()
    forecast = pd.read_csv(forecast_path) if forecast_path.exists() else pd.DataFrame()
    clean = pd.read_parquet(clean_path, columns=["time_block"]) if clean_path.exists() else pd.DataFrame()

    weighted = _metric_row(tori_eval, "Weighted obstruction density")
    raw = _metric_row(tori_eval, "Raw violation density")
    historical = _metric_row(tori_eval, "Time-safe historical mean")
    tori = _metric_row(tori_eval, "TORI final score")
    elrm = _metric_row(tori_eval, "ELRM operational priority")
    elrm_eff = _metric_row(tori_eval, "ELRM resource efficiency")
    capacity_loss = _metric_row(tori_eval, "Capacity-loss minutes")
    spillback = _metric_row(tori_eval, "Queue spillback risk")
    operational_priority = _metric_row(tori_eval, "Operational priority score")
    evidence_quality = _metric_row(tori_eval, "Evidence quality score")
    selected_forecast = _selected_forecast_row(forecast)

    static_candidates = [
        row
        for row in [raw, weighted, historical]
        if row is not None and _clean_float(row.get("capture_at_k_mean")) is not None
    ]
    best_static = (
        max(static_candidates, key=lambda row: float(row.get("capture_at_k_mean")))
        if static_candidates
        else None
    )
    selected_forecast_capture = _clean_float(
        selected_forecast.get("capture_at_k_mean") if selected_forecast is not None else None
    )
    best_static_capture = _clean_float(best_static.get("capture_at_k_mean") if best_static is not None else None)
    if selected_forecast_capture is not None and (
        best_static_capture is None or selected_forecast_capture >= best_static_capture
    ):
        headline_signal = f"Leakage-safe forecast ({selected_forecast.get('model')})"
        headline_capture = selected_forecast_capture
    else:
        headline_signal = str(best_static.get("method")) if best_static is not None else None
        headline_capture = best_static_capture

    if not tori_eval.empty:
        k20 = tori_eval[tori_eval["k"] == 20].sort_values("capture_at_k_mean", ascending=False)
        best_row = k20.iloc[0] if not k20.empty else None
    else:
        best_row = None

    time_counts = clean["time_block"].value_counts().to_dict() if not clean.empty else {}
    night_records = int(time_counts.get("00-06_night_early_morning", 0))
    evening_records = int(time_counts.get("18-22_evening_commercial_pressure", 0))
    evening_ratio = evening_records / night_records if night_records else None

    summary = {
        "headline_recurrence_signal": headline_signal,
        "headline_recurrence_capture_at_20": headline_capture,
        "best_static_recurrence_signal": str(best_static.get("method")) if best_static is not None else None,
        "best_static_recurrence_capture_at_20": best_static_capture,
        "raw_density_capture_at_20": _clean_float(raw.get("capture_at_k_mean") if raw is not None else None),
        "weighted_obstruction_capture_at_20": _clean_float(
            weighted.get("capture_at_k_mean") if weighted is not None else None
        ),
        "time_safe_historical_capture_at_20": _clean_float(
            historical.get("capture_at_k_mean") if historical is not None else None
        ),
        "selected_forecast_model": (
            str(selected_forecast.get("model")) if selected_forecast is not None else None
        ),
        "selected_forecast_capture_at_20": selected_forecast_capture,
        "tori_capture_at_20": _clean_float(tori.get("capture_at_k_mean") if tori is not None else None),
        "elrm_capture_at_20": _clean_float(elrm.get("capture_at_k_mean") if elrm is not None else None),
        "elrm_efficiency_capture_at_20": _clean_float(
            elrm_eff.get("capture_at_k_mean") if elrm_eff is not None else None
        ),
        "capacity_loss_capture_at_20": _clean_float(
            capacity_loss.get("capture_at_k_mean") if capacity_loss is not None else None
        ),
        "spillback_risk_capture_at_20": _clean_float(
            spillback.get("capture_at_k_mean") if spillback is not None else None
        ),
        "operational_priority_capture_at_20": _clean_float(
            operational_priority.get("capture_at_k_mean") if operational_priority is not None else None
        ),
        "evidence_quality_capture_at_20": _clean_float(
            evidence_quality.get("capture_at_k_mean") if evidence_quality is not None else None
        ),
        "best_validation_method_at_20": str(best_row.get("method")) if best_row is not None else None,
        "best_validation_capture_at_20": _clean_float(
            best_row.get("capture_at_k_mean") if best_row is not None else None
        ),
        "night_records": night_records,
        "evening_records": evening_records,
        "evening_to_night_record_ratio": round(evening_ratio, 5) if evening_ratio is not None else None,
        "evening_window_quality_note": (
            "The 18-22 window is unusually sparse in the provided records; ParkPulse flags this as data coverage risk rather than treating evening traffic as truly absent."
            if evening_records and night_records and evening_ratio < 0.02
            else "No severe evening-window sparsity detected."
        ),
        "judge_positioning": (
            "Predict recurrence with the best validated density/history/model signal; use TORI to explain severity; use capacity-loss, spillback, SLA and ELRM to drive operational deployment."
        ),
    }
    return summary


def export_strategy_validation_summary(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write strategy validation summary to tables."""
    config.ensure_directories()
    summary = summary or build_strategy_validation_summary()
    out_path = config.TABLES_DIR / "strategy_validation_summary.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary


def main() -> None:
    summary = export_strategy_validation_summary()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
