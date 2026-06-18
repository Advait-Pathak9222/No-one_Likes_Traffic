# Research-Backed Metric Upgrade

ParkPulse should not depend on one invented score. Illegal parking is a real
traffic-operations problem, so the system now separates **prediction** from
**action**:

1. **Predict recurrence** with the best validated density/history/model signal
   from leakage-safe forecasting and simple baselines.
2. **Explain obstruction** with TORI and road-space context.
3. **Prioritise operations** with capacity-loss pressure, queue-spillback risk,
   clearance SLA, ELRM and recovery per resource-hour.
4. **Stress-test policies** under patrol/tow budgets before asking officers to
   trust the priority queue.

## Why Move Beyond TORI / ELRM?

TORI is useful for explaining why a hotspot is bad. ELRM is useful for comparing
how much lane-time may be recovered. But a traffic police officer in a control
room needs more operational questions answered:

- Is this hotspot likely to reduce usable carriageway capacity?
- Can the queue spill into a signal, junction or main-road bottleneck?
- How fast should the first unit reach the zone?
- Is towing worth using here, or should it be patrol-only?
- Is the evidence strong enough to act now?

The new metrics answer these questions directly.

## Research Signals Used

- Curbside activity can disturb mainline traffic flow and create measurable
  congestion externalities. A causal study of curbside pick-ups/drop-offs shows
  that curb occupation can reduce network speed and that rerouting/management
  can reduce system travel time. Source:
  [Liu, Qian, Teo & Ma, 2022](https://arxiv.org/abs/2206.02164).
- Double parking is widely treated as an operational and safety problem, and
  data-driven frameworks can identify locations with the greatest benefit from
  removing problematic double parking. Source:
  [Gao, Ozbay & Marsico, 2020](https://arxiv.org/abs/2011.11238).
- Curbside parking demand is strongly spatial and temporal. Location,
  time-of-day and repeatability are meaningful when deciding where to manage
  curb pressure. Source:
  [Fiez & Ratliff, 2017](https://arxiv.org/abs/1712.01263).
- Transportation agencies commonly evaluate operations with delay, vehicle-hours
  travelled, speed, reliability and bottleneck concepts. Our dataset lacks
  direct speeds/queues, so ParkPulse uses transparent obstruction proxies instead
  of claiming measured travel-time savings.
- Open-source traffic tools such as SUMO and OSMnx suggest the next production
  path: snap hotspots onto a true road graph, simulate blockage/removal
  scenarios, and report before/after operational metrics. ParkPulse keeps this
  as a future integration because the current hackathon dataset does not include
  surveyed network geometry or live speeds.

## Metrics Now Implemented

### 1. Validated Recurrence Signal

ParkPulse compares raw density, weighted obstruction density, time-safe history,
and leakage-safe model predictions. The winning recurrence signal is selected by
validation instead of being hardcoded. That matters because a future police
dataset may have different recording patterns.

### 2. Capacity-Loss Pressure

Proxy for how strongly the hotspot may reduce usable road capacity:

`obstruction intensity × lane context × recurrence × time sensitivity`

This is closer to a real bottleneck concept than raw violation count.

### 3. Queue-Spillback Risk

Proxy for whether the obstruction can push queues into a junction, signal
approach, crossing, or main road:

`capacity-loss pressure + junction signal + main-road/heavy-vehicle context + peak-window sensitivity`

### 4. Clearance SLA

Field-friendly response deadline:

- 15 minutes: immediate clearance
- 30 minutes: rapid response
- 60 minutes: fixed-window response
- 120 minutes: watchlist / routine patrol

This turns analytics into a dispatch decision.

### 5. Evidence Quality

Trust score from:

- validation confidence,
- repeat volume,
- observed road-space context.

This prevents weak, sparse zones from looking as certain as well-supported
hotspots.

### 6. ELRM and Recovery / Resource-Hour

ELRM remains the payoff proxy. Recovery/resource-hour tells whether scarce
patrol and tow capacity is being used efficiently.

### 7. Deployment Policy Lab

The backend now compares dispatch rules under lean, standard and surge budgets:

- ParkPulse operational priority
- ELRM maximum recovery
- recovery per resource-hour
- capacity-loss first
- spillback first
- TORI-only
- raw violation density
- evidence-safe priority

Each policy is scored on recovered lane-minutes, capacity-loss minutes covered,
high-spillback zones covered, immediate-clearance zones covered, evidence
quality and resource efficiency. This moves the project closer to a real
operations platform because the system can explain not just *which hotspot is
ranked first*, but *why this dispatch rule is better when police capacity is
limited*.

## Judge-Facing Position

ParkPulse is implementable from day one because it runs on the violation data a
city already owns. It does not pretend to have live speed, lane GIS, signal
health or officer GPS. Instead, it produces honest operational proxies now, and
is designed so those live feeds can be plugged in later.

The strongest one-line answer:

> ParkPulse predicts where illegal-parking pressure will recur, then converts
> each hotspot into capacity loss, spillback risk, clearance SLA and recoverable
> lane-minutes so police can decide what to clear first.
