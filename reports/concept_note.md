# ParkPulse Bengaluru Concept Note

ParkPulse Bengaluru is an AI-driven parking intelligence system for identifying
illegal parking hotspots and prioritizing enforcement based on traffic
obstruction risk.

The system is designed around a practical enforcement question:

> With limited officers and tow vehicles, which illegal parking zones should be
> solved first?

Unlike a raw heatmap, ParkPulse weighs violations by vehicle footprint,
violation severity, time-window pressure, junction criticality, hotspot
persistence, validation confidence, and enforcement exposure.

The output is an action-ready enforcement plan: where to go, when to go, what
action to take, and why.

For a traffic control room, ParkPulse also creates a road-space intelligence
layer. Each hotspot receives exact coordinates, a lane-context proxy, the
dominant obstruction reason, historical enforcement presence, and a mitigation
plan. Unsupported fields are clearly marked: broken signal status and live
workforce availability require external integrations, while illegal-parking
obstruction and enforcement exposure are supported by the provided dataset.

To make corridor visualization more realistic, ParkPulse fits a data-inferred
local centerline (a smoothed local principal curve) through repeated hotspot
points, links nearby hotspots into corridors, and labels each with a bottleneck
class. This is still an inference from the violation coordinates, not surveyed
GIS lane geometry, but it presents road-like corridor segments instead of
disconnected dots. The React command center renders this risk network on an
interactive Bengaluru street basemap (used only for geographic context; the risk
layers themselves come solely from ParkPulse's own data).

ParkPulse also introduces an operational decision metric called Equivalent Lane
Recovery Minutes. This estimates the running-lane time likely to be recovered
in the target enforcement window if the recommended action is executed, reported
as a low/expected/high range and refined by a carriageway recovery class and a
small junction-clearance benefit. It is designed to help officers compare limited
patrol and tow capacity across many candidate hotspots without falsely claiming
direct speed or delay measurement.

The same backend can render a Google-Maps-style obstruction overlay where blue,
yellow, and red segments show low, moderate, and severe illegal-parking
obstruction risk. This is not live speed congestion; it is an enforcement
planning layer that tells police where parking is likely to remove road
capacity.
