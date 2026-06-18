"""Build the revised ParkPulse PM + Data Science pitch deck.

This deck is deliberately product-led: the data science supports a clear
operational promise for Bengaluru Traffic Police rather than reading like an
analytics report.

Run:
    PYTHONPATH=.deps:. MPLCONFIGDIR=outputs/.matplotlib python3 reports/build_pm_ds_deck.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pptx import Presentation

import build_pptx as b


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "parkpulse_pm_ds_deck_final.pptx"
OUTLINE = ROOT / "reports" / "parkpulse_pm_ds_deck_outline.md"
SCREENSHOTS = ROOT / "outputs" / "deck_screenshots"
FIGURES = ROOT / "outputs" / "figures"
TABLES = ROOT / "outputs" / "tables"

TOTAL = 18
b.TOTAL_SLIDES = TOTAL


def mval(d: dict, key: str, default=0):
    return d["metrics"].get(key, default)


def takeaway(slide, text: str, dark: bool = False):
    fill = b.NAVY_2 if dark else b.BLUE_50
    line = None if dark else b.BLUE_100
    color = b.WHITE if dark else b.BLUE_DARK
    b.rect(slide, 0.56, 1.55, 12.2, 0.38, fill=fill, line=line)
    b.tx(slide, 0.78, 1.64, 11.76, 0.16, text, size=9.4, color=color, bold=True, anchor=b.MSO_ANCHOR.MIDDLE)


def shot(slide, filename: str, x: float, y: float, w: float | None = None, hgt: float | None = None):
    path = SCREENSHOTS / filename
    if not path.exists():
        b.rect(slide, x, y, w or 5.0, hgt or 3.0, fill=b.BLUE_50, line=b.LINE)
        b.tx(slide, x + 0.2, y + 0.2, (w or 5.0) - 0.4, 0.3, f"Missing screenshot: {filename}", size=9, color=b.RED, bold=True)
        return None
    b.rect(slide, x - 0.04, y - 0.04, (w or 5.0) + 0.08, (hgt or 3.0) + 0.08, fill=b.WHITE, line=b.LINE)
    return b.pic(slide, str(path), x, y, w=w, hgt=hgt)


def small_kpi(slide, x, y, w, value, label, color=b.BLUE):
    b.rect(slide, x, y, w, 0.72, fill=b.WHITE, line=b.LINE)
    b.rect(slide, x, y, 0.05, 0.72, fill=color, line=None, rounded=False)
    b.tx(slide, x + 0.14, y + 0.08, w - 0.22, 0.26, value, size=14, color=b.INK, bold=True)
    b.tx(slide, x + 0.14, y + 0.42, w - 0.22, 0.18, label, size=6.5, color=b.MUTED, bold=True)


def proxy_badge(slide, x=9.05, y=6.86, text="Proxy estimate from enforcement records; not measured live traffic"):
    b.rect(slide, x, y, 3.45, 0.24, fill=b.ORANGE_50, line=b.ORANGE)
    b.tx(slide, x + 0.08, y + 0.055, 3.28, 0.1, text, size=6.2, color=b.ORANGE, bold=True, align=b.PP_ALIGN.CENTER)


def label_box(slide, x, y, w, h, label, body, color, fill=None):
    b.card(slide, x, y, w, h, label, body, accent=color, fill=fill or b.WHITE, title_size=10.4)


def dark_column(slide, x, y, w, h, title, items, accent):
    b.rect(slide, x, y, w, h, fill=b.NAVY_2, line=accent, lw=1.2)
    b.rect(slide, x, y, 0.07, h, fill=accent, line=None, rounded=False)
    b.tx(slide, x + 0.22, y + 0.18, w - 0.42, 0.28, title, size=12.3, color=b.WHITE, bold=True)
    for j, item in enumerate(items):
        b.tx(slide, x + 0.28, y + 0.72 + j * 0.34, w - 0.48, 0.18, "- " + item, size=8.8, color=b.RGBColor(0xD7, 0xE6, 0xFF))


def slide_1_title(prs, d, pg):
    s = b.blank(prs)
    b.rect(s, -0.1, -0.1, b.SW + 0.2, b.SH + 0.2, fill=b.NAVY, line=None, rounded=False)
    if (SCREENSHOTS / "pm_hotspot_map_crop.png").exists():
        b.rect(s, 7.12, 1.02, 5.38, 2.22, fill=b.NAVY_2, line=b.BLUE, lw=1.2)
        b.pic(s, str(SCREENSHOTS / "pm_hotspot_map_crop.png"), 7.22, 1.12, w=5.18, hgt=1.98)
    b.logo(s, 0.78, 0.58, dark=True)
    b.tx(s, 0.95, 1.45, 6.0, 0.56, "ParkPulse Bengaluru", size=35, color=b.WHITE, bold=True)
    b.tx(s, 0.98, 2.07, 6.0, 0.36, "Illegal Parking Impact Intelligence", size=16, color=b.YELLOW, bold=True)
    b.tx(s, 0.98, 2.72, 6.4, 0.86, "Which illegal parking should Bengaluru solve first?", size=25, color=b.WHITE, bold=True, spacing=1.0)
    b.tag(s, 0.98, 3.74, "Impact-weighted", b.ORANGE, w=1.55)
    b.tag(s, 2.68, 3.74, "Exposure-adjusted", b.BLUE, w=1.65)
    b.tag(s, 4.48, 3.74, "Resource-constrained", b.GREEN, w=1.82)
    eda = d["eda"]
    values = [
        (b.i_fmt(mval(d, "total_violations")), "violation records analysed"),
        (b.i_fmt(eda.get("active_days", 151)), "active calendar days"),
        (b.i_fmt(eda.get("stations", 55)), "police stations covered"),
        (b.i_fmt(mval(d, "total_hotspots")), "hotspot cells ranked"),
    ]
    for i, (value, label) in enumerate(values):
        small_kpi(s, 0.96 + i * 3.02, 5.05, 2.68, value, label, [b.YELLOW, b.BLUE, b.GREEN, b.ORANGE][i])
    b.tx(s, 0.98, 4.22, 11.2, 0.36, "A deployment decision system for control rooms, station inspectors and field officers - not a generic traffic dashboard.", size=12.4, color=b.RGBColor(0xD7, 0xE6, 0xFF), bold=True)
    b.tx(s, 0.98, 6.82, 11.2, 0.25, "Flipkart GRiD Round 2 | Theme 1 | AI-driven parking intelligence for illegal-parking hotspots and traffic-flow impact", size=8.6, color=b.RGBColor(0xC7, 0xD7, 0xF5), bold=True)


def slide_2_problem(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Problem", "Bengaluru does not have an illegal-parking data problem. It has a prioritization problem.", pg)
    takeaway(s, "All violations are not equal: a blocked running lane near a junction is operationally different from a low-impact challan.")
    stages = [
        ("Illegal parking", "Kerb or running-lane space occupied", b.ORANGE),
        ("Capacity loss", "Fewer usable lanes during the pressure window", b.BLUE),
        ("Queue spillback", "Junction, market, metro or corridor movement degrades", b.RED),
        ("Resource trade-off", "Patrol and tow units must be rationed by payoff", b.GREEN),
    ]
    x = 0.7
    for i, (title, body, color) in enumerate(stages):
        label_box(s, x, 2.35, 2.65, 1.36, title, body, color, b.WHITE)
        if i < len(stages) - 1:
            b.shp(s, b.MSO_SHAPE.RIGHT_ARROW, x + 2.72, 2.86, 0.32, 0.24, fill=color, line=None)
        x += 3.05
    label_box(s, 0.7, 4.35, 3.85, 1.46, "What a raw heatmap misses", ["Recording bias", "Officer/device visibility", "Vehicle footprint", "Tow/patrol capacity"], b.RED, b.RED_50)
    label_box(s, 4.75, 4.35, 3.85, 1.46, "What ParkPulse adds", ["Exposure adjustment", "Obstruction severity", "Repeat/chronic pressure", "Resource-constrained dispatch"], b.BLUE, b.BLUE_50)
    label_box(s, 8.8, 4.35, 3.55, 1.46, "Decision output", ["Which zone", "Which time window", "Which action", "Why this priority"], b.GREEN, b.GREEN_50)
    b.foot(s)


def slide_3_workflow(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Workflow shift", "From complaint-led patrolling to impact-weighted enforcement operations", pg)
    takeaway(s, "ParkPulse changes the operating model from 'where were violations recorded?' to 'where should the next enforcement unit go?'")
    headers = ["Current enforcement workflow", "ParkPulse workflow"]
    rows = [
        ["Complaint or patrol driven", "Daily command-center priority queue"],
        ["Raw visibility bias", "Exposure-adjusted hotspot ranking"],
        ["No congestion-impact ranking", "Obstruction, spillback and recovery proxies"],
        ["No officer-hour ROI", "Patrol/tow simulator and resource-hour payoff"],
        ["Limited feedback loop", "Closure/action fields become model feedback when integrated"],
    ]
    b.mini_table(s, 0.72, 2.18, 11.9, 3.36, headers, rows, col_widths=[5.95, 5.95], fs=10.2, header_fill=b.NAVY_2)
    b.rect(s, 0.9, 6.05, 11.55, 0.45, fill=b.BLUE_50, line=b.BLUE)
    b.tx(s, 1.1, 6.16, 11.1, 0.2, "Before: patrol harder. After: dispatch smarter, explain decisions, and learn after every shift.", size=11, color=b.BLUE_DARK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_4_personas(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Users", "Three police workflows, one shared operating system", pg)
    takeaway(s, "The product is designed around command, station planning and field execution - not around charts.")
    personas = [
        ("CONTROL ROOM", "Commander", "Allocate first-wave patrol/tow units", "Too many hotspots to inspect manually", "City priority queue + risk map", "Top-K high-impact capture", b.BLUE),
        ("STATION", "Inspector", "Plan local enforcement beats", "City heatmaps do not become local action", "Station-wise plan + time windows", "SLA compliance + repeat reduction", b.ORANGE),
        ("FIELD", "Officer / Tow Unit", "Clear the obstruction quickly", "Needs exact location, reason and action", "Mobile/printable field brief", "Closure time + recovery proxy", b.GREEN),
    ]
    for i, (badge, name, job, pain, feature, metric, color) in enumerate(personas):
        x = 0.65 + i * 4.12
        b.rect(s, x, 2.15, 3.72, 3.72, fill=b.WHITE, line=color, lw=1.25)
        b.tag(s, x + 0.22, 2.38, badge, color, w=1.2)
        b.tx(s, x + 0.22, 2.82, 3.22, 0.3, name, size=13.5, color=b.INK, bold=True)
        items = [("Job", job), ("Pain", pain), ("Feature", feature), ("Metric", metric)]
        for j, (label, text) in enumerate(items):
            yy = 3.35 + j * 0.52
            b.tx(s, x + 0.24, yy, 0.68, 0.18, label, size=7.4, color=color, bold=True)
            b.tx(s, x + 0.96, yy - 0.02, 2.48, 0.26, text, size=8.0, color=b.SLATE, spacing=1.02)
    b.foot(s)


def slide_5_journey(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Day-in-the-life", "A morning shift journey from control room to field clearance", pg)
    takeaway(s, "A good civic-tech product must fit the shift ritual, not ask officers to become analysts.")
    steps = [
        ("07:30", "Command Center opens", "City KPIs and corridor map"),
        ("07:35", "Top-20 zones ranked", "Obstruction-risk priority queue"),
        ("07:40", "Station plans issued", "Local time-window action plans"),
        ("08:00-12:00", "Field execution", "Tow/patrol/fixed-window enforcement"),
        ("End shift", "Feedback captured", "Closure/action data improves future runs"),
    ]
    x0, y = 0.75, 3.05
    for i, (time, title, body) in enumerate(steps):
        x = x0 + i * 2.42
        b.rect(s, x, y, 1.04, 1.04, fill=[b.BLUE, b.ORANGE, b.PURPLE, b.GREEN, b.NAVY_2][i], line=None)
        b.tx(s, x, y + 0.34, 1.04, 0.2, str(i + 1), size=15, color=b.WHITE, bold=True, align=b.PP_ALIGN.CENTER)
        b.tx(s, x - 0.34, y - 0.5, 1.72, 0.2, time, size=10, color=b.ORANGE, bold=True, align=b.PP_ALIGN.CENTER)
        b.tx(s, x - 0.46, y + 1.25, 2.0, 0.3, title, size=10.3, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
        b.tx(s, x - 0.44, y + 1.62, 1.96, 0.48, body, size=8.1, color=b.SLATE, align=b.PP_ALIGN.CENTER, spacing=1.05)
        if i < 4:
            b.line(s, x + 1.04, y + 0.52, x + 2.08, y + 0.52, color=b.LINE, lw=2)
    b.shp(s, b.MSO_SHAPE.LEFT_ARROW, 2.1, 5.48, 8.9, 0.22, fill=b.GREEN, line=None)
    b.tx(s, 4.1, 5.37, 4.85, 0.18, "Feedback loop: action / closure data improves tomorrow's priority queue", size=8.8, color=b.GREEN, bold=True, align=b.PP_ALIGN.CENTER)
    b.rect(s, 0.88, 5.98, 11.35, 0.42, fill=b.GREEN_50, line=b.GREEN)
    b.tx(s, 1.08, 6.08, 10.95, 0.18, "The same workflow is useful today with batch records, and becomes measured after closure/action feeds arrive.", size=10.2, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_6_dataset_honesty(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Data contract", "What we observe, what we model, what is a proxy, and what is absent", pg)
    takeaway(s, "Trust comes from labelling every claim: direct observation, modelled signal, transparent proxy or unavailable feed.")
    cols = [
        ("Observed directly", ["Location", "Timestamp", "Police station", "Vehicle class", "Violation text", "Validation status"], b.GREEN, b.GREEN_50),
        ("Modelled", ["Recurrence risk", "Hotspot persistence", "Exposure-adjusted ranking", "Patrol-coverage gap"], b.BLUE, b.BLUE_50),
        ("Transparent proxy", ["Obstruction-risk score", "Queue-spillback risk", "Equivalent lane recovery minutes", "Traffic-flow impact estimate"], b.ORANGE, b.ORANGE_50),
        ("Not available", ["Measured speed", "Queue length", "Closure timestamp", "Before-after enforcement outcome"], b.RED, b.RED_50),
    ]
    for i, (title, items, color, fill) in enumerate(cols):
        label_box(s, 0.58 + i * 3.08, 2.2, 2.82, 3.58, title, items, color, fill)
    b.tx(s, 0.72, 6.2, 11.9, 0.38, "Therefore: ParkPulse claims decision-support and impact-weighted prioritization today, not exact km/h improvement.", size=11, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_7_bias(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Bias stress test", "ParkPulse is not fooled by where enforcement is already visible", pg)
    takeaway(s, "High counts may mean true pressure, but they may also mean more officers, devices and validation coverage.")
    m = d["metrics"]
    small_kpi(s, 0.7, 2.12, 2.55, "0.85", "raw count vs recording exposure", b.RED)
    small_kpi(s, 3.55, 2.12, 2.55, "58%", "records with validation timestamp", b.GREEN)
    small_kpi(s, 6.4, 2.12, 2.55, b.p_fmt(m["robust_top20_overlap"]), "robust top-20 overlap", b.BLUE)
    small_kpi(s, 9.25, 2.12, 2.55, b.i_fmt(m["evening_records"]), "18-22 records: coverage risk", b.ORANGE)
    if (FIGURES / "topk_overlap_all_vs_high_confidence.png").exists():
        b.pic(s, str(FIGURES / "topk_overlap_all_vs_high_confidence.png"), 0.78, 3.28, w=4.6)
    flows = [
        ("Recording exposure bias", "Exposure-adjusted ranking", b.RED),
        ("Validation gaps", "Confidence bands", b.GREEN),
        ("Sparse evening records", "Coverage-risk warning", b.ORANGE),
        ("All vs high-confidence", "Robustness check", b.BLUE),
    ]
    for i, (bias, response, color) in enumerate(flows):
        y = 3.25 + i * 0.68
        b.rect(s, 5.72, y, 2.58, 0.46, fill=b.WHITE, line=color)
        b.tx(s, 5.84, y + 0.13, 2.34, 0.13, bias, size=7.4, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
        b.shp(s, b.MSO_SHAPE.RIGHT_ARROW, 8.45, y + 0.13, 0.38, 0.16, fill=color, line=None)
        b.rect(s, 8.96, y, 2.95, 0.46, fill=b.BLUE_50 if color == b.BLUE else b.WHITE, line=color)
        b.tx(s, 9.08, y + 0.13, 2.7, 0.13, response, size=7.4, color=color, bold=True, align=b.PP_ALIGN.CENTER)
    b.rect(s, 5.72, 6.15, 6.18, 0.42, fill=b.ORANGE_50, line=b.ORANGE)
    b.tx(s, 5.94, 6.25, 5.74, 0.18, "367 evening records is a coverage warning, not proof that evening risk is absent.", size=8.8, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_8_eda(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "EDA", "Why this is a targeted-enforcement problem, not generic clustering", pg)
    takeaway(s, "Obstruction pressure is concentrated, repeat vehicles matter, and road-space context changes enforcement priority.")
    b.pic(s, b.chart_concentration(d), 0.72, 2.15, w=4.5)
    label_box(s, 5.48, 2.18, 2.25, 1.1, "Concentrated", "Top 5 percent of cells hold about 65.5 percent of weighted obstruction.", b.BLUE, b.BLUE_50)
    label_box(s, 7.98, 2.18, 2.25, 1.1, "Repeating", "34.2 percent of known-vehicle records repeat at least twice.", b.PURPLE, b.PURPLE_50)
    label_box(s, 10.48, 2.18, 2.05, 1.1, "Chronic", "18.3 percent of known records are 3+ occurrence vehicles.", b.ORANGE, b.ORANGE_50)
    if (FIGURES / "theme_context_signal_weighted_obstruction.png").exists():
        b.pic(s, str(FIGURES / "theme_context_signal_weighted_obstruction.png"), 5.5, 3.72, w=6.65)
    b.rect(s, 1.0, 6.22, 11.0, 0.38, fill=b.NAVY, line=None)
    b.tx(s, 1.22, 6.31, 10.56, 0.16, "This is why enforcement should be targeted, not evenly spread.", size=10, color=b.WHITE, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_9_architecture(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Product architecture", "ParkPulse is a five-layer operating system for enforcement", pg)
    takeaway(s, "The architecture converts raw enforcement records into ranked actions, not just visualizations.")
    layers = [
        ("Data clean-room", "Violation records", "Normalised fields", b.BLUE),
        ("Hotspot engine", "Lat/lon + time", "250m cells + corridors", b.PURPLE),
        ("Scoring + model", "History + context", "Recurrence + obstruction risk", b.ORANGE),
        ("Action engine", "Risk + resources", "Tow/patrol/engineering plans", b.GREEN),
        ("Command product", "Plans + maps", "Briefs, simulator, queue", b.NAVY_2),
    ]
    for i, (layer, inp, out, color) in enumerate(layers):
        x = 0.68 + i * 2.48
        b.rect(s, x, 2.2, 2.18, 3.38, fill=b.WHITE, line=color, lw=1.2)
        b.tag(s, x + 0.14, 2.42, f"Layer {i+1}", color, w=0.82)
        b.tx(s, x + 0.15, 2.88, 1.88, 0.4, layer, size=10.8, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
        b.line(s, x + 0.35, 3.62, x + 1.82, 3.62, color=b.LINE, lw=1)
        b.tx(s, x + 0.18, 3.78, 1.82, 0.34, "Input", size=7.6, color=b.MUTED, bold=True, align=b.PP_ALIGN.CENTER)
        b.tx(s, x + 0.18, 4.12, 1.82, 0.36, inp, size=8.4, color=b.SLATE, align=b.PP_ALIGN.CENTER)
        b.tx(s, x + 0.18, 4.72, 1.82, 0.34, "Output", size=7.6, color=b.MUTED, bold=True, align=b.PP_ALIGN.CENTER)
        b.tx(s, x + 0.18, 5.06, 1.82, 0.38, out, size=8.4, color=b.SLATE, align=b.PP_ALIGN.CENTER)
        if i < 4:
            b.shp(s, b.MSO_SHAPE.RIGHT_ARROW, x + 2.2, 3.55, 0.25, 0.22, fill=color, line=None)
    b.foot(s)


def slide_10_ds_core(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Data Science core", "We optimize for top-K operational capture, not generic accuracy", pg)
    takeaway(s, "The modelling question is: which few zones should receive scarce enforcement capacity first?")
    blocks = [
        ("Spatial unit", "250m grid / hotspot cell", b.BLUE),
        ("Temporal unit", "Date x enforcement time-window", b.PURPLE),
        ("Features", "Lagged counts, rolling means, exposure, validation, vehicle obstruction, road context", b.ORANGE),
        ("Target", "Next-day / next-window recurrence and pressure", b.GREEN),
        ("Validation", "Time-safe split; no random future leakage", b.RED),
        ("Metrics", "Capture@K, NDCG@K, Precision@K", b.NAVY_2),
    ]
    for i, (title, body, color) in enumerate(blocks):
        row, col = divmod(i, 3)
        label_box(s, 0.72 + col * 4.05, 2.18 + row * 1.68, 3.62, 1.25, title, body, color, b.WHITE)
    flow = [("Features", b.BLUE), ("Target", b.PURPLE), ("Top-K ranking", b.ORANGE), ("Enforcement queue", b.GREEN)]
    for i, (label, color) in enumerate(flow):
        x = 1.18 + i * 2.78
        b.rect(s, x, 5.62, 2.16, 0.55, fill=color, line=None)
        b.tx(s, x + 0.08, 5.78, 2.0, 0.16, label, size=9.5, color=b.WHITE, bold=True, align=b.PP_ALIGN.CENTER)
        if i < 3:
            b.shp(s, b.MSO_SHAPE.RIGHT_ARROW, x + 2.25, 5.79, 0.28, 0.17, fill=color, line=None)
    b.tx(s, 1.16, 6.42, 11.0, 0.2, "Why top-K? Police need the best first 10-20 actions before the shift starts, not a perfect city-wide regression score.", size=9.6, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_11_density(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Why raw density is not enough", "A heatmap finds where violations were recorded; ParkPulse finds where enforcement should go next", pg)
    takeaway(s, "Prediction and action are different jobs: recurrence is only the first filter.")
    cases = [
        ("High count + high exposure", "May already be heavily patrolled; do not blindly over-allocate.", "Correct with exposure adjustment", b.RED),
        ("Medium count + heavy vehicles + junction", "Can block running lanes and spill queues despite fewer records.", "Raise obstruction priority", b.ORANGE),
        ("Emerging hotspot + low past exposure", "Hidden risk can be missed by raw historic density.", "Flag patrol gap", b.BLUE),
    ]
    for i, (title, body, response, color) in enumerate(cases):
        x = 0.78 + i * 4.0
        b.rect(s, x, 2.25, 3.5, 3.05, fill=b.WHITE, line=color, lw=1.3)
        b.tx(s, x + 0.2, 2.48, 3.05, 0.38, title, size=12, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
        b.tx(s, x + 0.24, 3.15, 3.0, 0.78, body, size=9.1, color=b.SLATE, align=b.PP_ALIGN.CENTER, spacing=1.12)
        b.rect(s, x + 0.28, 4.32, 2.94, 0.45, fill=[b.RED_50, b.ORANGE_50, b.BLUE_50][i], line=color)
        b.tx(s, x + 0.36, 4.44, 2.78, 0.16, response, size=8.4, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.rect(s, 1.0, 6.0, 11.0, 0.42, fill=b.GREEN_50, line=b.GREEN)
    b.tx(s, 1.18, 6.1, 10.62, 0.2, "ParkPulse first predicts recurrence, then adds obstruction severity, confidence, action type and officer-hour ROI.", size=10.2, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_12_scoring(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Scoring logic", "Prediction, explanation and dispatch are deliberately separate jobs", pg)
    takeaway(s, "A single magic score is fragile; ParkPulse separates recurrence, obstruction explanation and resource-constrained dispatch.")
    b.rect(s, 0.75, 2.22, 3.55, 2.74, fill=b.BLUE_50, line=b.BLUE)
    b.tx(s, 0.95, 2.46, 3.15, 0.35, "1. Recurrence model", size=14, color=b.BLUE_DARK, bold=True, align=b.PP_ALIGN.CENTER)
    b.tx(s, 1.0, 3.05, 3.05, 1.05, "Predicts where pressure returns using lagged counts, rolling windows, exposure and validation features.", size=9.2, color=b.INK, align=b.PP_ALIGN.CENTER, spacing=1.12)
    b.shp(s, b.MSO_SHAPE.RIGHT_ARROW, 4.38, 3.48, 0.38, 0.26, fill=b.BLUE, line=None)
    b.rect(s, 4.9, 2.22, 3.55, 2.74, fill=b.ORANGE_50, line=b.ORANGE)
    b.tx(s, 5.1, 2.46, 3.15, 0.35, "2. Obstruction index", size=14, color=b.ORANGE, bold=True, align=b.PP_ALIGN.CENTER)
    b.tx(s, 5.16, 3.05, 3.03, 1.05, "Explains severity using persistence, time pressure, junction context, vehicle footprint and repeat pressure.", size=9.2, color=b.INK, align=b.PP_ALIGN.CENTER, spacing=1.12)
    b.shp(s, b.MSO_SHAPE.RIGHT_ARROW, 8.53, 3.48, 0.38, 0.26, fill=b.ORANGE, line=None)
    b.rect(s, 9.05, 2.22, 3.55, 2.74, fill=b.GREEN_50, line=b.GREEN)
    b.tx(s, 9.25, 2.46, 3.15, 0.35, "3. Dispatch priority", size=14, color=b.GREEN, bold=True, align=b.PP_ALIGN.CENTER)
    b.tx(s, 9.3, 3.05, 3.04, 1.05, "Sequences field action using recovery potential, confidence, patrol gap and resource requirement.", size=9.2, color=b.INK, align=b.PP_ALIGN.CENTER, spacing=1.12)
    b.tx(s, 1.0, 5.32, 3.05, 0.18, "Predict recurrence", size=9.2, color=b.BLUE_DARK, bold=True, align=b.PP_ALIGN.CENTER)
    b.tx(s, 5.13, 5.32, 3.1, 0.18, "Explain obstruction", size=9.2, color=b.ORANGE, bold=True, align=b.PP_ALIGN.CENTER)
    b.tx(s, 9.32, 5.32, 3.0, 0.18, "Dispatch resources", size=9.2, color=b.GREEN, bold=True, align=b.PP_ALIGN.CENTER)
    b.rect(s, 1.4, 5.85, 10.5, 0.42, fill=b.NAVY, line=None)
    b.tx(s, 1.62, 5.95, 10.05, 0.2, "All traffic-flow impact values are modelled proxies until speed, queue and closure feeds are connected.", size=10.0, color=b.WHITE, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_13_validation(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Validation + differentiation", "Why ParkPulse beats a heatmap", pg)
    takeaway(s, "Raw density tells us where violations return. ParkPulse tells us where limited enforcement creates the highest operational payoff.")
    m = d["metrics"]
    small_kpi(s, 0.72, 2.12, 2.35, b.p_fmt(m["selected_forecast_capture_at_20"]), "Capture@20: top-20 zones vs next-day high-pressure cells", b.BLUE)
    small_kpi(s, 3.28, 2.12, 2.35, b.p_fmt(m["raw_count_baseline_capture_at_20"]), "raw-density Capture@20: recurrence baseline", b.MUTED)
    small_kpi(s, 5.84, 2.12, 2.35, b.p_fmt(m["robust_top20_overlap"]), "top-20 overlap: all vs high-confidence records", b.GREEN)
    small_kpi(s, 8.4, 2.12, 2.35, "+" + b.f_fmt(m["parkpulse_vs_density_recovery_uplift_pct"]) + "%", "recovery-proxy uplift under same resources", b.ORANGE)
    b.rect(s, 10.96, 2.12, 1.36, 0.72, fill=b.ORANGE_50, line=b.ORANGE)
    b.tx(s, 11.08, 2.27, 1.12, 0.14, "Proxy", size=9, color=b.ORANGE, bold=True, align=b.PP_ALIGN.CENTER)
    b.tx(s, 11.08, 2.48, 1.12, 0.12, "not live delay", size=6.2, color=b.MUTED, bold=True, align=b.PP_ALIGN.CENTER)
    rows = [
        ["What it ranks", "Recorded counts", "Where pressure returns", "Where enforcement should go next"],
        ["Bias handling", "Can reflect patrol/device bias", "Partly learns history", "Exposure + confidence aware"],
        ["Traffic-flow impact", "None", "None", "Obstruction and spillback proxies"],
        ["Action output", "No tow/patrol guidance", "No dispatch guidance", "Tow, patrol, fixed-window or engineering"],
        ["Field usability", "Map only", "Prediction list", "Brief: location, reason, SLA, resource"],
    ]
    b.mini_table(s, 0.72, 3.25, 11.85, 2.45, ["Decision question", "Raw heatmap", "Density forecast", "ParkPulse"], rows, col_widths=[2.4, 2.9, 2.85, 3.7], fs=6.95, header_fill=b.BLUE_50)
    b.rect(s, 1.0, 6.14, 11.0, 0.43, fill=b.PURPLE_50, line=b.PURPLE)
    b.tx(s, 1.18, 6.25, 10.64, 0.18, "Prediction layer finds where pressure returns. Action layer decides what to do with scarce patrol and tow capacity.", size=9.8, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s)


def slide_14_command(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Product walkthrough", "Command Center: one city map, six decision numbers, one priority queue", pg)
    takeaway(s, "The control room sees what to act on first, not a generic traffic dashboard.")
    shot(s, "pm_command_center_crop.png", 0.55, 2.08, w=8.55, hgt=4.72)
    label_box(s, 9.35, 2.18, 3.05, 0.78, "KPI cards", "Six decision numbers for the shift.", b.BLUE, b.BLUE_50)
    label_box(s, 9.35, 3.12, 3.05, 0.78, "Risk map", "Basemap + inferred corridor-risk lanes.", b.ORANGE, b.ORANGE_50)
    label_box(s, 9.35, 4.06, 3.05, 0.78, "Priority queue", "Top actions ordered by payoff.", b.GREEN, b.GREEN_50)
    label_box(s, 9.35, 5.0, 3.05, 0.78, "Proxy labels", "Impact estimates are clearly marked.", b.PURPLE, b.PURPLE_50)
    b.rect(s, 9.35, 5.98, 3.05, 0.42, fill=b.NAVY, line=None)
    b.tx(s, 9.48, 6.08, 2.79, 0.18, "Built as a working product, not a mock chart.", size=8.6, color=b.WHITE, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s, note="Live screenshot from the ParkPulse React prototype")


def slide_15_station_field(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Product walkthrough", "Station inspector and field officer: from hotspot explanation to action brief", pg)
    takeaway(s, "A hotspot card answers: where, when, why, what action, confidence, deadline and required resource.")
    shot(s, "pm_hotspot_field_crop.png", 0.55, 2.1, w=6.6, hgt=4.45)
    b.rect(s, 7.45, 2.12, 4.85, 4.45, fill=b.WHITE, line=b.BLUE, lw=1.2)
    b.tx(s, 7.72, 2.38, 4.32, 0.34, "Field Brief", size=17, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    brief = [
        ("Location", "Outer Ring Road, Marathahalli"),
        ("Best window", "00-06 night / early morning"),
        ("Action", "Pre-position tow + patrol unit"),
        ("Reason", "Main-road illegal parking likely blocking running lane"),
        ("Confidence", "High confidence; validation-aware"),
        ("SLA", "Immediate clearance: within 30 minutes"),
        ("Resource", "1 tow vehicle + 1 patrol unit"),
    ]
    for i, (label, value) in enumerate(brief):
        y = 2.92 + i * 0.43
        b.tx(s, 7.74, y, 0.95, 0.16, label, size=7.2, color=b.BLUE, bold=True)
        b.tx(s, 8.72, y - 0.02, 3.28, 0.2, value, size=7.7, color=b.SLATE, bold=(label in ["Action", "SLA"]))
    b.rect(s, 7.68, 6.15, 4.2, 0.34, fill=b.GREEN_50, line=b.GREEN)
    b.tx(s, 7.86, 6.23, 3.84, 0.15, "This is the bridge from data science to police action.", size=8.6, color=b.INK, bold=True, align=b.PP_ALIGN.CENTER)
    b.foot(s, note="Live screenshot from Hotspot Intelligence after basemap/corridor fix")


def slide_16_simulator(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Deployment simulator", "Limited patrol and tow resources become a measurable allocation plan", pg)
    takeaway(s, "The simulator turns enforcement strategy into resource-constrained dispatch decisions before a shift begins.")
    shot(s, "pm_deployment_simulator_crop.png", 0.55, 2.08, w=7.15, hgt=4.75)
    m = d["metrics"]
    label_box(s, 8.0, 2.15, 4.3, 0.86, "Resource inputs", "Patrol units + tow vehicles + station + time window", b.BLUE, b.BLUE_50)
    b.shp(s, b.MSO_SHAPE.DOWN_ARROW, 9.95, 3.08, 0.34, 0.28, fill=b.BLUE, line=None)
    label_box(s, 8.0, 3.42, 4.3, 0.86, "Selected zones", "The highest payoff hotspots under the same resource budget", b.ORANGE, b.ORANGE_50)
    b.shp(s, b.MSO_SHAPE.DOWN_ARROW, 9.95, 4.35, 0.34, 0.28, fill=b.ORANGE, line=None)
    label_box(s, 8.0, 4.7, 4.3, 0.86, "Covered / uncovered risk", "Covered obstruction proxy, uncovered risk and resource-hour ROI", b.GREEN, b.GREEN_50)
    small_kpi(s, 8.0, 5.88, 1.95, b.i_fmt(m["standard_budget_recovery_minutes"]) + " min", "standard-shift lane-recovery proxy", b.GREEN)
    small_kpi(s, 10.35, 5.88, 1.95, "+" + b.f_fmt(m["parkpulse_vs_density_recovery_uplift_pct"]) + "%", "vs raw-density dispatch; same budget", b.PURPLE)
    proxy_badge(s, x=8.0, y=6.74, text="Proxy planning back-test; not measured live traffic delay")
    b.foot(s, note="Live screenshot from the ParkPulse deployment simulator")


def slide_17_roadmap(prs, d, pg):
    s = b.blank(prs)
    b.header(s, "Rollout roadmap", "Useful tomorrow morning, stronger as richer feeds arrive", pg)
    takeaway(s, "The MVP is day-one deployable from violation records; production integrations convert proxies into measured outcomes.")
    phases = [
        ("Day 1", "Batch dashboard", ["Decision support", "Hotspot ranking", "Station-wise plans"], b.BLUE),
        ("30 days", "Feedback loop", ["Outcome learning", "Closure/tow timestamps", "SLA compliance"], b.ORANGE),
        ("90 days", "Measured impact", ["Measured traffic impact", "Speed + queue feeds", "Before-after review"], b.GREEN),
        ("Next feeds", "Full command stack", ["Road graph/lane width", "Signal health", "Patrol roster + events"], b.PURPLE),
    ]
    for i, (phase, title, items, color) in enumerate(phases):
        x = 0.72 + i * 3.02
        b.tag(s, x, 2.18, phase, color, w=1.05)
        label_box(s, x, 2.68, 2.68, 2.78, title, items, color, b.WHITE)
        if i < 3:
            b.shp(s, b.MSO_SHAPE.RIGHT_ARROW, x + 2.72, 3.82, 0.22, 0.2, fill=color, line=None)
    b.mini_table(s, 0.96, 5.85, 11.36, 0.58, ["Success metric", "Examples"], [["Operational adoption", "Top-K capture, SLA compliance, repeat-offender reduction, officer-hour ROI, closure-time reduction"]], col_widths=[2.4, 8.96], fs=7.6)
    b.foot(s)


def slide_18_close(prs, d, pg):
    s = b.blank(prs)
    b.rect(s, -0.1, -0.1, b.SW + 0.2, b.SH + 0.2, fill=b.NAVY, line=None, rounded=False)
    b.logo(s, 0.72, 0.52, dark=True)
    b.tx(s, 0.92, 1.22, 11.35, 0.55, "Defensible today. Measurable tomorrow.", size=31, color=b.WHITE, bold=True)
    b.tx(s, 0.95, 1.92, 10.8, 0.36, "ParkPulse narrows the field, explains the reason, dispatches the right resource, and learns after every shift.", size=14, color=b.YELLOW, bold=True)
    claims = [
        ("Claim with confidence now", ["Recurring hotspots", "Repeat/chronic pressure", "Exposure-adjusted priority", "Station-wise plans"], b.GREEN),
        ("Use as transparent proxy", ["Obstruction risk", "Spillback risk", "Lane-recovery minutes", "Traffic-flow impact estimate"], b.ORANGE),
        ("Measure after integration", ["Speed improvement", "Queue reduction", "Closure impact", "Manpower response effectiveness"], b.BLUE),
    ]
    for i, (title, items, color) in enumerate(claims):
        x = 0.95 + i * 4.08
        dark_column(s, x, 3.02, 3.66, 2.35, title, items, color)
    b.rect(s, 1.05, 6.15, 11.1, 0.55, fill=b.BLUE, line=None)
    b.tx(s, 1.24, 6.31, 10.72, 0.18, "ParkPulse is not a heatmap. It is a decision system for deciding which illegal parking Bengaluru should solve first.", size=11.5, color=b.WHITE, bold=True, align=b.PP_ALIGN.CENTER)


SLIDES = [
    slide_1_title,
    slide_2_problem,
    slide_3_workflow,
    slide_4_personas,
    slide_5_journey,
    slide_6_dataset_honesty,
    slide_7_bias,
    slide_8_eda,
    slide_9_architecture,
    slide_10_ds_core,
    slide_11_density,
    slide_12_scoring,
    slide_13_validation,
    slide_14_command,
    slide_15_station_field,
    slide_16_simulator,
    slide_17_roadmap,
    slide_18_close,
]


OUTLINE_ROWS = [
    ("ParkPulse Bengaluru", "Hook judges on the decision question.", "Which illegal parking should Bengaluru solve first?", "Dark title, headline metrics, product thesis.", "Strong hero title with KPI strip.", "Open by saying this is not a heatmap; it is impact-weighted enforcement prioritization.", "Remove generic title clutter."),
    ("The Real Problem", "Show that prioritization is the bottleneck.", "All violations are not equal.", "Violation-to-spillback chain, raw heatmap limitation, ParkPulse addition.", "Four-step flow plus three cards.", "Use lane blockage and scarce tow units as the story.", "Remove generic traffic dashboard language."),
    ("Current Workflow vs ParkPulse Workflow", "Make the PM before/after obvious.", "ParkPulse changes the operating model.", "Before/after table across bias, impact, ROI and feedback.", "Two-column comparison.", "Say the current workflow sees records; ParkPulse creates actions.", "Remove dense methodology text."),
    ("User Personas", "Show product users and jobs-to-be-done.", "Command, station and field workflows share one OS.", "Commander, inspector, field officer cards.", "Persona cards with metric.", "Explain that each user gets a different surface, not a generic dashboard.", "Remove broad user statements."),
    ("Day-in-the-Life Journey", "Make adoption feel real.", "The product fits the morning shift ritual.", "Five-step timeline from 7:30 AM to end-of-shift feedback.", "Operational timeline.", "Narrate a real control-room morning.", "Remove abstract roadmap from early deck."),
    ("Dataset and Honest Measurement", "Build trust.", "Every claim is labelled.", "Observed/modelled/proxy/not available.", "Four-column evidence contract.", "Say exact speed/queue reduction is not claimed.", "Remove overclaiming phrases."),
    ("Bias Stress Test", "Explain why raw counts are risky.", "ParkPulse corrects for visibility bias.", "Exposure correlation, validation timestamp, robust overlap, sparse evening records.", "Metric strip plus validation figures.", "Say high count can mean more enforcement visibility.", "Remove unsupported density claims."),
    ("EDA Insights", "Show the data story in few signals.", "Targeted enforcement is justified.", "Concentration, repeat vehicles, chronic zones, road-space context.", "Concentration chart and context chart.", "Use only 3-4 insights.", "Remove extra tables."),
    ("Product Architecture", "Frame as an operating system.", "Raw records become ranked actions.", "Five layers with input and output.", "Architecture stack.", "Make it product architecture, not ML pipeline only.", "Remove code/process laundry lists."),
    ("DS Core", "Explain modelling without overload.", "Optimize top-K operational capture.", "Spatial/temporal units, features, target, validation, metrics.", "Six modelling blocks.", "Tell why top-K matters for police.", "Remove generic accuracy metrics."),
    ("Why Raw Density Is Not Enough", "Defend differentiation.", "Prediction and action are different jobs.", "Three scenarios: over-patrolled, obstructive medium count, hidden risk.", "Scenario cards.", "Say raw density predicts recurrence; ParkPulse decides action.", "Remove any 'model beats everything' framing."),
    ("Scoring Logic", "Separate recurrence, explanation and dispatch.", "No single magic score.", "Recurrence model, obstruction index, dispatch priority.", "Three-score logic board.", "Repeat proxy honesty.", "Remove formula overload."),
    ("Validation + Differentiation", "Show why honest validation still supports a stronger product.", "Raw density tells us where violations return; ParkPulse tells us where limited enforcement creates highest payoff.", "Capture@20, raw-density baseline, robustness, recovery-proxy uplift, and raw heatmap vs ParkPulse table.", "Metric strip plus comparison table.", "Defend the close model-vs-density result by separating prediction from action.", "Remove inflated ML claims and unclear metric denominators."),
    ("Command Center", "Show working product.", "A control room can act in seconds.", "Large product screenshot, KPI cards, risk map, priority queue, proxy labels.", "Dominant live screenshot with short callouts.", "Walk through the screen like a duty officer.", "Remove decorative screenshots and long paragraph blocks."),
    ("Station + Field Officer", "Complete the field journey.", "The hotspot card becomes an action brief.", "Live hotspot screenshot plus field-brief card: location, window, action, reason, confidence, SLA, resource.", "Screenshot plus mock field brief.", "Show how a field officer knows what to do.", "Remove excess charts."),
    ("Deployment Simulator", "Show resource allocation.", "Limited units become measurable plans.", "Resource inputs, selected zones, covered/uncovered risk, recovery-proxy uplift.", "Large simulator screenshot plus resource-flow cards.", "Move sliders in the demo and clarify proxy meaning.", "Remove generic ROI claims."),
    ("Rollout Roadmap", "Prove implementability.", "Useful now; measurable as feeds arrive.", "Day 1 decision support, 30-day outcome learning, 90-day measured traffic impact, next command feeds.", "PM roadmap.", "State exactly what data is needed next.", "Remove vague future AI."),
    ("Defensibility and Close", "End with trust and ambition.", "Defensible today. Measurable tomorrow.", "Claim with confidence now, transparent proxy, measure after integration.", "Clean dark closing board.", "Final line: not a heatmap, a decision system for deciding what Bengaluru should solve first.", "Remove duplicate columns and hidden caveats."),
]


def write_outline():
    lines = [
        "# ParkPulse PM + Data Science Deck Outline",
        "",
        "This rewrite follows the ChatGPT Plus deck prompt: product-led, judge-facing, honest about proxies, and built around impact-weighted enforcement prioritization.",
        "",
    ]
    for i, row in enumerate(OUTLINE_ROWS, 1):
        title, objective, main, blocks, visual, speaker, remove = row
        lines.extend([
            f"## Slide {i}: {title}",
            f"- Objective: {objective}",
            f"- Main takeaway: {main}",
            f"- Content blocks: {blocks}",
            f"- Suggested visual: {visual}",
            f"- Speaker note: {speaker}",
            f"- Remove from current deck: {remove}",
            "",
        ])
    OUTLINE.write_text("\n".join(lines), encoding="utf-8")


def build():
    d = b.load_data()
    prs = Presentation()
    prs.slide_width = b.Inches(b.SW)
    prs.slide_height = b.Inches(b.SH)
    for i, fn in enumerate(SLIDES, 1):
        fn(prs, d, i)
    prs.save(str(OUT))
    write_outline()
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {len(prs.slides)} slides).")
    print(f"Wrote {OUTLINE}.")


if __name__ == "__main__":
    build()
