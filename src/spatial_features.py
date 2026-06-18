"""Spatial feature engineering utilities."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import config


REFERENCE_LATITUDE = 12.97
METERS_PER_LAT_DEGREE = 111_320.0
METERS_PER_LON_DEGREE = METERS_PER_LAT_DEGREE * math.cos(math.radians(REFERENCE_LATITUDE))


def add_coordinate_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convert coordinate columns and flag Bengaluru-boundary validity."""
    out = df.copy()
    out["lat"] = pd.to_numeric(out.get("latitude"), errors="coerce")
    out["lon"] = pd.to_numeric(out.get("longitude"), errors="coerce")
    bounds = config.BENGALURU_BOUNDS
    out["has_valid_coordinates"] = out["lat"].notna() & out["lon"].notna()
    out["is_within_bengaluru_bounds"] = (
        out["has_valid_coordinates"]
        & out["lat"].between(bounds["lat_min"], bounds["lat_max"])
        & out["lon"].between(bounds["lon_min"], bounds["lon_max"])
    )
    return out


def _grid_id(lat: pd.Series, lon: pd.Series, grid_meters: int) -> pd.Series:
    lat_step = grid_meters / METERS_PER_LAT_DEGREE
    lon_step = grid_meters / METERS_PER_LON_DEGREE
    lat_bucket = np.floor((lat - config.BENGALURU_BOUNDS["lat_min"]) / lat_step)
    lon_bucket = np.floor((lon - config.BENGALURU_BOUNDS["lon_min"]) / lon_step)
    valid = lat.notna() & lon.notna()
    ids = pd.Series("invalid", index=lat.index, dtype="object")
    ids.loc[valid] = (
        grid_meters.__str__()
        + "m_"
        + lat_bucket.loc[valid].astype("int64").astype(str)
        + "_"
        + lon_bucket.loc[valid].astype("int64").astype(str)
    )
    return ids


def add_grid_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic approximate spatial grid IDs."""
    out = df.copy()
    if "lat" not in out.columns or "lon" not in out.columns:
        out = add_coordinate_features(out)
    for grid_meters in config.GRID_SIZES_METERS:
        out[f"grid_id_{grid_meters}m"] = _grid_id(out["lat"], out["lon"], grid_meters)
    return out


def haversine_distance_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Compute haversine distance in meters."""
    radius_m = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(
        dlambda / 2
    ) ** 2
    return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))

