# ParkPulse Bengaluru Frontend

React command-center frontend for **Theme 1: Poor Visibility on
Parking-Induced Congestion** — illegal parking impact intelligence and
enforcement prioritization.

## What It Does

The frontend presents ParkPulse as an operational traffic enforcement command
center:

- command-center KPI view,
- Bengaluru hotspot map on a MapMyIndia/Mappls basemap,
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

The app ships with the competition MapMyIndia/Mappls web key. To override it:

```bash
export VITE_MAPMYINDIA_MAP_KEY="your_mapmyindia_or_mappls_key"
```

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://lvh.me:5173
```

> Use `lvh.me` (a public hostname that resolves to `127.0.0.1`), not `localhost` —
> the MapMyIndia / Mappls web key rejects loopback hostnames. See **Operational UX
> Notes** below.

## Build

```bash
npm run build
npm run preview
# then open http://lvh.me:4173
```

The default build path uses `esbuild` so the prototype remains runnable even on
macOS environments where Rollup's optional native package is unavailable or
partially downloaded. Vite is still listed for clean environments:

```bash
npm run vite:dev
npm run vite:build
```

## Operational UX Notes

The City Hotspot Map uses a **MapMyIndia / Mappls WebGL vector basemap** as the
primary Bengaluru basemap, with the ParkPulse layers drawn as native map layers
(`mappls.Polyline` corridor-risk lines + clickable `mappls.Marker` hotspots).

A fallback mechanism is built in for **devices/browsers without WebGL** (or with
hardware acceleration off) and for cases where the map provider is unreachable: the
dashboard automatically renders an **OpenStreetMap basemap (Leaflet)** with the same
ParkPulse layers, so the judge demo never goes blank. The active provider is shown
in the map badge. The analytical layers are always ParkPulse-generated (hotspot
points, inferred lane context, inferred corridor obstruction risk from the backend
exports), independent of the basemap.

Whitelist the serving domain on the MapMyIndia / Mappls web key in the console:

```text
lvh.me
```

`lvh.me` resolves to `127.0.0.1`, so it runs locally while presenting a real domain
that MapMyIndia accepts (loopback hostnames like `localhost` are rejected). If the
app is deployed, add the deployment domain as well. The MapMyIndia vector map
requires WebGL — Safari renders it out of the box; in Chrome enable
`chrome://settings/system` → "Use graphics acceleration" if it shows the fallback.

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
- Leaflet, BSD-2-Clause (runtime emergency fallback only)
- Recharts, MIT
- lucide-react, ISC

## Acknowledgements

- Data source: Bengaluru Traffic Police / ASTraM enforcement records shared for
  Flipkart Gridlock Round 2 Theme 1, **Poor Visibility on Parking-Induced
  Congestion**.
- Maps: MapMyIndia / Mappls web mapping services provide the geographic context
  layer where the key is active.
- Product intelligence: ParkPulse generates the hotspot rankings, risk layers,
  field briefs and deployment simulation from the provided records.

## Methodology Caution

ParkPulse estimates obstruction-risk and enforcement-priority modelled measures. It does
not claim exact speed improvement or exact travel-time reduction because direct
speed, flow, and queue-length data are not present in the provided dataset.
