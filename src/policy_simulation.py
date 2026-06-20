"""Deployment policy simulation for ParkPulse.

This module compares how different dispatch policies perform under realistic
patrol/tow constraints. It is intentionally simple and transparent: a duty
officer can understand the rule, the budget, and the resulting trade-off.

The simulator does not claim measured traffic delay. It compares policies using
the operational estimates already exported by the backend:

- recoverable lane-minutes,
- capacity-loss minutes covered,
- high-spillback zones covered,
- evidence quality,
- and resource efficiency.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from . import config


@dataclass(frozen=True)
class BudgetScenario:
    """A patrol/tow resource scenario."""

    name: str
    patrol_units: int
    tow_units: int
    description: str

    @property
    def patrol_hours(self) -> float:
        return float(self.patrol_units * 2)

    @property
    def tow_hours(self) -> float:
        return float(self.tow_units * 2)


BUDGET_SCENARIOS = [
    BudgetScenario("lean", 6, 1, "Minimum viable field deployment"),
    BudgetScenario("standard", 10, 3, "Typical command-center shift allocation"),
    BudgetScenario("surge", 16, 6, "Event-day or special-drive deployment"),
]

POLICY_SCORE_COLUMNS = {
    "ParkPulse operational priority": "operational_priority_score_0_100",
    "ELRM maximum recovery": "estimated_lane_recovery_minutes",
    "Recovery per resource-hour": "recovery_minutes_per_resource_hour",
    "Capacity-loss first": "estimated_capacity_loss_minutes",
    "Spillback first": "queue_spillback_risk_0_100",
    "TORI-only action score": "final_tori_0_100",
    "Raw violation density": "violation_count",
    "Evidence-safe priority": "evidence_safe_priority_score",
}


def _add_policy_scores(impact: pd.DataFrame) -> pd.DataFrame:
    """Add derived policy scores used by the simulator."""
    frame = impact.copy()
    frame["evidence_safe_priority_score"] = (
        frame["operational_priority_score_0_100"].fillna(0)
        * (frame["evidence_quality_score_0_100"].fillna(0).clip(lower=0, upper=100) / 100.0)
    )
    return frame


def _select_with_budget(
    frame: pd.DataFrame,
    score_col: str,
    patrol_budget: float,
    tow_budget: float,
) -> pd.DataFrame:
    """Greedily select zones that fit patrol/tow budgets."""
    selected: list[pd.Series] = []
    patrol_used = 0.0
    tow_used = 0.0
    ranked = frame.sort_values(score_col, ascending=False).copy()
    for _, row in ranked.iterrows():
        patrol = float(row.get("estimated_patrol_hours", 0.0) or 0.0)
        tow = float(row.get("estimated_tow_hours", 0.0) or 0.0)
        if patrol_used + patrol <= patrol_budget and tow_used + tow <= tow_budget:
            selected.append(row)
            patrol_used += patrol
            tow_used += tow
    if not selected:
        return frame.iloc[0:0].copy()
    return pd.DataFrame(selected)


def _summarize_selection(
    selected: pd.DataFrame,
    scenario: BudgetScenario,
    policy_name: str,
) -> dict[str, Any]:
    """Compute operational outcomes for a selected deployment set."""
    if selected.empty:
        return {
            "scenario": scenario.name,
            "scenario_description": scenario.description,
            "policy": policy_name,
            "selected_hotspots": 0,
            "patrol_units": scenario.patrol_units,
            "tow_units": scenario.tow_units,
            "patrol_hours_budget": scenario.patrol_hours,
            "tow_hours_budget": scenario.tow_hours,
            "patrol_hours_used": 0.0,
            "tow_hours_used": 0.0,
            "estimated_lane_recovery_minutes": 0.0,
            "capacity_loss_minutes_covered": 0.0,
            "high_spillback_zones_covered": 0,
            "immediate_clearance_zones_covered": 0,
            "mean_spillback_risk": 0.0,
            "mean_evidence_quality": 0.0,
            "recovery_per_resource_hour": 0.0,
            "first_wave_sla_minutes": None,
        }

    patrol_used = float(selected["estimated_patrol_hours"].fillna(0).sum())
    tow_used = float(selected["estimated_tow_hours"].fillna(0).sum())
    resource_hours = max(1.0, patrol_used + tow_used)
    return {
        "scenario": scenario.name,
        "scenario_description": scenario.description,
        "policy": policy_name,
        "selected_hotspots": int(len(selected)),
        "patrol_units": scenario.patrol_units,
        "tow_units": scenario.tow_units,
        "patrol_hours_budget": scenario.patrol_hours,
        "tow_hours_budget": scenario.tow_hours,
        "patrol_hours_used": round(patrol_used, 1),
        "tow_hours_used": round(tow_used, 1),
        "estimated_lane_recovery_minutes": round(float(selected["estimated_lane_recovery_minutes"].sum()), 1),
        "capacity_loss_minutes_covered": round(float(selected["estimated_capacity_loss_minutes"].sum()), 1),
        "high_spillback_zones_covered": int((selected["queue_spillback_risk_0_100"] >= 70).sum()),
        "immediate_clearance_zones_covered": int((selected["clearance_sla_minutes"] <= 30).sum()),
        "mean_spillback_risk": round(float(selected["queue_spillback_risk_0_100"].mean()), 1),
        "mean_evidence_quality": round(float(selected["evidence_quality_score_0_100"].mean()), 1),
        "recovery_per_resource_hour": round(float(selected["estimated_lane_recovery_minutes"].sum()) / resource_hours, 1),
        "first_wave_sla_minutes": int(selected["clearance_sla_minutes"].min()),
    }


def simulate_deployment_policies(impact: pd.DataFrame | None = None) -> pd.DataFrame:
    """Run all policies across all budget scenarios."""
    if impact is None:
        impact = pd.read_csv(config.TABLES_DIR / "operational_impact_plan.csv")
    frame = _add_policy_scores(impact)

    rows: list[dict[str, Any]] = []
    for scenario in BUDGET_SCENARIOS:
        for policy_name, score_col in POLICY_SCORE_COLUMNS.items():
            if score_col not in frame.columns:
                continue
            selected = _select_with_budget(
                frame,
                score_col=score_col,
                patrol_budget=scenario.patrol_hours,
                tow_budget=scenario.tow_hours,
            )
            rows.append(_summarize_selection(selected, scenario, policy_name))
    return pd.DataFrame(rows)


def summarize_policy_simulation(results: pd.DataFrame) -> dict[str, Any]:
    """Create a compact judge-facing policy comparison summary."""
    if results.empty:
        return {}
    standard = results[results["scenario"] == "standard"].copy()
    if standard.empty:
        standard = results.copy()

    best_recovery = standard.sort_values("estimated_lane_recovery_minutes", ascending=False).iloc[0]
    parkpulse = standard[standard["policy"] == "ParkPulse operational priority"]
    parkpulse_row = parkpulse.iloc[0] if not parkpulse.empty else best_recovery

    def _value(policy: str, col: str) -> float | None:
        row = standard[standard["policy"] == policy]
        if row.empty:
            return None
        return float(row.iloc[0][col])

    def _uplift(policy: str, col: str) -> float | None:
        base = _value(policy, col)
        current = float(parkpulse_row[col])
        if base is None or base <= 0:
            return None
        return round(100.0 * (current - base) / base, 1)

    summary = {
        "standard_budget_policy": str(parkpulse_row["policy"]),
        "standard_budget_best_recovery_policy": str(best_recovery["policy"]),
        "standard_budget_recovery_minutes": float(parkpulse_row["estimated_lane_recovery_minutes"]),
        "standard_budget_capacity_loss_minutes": float(parkpulse_row["capacity_loss_minutes_covered"]),
        "standard_budget_high_spillback_zones": int(parkpulse_row["high_spillback_zones_covered"]),
        "standard_budget_immediate_clearance_zones": int(parkpulse_row["immediate_clearance_zones_covered"]),
        "standard_budget_recovery_per_resource_hour": float(parkpulse_row["recovery_per_resource_hour"]),
        "standard_budget_mean_evidence_quality": float(parkpulse_row["mean_evidence_quality"]),
        "parkpulse_vs_tori_recovery_uplift_pct": _uplift("TORI-only action score", "estimated_lane_recovery_minutes"),
        "parkpulse_vs_density_recovery_uplift_pct": _uplift("Raw violation density", "estimated_lane_recovery_minutes"),
        "parkpulse_vs_tori_spillback_uplift_pct": _uplift("TORI-only action score", "high_spillback_zones_covered"),
        "policy_lab_note": (
            "Policy simulation compares dispatch rules under patrol/tow budgets using transparent operational estimates. "
            "It is a planning back-test, not measured live traffic delay."
        ),
    }
    return summary


def export_policy_simulation(results: pd.DataFrame | None = None) -> dict[str, Any]:
    """Write policy simulation outputs."""
    config.ensure_directories()
    results = results if results is not None else simulate_deployment_policies()
    results.to_csv(config.TABLES_DIR / "deployment_policy_simulation.csv", index=False)

    summary = summarize_policy_simulation(results)
    out_path = config.TABLES_DIR / "deployment_policy_summary.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary


def main() -> None:
    results = simulate_deployment_policies()
    summary = export_policy_simulation(results)
    print(results.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
