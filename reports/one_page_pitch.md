# ParkPulse Bengaluru — One-Page Pitch

## The problem (Theme 1)
On-street and spillover illegal parking near markets, metro stations, junctions, and
signals chokes carriageways and intersections. Enforcement today is patrol-based and
reactive: there is no shared view of *which* illegal-parking zones actually hurt traffic
flow the most, so limited officers and tow vehicles are not aimed where they recover the
most road capacity.

## Why it is hard
The available data is enforcement violation records — not speed, queue length, travel
time, lane-level GIS, signal-health telemetry, or live patrol rosters. A credible product
has to quantify traffic impact and prioritise enforcement **without pretending to measure
things the data does not contain.**

## What ParkPulse does
ParkPulse turns ~298k cleaned Bengaluru violation records into an operational
decision-support system for traffic police:

1. **Detects recurring hotspots** by grid + station + time-window (not one-off points).
2. **Forecasts recurrence with the validated signal** — leakage-safe model features,
   raw density, weighted obstruction, and time-safe history are compared rather than
   assumed.
3. **Scores action risk (TORI)** from density, persistence, time-window pressure,
   junction criticality, vehicle footprint, severity, validation confidence, and an
   enforcement-exposure adjustment so raw counts are not blindly trusted.
4. **Infers a corridor risk network** — repeated hotspots are snapped onto a data-fitted
   centerline, linked into corridors, and labelled with a bottleneck class
   (arterial kerb-lane choke, junction-mouth blocker, metro/market spillover, …).
5. **Recommends an action per zone** (tow, fixed-window patrol, engineering fix,
   spillover control, watchlist) with patrol/tow hour estimates.
6. **Quantifies field impact** with capacity-loss pressure, queue-spillback
   risk, clearance SLA, evidence quality, ELRM and recovery/resource-hour.

## The hard operational layer
**Equivalent Lane Recovery Minutes** estimates the running-lane time recovered in the
target window if the recommended action is executed. It is reported as a **range**
(conservative → optimistic effectiveness) so assumptions stay explicit, and it is refined
by a carriageway recovery class and a small junction-clearance benefit.

> Acting on the top-20 zones recovers ≈ **3,200 equivalent lane-minutes** (range
> ≈ 2,600–3,800) at ≈ **33 recovery-minutes per resource-hour.**

ParkPulse also reports capacity-loss pressure, queue-spillback risk, clearance SLA and
evidence quality. Together, these tell a duty officer whether the hotspot is merely
frequent, or whether it can actually choke a carriageway or junction. ELRM is a
transparent operational proxy for comparing deployments — **not** a measured
travel-time saving.

## Why judges can trust it
- **Built only on the provided dataset.** No external GIS, no purchased traffic/speed
  feed, no map-matching service. The command map renders offline with no third-party tiles.
- **Honest about limits.** Speed, queue, surveyed lane geometry, signal-health, and live
  workforce are clearly marked as optional future integrations, never silently assumed.
- **Validated.** Recurrence is led by the best validation signal, not a hardcoded
  score; TORI is explicitly the action/explanation layer; ELRM is back-tested as
  a separate operational proxy; robustness is checked with top-K overlap.
- **Policy-tested.** A deployment policy lab compares ParkPulse against TORI-only,
  raw-density, ELRM-first, capacity-first and spillback-first dispatch under patrol/tow
  budgets.
- **Data quirks are surfaced.** The 18:00–22:00 window is unusually sparse in the
  provided records, so the system flags it as coverage risk instead of pretending
  evening traffic is absent.

## Deployable today
Because it needs only the enforcement data a city already owns, ParkPulse runs without any
data-sharing agreement. It ships as a React command center (Command Center, Live Ops Brief,
Priority Queue, Hotspot Intelligence, Tomorrow's Risk, Deployment Simulator, Station View,
Methodology) plus printable per-zone field briefs for officers.

**ParkPulse does not just show illegal parking. It tells Bengaluru Traffic Police which
illegal parking to solve first.**
