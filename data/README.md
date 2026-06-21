# Data

Raw police violation data is not committed here.

The Theme 1 enforcement dataset was provided through the Flipkart Gridlock
Round 2 problem statement by Bengaluru Traffic Police / ASTraM. ParkPulse uses
that dataset to derive hotspot rankings, operational risk estimates and
deployment recommendations.

By default, ParkPulse looks for the official Theme 1 dataset at:

```text
../Datasets/jan to may police violation_anonymized791b166_Theme_1.csv
```

For a different local path, set:

```bash
export PARKPULSE_DATASET_PATH="/absolute/path/to/theme_1.csv"
```

The backend writes generated artifacts under `outputs/`, and the frontend-ready
demo JSON/GeoJSON files are mirrored to `frontend/public/data/`.
