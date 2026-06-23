<h1 align="center">ParkPulse Bengaluru</h1>

<p align="center">
  <b>AI-driven parking intelligence for illegal-parking hotspots and targeted enforcement.</b>
  <br>
  <b>Theme:</b> Poor Visibility on Parking-Induced Congestion
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-2874F0">
  <img alt="React" src="https://img.shields.io/badge/React-TypeScript-172337">
  <img alt="MapMyIndia" src="https://img.shields.io/badge/Maps-MapMyIndia%20%2F%20Mappls-004AAD">
  <img alt="Backend" src="https://img.shields.io/badge/Pipeline-16%20Stages-FC5A1E">
  <img alt="Data" src="https://img.shields.io/badge/Records-298,450-16A34A">
  <img alt="Theme" src="https://img.shields.io/badge/Theme-Parking--Induced%20Congestion-FFE500">
</p>

---

## What ParkPulse Does

ParkPulse addresses **Poor Visibility on Parking-Induced Congestion** by
converting police parking-violation records into an enforcement decision system.
It answers four operational questions:

| Question | ParkPulse output |
|---|---|
| Where is illegal-parking pressure recurring? | 250 m hotspot cells, DBSCAN clusters, station/time-window rankings |
| Which zones should be solved first? | exposure-adjusted obstruction risk and operational priority |
| Why is this hotspot important? | repeat pressure, patrol gap, capacity loss, spillback risk, evidence quality |
| What should officers do? | tow/patrol/fixed-window action, field brief, station plan, deployment simulator |

The system is honest about the data boundary: the supplied records do not
contain measured speed, queue length, signal health, closure timestamps or live
workforce feeds. Traffic-impact fields are therefore modelled estimates for
decision support, not claims of measured congestion reduction.

---

## Repository Contents

```text
theme1_parking_intelligence/
  src/                    Backend cleaning, EDA, scoring, modelling and exports
  frontend/               React + TypeScript command-center dashboard
  frontend/public/data/   Demo-ready JSON/GeoJSON data consumed by the dashboard
  app/                    Optional Streamlit analysis dashboard
  data/README.md          Raw data placement instructions
  run_pipeline.py         Full reproducible backend pipeline
  requirements.txt        Runtime Python dependencies
```

Intentionally excluded from the runtime repository:

- raw police CSV files,
- generated `outputs/`,
- pitch decks, concept-note builders and video-script artifacts,
- local environments such as `.venv/`, `.deps/` and `node_modules/`.

---

## Requirements

| Tool | Version |
|---|---|
| Python | 3.10 or newer |
| Node.js | 18 or newer |
| npm | bundled with Node.js |
| MapMyIndia / Mappls key | included competition web key, overrideable via env |

The backend uses scikit-learn's `HistGradientBoostingRegressor` by default.
LightGBM/XGBoost are optional accelerators and are not required to run the
submission.

---

## 1. Clone And Enter Project

```bash
git clone https://github.com/Advait-Pathak9222/No-one_Likes_Traffic.git
cd No-one_Likes_Traffic
```

If the repository is checked out as the parent folder, enter:

```bash
cd "Round-2/theme1_parking_intelligence"
```

---

## 2. Create Python Environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 3. Place The Dataset

The raw dataset is not committed. Use either option below.

Default expected layout:

```text
Round-2/
  Datasets/
    jan to may police violation_anonymized791b166_Theme_1.csv
  theme1_parking_intelligence/
```

Or set an explicit path.

macOS / Linux:

```bash
export PARKPULSE_DATASET_PATH="/absolute/path/to/theme_1.csv"
```

Windows PowerShell:

```powershell
$env:PARKPULSE_DATASET_PATH="C:\absolute\path\to\theme_1.csv"
```

---

## 4. Run Backend Pipeline

From the project root:

```bash
python run_pipeline.py
```

Expected final output:

```text
[16/16] Exporting frontend JSON/GeoJSON...
ParkPulse pipeline complete.
```

Generated files are written to:

```text
outputs/tables/
outputs/figures/
outputs/maps/
outputs/frontend/
frontend/public/data/
```

The dashboard can also run immediately from the committed
`frontend/public/data/` files if the raw CSV is unavailable.

---

## 5. Run Frontend Dashboard

Optional: override the default competition MapMyIndia / Mappls map key.

macOS / Linux:

```bash
export VITE_MAPMYINDIA_MAP_KEY="your_mapmyindia_or_mappls_key"
```

Windows PowerShell:

```powershell
$env:VITE_MAPMYINDIA_MAP_KEY="your_mapmyindia_or_mappls_key"
```

Build and serve:

```bash
cd frontend
npm ci
npm run build
npm run preview
```

Open the dashboard at:

```text
http://lvh.me:4173
```

> **Why `lvh.me` and not `localhost`?** The MapMyIndia / Mappls web key authorises
> the map by request domain, and the provider **rejects `localhost` / `127.0.0.1`**
> (loopback hostnames). `lvh.me` is a public hostname that resolves to `127.0.0.1`,
> so the dashboard runs locally while still presenting a real domain to MapMyIndia.
> Opening `http://127.0.0.1:4173` also works, but the MapMyIndia basemap will use the
> offline fallback there (see **Maps and WebGL fallback** below).

Development mode:

```bash
npm run dev
```

Open:

```text
http://lvh.me:5173
```

Dashboard pages:

- Command Center
- Live Ops Brief
- Intelligence Report
- Hotspot Intelligence
- Deployment Simulator
- Methodology

### Vercel Deployment

The dashboard deploys as a static build from `frontend/` (config in
`frontend/vercel.json`). After importing the GitHub repo into Vercel, set:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework Preset | Other |
| Build Command | `npm run build` |
| Output Directory | `dist` |

Setting **Root Directory = `frontend`** is what stops Vercel from treating the
repository root as a Python app. `frontend/vercel.json` supplies the build
command, output directory, SPA rewrite and cache headers.

After Vercel creates the site, add the generated domain to the MapMyIndia /
Mappls web key allowlist, for example:

```text
your-project.vercel.app
```

### Maps and WebGL fallback

The Command Center and Hotspot Intelligence maps render a **MapMyIndia / Mappls
WebGL vector basemap**, with the ParkPulse hotspot and corridor-risk layers drawn
as **native map layers** — color-coded corridor-risk lines (`mappls.Polyline`) and
clickable hotspot markers (`mappls.Marker`) that stay aligned to the streets while
panning and zooming.

Because the MapMyIndia vector map is WebGL-based, **a fallback mechanism is built in
for devices or browsers without WebGL** (or with hardware acceleration disabled):
the dashboard automatically switches to an **OpenStreetMap basemap (Leaflet)** and
re-renders the same ParkPulse risk layers natively on it, so the demo never goes
blank. The active provider is shown in the map badge.

Provider selection is automatic:

| Condition | Basemap |
|---|---|
| Authorised domain (e.g. `lvh.me`) **and** WebGL available | MapMyIndia / Mappls (primary) |
| WebGL unavailable, domain not authorised, or provider unreachable | OpenStreetMap (automatic fallback) |

To authorise the MapMyIndia basemap for local use, add the serving domain to the
web key's allowed-domains list in the Mappls console:

```text
lvh.me
```

If the dashboard is hosted, also add the hosted domain. IP / Sub-Net restrictions
are for server-side keys and should be left blank for this browser dashboard.

> **WebGL tip:** MapMyIndia's vector map needs WebGL. Safari renders it out of the
> box. If Chrome shows the OpenStreetMap fallback, enable
> `chrome://settings/system` → "Use graphics acceleration", or set
> `chrome://flags` → "Override software rendering list" → Enabled, then relaunch.

---

## Acknowledgements

ParkPulse stands on top of the official Flipkart GridLock Round 2 ecosystem:

| Contribution | Acknowledgement |
|---|---|
| Traffic enforcement dataset | Bengaluru Traffic Police / ASTraM, shared for the hackathon problem statement |
| Mapping infrastructure | MapMyIndia / Mappls web mapping services |
| Analytics and product layer | ParkPulse ranking, scoring, simulation and dashboard built by the team |

All hotspot rankings, obstruction-risk estimates, deployment plans and dashboard
layers are derived by ParkPulse from the provided enforcement records. MapMyIndia
/ Mappls is used as the geographic context layer; it does not alter the scoring
logic.

---

## Validation Snapshot

| Metric | Value |
|---|---:|
| Violation records analysed | 298,450 |
| Active days | 151 |
| Police stations | 55 |
| Hotspot cells ranked | 10,306 |
| Recurrence Capture@20 | 15.2% |
| Inferred corridors | 103 |

Evaluation is time-safe and operationally focused:

- Capture@K
- NDCG@K
- robustness across all-record vs high-confidence records
- raw-density baseline comparison

---

## Reproducibility Checklist

Run these before submission or judging:

```bash
python run_pipeline.py
cd frontend
npm ci
npm run build
npm run preview
# then open http://lvh.me:4173 (MapMyIndia basemap) in a WebGL-capable browser
```

The latest sanity check completed:

- full 16-stage backend pipeline,
- React/TypeScript production build,
- frontend data loading from `frontend/public/data/`,
- no dependency on raw deck/concept-note generation code.

---

## Project Principle

ParkPulse is built for a real control-room workflow: narrow the field, explain
the reason, dispatch the right enforcement resource and learn from future
closure data when those feeds become available.
