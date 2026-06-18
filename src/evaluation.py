"""Evaluation helpers for ranking and hotspot-capture metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def capture_at_k(frame: pd.DataFrame, score_col: str, actual_col: str, k: int) -> float:
    """Share of actual impact captured by top-k predicted rows."""
    if frame.empty or actual_col not in frame or score_col not in frame:
        return 0.0
    total = frame[actual_col].sum()
    if total <= 0:
        return 0.0
    top = frame.sort_values(score_col, ascending=False).head(k)
    return float(top[actual_col].sum() / total)


def precision_at_k(frame: pd.DataFrame, score_col: str, label_col: str, k: int) -> float:
    """Precision among top-k predicted rows."""
    if frame.empty or label_col not in frame or score_col not in frame:
        return 0.0
    top = frame.sort_values(score_col, ascending=False).head(k)
    if len(top) == 0:
        return 0.0
    return float(top[label_col].mean())


def ndcg_at_k(frame: pd.DataFrame, score_col: str, actual_col: str, k: int) -> float:
    """Compute NDCG@K for ranking quality."""
    if frame.empty:
        return 0.0
    predicted = frame.sort_values(score_col, ascending=False).head(k)[actual_col].to_numpy()
    ideal = frame.sort_values(actual_col, ascending=False).head(k)[actual_col].to_numpy()

    def dcg(values: np.ndarray) -> float:
        if values.size == 0:
            return 0.0
        discounts = np.log2(np.arange(2, values.size + 2))
        return float(np.sum(values / discounts))

    ideal_dcg = dcg(ideal)
    return 0.0 if ideal_dcg == 0 else dcg(predicted) / ideal_dcg

