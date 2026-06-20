"""Run the ParkPulse Bengaluru preprocessing and intelligence pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
LOCAL_DEPS = PROJECT_DIR / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / "outputs" / ".matplotlib"))
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")
os.environ.setdefault("OMP_NUM_THREADS", "4")

from src import config  # noqa: E402
from src.clean import build_clean_dataset  # noqa: E402
from src.congestion_overlay import build_and_export_congestion_overlay  # noqa: E402
from src.corridor_intelligence import enrich_roadspace, export_corridor_summary  # noqa: E402
from src.exposure import build_exposure_table  # noqa: E402
from src.forecasting import build_cell_date_timeblock_table, train_forecast_model  # noqa: E402
from src.hotspots import run_dbscan, summarize_dbscan_clusters  # noqa: E402
from src.impact_scoring import build_tori_table  # noqa: E402
from src.impact_metrics import (  # noqa: E402
    build_operational_impact_table,
    export_operational_impact,
)
from src.map_outputs import generate_maps  # noqa: E402
from src.policy_simulation import export_policy_simulation, simulate_deployment_policies  # noqa: E402
from src.plots import generate_basic_plots  # noqa: E402
from src.recommendations import build_enforcement_plan, write_operational_intelligence_summary  # noqa: E402
from src.roadspace_intelligence import (  # noqa: E402
    build_roadspace_intelligence,
    export_roadspace_intelligence,
)
from src.robustness import build_all_vs_high_confidence_report  # noqa: E402
from src.strategy_validation import export_strategy_validation_summary  # noqa: E402
from src.theme_signal_eda import export_theme_signal_eda  # noqa: E402
from src.tori_evaluation import evaluate_tori_ranking  # noqa: E402
from src.export_frontend_data import main as export_frontend_data  # noqa: E402


def main() -> None:
    """Run all completed pipeline stages in order."""
    config.ensure_directories()

    print("[1/16] Cleaning raw violation data...")
    clean_df = build_clean_dataset()

    print("[2/16] Building enforcement exposure table...")
    exposure = build_exposure_table(clean_df)
    exposure.to_parquet(config.PROCESSED_DIR / "exposure_table.parquet", index=False)
    exposure.sort_values("exposure_adjusted_density", ascending=False).head(200).to_csv(
        config.TABLES_DIR / "top_hotspots_exposure_adjusted.csv", index=False
    )

    print("[3/16] Running Theme-1 signal EDA...")
    export_theme_signal_eda()

    print("[4/16] Running DBSCAN hotspot clustering...")
    clustered = run_dbscan(clean_df, eps_meters=100, min_samples=25)
    clustered[["violation_id", "dbscan_cluster_id"]].to_parquet(
        config.PROCESSED_DIR / "dbscan_cluster_assignments.parquet", index=False
    )
    summarize_dbscan_clusters(clustered).to_csv(
        config.TABLES_DIR / "dbscan_cluster_summary.csv", index=False
    )

    print("[5/16] Computing TORI hotspot rankings...")
    tori = build_tori_table(clean_df)
    tori.to_parquet(config.PROCESSED_DIR / "hotspot_tori_table.parquet", index=False)
    tori.sort_values("final_tori", ascending=False).head(250).to_csv(
        config.TABLES_DIR / "top_hotspots_by_tori.csv", index=False
    )
    tori.sort_values("violation_count", ascending=False).head(250).to_csv(
        config.TABLES_DIR / "top_hotspots_by_density.csv", index=False
    )
    tori.sort_values("exposure_adjusted_tori", ascending=False).head(250).to_csv(
        config.TABLES_DIR / "top_hotspots_by_exposure_adjusted_tori.csv", index=False
    )

    print("[6/16] Building enforcement recommendations...")
    plan = build_enforcement_plan(tori, top_n=250)
    plan.to_csv(config.TABLES_DIR / "daily_enforcement_plan.csv", index=False)
    plan.groupby("station").head(5).to_csv(
        config.TABLES_DIR / "station_deployment_plan.csv", index=False
    )
    write_operational_intelligence_summary(tori, plan)

    print("[7/16] Building road-space, lane-obstruction and corridor intelligence...")
    roadspace = build_roadspace_intelligence(clean_df, tori, plan, top_n=500)
    roadspace = enrich_roadspace(roadspace)
    export_roadspace_intelligence(roadspace)
    corridor_summary = export_corridor_summary(roadspace)
    print(f"        Linked {len(roadspace):,} hotspots into {len(corridor_summary):,} inferred corridors.")

    print("[8/16] Building traffic-style obstruction overlay...")
    build_and_export_congestion_overlay(clean_df, tori, plan)

    print("[9/16] Estimating operational recovery impact...")
    impact = build_operational_impact_table(plan, roadspace)
    export_operational_impact(impact)

    print("[10/16] Simulating deployment policies under patrol/tow budgets...")
    policy_results = simulate_deployment_policies(impact)
    export_policy_simulation(policy_results)

    print("[11/16] Building leakage-safe forecasting table...")
    forecast_table = build_cell_date_timeblock_table(clean_df)
    forecast_table.to_parquet(
        config.PROCESSED_DIR / "forecast_target_table.parquet", index=False
    )
    forecast_metrics, forecast_predictions = train_forecast_model(forecast_table)
    forecast_metrics.to_csv(config.TABLES_DIR / "forecast_validation_metrics.csv", index=False)
    forecast_predictions.groupby("created_date").head(50).to_csv(
        config.TABLES_DIR / "next_day_hotspot_predictions.csv", index=False
    )

    print("[12/16] Evaluating recurrence and operational ranking quality...")
    tori_evaluation = evaluate_tori_ranking()
    tori_evaluation.to_csv(config.TABLES_DIR / "tori_ranking_evaluation.csv", index=False)

    print("[13/16] Building judge-facing strategy validation summary...")
    export_strategy_validation_summary()

    print("[14/16] Running robustness checks...")
    overlap, comparison = build_all_vs_high_confidence_report(clean_df)
    overlap.to_csv(config.TABLES_DIR / "robust_topk_overlap_all_vs_high_confidence.csv", index=False)
    comparison.to_csv(config.TABLES_DIR / "robust_hotspots_all_vs_high_confidence.csv", index=False)

    print("[15/16] Generating figures and maps...")
    generate_basic_plots()
    generate_maps()

    print("[16/16] Exporting frontend JSON/GeoJSON...")
    export_frontend_data()

    print("\nParkPulse pipeline complete.")
    print(f"Tables: {config.TABLES_DIR}")
    print(f"Figures: {config.FIGURES_DIR}")
    print(f"Maps: {config.MAPS_DIR}")


if __name__ == "__main__":
    main()
