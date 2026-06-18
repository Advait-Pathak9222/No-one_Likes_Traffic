"""Static plot generation for ParkPulse outputs."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from . import config


def _save_bar(series: pd.Series, title: str, xlabel: str, ylabel: str, path) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    series.plot(kind="bar", ax=ax, color="#2874F0")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def generate_basic_plots() -> None:
    """Generate EDA and output sanity plots from processed tables."""
    config.ensure_directories()
    df = pd.read_parquet(
        config.PROCESSED_DIR / "violations_clean.parquet",
        columns=["hour", "station", "vehicle_type_norm", "validation_status_norm"],
    )
    _save_bar(
        df["hour"].value_counts().sort_index(),
        "Violation Records by Hour of Day",
        "Hour",
        "Records",
        config.FIGURES_DIR / "hourly_distribution.png",
    )
    _save_bar(
        df["station"].value_counts().head(20).sort_values(),
        "Top 20 Police Stations by Recorded Parking Violations",
        "Police Station",
        "Records",
        config.FIGURES_DIR / "top20_police_stations.png",
    )
    _save_bar(
        df["vehicle_type_norm"].value_counts().sort_values(),
        "Normalized Vehicle Mix",
        "Vehicle Class",
        "Records",
        config.FIGURES_DIR / "vehicle_mix_normalized.png",
    )
    _save_bar(
        df["validation_status_norm"].value_counts().sort_values(),
        "Validation Status Mix",
        "Validation Status",
        "Records",
        config.FIGURES_DIR / "validation_status_mix.png",
    )

    if (config.PROCESSED_DIR / "hotspot_tori_table.parquet").exists():
        tori = pd.read_parquet(
            config.PROCESSED_DIR / "hotspot_tori_table.parquet",
            columns=["violation_count", "final_tori_0_100"],
        )
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(
            tori["violation_count"],
            tori["final_tori_0_100"],
            s=12,
            alpha=0.45,
            color="#FB641B",
        )
        ax.set_xscale("log")
        ax.set_title("Raw Density vs TORI Action Score")
        ax.set_xlabel("Violation count, log scale")
        ax.set_ylabel("TORI action score")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(config.FIGURES_DIR / "density_vs_tori.png", dpi=160)
        plt.close(fig)

    metrics_path = config.TABLES_DIR / "forecast_validation_metrics.csv"
    if metrics_path.exists():
        metrics = pd.read_csv(metrics_path)
        fig, ax = plt.subplots(figsize=(10, 6))
        for model, model_df in metrics.groupby("model"):
            model_df = model_df.sort_values("k")
            ax.plot(
                model_df["k"],
                model_df["capture_at_k_mean"],
                marker="o",
                label=model,
            )
        ax.set_title("Forecast Validation: Mean Capture@K")
        ax.set_xlabel("Top-K predicted enforcement zones")
        ax.set_ylabel("Share of next-period weighted obstruction captured")
        ax.grid(alpha=0.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(config.FIGURES_DIR / "forecast_capture_at_k.png", dpi=160)
        plt.close(fig)

    robust_path = config.TABLES_DIR / "robust_topk_overlap_all_vs_high_confidence.csv"
    if robust_path.exists():
        robust = pd.read_csv(robust_path)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(robust["k"], robust["topk_overlap_share"], marker="o", color="#2874F0")
        ax.set_title("Robustness: Top-K Overlap, All Records vs High-Confidence Records")
        ax.set_xlabel("Top-K hotspots")
        ax.set_ylabel("Overlap share")
        ax.set_ylim(0, 1.05)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(config.FIGURES_DIR / "topk_overlap_all_vs_high_confidence.png", dpi=160)
        plt.close(fig)

    tori_eval_path = config.TABLES_DIR / "tori_ranking_evaluation.csv"
    if tori_eval_path.exists():
        evaluation = pd.read_csv(tori_eval_path)
        k20 = evaluation[evaluation["k"] == 20].sort_values("capture_at_k_mean")
        if not k20.empty:
            colors = [
                "#FB641B"
                if "TORI" in method
                else "#32A66A"
                if "ELRM" in method or "Capacity" in method or "Spillback" in method or "Operational" in method
                else "#2874F0"
                for method in k20["method"]
            ]
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.barh(k20["method"], k20["capture_at_k_mean"] * 100, color=colors)
            ax.set_title("Validation: Capture@20 by Ranking Signal")
            ax.set_xlabel("Capture@20 (% of next-period weighted obstruction captured)")
            ax.set_ylabel("")
            ax.grid(axis="x", alpha=0.25)
            fig.tight_layout()
            fig.savefig(config.FIGURES_DIR / "validation_capture_at20_comparison.png", dpi=160)
            plt.close(fig)

    if "time_block" not in df.columns:
        df_time = pd.read_parquet(config.PROCESSED_DIR / "violations_clean.parquet", columns=["time_block"])
    else:
        df_time = df
    time_counts = df_time["time_block"].value_counts().sort_values()
    _save_bar(
        time_counts,
        "Record Coverage by Operational Time Window",
        "Operational time window",
        "Violation records",
        config.FIGURES_DIR / "time_window_record_coverage.png",
    )

    impact_path = config.TABLES_DIR / "operational_impact_plan.csv"
    if impact_path.exists():
        impact = pd.read_csv(impact_path)

        action_recovery = (
            impact.groupby("recommended_action")["estimated_lane_recovery_minutes"]
            .sum()
            .sort_values(ascending=True)
        )
        _save_bar(
            action_recovery,
            "Equivalent Lane Recovery Minutes by Recommended Action",
            "Recommended action",
            "Equivalent lane recovery minutes",
            config.FIGURES_DIR / "lane_recovery_by_action.png",
        )

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(
            impact["resource_hours"],
            impact["estimated_lane_recovery_minutes"],
            s=24,
            alpha=0.55,
            color="#2874F0",
        )
        ax.set_title("Resource Hours vs Equivalent Lane Recovery Minutes")
        ax.set_xlabel("Estimated patrol + tow hours")
        ax.set_ylabel("Equivalent lane recovery minutes")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(config.FIGURES_DIR / "resource_hours_vs_lane_recovery.png", dpi=160)
        plt.close(fig)

        required_cols = {
            "capacity_loss_pressure_0_100",
            "queue_spillback_risk_0_100",
            "clearance_sla_minutes",
            "estimated_lane_recovery_minutes",
        }
        if required_cols.issubset(impact.columns):
            fig, ax = plt.subplots(figsize=(9, 6))
            scatter = ax.scatter(
                impact["capacity_loss_pressure_0_100"],
                impact["queue_spillback_risk_0_100"],
                s=impact["estimated_lane_recovery_minutes"].clip(lower=10, upper=260),
                c=impact["clearance_sla_minutes"],
                cmap="RdYlGn_r",
                alpha=0.62,
                edgecolor="white",
                linewidth=0.4,
            )
            ax.set_title("Operational Risk: Capacity Pressure vs Queue Spillback")
            ax.set_xlabel("Capacity-loss pressure (0–100)")
            ax.set_ylabel("Queue-spillback risk (0–100)")
            ax.grid(alpha=0.25)
            cbar = fig.colorbar(scatter, ax=ax)
            cbar.set_label("Clearance SLA minutes")
            fig.tight_layout()
            fig.savefig(config.FIGURES_DIR / "capacity_spillback_clearance_matrix.png", dpi=160)
            plt.close(fig)

    policy_path = config.TABLES_DIR / "deployment_policy_simulation.csv"
    if policy_path.exists():
        policy = pd.read_csv(policy_path)
        standard = policy[policy["scenario"] == "standard"].sort_values(
            "estimated_lane_recovery_minutes",
            ascending=True,
        )
        if not standard.empty:
            fig, ax = plt.subplots(figsize=(11, 6))
            colors = [
                "#FB641B" if name == "ParkPulse operational priority" else "#2874F0"
                for name in standard["policy"]
            ]
            ax.barh(standard["policy"], standard["estimated_lane_recovery_minutes"], color=colors)
            ax.set_title("Deployment Policy Lab: Standard Budget Recovery")
            ax.set_xlabel("Recovered equivalent lane-minutes")
            ax.set_ylabel("")
            ax.grid(axis="x", alpha=0.25)
            fig.tight_layout()
            fig.savefig(config.FIGURES_DIR / "deployment_policy_recovery_comparison.png", dpi=160)
            plt.close(fig)

        frontier = policy.pivot_table(
            index="scenario",
            columns="policy",
            values="estimated_lane_recovery_minutes",
            aggfunc="first",
        ).reindex(["lean", "standard", "surge"])
        if not frontier.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            for policy_name in frontier.columns:
                line_width = 3 if policy_name == "ParkPulse operational priority" else 1.6
                alpha = 1.0 if policy_name == "ParkPulse operational priority" else 0.65
                ax.plot(frontier.index, frontier[policy_name], marker="o", linewidth=line_width, alpha=alpha, label=policy_name)
            ax.set_title("Deployment Policy Lab: Budget Frontier")
            ax.set_xlabel("Resource scenario")
            ax.set_ylabel("Recovered equivalent lane-minutes")
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8, ncol=2)
            fig.tight_layout()
            fig.savefig(config.FIGURES_DIR / "deployment_policy_budget_frontier.png", dpi=160)
            plt.close(fig)


def main() -> None:
    generate_basic_plots()
    print(f"Wrote figures to {config.FIGURES_DIR}")


if __name__ == "__main__":
    main()
