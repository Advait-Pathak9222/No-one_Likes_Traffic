"""Hotspot discovery helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from . import config


EARTH_RADIUS_M = 6_371_000.0


def run_dbscan(df: pd.DataFrame, eps_meters: float = 100, min_samples: int = 25) -> pd.DataFrame:
    """Run haversine DBSCAN on valid coordinate rows."""
    out = df.copy()
    out["dbscan_cluster_id"] = -1
    valid = out["has_valid_coordinates"] & out["is_within_bengaluru_bounds"]
    coords = np.radians(out.loc[valid, ["lat", "lon"]].to_numpy())
    if len(coords) == 0:
        return out
    model = DBSCAN(
        eps=eps_meters / EARTH_RADIUS_M,
        min_samples=min_samples,
        metric="haversine",
        n_jobs=-1,
    )
    labels = model.fit_predict(coords)
    out.loc[valid, "dbscan_cluster_id"] = labels
    return out


def summarize_dbscan_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize DBSCAN cluster geometry and context."""
    clustered = df[df["dbscan_cluster_id"] >= 0].copy()
    if clustered.empty:
        return pd.DataFrame()
    return (
        clustered.groupby("dbscan_cluster_id")
        .agg(
            cluster_size=("violation_id", "count"),
            centroid_lat=("lat", "mean"),
            centroid_lon=("lon", "mean"),
            cluster_station_mode=("station", lambda s: s.mode().iloc[0] if len(s.mode()) else "Unknown"),
            cluster_junction_mode=("junction", lambda s: s.mode().iloc[0] if len(s.mode()) else "Unknown"),
            mean_record_weight=("record_weight", "mean"),
            active_days=("created_date", "nunique"),
        )
        .reset_index()
        .sort_values("cluster_size", ascending=False)
    )


def main() -> None:
    config.ensure_directories()
    df = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet")
    clustered = run_dbscan(df, eps_meters=100, min_samples=25)
    clustered[["violation_id", "dbscan_cluster_id"]].to_parquet(
        config.PROCESSED_DIR / "dbscan_cluster_assignments.parquet", index=False
    )
    summary = summarize_dbscan_clusters(clustered)
    summary.to_csv(config.TABLES_DIR / "dbscan_cluster_summary.csv", index=False)
    print(f"Wrote DBSCAN summary with {len(summary):,} clusters.")


if __name__ == "__main__":
    main()

