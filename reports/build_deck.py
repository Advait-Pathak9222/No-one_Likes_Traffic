"""Build a self-contained management-style HTML slide deck for ParkPulse.

Reads pipeline outputs, renders clean infographics with matplotlib, embeds them
as base64, and writes a single portable HTML file (print-to-PDF friendly).

Run:  PYTHONPATH=.deps:. MPLCONFIGDIR=outputs/.matplotlib python3 reports/build_deck.py
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
FRONTEND = ROOT / "outputs" / "frontend"
OUT = ROOT / "reports" / "parkpulse_deck.html"

BLUE = "#2874f0"
ORANGE = "#fb641b"
INK = "#172337"
GREEN = "#2fb673"
PURPLE = "#8060d0"
SLATE = "#94a3b8"
GRID = "#dce6f4"

plt.rcParams.update(
    {
        "font.size": 13,
        "font.family": "DejaVu Sans",
        "text.color": INK,
        "axes.edgecolor": GRID,
        "axes.linewidth": 1.0,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "figure.dpi": 150,
    }
)

WINDOW_LABEL = {
    "00-06_night_early_morning": "00–06 Night",
    "06-09_morning_buildup": "06–09 AM build-up",
    "09-12_commercial_morning_peak": "09–12 AM peak",
    "12-15_market_midday_pressure": "12–15 Midday",
    "15-18_school_evening_buildup": "15–18 PM build-up",
    "18-22_evening_commercial_pressure": "18–22 PM peak",
    "22-24_late_night": "22–24 Late",
    "unknown": "Unknown",
}
VEHICLE_LABEL = {
    "two_wheeler": "Two-wheeler",
    "car": "Car",
    "auto_cab": "Auto / Cab",
    "goods_light": "Goods (light)",
    "heavy": "Heavy",
    "unknown": "Unknown",
}


def fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def file_to_b64(path: Path) -> str:
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _clean_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def chart_capture() -> str:
    df = pd.read_csv(TABLES / "tori_ranking_evaluation.csv")
    df = df[df["k"] == 20].copy()
    order = [
        "Weighted obstruction density",
        "Raw violation density",
        "Time-safe historical mean",
        "Time-safe rolling baseline",
        "TORI exposure-adjusted",
        "TORI stable component",
        "TORI final score",
    ]
    df = df.set_index("method").reindex(order).reset_index()
    vals = (df["capture_at_k_mean"] * 100).tolist()
    colors = [BLUE if "TORI" not in m else ORANGE for m in df["method"]]
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    bars = ax.barh(df["method"], vals, color=colors, edgecolor="white", height=0.7)
    ax.invert_yaxis()
    for bar, v in zip(bars, vals):
        ax.text(v + 0.15, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%", va="center", fontweight="bold", fontsize=12)
    ax.set_xlabel("Capture@20 (share of next-period high-pressure cells)")
    ax.set_xlim(0, max(vals) * 1.18)
    _clean_axes(ax)
    ax.tick_params(axis="y", length=0)
    return fig_to_b64(fig)


def chart_elrm_by_action() -> str:
    df = pd.read_csv(TABLES / "operational_impact_plan.csv")
    g = df.groupby("recommended_action")["estimated_lane_recovery_minutes"].sum().sort_values()
    labels = [a.replace(" + ", "\n+ ") for a in g.index]
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    bars = ax.barh(labels, g.values, color=BLUE, edgecolor="white", height=0.66)
    for bar, v in zip(bars, g.values):
        ax.text(v + max(g.values) * 0.01, bar.get_y() + bar.get_height() / 2, f"{v:,.0f}", va="center", fontweight="bold", fontsize=12)
    ax.set_xlabel("Equivalent Lane Recovery Minutes (ELRM) across the plan")
    ax.set_xlim(0, max(g.values) * 1.16)
    _clean_axes(ax)
    ax.tick_params(axis="y", length=0)
    return fig_to_b64(fig)


def chart_time_windows() -> str:
    df = pd.read_csv(TABLES / "time_block_distribution.csv")
    df = df[df["category"] != "unknown"]
    df["label"] = df["category"].map(WINDOW_LABEL).fillna(df["category"])
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    bars = ax.bar(df["label"], df["count"] / 1000, color=ORANGE, edgecolor="white", width=0.66)
    for bar, v in zip(bars, df["count"] / 1000):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1.2, f"{v:.0f}k", ha="center", fontweight="bold", fontsize=11)
    ax.set_ylabel("Violations (thousands)")
    ax.set_ylim(0, max(df["count"] / 1000) * 1.18)
    plt.xticks(rotation=28, ha="right")
    _clean_axes(ax)
    return fig_to_b64(fig)


def chart_donut(series: pd.Series, palette: list[str], title: str) -> str:
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    wedges, _ = ax.pie(
        series.values,
        colors=palette[: len(series)],
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2},
    )
    total = series.sum()
    ax.legend(
        wedges,
        [f"{name} · {v / total:.0%}" for name, v in series.items()],
        loc="center left",
        bbox_to_anchor=(0.98, 0.5),
        frameon=False,
        fontsize=12,
    )
    ax.set_aspect("equal")
    return fig_to_b64(fig)


def chart_action_mix() -> str:
    df = pd.read_csv(TABLES / "daily_enforcement_plan.csv")
    counts = df["recommended_action"].value_counts()
    short = {
        "Fixed-window enforcement": "Fixed-window",
        "Engineering fix + targeted patrol": "Engineering + patrol",
        "Targeted patrol": "Targeted patrol",
        "Tow + fixed-window enforcement": "Tow + enforcement",
        "Metro/market spillover control": "Metro / market",
    }
    counts.index = [short.get(i, i) for i in counts.index]
    return chart_donut(counts, [BLUE, PURPLE, GREEN, ORANGE, SLATE], "Action mix")


def chart_vehicle_mix() -> str:
    df = pd.read_csv(TABLES / "vehicle_type_norm_distribution.csv")
    df = df[df["category"] != "unknown"]
    s = pd.Series(df["count"].values, index=[VEHICLE_LABEL.get(c, c) for c in df["category"]])
    return chart_donut(s, [BLUE, ORANGE, PURPLE, GREEN, SLATE], "Vehicle mix")


def load_numbers() -> dict:
    metrics = json.loads((FRONTEND / "metrics.json").read_text())
    summary = json.loads((TABLES / "operational_impact_summary.json").read_text())
    corridors = pd.read_csv(TABLES / "corridor_summary.csv")
    top_corridors = corridors.head(5)[["corridor_name", "station", "linked_hotspots", "total_violations", "dominant_bottleneck"]]
    return {"metrics": metrics, "summary": summary, "n_corridors": len(corridors), "top_corridors": top_corridors}


def kpi_tile(value: str, label: str, accent: str = BLUE) -> str:
    return f'<div class="tile"><div class="tile-bar" style="background:{accent}"></div><div class="tile-value">{value}</div><div class="tile-label">{label}</div></div>'


def tori_bar(name: str, weight: float) -> str:
    return (
        f'<div class="wbar"><span class="wname">{name}</span>'
        f'<span class="wtrack"><span class="wfill" style="width:{weight * 100 * 4:.0f}px"></span></span>'
        f'<span class="wval">{weight:.2f}</span></div>'
    )


def build_html() -> str:
    n = load_numbers()
    m, s = n["metrics"], n["summary"]
    img_capture = chart_capture()
    img_elrm = chart_elrm_by_action()
    img_windows = chart_time_windows()
    img_action = chart_action_mix()
    img_vehicle = chart_vehicle_mix()
    img_overlay = file_to_b64(FIGURES / "congestion_risk_overlay.png")

    tc_rows = "".join(
        f"<tr><td><b>{r.corridor_name}</b></td><td>{r.station}</td><td>{r.linked_hotspots}</td>"
        f"<td>{int(r.total_violations):,}</td><td>{r.dominant_bottleneck}</td></tr>"
        for r in n["top_corridors"].itertuples()
    )

    tori_components = "".join(
        tori_bar(name, w)
        for name, w in [
            ("Violation density", 0.25),
            ("Persistence (recurs on many days)", 0.20),
            ("Time-window pressure", 0.15),
            ("Junction / signal criticality", 0.15),
            ("Violation severity", 0.10),
            ("Vehicle obstruction footprint", 0.10),
            ("Validation confidence", 0.05),
        ]
    )

    def slide(num, eyebrow, title, body, kicker="ParkPulse Bengaluru · Theme 1"):
        return f"""
        <section class="slide">
          <div class="slide-head"><span class="eyebrow">{eyebrow}</span><span class="pageno">{num} / 14</span></div>
          <h2>{title}</h2>
          <div class="slide-body">{body}</div>
          <div class="slide-foot">{kicker}</div>
        </section>"""

    slides = []

    # 1 — Title
    slides.append(f"""
    <section class="slide title-slide">
      <div class="brandmark">P</div>
      <span class="eyebrow light">Bengaluru Traffic Command Center · Theme 1</span>
      <h1>ParkPulse Bengaluru</h1>
      <p class="lede">AI-driven illegal-parking intelligence that tells Bengaluru Traffic Police
      <b>which illegal parking to solve first</b> — and how much road capacity each action recovers.</p>
      <div class="title-tiles">
        {kpi_tile(f"{m['total_violations']:,}", "violations analysed", BLUE)}
        {kpi_tile(f"{m['total_hotspots']:,}", "recurring hotspots", PURPLE)}
        {kpi_tile(f"{m['top20_lane_recovery_minutes']:,.0f} min", "top-20 lane recovery (ELRM)", ORANGE)}
        {kpi_tile(f"{m['robust_top20_overlap'] * 100:.0f}%", "robust top-20 stability", GREEN)}
      </div>
      <div class="slide-foot">Self-contained on the provided enforcement dataset · no external GIS or paid feeds</div>
    </section>""")

    # 2 — Problem
    slides.append(slide(2, "The problem", "On-street parking is choking Bengaluru's carriageways", f"""
      <div class="two-col">
        <div>
          <p class="big-statement">Illegal and spillover parking near markets, metro stations, junctions and signals
          eats into running lanes and chokes intersections — exactly where the city can least afford lost capacity.</p>
          <ul class="bullets">
            <li>Spillover concentrates around commercial cores, metro feeders and arterial kerbs.</li>
            <li>A blocked kerb lane on an arterial removes a large share of moving capacity.</li>
            <li>Impact is uneven — a night two-wheeler ≠ a peak-hour goods vehicle at a junction.</li>
          </ul>
        </div>
        <div class="callout">
          <div class="callout-num">{m['total_violations']:,}</div>
          <div class="callout-cap">violation records across Jan–May form the evidence base</div>
        </div>
      </div>"""))

    # 3 — Why hard today
    slides.append(slide(3, "Why it's hard today", "Enforcement is reactive, and impact is invisible", f"""
      <div class="three-col">
        <div class="mini-card"><h3>Patrol-based &amp; reactive</h3><p>Officers and tow vehicles are dispatched on intuition and complaints, not on measured obstruction impact.</p></div>
        <div class="mini-card"><h3>No impact heatmap</h3><p>There is no shared view linking <i>where</i> parking violations cluster to <i>how much</i> traffic flow they cost.</p></div>
        <div class="mini-card"><h3>Hard to prioritise</h3><p>With limited capacity, which of thousands of hotspots should be solved first — and in which time window?</p></div>
      </div>
      <div class="data-gap">
        <b>The honest constraint:</b> the dataset has violation records — <b>no</b> speed, queue, travel-time, lane GIS,
        signal-health or live-roster feeds. ParkPulse quantifies impact with transparent proxies instead of inventing data.
      </div>"""))

    # 4 — Approach
    pipeline = "".join(
        f'<div class="pipe-step"><span>{i + 1}</span>{label}</div>' + ('<div class="pipe-arrow">→</div>' if i < 7 else "")
        for i, label in enumerate([
            "Clean &amp; normalise", "Recurring hotspots", "Recurrence engine", "Road-space intel",
            "Capacity &amp; spillback", "ELRM payoff", "Action plan", "Command center",
        ])
    )
    slides.append(slide(4, "Our approach", "One pipeline: from raw records to a ranked action plan", f"""
      <div class="pipeline">{pipeline}</div>
      <div class="two-col" style="margin-top:22px">
        <div class="mini-card"><h3>Predict recurrence</h3><p>Raw density, weighted obstruction, time-safe history and leakage-safe models are compared; the validation winner leads recurrence.</p></div>
        <div class="mini-card"><h3>Quantify &amp; act</h3><p>Capacity-loss pressure, spillback risk, clearance SLA and ELRM convert hotspots into police deployment decisions.</p></div>
      </div>"""))

    # 5 — Data foundation
    slides.append(slide(5, "Data foundation", "Cleaned, normalised, and time-aware", f"""
      <div class="tiles-row">
        {kpi_tile(f"{m['total_violations']:,}", "clean violation records")}
        {kpi_tile(f"{m['total_hotspots']:,}", "grid×station×window hotspots", PURPLE)}
        {kpi_tile("7", "operational time windows", ORANGE)}
        {kpi_tile("5", "normalised vehicle classes", GREEN)}
      </div>
      <div class="two-col chart-col">
        <figure><img src="{img_windows}"/><figcaption>When violations happen — night and the 09–12 commercial peak dominate.</figcaption></figure>
        <figure><img src="{img_vehicle}"/><figcaption>What parks illegally — two-wheelers lead, but cars/autos/goods drive obstruction.</figcaption></figure>
      </div>"""))

    # 6 — TORI
    slides.append(slide(6, "Core metric #1", "TORI — Traffic Obstruction Risk Index", f"""
      <div class="two-col">
        <div>
          <p class="big-statement">An explainable 0–100 priority score — built from transparent, weighted components, not a black box.</p>
          <div class="wbars">{tori_components}</div>
        </div>
        <div class="callout soft">
          <p><b>Why a proxy?</b> With no speed or queue data, TORI estimates <i>obstruction priority</i>, not measured congestion.</p>
          <p><b>Exposure-aware:</b> raw counts are adjusted so heavily-policed zones don't look artificially risky.</p>
        </div>
      </div>"""))

    # 7 — Honesty
    slides.append(slide(7, "Trust by design", "We are explicit about what we do — and don't — measure", f"""
      <div class="two-col">
        <div class="mini-card ok"><h3>Derived from the dataset</h3>
          <ul class="bullets tight"><li>Illegal-parking obstruction risk (TORI)</li><li>Enforcement-exposure adjustment</li>
          <li>Inferred corridors &amp; bottleneck class</li><li>Equivalent Lane Recovery Minutes</li></ul></div>
        <div class="mini-card warn"><h3>Marked as future integrations</h3>
          <ul class="bullets tight"><li>Live vehicle speed / queue length</li><li>Surveyed lane-level GIS geometry</li>
          <li>Signal-health telemetry</li><li>Live workforce / patrol GPS</li></ul></div>
      </div>
      <div class="data-gap ok-gap"><b>No external data:</b> every analytical layer uses only the provided records.
      The command map's basemap is cosmetic context only. ParkPulse deploys on data a city already owns.</div>"""))

    # 8 — Corridor intelligence
    slides.append(slide(8, "Road-network story", "Corridor &amp; bottleneck intelligence", f"""
      <div class="two-col">
        <figure class="overlay-fig"><img src="{img_overlay}"/><figcaption>Inferred corridor obstruction risk — blue→yellow→red — from violation coordinates (not live speed).</figcaption></figure>
        <div>
          <div class="tiles-row stacked">
            {kpi_tile(f"{n['n_corridors']}", "inferred corridors", BLUE)}
            {kpi_tile("9", "bottleneck classes", PURPLE)}
          </div>
          <table class="mini-table"><thead><tr><th>Corridor</th><th>Station</th><th>Spots</th><th>Violations</th><th>Bottleneck</th></tr></thead>
          <tbody>{tc_rows}</tbody></table>
        </div>
      </div>"""))

    # 9 — Operational metrics
    elrm_low = s.get("top20_lane_recovery_minutes_low")
    elrm_high = s.get("top20_lane_recovery_minutes_high")
    slides.append(slide(9, "Operational impact", "From hotspot score to field decision", f"""
      <div class="two-col">
        <div>
          <div class="hero-number">{m['top20_lane_recovery_minutes']:,.0f}<span>min</span></div>
          <div class="hero-cap">equivalent lane-minutes recovered by actioning the <b>top-20</b> zones<br/>
          range {elrm_low:,.0f}–{elrm_high:,.0f} min · {m['recovery_minutes_per_resource_hour']:.1f} min recovered per resource-hour</div>
          <p class="note">ParkPulse also reports capacity-loss pressure, queue-spillback risk, clearance SLA and evidence quality.
          These are transparent control-room proxies — <b>not</b> measured live speed or queue length.</p>
        </div>
        <figure><img src="{img_elrm}"/><figcaption>Where recovery concentrates — by recommended action across the plan.</figcaption></figure>
      </div>"""))

    # 10 — Results & validation
    slides.append(slide(10, "Evidence", "Results &amp; validation: two jobs, done honestly", f"""
      <div class="two-col">
        <figure><img src="{img_capture}"/><figcaption>Capture@20. The best validated recurrence signal leads; TORI explains &amp; prioritises action.</figcaption></figure>
        <div>
          <div class="tiles-row stacked">
            {kpi_tile(f"{m['robust_top20_overlap'] * 100:.0f}%", "robust top-20 overlap (stability)", GREEN)}
            {kpi_tile(f"{m['plan_lane_recovery_minutes']:,.0f} min", "plan-wide lane recovery (ELRM)", ORANGE)}
            {kpi_tile(f"{(m.get('parkpulse_vs_tori_recovery_uplift_pct') or 0):.1f}%", "policy-lab uplift vs TORI-only", PURPLE)}
          </div>
          <div class="callout soft"><p><b>Key insight:</b> forecast <i>where pressure recurs</i> using the validation-winning density/history/model signal,
          then use capacity-loss, spillback, SLA, TORI, ELRM and policy simulation to decide what to clear first. Two distinct jobs, each with the right tool.</p></div>
        </div>
      </div>"""))

    # 11 — Product
    pages = "".join(
        f'<div class="page-chip">{p}</div>'
        for p in ["Command Center", "Live Ops Brief", "Priority Queue", "Hotspot Intelligence",
                  "Tomorrow's Risk", "Deployment Simulator", "Station View", "Methodology"]
    )
    slides.append(slide(11, "The product", "A command center, not a notebook", f"""
      <p class="big-statement">Eight operational views turn the analysis into a daily decision tool for a control room.</p>
      <div class="page-chips">{pages}</div>
      <div class="two-col" style="margin-top:18px">
        <div class="mini-card"><h3>Real Bengaluru map</h3><p>An interactive street map renders the inferred corridor-risk network and clickable hotspots, each opening a printable field brief.</p></div>
        <div class="mini-card"><h3>Action mix</h3><figure class="inline-donut"><img src="{img_action}"/></figure></div>
      </div>"""))

    # 12 — Simulator
    slides.append(slide(12, "Decision support", "What-if deployment simulator", """
      <div class="two-col">
        <div><p class="big-statement">Set patrol units and tow vehicles; ParkPulse greedily fills capacity by recovery-per-resource-hour.</p>
        <ul class="bullets"><li>Shows covered hotspots, recoverable lane-minutes, and % of recovery potential captured.</li>
        <li>Filter by station and time window to plan a single shift.</li>
        <li>Answers “if I had N units tonight, where do they go and what do we get back?”</li></ul></div>
        <div class="callout"><div class="callout-num">min / resource-hr</div>
        <div class="callout-cap">the simulator optimises for recovery efficiency, not just coverage count</div></div>
      </div>"""))

    # 13 — Deployable today
    slides.append(slide(13, "Why it stands out", "Deployable today — no data-sharing required", f"""
      <div class="three-col">
        <div class="mini-card"><h3>Self-contained</h3><p>Runs entirely on the enforcement records a city already holds. No external GIS, no paid traffic feed.</p></div>
        <div class="mini-card"><h3>Explainable</h3><p>Every score and number is decomposable and labelled as a proxy — built for officer trust and audit.</p></div>
        <div class="mini-card"><h3>Extensible</h3><p>Speed, signal-health and roster feeds slot in as clearly-marked upgrades when available.</p></div>
      </div>
      <div class="data-gap ok-gap">From day one ParkPulse delivers a ranked, time-windowed, action-ready plan with a hard recovery number — and gets sharper as richer feeds are added.</div>"""))

    # 14 — Closing + glossary
    slides.append(slide(14, "Closing", "Solve the right parking, first", f"""
      <p class="big-statement center">ParkPulse does not just show illegal parking.<br/>It tells Bengaluru Traffic Police <b>which illegal parking to solve first.</b></p>
      <div class="glossary-grid">
        <div><b>TORI</b> — Traffic Obstruction Risk Index (0–100), explainable priority proxy.</div>
        <div><b>ELRM</b> — Equivalent Lane Recovery Minutes; recoverable lane-time, shown as a range.</div>
        <div><b>Carriageway class</b> — full-lane / partial-lane / edge recovery.</div>
        <div><b>Bottleneck class</b> — how a hotspot chokes the road (kerb-lane, junction-mouth…).</div>
        <div><b>Exposure adjustment</b> — removes over-policing bias from raw counts.</div>
        <div><b>Robust top-20</b> — stability of the ranking under high-confidence-only data.</div>
        <div><b>Capture@K</b> — share of next-period high-pressure cells caught by the top-K zones.</div>
        <div><b>Recovery / resource-hr</b> — lane-minutes recovered per patrol+tow hour.</div>
      </div>"""))

    css = """
    :root{--blue:#2874f0;--orange:#fb641b;--ink:#172337;--muted:#5f6c7b;--line:#e6eaf2;--bg:#eef2f7;--green:#2fb673;--purple:#8060d0;}
    *{box-sizing:border-box;}
    body{margin:0;background:var(--bg);font-family:Inter,'Segoe UI',system-ui,-apple-system,sans-serif;color:var(--ink);}
    .slide{position:relative;width:1280px;min-height:720px;margin:26px auto;background:#fff;border-radius:18px;
      box-shadow:0 18px 48px rgba(23,35,55,.14);padding:46px 56px 60px;overflow:hidden;}
    .slide-head{display:flex;justify-content:space-between;align-items:center;}
    .eyebrow{color:var(--orange);font-weight:800;text-transform:uppercase;letter-spacing:.14em;font-size:13px;}
    .eyebrow.light{color:rgba(255,255,255,.8);}
    .pageno{color:var(--muted);font-weight:700;font-size:13px;}
    h1{font-size:62px;letter-spacing:-.04em;margin:14px 0 10px;}
    h2{font-size:34px;letter-spacing:-.03em;margin:12px 0 18px;}
    h3{font-size:18px;margin:0 0 6px;}
    .slide-body{font-size:16px;}
    .slide-foot{position:absolute;left:56px;bottom:22px;color:var(--muted);font-size:12.5px;font-weight:600;}
    .lede{font-size:21px;line-height:1.55;color:#33425a;max-width:980px;}
    .big-statement{font-size:21px;line-height:1.5;color:#2b3a52;max-width:560px;}
    .big-statement.center{text-align:center;max-width:none;font-size:26px;margin:18px auto 26px;}
    .bullets{line-height:1.7;color:#33425a;padding-left:20px;} .bullets.tight{line-height:1.5;font-size:15px;}
    .two-col{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:start;}
    .three-col{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}
    .chart-col figure,.two-col figure{margin:0;} .two-col img{width:100%;border-radius:10px;}
    figcaption{color:var(--muted);font-size:13px;margin-top:8px;line-height:1.45;}
    .overlay-fig img{border:1px solid var(--line);}
    .mini-card{background:#f8fbff;border:1px solid var(--line);border-radius:14px;padding:18px 20px;}
    .mini-card p{color:#33425a;line-height:1.55;margin:0;font-size:15px;}
    .mini-card.ok{background:#eefaf2;border-color:#bfe8cf;} .mini-card.warn{background:#fff6ec;border-color:#ffd9b8;}
    .tile{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px;position:relative;overflow:hidden;}
    .tile-bar{position:absolute;left:0;top:0;bottom:0;width:6px;}
    .tile-value{font-size:30px;font-weight:800;letter-spacing:-.03em;}
    .tile-label{color:var(--muted);font-size:13px;font-weight:700;margin-top:4px;text-transform:uppercase;letter-spacing:.04em;}
    .title-tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:34px;}
    .tiles-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:6px 0 22px;}
    .tiles-row.stacked{grid-template-columns:1fr;gap:12px;margin-bottom:16px;}
    .callout{background:linear-gradient(135deg,var(--blue),var(--ink));color:#fff;border-radius:16px;padding:28px;display:flex;flex-direction:column;justify-content:center;min-height:200px;}
    .callout.soft{background:#f3f7ff;color:#2b3a52;border:1px solid #cfe0ff;} .callout.soft p{margin:0 0 10px;line-height:1.55;}
    .callout-num{font-size:40px;font-weight:800;letter-spacing:-.03em;} .callout-cap{margin-top:8px;opacity:.9;line-height:1.45;}
    .data-gap{margin-top:22px;background:#fff6ec;border:1px solid #ffd9b8;border-radius:14px;padding:16px 20px;color:#7a4a1e;line-height:1.55;font-size:15px;}
    .data-gap.ok-gap{background:#eefaf2;border-color:#bfe8cf;color:#1d6b41;}
    .pipeline{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-top:10px;}
    .pipe-step{background:#fff;border:1.5px solid var(--blue);color:var(--blue);border-radius:12px;padding:14px 14px;font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px;}
    .pipe-step span{background:var(--blue);color:#fff;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:12px;}
    .pipe-arrow{color:var(--muted);font-weight:800;}
    .wbars{margin-top:14px;display:grid;gap:11px;}
    .wbar{display:flex;align-items:center;gap:12px;font-size:14px;}
    .wname{width:230px;color:#33425a;} .wtrack{flex:0 0 auto;background:#eef2f7;border-radius:6px;height:14px;width:160px;position:relative;}
    .wfill{position:absolute;left:0;top:0;bottom:0;background:var(--blue);border-radius:6px;} .wval{font-weight:800;color:var(--ink);}
    .mini-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px;}
    .mini-table th{text-align:left;color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:.04em;border-bottom:1px solid var(--line);padding:7px 8px;}
    .mini-table td{border-bottom:1px solid var(--line);padding:7px 8px;}
    .hero-number{font-size:96px;font-weight:800;letter-spacing:-.05em;color:var(--blue);line-height:1;} .hero-number span{font-size:30px;margin-left:8px;color:var(--muted);}
    .hero-cap{font-size:17px;color:#33425a;margin-top:8px;line-height:1.5;} .note{color:var(--muted);font-size:14px;line-height:1.55;margin-top:16px;}
    .page-chips{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px;} .page-chip{background:var(--blue);color:#fff;border-radius:999px;padding:9px 16px;font-weight:700;font-size:14px;}
    .page-chip:nth-child(even){background:var(--ink);}
    .inline-donut img,.two-col .inline-donut img{width:74%;} .callout-num{font-size:34px;}
    .glossary-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 28px;font-size:14px;color:#33425a;line-height:1.5;max-width:1080px;margin:0 auto;}
    .glossary-grid b{color:var(--ink);}
    .title-slide{background:linear-gradient(135deg,#142036,#1d355e 55%,#2874f0);color:#fff;}
    .title-slide .slide-foot{color:rgba(255,255,255,.75);}
    .title-slide .tile{background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.16);} .title-slide .tile-value{color:#fff;} .title-slide .tile-label{color:rgba(255,255,255,.8);}
    .brandmark{width:60px;height:60px;border-radius:16px;background:linear-gradient(135deg,#2874f0,#fb641b);display:grid;place-items:center;font-weight:900;font-size:30px;color:#fff;margin-bottom:18px;}
    @media print{body{background:#fff;} .slide{margin:0;border-radius:0;box-shadow:none;page-break-after:always;width:100%;min-height:100vh;}}
    """

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>ParkPulse Bengaluru — Deck</title><style>{css}</style></head>
    <body>{''.join(slides)}</body></html>"""


def main() -> None:
    OUT.write_text(build_html(), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT} ({size_kb:.0f} KB, 14 slides).")


if __name__ == "__main__":
    main()
