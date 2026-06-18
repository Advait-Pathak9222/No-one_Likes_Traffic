# ParkPulse 3-Minute Product Pitch Script

## Recording Setup

- Open the app at `http://127.0.0.1:4173`.
- Use browser zoom around 90 percent if the screen feels crowded.
- Keep the cursor visible. Move slowly and deliberately.
- Start on the **Command Center** page.
- Target length: 2 minutes 50 seconds to 3 minutes 10 seconds.

---

## 0:00-0:20 — Opening Problem

**Screen:** Command Center hero section.

**Say:**
> Bengaluru does not only have a parking-enforcement problem. It has a road-capacity allocation problem. One illegally parked vehicle on a narrow commercial road or near a junction can choke a running lane, create spillback, and waste police response time. Today, enforcement is often reactive. ParkPulse asks one operational question: which illegal parking should Bengaluru solve first?

---

## 0:20-0:50 — Product Thesis

**Screen action:** Point to the six KPI cards on the Command Center.

**Say:**
> ParkPulse converts five months of police violation records into a deployment engine. It does three things. First, it predicts recurring illegal-parking pressure. Second, it explains traffic obstruction using transparent proxy metrics like TORI, spillback risk, repeat-vehicle pressure, patrol gap, and equivalent lane-recovery minutes. Third, it turns those scores into station-wise enforcement actions: tow, fixed-window patrol, engineering support, or spillover control.

**Show:** Point to:
- `Recurrence Capture@20`
- `Top-20 Lane Recovery`
- `High Spillback Zones`
- `Chronic Repeat Zones`
- `Patrol-Gap Zones`

---

## 0:50-1:25 — Hotspot Map And Corridor Risk

**Screen action:** On Command Center, show the **City Corridor Risk Map**.

**Do this:**
1. Toggle **Corridor risk** off and on once.
2. Move **Min obstruction score** from around `80` to `90`, then back to `80`.
3. Click a visible high-priority hotspot or click the #1 row in the priority panel.

**Say:**
> The map is where this becomes operational. The background is a real Bengaluru basemap. The colored lines are inferred corridor-obstruction risk from our dataset: blue is low, yellow is moderate, and red is severe. These are not claimed as live Google traffic speeds. They are an honest obstruction-risk layer built from violation coordinates, vehicle type, road-space context, recurrence, and severity.

---

## 1:25-1:55 — Why This Hotspot?

**Screen:** Hotspot Intelligence page.

**Do this:**
1. Scroll slightly to the **Hotspot Location & Corridor Risk Map**.
2. Point to the selected hotspot circle and colored corridor segments.
3. Point to the top pills: action, confidence, spillback, SLA, repeat, patrol gap, recovery.

**Say:**
> For every hotspot, the officer sees the exact location, nearby corridor pressure, and the reason behind the recommendation. Here, ParkPulse explains whether the issue is repeat parking, a main-road kerb-lane obstruction, a double-park lane squeeze, or a patrol-coverage gap. The system does not just say “high risk.” It says why this location matters, what action fits, and how fast the first unit should respond.

---

## 1:55-2:25 — Deployment Simulator

**Screen action:** Click **Deployment Simulator** in the sidebar.

**Do this:**
1. Move **Patrol units** upward, for example from `10` to `15`.
2. Move **Tow vehicles** upward, for example from `3` to `6`.
3. Point to the changing cards: Covered Hotspots, Recoverable Lane-Min, Recovery Coverage, Patrol/Tow Used.

**Say:**
> In a control room, resources are always limited. This simulator lets a duty officer test how many patrol and tow units are needed before the shift begins. As I increase capacity, ParkPulse recalculates covered hotspots and recoverable lane-minutes. This is the difference between a dashboard and a deployment product: it helps choose the best action under constraints.

---

## 2:25-2:45 — Live Ops Brief

**Screen action:** Click **Live Ops Brief**.

**Do this:**
1. Show the radio brief.
2. Point to Dispatch Wave and Escalation Triggers.

**Say:**
> The Live Ops Brief is built for moments of chaos. It gives the first radio message, station-wise dispatch waves, tow-queue risks, chronic repeat pressure, patrol-gap zones, and a five-minute runbook. A senior officer can decide the first wave without reading raw tables.

---

## 2:45-3:05 — Honest Impact And Close

**Screen action:** Optionally click **Methodology**, or stay on Live Ops Brief.

**Say:**
> The current dataset does not contain live speed, signal-health, exact lane geometry, or before-after closure outcomes, so ParkPulse labels traffic-flow impact as a transparent proxy. That is the honest engineering choice. But it is day-one implementable because it works with data police already collect. As richer feeds arrive, the same system becomes a measured congestion-impact engine. ParkPulse narrows the field, explains the reason, dispatches the right resource, and learns after every shift.

**Final line:**
> ParkPulse is not just hotspot detection. It is targeted enforcement intelligence for recovering Bengaluru’s road capacity.

---

## Backup One-Line Answers For Judges

- **What is TORI?** Traffic Obstruction Risk Index: an explainable severity score for how damaging a parking hotspot is likely to be.
- **Is the red/yellow/blue layer live traffic speed?** No. It is inferred corridor-obstruction risk from violation records, clearly labelled as a proxy.
- **What makes this day-one implementable?** It uses existing police violation data, station names, timestamps, vehicle classes, violation text, and coordinates.
- **What improves it in production?** Add speed feeds, signal-health, surveyed road geometry, patrol GPS, tow availability, and closure timestamps.
