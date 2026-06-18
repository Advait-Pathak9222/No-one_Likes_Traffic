"""Vehicle type normalization and obstruction weighting."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip().upper())


def normalize_vehicle_type(value: object) -> str:
    """Map raw vehicle type text into an operational obstruction class."""
    text = _clean_text(value)
    if not text:
        return "unknown"

    if re.search(r"MOTOR\s*CYCLE|MOTORCYCLE|SCOOTER|MOPED|TWO\s*WHEELER|BIKE", text):
        return "two_wheeler"
    if re.search(r"MAXI\s*-?\s*CAB|MOTOR\s*CAB|TAXI|CAB|PASSENGER\s*AUTO|AUTO", text):
        return "auto_cab"
    if re.search(r"LGV|TEMPO|VAN|GOODS\s*AUTO|GOODS", text):
        return "goods_light"
    if re.search(r"HGV|LORRY|TANKER|TRUCK|BUS|BMTC|KSRTC|TRACTOR", text):
        return "heavy"
    if re.search(r"CAR|JEEP|SUV", text):
        return "car"
    return "unknown"


def choose_vehicle_type(row: pd.Series) -> object:
    """Prefer updated vehicle type when available; fall back to original."""
    updated = row.get("updated_vehicle_type")
    if not pd.isna(updated) and str(updated).strip():
        return updated
    return row.get("vehicle_type")


def add_vehicle_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add canonical vehicle type and obstruction weight columns."""
    out = df.copy()
    out["vehicle_type_raw"] = out.get("vehicle_type", pd.Series(np.nan, index=out.index))
    out["updated_vehicle_type_raw"] = out.get(
        "updated_vehicle_type", pd.Series(np.nan, index=out.index)
    )
    out["vehicle_type_final"] = out.apply(choose_vehicle_type, axis=1)
    out["vehicle_type_norm"] = out["vehicle_type_final"].map(normalize_vehicle_type)
    out["vehicle_obstruction_weight"] = out["vehicle_type_norm"].map(
        config.VEHICLE_OBSTRUCTION_WEIGHTS
    ).fillna(config.VEHICLE_OBSTRUCTION_WEIGHTS["unknown"])
    return out

