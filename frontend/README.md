# ParkPulse Bengaluru Frontend

React command-center frontend for Theme 1: illegal parking impact intelligence
and enforcement prioritization.

## What It Does

The frontend presents ParkPulse as an operational traffic enforcement command
center:

- command-center KPI view,
- Bengaluru hotspot map with cached basemap tiles,
- live ops radio brief for chaotic enforcement windows,
- enforcement priority queue,
- hotspot drilldown,
- tomorrow's risk evidence,
- deployment simulator,
- station priority view,
- methodology page.

It consumes precomputed artifacts from:

`../outputs/frontend/`

and mirrored Vite public data from:

`public/data/`

The frontend never reads the raw CSV and does not perform heavy scoring.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Build

```bash
npm run build
npm run preview
```

The default build path uses `esbuild` so the prototype remains runnable even on
macOS environments where Rollup's optional native package is unavailable or
partially downloaded. Vite is still listed for clean environments:

```bash
npm run vite:dev
npm run vite:build
```

## Operational UX Notes

The City Hotspot Map uses Leaflet with locally cached CARTO/OpenStreetMap tiles
for the Bengaluru view. This keeps the judge demo stable even if the venue
network is weak. The analytical layers are still ParkPulse-generated: hotspot
points, inferred lane context and inferred corridor obstruction risk come from the
backend exports, not from the basemap.

When available, the map uses `public/data/lane_hotspots.geojson`, which includes
inferred lane context, dominant obstruction reason, mitigation steps, signal-feed
status, and historical enforcement coverage estimate. If that file is missing,
the app falls back to the older `hotspots.geojson` layer.

The backend also exports `public/data/congestion_risk_segments.geojson` for a
Google-Maps-style blue/yellow/red obstruction overlay. The colors represent
illegal-parking obstruction risk, not live speed congestion.

The Live Ops Brief page is designed for police personnel during time pressure:

- radio-style first dispatch instruction,
- patrol and tow-hour demand,
- station-wise dispatch waves,
- tow and engineering escalation triggers,
- five-minute commander runbook.

## Data Export

From the parent `theme1_parking_intelligence` folder:

```bash
PYTHONPATH=.deps:. python3 -m src.export_frontend_data
```

or run the full pipeline:

```bash
PYTHONPATH=.deps:. python3 run_pipeline.py
```

## Mock Data Fallback

If JSON/GeoJSON outputs are missing, the app falls back to realistic mock
Bengaluru hotspots. Mock data is only for frontend demo resilience.

## Open Source Components

- React, MIT
- esbuild, MIT
- Vite, MIT
- Leaflet, BSD-2-Clause
- Recharts, MIT
- lucide-react, ISC

## Methodology Caution

ParkPulse estimates obstruction-risk and enforcement-priority modelled measures. It does
not claim exact speed improvement or exact travel-time reduction because direct
speed, flow, and queue-length data are not present in the provided dataset.
