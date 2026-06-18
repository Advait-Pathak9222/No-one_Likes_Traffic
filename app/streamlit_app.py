"""Command-center dashboard for ParkPulse Bengaluru."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
LOCAL_DEPS = PROJECT_DIR / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src import config


FLIPKART_BLUE = "#2874F0"
FLIPKART_ORANGE = "#FB641B"
INK = "#172337"
MUTED = "#5F6C7B"
LIGHT_BG = "#F5F7FB"
CARD_BG = "#FFFFFF"


st.set_page_config(
    page_title="ParkPulse Bengaluru",
    page_icon="P",
    layout="wide",
)


st.markdown(
    f"""
    <style>
    .main .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 2.5rem;
    }}
    .park-hero {{
        background: linear-gradient(135deg, {FLIPKART_BLUE} 0%, #174EA6 55%, {INK} 100%);
        padding: 1.4rem 1.6rem;
        border-radius: 18px;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 10px 28px rgba(23, 35, 55, 0.18);
    }}
    .park-hero h1 {{
        margin: 0;
        font-size: 2.1rem;
        letter-spacing: -0.03em;
    }}
    .park-hero p {{
        margin: 0.35rem 0 0 0;
        color: rgba(255,255,255,0.86);
        font-size: 1.02rem;
    }}
    .section-title {{
        margin-top: 0.4rem;
        color: {INK};
        font-size: 1.35rem;
        font-weight: 750;
    }}
    .metric-card {{
        background: {CARD_BG};
        border: 1px solid #E6EAF2;
        border-radius: 16px;
        padding: 1rem 1rem;
        box-shadow: 0 6px 18px rgba(23,35,55,0.06);
        min-height: 112px;
        color: {INK};
    }}
    .metric-card .label {{
        color: {MUTED};
        font-size: 0.85rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .metric-card .value {{
        color: {INK};
        font-size: 1.85rem;
        font-weight: 800;
        margin-top: 0.2rem;
    }}
    .metric-card .hint {{
        color: {MUTED};
        font-size: 0.82rem;
        margin-top: 0.2rem;
    }}
    .zone-card {{
        background: {CARD_BG};
        border: 1px solid #E6EAF2;
        border-left: 6px solid {FLIPKART_ORANGE};
        border-radius: 16px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 6px 18px rgba(23,35,55,0.06);
        color: {INK};
    }}
    .zone-card h4 {{
        margin: 0 0 0.2rem 0;
        color: {INK};
    }}
    .zone-card p {{
        color: {INK};
        font-weight: 500;
        line-height: 1.55;
    }}
    .pill {{
        display: inline-block;
        background: #EAF1FF;
        color: {FLIPKART_BLUE};
        padding: 0.18rem 0.55rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        margin-right: 0.25rem;
        margin-top: 0.25rem;
    }}
    .orange-pill {{
        background: #FFF0E5;
        color: {FLIPKART_ORANGE};
    }}
    .note-box {{
        background: {LIGHT_BG};
        border: 1px solid #E6EAF2;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        color: {INK};
    }}
    .small-muted {{
        color: {MUTED};
        font-size: 0.88rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_tables():
    plan_path = config.TABLES_DIR / "daily_enforcement_plan.csv"
    tori_path = config.PROCESSED_DIR / "hotspot_tori_table.parquet"
    quality_path = config.TABLES_DIR / "data_quality_summary.csv"
    forecast_path = config.TABLES_DIR / "forecast_validation_metrics.csv"
    robust_path = config.TABLES_DIR / "robust_topk_overlap_all_vs_high_confidence.csv"
    station_path = config.TABLES_DIR / "station_deployment_plan.csv"
    tori_eval_path = config.TABLES_DIR / "tori_ranking_evaluation.csv"

    if not plan_path.exists() or not tori_path.exists():
        return None

    return {
        "plan": pd.read_csv(plan_path),
        "tori": pd.read_parquet(tori_path),
        "quality": pd.read_csv(quality_path) if quality_path.exists() else pd.DataFrame(),
        "forecast": pd.read_csv(forecast_path) if forecast_path.exists() else pd.DataFrame(),
        "robust": pd.read_csv(robust_path) if robust_path.exists() else pd.DataFrame(),
        "station_plan": pd.read_csv(station_path) if station_path.exists() else pd.DataFrame(),
        "tori_eval": pd.read_csv(tori_eval_path) if tori_eval_path.exists() else pd.DataFrame(),
    }


def format_int(value: float | int) -> str:
    return f"{int(value):,}"


def format_pct(value: float) -> str:
    return f"{100 * float(value):.1f}%"


def prettify_time_block(value: str) -> str:
    """Convert internal time-block IDs into compact display labels."""
    mapping = {
        "00-06_night_early_morning": "00-06 Night",
        "06-09_morning_buildup": "06-09 Morning",
        "09-12_commercial_morning_peak": "09-12 Commercial",
        "12-15_market_midday_pressure": "12-15 Midday",
        "15-18_school_evening_buildup": "15-18 Evening Build",
        "18-22_evening_commercial_pressure": "18-22 Evening",
        "22-24_late_night": "22-24 Late",
    }
    return mapping.get(str(value), str(value).replace("_", " ").title())


def metric_card(label: str, value: str, hint: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def zone_card(row: pd.Series, rank_prefix: str = "#") -> None:
    time_label = prettify_time_block(row["time_block"])
    st.markdown(
        f"""
        <div class="zone-card">
            <h4>{rank_prefix}{int(row['rank'])} · {row['zone_name_readable']}</h4>
            <div class="small-muted">{row['station']} · {time_label}</div>
            <span class="pill orange-pill">TORI {row['final_tori_0_100']:.1f}</span>
            <span class="pill">{row['confidence_band']} confidence</span>
            <span class="pill">{row['recommended_action']}</span>
            <p style="margin-top:0.75rem; margin-bottom:0;">{row['reasoning']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_station_summary(tori: pd.DataFrame, plan: pd.DataFrame) -> pd.DataFrame:
    station_summary = (
        tori.groupby("station")
        .agg(
            hotspot_rows=("grid_id_250m", "count"),
            total_violations=("violation_count", "sum"),
            mean_tori=("final_tori_0_100", "mean"),
            max_tori=("final_tori_0_100", "max"),
            high_confidence_share=("high_confidence_share", "mean"),
        )
        .reset_index()
    )
    plan_summary = (
        plan.groupby("station")
        .agg(
            recommended_zones=("rank", "count"),
            total_patrol_hours=("estimated_patrol_hours", "sum"),
            total_tow_hours=("estimated_tow_hours", "sum"),
            mean_enforcement_roi=("enforcement_roi", "mean"),
        )
        .reset_index()
    )
    return station_summary.merge(plan_summary, on="station", how="left").fillna(0)


def add_tori_bucket(frame: pd.DataFrame) -> pd.DataFrame:
    """Add readable TORI bucket labels for charts."""
    out = frame.copy()
    out["tori_bucket"] = pd.cut(
        out["final_tori_0_100"],
        bins=[-0.1, 50, 75, 90, 100.1],
        labels=["Low (<50)", "Medium (50-75)", "High (75-90)", "Critical (90+)"],
    )
    return out


def make_city_coordinate_scatter(map_df: pd.DataFrame, height: int = 520):
    """Create a tile-free lat/lon chart so rendering does not depend on map tiles."""
    plot_df = add_tori_bucket(map_df)
    fig = px.scatter(
        plot_df,
        x="centroid_lon",
        y="centroid_lat",
        color="final_tori_0_100",
        size="violation_count",
        hover_name="station",
        hover_data={
            "time_block": True,
            "zone_name": True,
            "violation_count": True,
            "confidence_band": True,
            "centroid_lon": ":.5f",
            "centroid_lat": ":.5f",
        },
        color_continuous_scale=[FLIPKART_BLUE, FLIPKART_ORANGE],
        height=height,
    )
    fig.update_traces(marker={"opacity": 0.72, "line": {"width": 0.5, "color": "white"}})
    fig.update_layout(
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        coloraxis_colorbar_title="TORI",
        margin={"r": 0, "t": 10, "l": 0, "b": 0},
        plot_bgcolor="#F8FAFF",
        paper_bgcolor="white",
    )
    return fig


def display_embedded_map(map_file: Path, height: int = 620) -> None:
    if map_file.exists():
        components.html(map_file.read_text(encoding="utf-8"), height=height, scrolling=False)
    else:
        st.info("Map file not found. Run `python3 run_pipeline.py` to regenerate maps.")


def page_command_center(plan: pd.DataFrame, tori: pd.DataFrame, quality: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Today\'s Enforcement Command Center</div>', unsafe_allow_html=True)

    high_risk = int((plan["final_tori_0_100"] >= 90).sum())
    tow_actions = int(plan["recommended_action"].str.contains("Tow", case=False, na=False).sum())
    station_count = int(plan["station"].nunique())
    top20_tori = float(plan.head(20)["final_tori_0_100"].sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Priority Zones", format_int(len(plan)), "action-ready hotspots")
    with c2:
        metric_card("High-Risk Zones", format_int(high_risk), "TORI score >= 90")
    with c3:
        metric_card("Tow-Ready Zones", format_int(tow_actions), "high obstruction candidates")
    with c4:
        metric_card("Stations Covered", format_int(station_count), f"Top-20 TORI sum {top20_tori:.1f}")

    st.write("")
    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.subheader("Top Enforcement Priorities")
        for _, row in plan.head(5).iterrows():
            zone_card(row)

    with right:
        st.subheader("City Hotspot Layout")
        st.caption("Tile-free coordinate view for reliable rendering. Use Maps page for full HTML maps.")
        map_df = tori.sort_values("final_tori", ascending=False).head(800).copy()
        fig = make_city_coordinate_scatter(map_df, height=520)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Action Mix")
    action_counts = plan["recommended_action"].value_counts().reset_index()
    action_counts.columns = ["action", "zones"]
    fig = px.bar(
        action_counts,
        x="zones",
        y="action",
        orientation="h",
        color="zones",
        color_continuous_scale=[FLIPKART_BLUE, FLIPKART_ORANGE],
        height=360,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def page_tori_literature(
    tori: pd.DataFrame,
    forecast: pd.DataFrame,
    robust: pd.DataFrame,
    tori_eval: pd.DataFrame,
) -> None:
    st.markdown('<div class="section-title">TORI Literature: What The Score Means</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="note-box">
        <b>TORI</b> stands for <b>Traffic Obstruction Risk Index</b>. It is an
        explainable prioritization score for illegal-parking enforcement. TORI
        does not claim exact speed loss or exact travel-time savings because the
        dataset contains violation/enforcement records, not vehicle speeds or
        queue lengths.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    c1, c2 = st.columns([1, 1], gap="large")

    with c1:
        st.subheader("Why Raw Violation Counts Are Not Enough")
        st.markdown(
            """
            A raw heatmap rewards locations where violations are recorded often.
            That can be useful, but it misses three things:

            - A heavy vehicle blocks more road capacity than a two-wheeler.
            - A violation near a junction, signal, bus stop, metro station, or
              market can hurt traffic more than one on a quiet road.
            - Some zones look large only because enforcement devices or patrols
              are more active there.

            TORI corrects this by combining obstruction risk, recurrence,
            road context, validation confidence, and exposure adjustment.
            """
        )

    with c2:
        st.subheader("TORI Formula")
        st.code(
            """
stable_tori =
    0.25 * density_score
  + 0.20 * persistence_score
  + 0.15 * temporal_pressure
  + 0.15 * junction_criticality_score
  + 0.10 * violation_severity_score
  + 0.10 * vehicle_obstruction_score
  + 0.05 * validation_confidence_score

final_tori =
    0.72 * stable_tori
  + 0.18 * exposure_adjusted_tori
  + 0.10 * context_risk_score
            """,
            language="text",
        )

    st.subheader("TORI Value Distribution")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Median TORI", f"{tori['final_tori_0_100'].median():.1f}", "rank-scaled score")
    with c2:
        metric_card("90th Percentile", f"{tori['final_tori_0_100'].quantile(0.90):.1f}", "priority threshold")
    with c3:
        metric_card("Raw Score Median", f"{tori['final_tori'].median():.3f}", "unscaled TORI")
    with c4:
        metric_card("Raw Score Max", f"{tori['final_tori'].max():.3f}", "highest obstruction score")

    dist_left, dist_right = st.columns(2, gap="large")
    with dist_left:
        fig = px.histogram(
            tori,
            x="final_tori",
            nbins=45,
            color_discrete_sequence=[FLIPKART_BLUE],
            title="Raw TORI Distribution",
            height=390,
        )
        fig.update_layout(xaxis_title="Raw final_tori", yaxis_title="Hotspot buckets")
        st.plotly_chart(fig, use_container_width=True)
    with dist_right:
        fig = px.histogram(
            tori,
            x="final_tori_0_100",
            nbins=40,
            color_discrete_sequence=[FLIPKART_ORANGE],
            title="Rank-Scaled TORI Distribution",
            height=390,
        )
        fig.update_layout(xaxis_title="TORI 0-100 percentile score", yaxis_title="Hotspot buckets")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "The 0-100 TORI score is percentile-scaled, so it intentionally spreads hotspots for ranking. "
            "Use raw `final_tori` to inspect the actual distribution shape."
        )

    st.subheader("Components")
    components_df = pd.DataFrame(
        [
            ("Density", "How concentrated the violation pressure is in a zone/time block."),
            ("Persistence", "Whether the hotspot repeats across many active days."),
            ("Temporal pressure", "Whether that time block is important for the station."),
            ("Junction criticality", "Whether the zone is near junction/signal/market/metro/bus/school contexts."),
            ("Violation severity", "Whether the offence directly blocks main roads, crossings, footpaths, etc."),
            ("Vehicle obstruction", "Whether the vehicle mix occupies larger road width."),
            ("Validation confidence", "How reliable the records are based on status and SCITA flow."),
            ("Exposure adjustment", "Whether the hotspot remains important after accounting for device/patrol activity."),
        ],
        columns=["Component", "Interpretation"],
    )
    st.dataframe(components_df, use_container_width=True, hide_index=True)

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Density vs Raw TORI")
        scatter_df = tori.copy()
        scatter_df["violation_count_log"] = scatter_df["violation_count"].clip(lower=1)
        fig = px.scatter(
            scatter_df,
            x="violation_count_log",
            y="final_tori",
            color="confidence_band",
            size="mean_vehicle_obstruction",
            hover_name="station",
            hover_data=["time_block", "zone_name"],
            log_x=True,
            height=420,
            opacity=0.42,
        )
        fig.update_layout(
            xaxis_title="Violation count, log scale",
            yaxis_title="Raw final_tori",
            legend_title="Confidence",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Validation Evidence")
        if not forecast.empty:
            selected = forecast[forecast["selected_for_predictions"] == True]
            if not selected.empty:
                best20 = selected[selected["k"] == 20].iloc[0]
                metric_card(
                    "Selected Model Capture@20",
                    format_pct(best20["capture_at_k_mean"]),
                    f"{best20['model']} · validation {best20['validation_start']} to {best20['validation_end']}",
                )
        if not robust.empty:
            top20 = robust[robust["k"] == 20].iloc[0]
            metric_card(
                "Robust Top-20 Overlap",
                format_pct(top20["topk_overlap_share"]),
                "all records vs high-confidence records",
            )

    if not tori_eval.empty:
        st.subheader("Is TORI A Good Prediction Method?")
        eval20 = tori_eval[tori_eval["k"] == 20].sort_values(
            "capture_at_k_mean", ascending=False
        )
        best_method = eval20.iloc[0]
        tori_final = eval20[eval20["method"] == "TORI final score"].iloc[0]
        weighted_density = eval20[eval20["method"] == "Weighted obstruction density"].iloc[0]

        e1, e2, e3 = st.columns(3)
        with e1:
            metric_card(
                "Best Ranking Signal @20",
                format_pct(best_method["capture_at_k_mean"]),
                str(best_method["method"]),
            )
        with e2:
            metric_card(
                "TORI Final @20",
                format_pct(tori_final["capture_at_k_mean"]),
                "retrospective static diagnostic",
            )
        with e3:
            metric_card(
                "Weighted Density @20",
                format_pct(weighted_density["capture_at_k_mean"]),
                "stronger predictive signal",
            )

        st.markdown(
            """
            <div class="note-box">
            <b>Interpretation:</b> TORI is valuable as an explainable impact and
            action-prioritization index, but it should not be used alone as the
            forecasting model. Historical density and weighted obstruction
            density are stronger predictors of future violation pressure. The
            final product should therefore use <b>forecasting for where pressure
            will recur</b> and <b>TORI for how damaging and actionable that
            pressure is</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )

        fig = px.bar(
            eval20,
            x="capture_at_k_mean",
            y="method",
            color="diagnostic_type",
            orientation="h",
            title="Ranking Methods Compared at Capture@20",
            color_discrete_map={
                "time_safe": FLIPKART_BLUE,
                "retrospective_static": FLIPKART_ORANGE,
            },
            height=420,
        )
        fig.update_layout(
            xaxis_tickformat=".0%",
            xaxis_title="Mean Capture@20",
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig, use_container_width=True)


def page_station_deployment(plan: pd.DataFrame, tori: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Station-Wise Deployment Cards</div>', unsafe_allow_html=True)
    station_summary = build_station_summary(tori, plan)
    station_summary = station_summary.sort_values("max_tori", ascending=False)

    top_station_names = station_summary.head(20)["station"].tolist()
    station = st.selectbox("Select police station", top_station_names)
    station_plan = plan[plan["station"] == station].sort_values("rank").head(8)
    station_row = station_summary[station_summary["station"] == station].iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Max TORI", f"{station_row['max_tori']:.1f}", "highest hotspot risk")
    with c2:
        metric_card("Recommended Zones", format_int(station_row["recommended_zones"]), "in city priority list")
    with c3:
        metric_card("Patrol Hours", f"{station_row['total_patrol_hours']:.1f}", "estimated")
    with c4:
        metric_card("Tow Hours", f"{station_row['total_tow_hours']:.1f}", "estimated")
    with c5:
        metric_card("Mean ROI", f"{station_row['mean_enforcement_roi']:.2f}", "impact/resource-hour")

    st.write("")
    chart_left, chart_mid, chart_right = st.columns([1, 1, 1], gap="large")
    station_tori = tori[tori["station"] == station].copy()

    with chart_left:
        fig = px.histogram(
            station_tori,
            x="final_tori_0_100",
            nbins=24,
            color_discrete_sequence=[FLIPKART_BLUE],
            height=300,
            title="TORI distribution",
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font={"color": INK, "size": 12},
            margin={"l": 20, "r": 10, "t": 52, "b": 40},
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart_mid:
        block = (
            station_tori.groupby("time_block")
            .agg(total_violations=("violation_count", "sum"), max_tori=("final_tori_0_100", "max"))
            .reset_index()
            .sort_values("max_tori", ascending=False)
        )
        block["time_window"] = block["time_block"].map(prettify_time_block)
        fig = px.bar(
            block,
            x="max_tori",
            y="time_window",
            orientation="h",
            color="total_violations",
            color_continuous_scale=[FLIPKART_BLUE, FLIPKART_ORANGE],
            height=330,
            title="Best enforcement windows",
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending", "title": None},
            xaxis_title="Max TORI",
            margin={"l": 15, "r": 10, "t": 52, "b": 40},
            coloraxis_colorbar={
                "title": "Violations",
                "len": 0.70,
                "thickness": 12,
            },
            font={"size": 12},
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart_right:
        action_df = station_plan["recommended_action"].value_counts().reset_index()
        action_df.columns = ["action", "zones"]
        if action_df.empty:
            st.info("No action rows for this station.")
        else:
            fig = px.pie(
                action_df,
                names="action",
                values="zones",
                hole=0.48,
                color_discrete_sequence=[FLIPKART_ORANGE, FLIPKART_BLUE, "#6C8CD5", "#F6A15A"],
                title="Action mix",
                height=300,
            )
            fig.update_layout(
                paper_bgcolor="white",
                font={"color": INK, "size": 12},
                margin={"l": 10, "r": 10, "t": 52, "b": 20},
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Deployment Cards: {station}")
    if station_plan.empty:
        st.info("No top deployment rows found for this station.")
    else:
        card_cols = st.columns(2)
        for idx, (_, row) in enumerate(station_plan.iterrows()):
            with card_cols[idx % 2]:
                zone_card(row)

    st.subheader("City-Level Station Ranking")
    fig = px.bar(
        station_summary.head(20),
        x="max_tori",
        y="station",
        orientation="h",
        color="total_violations",
        color_continuous_scale=[FLIPKART_BLUE, FLIPKART_ORANGE],
        height=560,
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        plot_bgcolor="white",
        paper_bgcolor="white",
        font={"color": INK},
        margin={"l": 20, "r": 20, "t": 40, "b": 40},
    )
    st.plotly_chart(fig, use_container_width=True)


def page_hotspot_investigator(plan: pd.DataFrame, tori: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">Why This Hotspot?</div>', unsafe_allow_html=True)
    choices = (
        plan.assign(
            label=lambda x: x["rank"].astype(str)
            + " · "
            + x["station"].astype(str)
            + " · "
            + x["zone_name_readable"].astype(str).str.slice(0, 55)
        )
        .set_index("label")
        .to_dict("index")
    )
    label = st.selectbox("Choose hotspot", list(choices.keys()))
    row = pd.Series(choices[label])

    zone_card(row)

    matched = tori[
        (tori["station"] == row["station"])
        & (tori["time_block"] == row["time_block"])
        & (tori["centroid_lat"].round(6) == round(row["centroid_lat"], 6))
        & (tori["centroid_lon"].round(6) == round(row["centroid_lon"], 6))
    ]
    detail = matched.iloc[0] if not matched.empty else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Violations", format_int(row["violation_count"]), "in hotspot-time bucket")
    with c2:
        metric_card("Stable TORI", f"{row['stable_tori']:.3f}", "recurring pressure")
    with c3:
        metric_card("Exposure-Adjusted", f"{row['exposure_adjusted_tori']:.3f}", "patrol bias aware")
    with c4:
        metric_card("ROI", f"{row['enforcement_roi']:.2f}", "impact per resource-hour")

    if detail is not None:
        st.subheader("Score Breakdown")
        breakdown = pd.DataFrame(
            {
                "component": [
                    "Density",
                    "Persistence",
                    "Temporal Pressure",
                    "Junction Criticality",
                    "Violation Severity",
                    "Vehicle Obstruction",
                    "Validation Confidence",
                    "Context Risk",
                ],
                "score": [
                    detail["density_score"],
                    detail["persistence_score"],
                    detail["temporal_pressure"],
                    detail["junction_criticality_score"],
                    detail["violation_severity_score"],
                    detail["vehicle_obstruction_score"],
                    detail["validation_confidence_score"],
                    detail["context_risk_score"],
                ],
            }
        )
        fig = px.bar(
            breakdown,
            x="score",
            y="component",
            orientation="h",
            color="score",
            color_continuous_scale=[FLIPKART_BLUE, FLIPKART_ORANGE],
            range_x=[0, 1],
            height=430,
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Operational Interpretation")
        st.markdown(
            f"""
            <div class="note-box">
            This zone is prioritized because it combines <b>{row['violation_count']:,}</b>
            recorded violations in the selected operational bucket, a TORI score of
            <b>{row['final_tori_0_100']:.1f}</b>, and the recommended action:
            <b>{row['recommended_action']}</b>.
            <br><br>
            <b>Why:</b> {row['reasoning']}
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_simulator(plan: pd.DataFrame) -> None:
    st.markdown('<div class="section-title">What-If Enforcement Simulator</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="note-box">
        Choose available patrol and tow capacity. ParkPulse greedily selects the
        highest-ROI zones that fit the resource budget and estimates how much
        of the top-priority TORI pool is covered.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        patrol_units = st.slider("Patrol teams", 1, 30, 4)
    with col_b:
        tow_units = st.slider("Tow units", 0, 15, 1)
    with col_c:
        hours_per_unit = st.slider("Hours per unit", 1, 8, 3)

    station_options = ["All"] + sorted(plan["station"].dropna().unique().tolist())
    f1, f2, f3 = st.columns(3)
    with f1:
        station_filter = st.selectbox("Station filter", station_options)
    with f2:
        objective = st.selectbox(
            "Optimization objective",
            ["Highest TORI first", "Highest ROI first", "Tow-heavy first"],
        )
    with f3:
        minimum_confidence = st.selectbox(
            "Minimum confidence",
            ["Low", "Medium", "High"],
            index=0,
        )

    action_options = sorted(plan["recommended_action"].dropna().unique().tolist())
    selected_actions = st.multiselect(
        "Allowed action types",
        action_options,
        default=action_options,
    )
    time_options = sorted(plan["time_block"].dropna().unique().tolist())
    selected_time_blocks_pretty = st.multiselect(
        "Allowed time windows",
        [prettify_time_block(value) for value in time_options],
        default=[prettify_time_block(value) for value in time_options],
    )
    pretty_to_raw_time = {prettify_time_block(value): value for value in time_options}
    selected_time_blocks = [pretty_to_raw_time[value] for value in selected_time_blocks_pretty]

    candidate_pool = plan.copy()
    if station_filter != "All":
        candidate_pool = candidate_pool[candidate_pool["station"] == station_filter]
    if selected_actions:
        candidate_pool = candidate_pool[candidate_pool["recommended_action"].isin(selected_actions)]
    if selected_time_blocks:
        candidate_pool = candidate_pool[candidate_pool["time_block"].isin(selected_time_blocks)]

    confidence_order = {"Low": 0, "Medium": 1, "High": 2}
    min_conf_value = confidence_order[minimum_confidence]
    candidate_pool = candidate_pool[
        candidate_pool["confidence_band"].map(confidence_order).fillna(0) >= min_conf_value
    ].copy()

    patrol_budget = patrol_units * hours_per_unit
    tow_budget = tow_units * hours_per_unit

    if objective == "Highest TORI first":
        candidate_pool = candidate_pool.sort_values(
            ["final_tori_0_100", "enforcement_roi"], ascending=False
        )
    elif objective == "Highest ROI first":
        candidate_pool = candidate_pool.sort_values(
            ["enforcement_roi", "final_tori_0_100"], ascending=False
        )
    else:
        candidate_pool = candidate_pool.assign(
            tow_priority=candidate_pool["estimated_tow_hours"].gt(0).astype(int)
        ).sort_values(["tow_priority", "final_tori_0_100"], ascending=False)

    selected_rows = []
    patrol_used = 0.0
    tow_used = 0.0
    for _, row in candidate_pool.iterrows():
        next_patrol = patrol_used + float(row["estimated_patrol_hours"])
        next_tow = tow_used + float(row["estimated_tow_hours"])
        if next_patrol <= patrol_budget and next_tow <= tow_budget:
            selected_rows.append(row)
            patrol_used = next_patrol
            tow_used = next_tow

    selected = pd.DataFrame(selected_rows)
    total_tori_pool = float(candidate_pool["final_tori_0_100"].sum())
    covered_tori = float(selected["final_tori_0_100"].sum()) if not selected.empty else 0.0
    coverage = covered_tori / total_tori_pool if total_tori_pool else 0.0
    top50_pool = float(candidate_pool.head(50)["final_tori_0_100"].sum())
    top50_coverage = covered_tori / top50_pool if top50_pool else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Covered Zones", format_int(len(selected)), f"objective: {objective}")
    with c2:
        metric_card("Covered TORI", f"{covered_tori:.1f}", f"{format_pct(coverage)} of filtered candidate risk")
    with c3:
        metric_card("Patrol Used", f"{patrol_used:.1f}/{patrol_budget:.1f}", "team-hours")
    with c4:
        metric_card("Tow Used", f"{tow_used:.1f}/{tow_budget:.1f}", "tow-hours")

    st.progress(min(coverage, 1.0), text=f"Coverage of filtered candidate TORI: {format_pct(coverage)}")
    st.progress(min(top50_coverage, 1.0), text=f"Coverage of top-50 filtered TORI: {format_pct(top50_coverage)}")
    st.caption(
        f"Filtered candidate pool: {len(candidate_pool):,} zones. "
        "Changing station, action, confidence, time window, objective, or resources changes this pool and selection."
    )

    fig = go.Figure(
        data=[
            go.Bar(name="Covered TORI", x=["TORI Pool"], y=[covered_tori], marker_color=FLIPKART_ORANGE),
            go.Bar(
                name="Uncovered TORI",
                x=["TORI Pool"],
                y=[max(total_tori_pool - covered_tori, 0)],
                marker_color="#D9E2F3",
            ),
        ]
    )
    fig.update_layout(
        barmode="stack",
        height=310,
        yaxis_title="TORI score sum",
        title="Resource Coverage of Priority Risk",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recommended Deployment Under This Budget")
    if selected.empty:
        st.warning(
            "No zones fit the selected resource budget and filters. Increase patrol/tow hours, "
            "allow more actions, or lower the confidence filter."
        )
    else:
        for _, row in selected.head(8).iterrows():
            zone_card(row)
        with st.expander("Show selected deployment table"):
            st.dataframe(
                selected[
                    [
                        "rank",
                        "station",
                        "zone_name_readable",
                        "time_block",
                        "final_tori_0_100",
                        "recommended_action",
                        "estimated_patrol_hours",
                        "estimated_tow_hours",
                        "enforcement_roi",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )


def page_model_evidence(
    forecast: pd.DataFrame,
    robust: pd.DataFrame,
    tori_eval: pd.DataFrame,
) -> None:
    st.markdown('<div class="section-title">Model Evidence And Robustness</div>', unsafe_allow_html=True)
    if forecast.empty:
        st.warning("Forecast metrics not found. Run `python3 run_pipeline.py`.")
    else:
        fig = px.line(
            forecast,
            x="k",
            y="capture_at_k_mean",
            color="model",
            markers=True,
            title="Forecast Validation: Capture@K",
            height=440,
        )
        fig.update_layout(yaxis_title="Mean share of next-day TORI proxy captured", xaxis_title="Top-K zones")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(forecast, use_container_width=True, hide_index=True)

    if not robust.empty:
        st.subheader("Robustness: All Records vs High-Confidence Records")
        fig = px.line(
            robust,
            x="k",
            y="topk_overlap_share",
            markers=True,
            color_discrete_sequence=[FLIPKART_BLUE],
            height=360,
        )
        fig.update_layout(yaxis_tickformat=".0%", yaxis_title="Top-K overlap", xaxis_title="Top-K")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(robust, use_container_width=True, hide_index=True)

    if not tori_eval.empty:
        st.subheader("TORI Ranking Diagnostic")
        fig = px.line(
            tori_eval,
            x="k",
            y="capture_at_k_mean",
            color="method",
            markers=True,
            line_dash="diagnostic_type",
            height=460,
            title="Does TORI Capture Future Obstruction Pressure?",
        )
        fig.update_layout(
            yaxis_tickformat=".0%",
            yaxis_title="Mean Capture@K",
            xaxis_title="Top-K zones",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(tori_eval, use_container_width=True, hide_index=True)


def page_maps() -> None:
    st.markdown('<div class="section-title">Precomputed Map Artifacts</div>', unsafe_allow_html=True)
    map_choice = st.radio(
        "Map layer",
        ["TORI Priority Hotspots", "Raw Violation Heatmap"],
        horizontal=True,
    )
    if map_choice == "TORI Priority Hotspots":
        display_embedded_map(config.MAPS_DIR / "tori_priority_hotspots.html")
    else:
        display_embedded_map(config.MAPS_DIR / "raw_violation_heatmap.html")


tables = load_tables()

st.markdown(
    """
    <div class="park-hero">
        <h1>ParkPulse Bengaluru</h1>
        <p>Impact-weighted illegal parking intelligence for targeted traffic enforcement.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if tables is None:
    st.warning("Pipeline outputs are missing. Run `python3 run_pipeline.py` first.")
    st.stop()

plan = tables["plan"]
tori = tables["tori"]
quality = tables["quality"]
forecast = tables["forecast"]
robust = tables["robust"]
tori_eval = tables["tori_eval"]

with st.sidebar:
    st.markdown("### ParkPulse Navigation")
    page = st.radio(
        "Choose view",
        [
            "Command Center",
            "TORI Literature",
            "Station Deployment",
            "Hotspot Investigator",
            "What-If Simulator",
            "Model Evidence",
            "Maps",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Prototype mode")
    st.caption("TORI is an obstruction-risk proxy, not a direct speed measurement.")

if page == "Command Center":
    page_command_center(plan, tori, quality)
elif page == "TORI Literature":
    page_tori_literature(tori, forecast, robust, tori_eval)
elif page == "Station Deployment":
    page_station_deployment(plan, tori)
elif page == "Hotspot Investigator":
    page_hotspot_investigator(plan, tori)
elif page == "What-If Simulator":
    page_simulator(plan)
elif page == "Model Evidence":
    page_model_evidence(forecast, robust, tori_eval)
elif page == "Maps":
    page_maps()
