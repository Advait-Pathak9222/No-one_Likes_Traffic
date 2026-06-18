# Final Approach

ParkPulse Bengaluru converts raw illegal-parking violation records into a
decision-support system for traffic enforcement.

The pipeline has five layers:

1. **Data quality and normalization**
   - timestamp parsing,
   - Bengaluru coordinate checks,
   - vehicle type normalization,
   - violation parsing,
   - validation confidence scoring.

2. **Spatial-temporal hotspot intelligence**
   - deterministic 100m and 250m grid cells,
   - DBSCAN natural hotspot clusters,
   - station and time-block aggregation.

3. **Exposure-aware scoring**
   - patrol/device exposure proxies,
   - exposure-adjusted density,
   - raw and adjusted hotspot comparisons.

4. **Validated recurrence engine**
   - weighted obstruction density,
   - raw density baseline,
   - time-safe historical means,
   - leakage-safe next-period forecasting,
   - Capture@K / NDCG@K validation,
   - explicit finding: recurrence is predicted with the best validated
     density/history/model signal, not by treating TORI as the only model.

5. **TORI: Traffic Obstruction Risk Index**
   - density,
   - persistence,
   - temporal pressure,
   - junction criticality,
   - violation severity,
   - vehicle obstruction,
   - validation confidence.

6. **Road-space intelligence for police operations**
   - exact hotspot centroids from violation coordinates,
   - observed coordinate bounds,
   - lane-context proxy,
   - dominant obstruction reason,
   - historical enforcement/workforce presence proxy,
   - explicit external-feed flags for signal health and live roster data.

7. **Traffic-style obstruction overlay and corridor intelligence**
   - inferred corridor segments from repeated hotspot coordinates,
   - a data-fitted local principal-curve centerline (smoothed local PCA) so the
     corridor geometry bends with the violation point cloud instead of collapsing
     to one straight chord — still inferred from the dataset, not official GIS,
   - blue/yellow/red road obstruction risk bands,
   - repeated hotspots linked into corridors with a bottleneck class
     (arterial kerb-lane choke, junction-mouth blocker, metro/market spillover,
     footpath-displacement, heavy-vehicle width loss) and a junction-sensitivity
     band,
   - an offline interactive vector map in the React app plus HTML/PNG artifacts,
   - clearly labelled as parking-obstruction proxy, not live speed data.

8. **Operational impact metrics**
   - Equivalent Lane Recovery Minutes (ELRM),
   - a repeatable proxy for recovered running-lane time in the target window,
   - combines obstruction intensity, window duration, carriageway context,
     recurrence, action fit, and confidence,
   - refined by a dataset-derived carriageway recovery class (full-lane /
     partial-lane / edge-footpath) and a small capped junction-clearance benefit,
   - reported as a low/expected/high range so the effectiveness assumption is
     explicit,
   - capacity-loss pressure for bottleneck severity,
   - queue-spillback risk for junction/signal spillover,
   - clearance SLA for the first-response deadline,
   - evidence-quality score so weakly supported zones are not over-claimed,
   - used in the simulator and deployment story instead of vague impact claims.

9. **Operational recommendations**
   - patrol,
   - towing,
   - fixed-window enforcement,
   - sign audit,
   - engineering fix,
   - metro/market spillover control.

10. **Deployment policy lab**
   - compares dispatch rules under lean, standard and surge patrol/tow budgets,
   - evaluates ParkPulse operational priority against TORI-only, raw-density,
     ELRM-first, capacity-first, spillback-first and evidence-safe rules,
   - reports recovered lane-minutes, capacity-loss minutes covered,
     high-spillback zones covered, immediate-clearance zones covered, evidence
     quality and recovery per resource-hour,
   - makes the dashboard defendable as an operations product rather than a static
     ranked list.

Every analytical layer above is built **only** from the provided enforcement
violation dataset. ParkPulse uses no external road-network GIS, no purchased
traffic or speed feed, and no map-matching service. The command-center map
overlays its risk layers on an OpenStreetMap/CARTO street basemap used purely
for geographic context (it feeds no analysis, and the risk layers still render
if the basemap is unavailable). This keeps the system deployable on data a city
already owns, with no data-sharing agreement required.

The solution intentionally avoids claiming exact travel-time savings because
the dataset does not include speed, flow, or queue-length measurements.

It also avoids claiming surveyed lane geometry, broken traffic-light status, or
live police workforce availability because these are not present in the
provided data. Instead, ParkPulse exposes them as integration points:

- lane geometry / lane counts from GIS or road inventory,
- signal-health feed from traffic signal control systems,
- live police workforce from duty roster or patrol GPS.
- live speed/congestion feed from sensors, probe vehicles, or map APIs.
