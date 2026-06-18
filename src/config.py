"""Project configuration for ParkPulse Bengaluru."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
ROUND2_DIR = PROJECT_DIR.parent

DEFAULT_DATASET_PATH = (
    ROUND2_DIR
    / "Datasets"
    / "jan to may police violation_anonymized791b166_Theme_1.csv"
)
DATASET_PATH = Path(os.environ.get("PARKPULSE_DATASET_PATH", DEFAULT_DATASET_PATH)).expanduser()

OUTPUT_DIR = PROJECT_DIR / "outputs"
PROCESSED_DIR = OUTPUT_DIR / "processed"
TABLES_DIR = OUTPUT_DIR / "tables"
FIGURES_DIR = OUTPUT_DIR / "figures"
MAPS_DIR = OUTPUT_DIR / "maps"
MODELS_DIR = OUTPUT_DIR / "models"
REPORTS_DIR = PROJECT_DIR / "reports"

DEFAULT_TIMEZONE = "Asia/Kolkata"

BENGALURU_BOUNDS = {
    "lat_min": 12.70,
    "lat_max": 13.35,
    "lon_min": 77.35,
    "lon_max": 77.85,
}

TIME_BLOCK_LABELS = [
    "00-06_night_early_morning",
    "06-09_morning_buildup",
    "09-12_commercial_morning_peak",
    "12-15_market_midday_pressure",
    "15-18_school_evening_buildup",
    "18-22_evening_commercial_pressure",
    "22-24_late_night",
]

VEHICLE_OBSTRUCTION_WEIGHTS = {
    "heavy": 1.60,
    "goods_light": 1.30,
    "auto_cab": 1.15,
    "car": 1.00,
    "two_wheeler": 0.65,
    "unknown": 0.90,
}

VIOLATION_SEVERITY_WEIGHTS = {
    "parking near traffic light or zebra cross": 1.60,
    "parking near road crossing": 1.55,
    "parking near bus stop school hospital": 1.45,
    "parking in main road": 1.40,
    "double parking": 1.35,
    "parking on footpath": 1.25,
    "no parking": 1.10,
    "wrong parking": 1.00,
    "other parking violation": 1.00,
    "defective number plate": 0.35,
}

VALIDATION_CONFIDENCE_WEIGHTS = {
    "approved": 1.00,
    "created1": 0.80,
    "processing": 0.80,
    "pending": 0.80,
    "missing_sent_to_scita": 0.75,
    "missing_not_sent": 0.55,
    "duplicate": 0.40,
    "rejected": 0.25,
    "unknown": 0.60,
}

JUNCTION_CRITICALITY_WEIGHTS = {
    "signal_or_zebra": 1.50,
    "crossing_or_named_junction": 1.40,
    "metro_bus_market": 1.30,
    "school_hospital_footpath": 1.20,
    "default": 1.00,
}

GRID_SIZES_METERS = (100, 250)


def ensure_directories() -> None:
    """Create all project output directories."""
    for path in [
        OUTPUT_DIR,
        PROCESSED_DIR,
        TABLES_DIR,
        FIGURES_DIR,
        MAPS_DIR,
        MODELS_DIR,
        REPORTS_DIR,
        PROJECT_DIR / "notebooks",
        PROJECT_DIR / "app",
        PROJECT_DIR / "data",
    ]:
        path.mkdir(parents=True, exist_ok=True)
