# Pitch Story

Illegal parking does not affect Bengaluru traffic uniformly.

A two-wheeler parked on a quiet road at night is not the same as a cab, auto,
or goods vehicle parked near KR Market, a signal, a road crossing, or a metro
station during peak hours.

ParkPulse Bengaluru captures this difference.

It does not simply ask:

> Where are parking violations frequent?

It asks:

> Where will enforcement recover the most road capacity per officer-hour?

ParkPulse deliberately separates prediction from action.

First, it forecasts where pressure is likely to recur using whichever signal wins
validation on the current data: leakage-safe model features, raw density,
weighted obstruction, and time-safe history are all kept visible.

Then it uses TORI and road-space context to explain why a recurring hotspot is
damaging and which enforcement action fits.

To answer that in an operationally repeatable way, ParkPulse adds a control-room
impact layer:

> capacity-loss pressure, queue-spillback risk, clearance SLA, evidence quality
> and Equivalent Lane Recovery Minutes

ELRM estimates the running-lane time likely to be recovered in the target window
if the recommended patrol, tow, or engineering action is executed. Capacity-loss
pressure and spillback risk tell whether a hotspot can choke a carriageway or
junction; clearance SLA tells how quickly the first unit should reach it; evidence
quality tells how much trust to place in the recommendation. None of this is fake
live congestion telemetry. It is a transparent enforcement impact proxy built
from the evidence available in the dataset.

Crucially, every analytical layer — hotspots, TORI, the corridor risk network,
and ELRM — is built only on the provided enforcement records. No external GIS, no
purchased traffic feed, no map-matching. The command map adds a street basemap
only for geographic context. That means ParkPulse is deployable on the data a
city already owns, today, with no data-sharing agreement.

The final dashboard gives Bengaluru Traffic Police a daily priority queue:

- where to act,
- when to act,
- what action to take,
- why the zone matters,
- and how confident the system is.

Final line:

**ParkPulse does not just show illegal parking. It tells Bengaluru Traffic
Police which illegal parking to solve first.**
