"""Robust violation parsing and severity scoring."""

from __future__ import annotations

import ast
import re

import numpy as np
import pandas as pd

from . import config


def _safe_literal_list(value: str) -> list[str] | None:
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return None
    if isinstance(parsed, (list, tuple, set)):
        return [str(item) for item in parsed]
    if isinstance(parsed, str):
        return [parsed]
    return None


def split_violation_text(value: object) -> list[str]:
    """Split a raw violation cell into rough violation phrases."""
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []

    literal = _safe_literal_list(text)
    if literal is not None:
        raw_parts = literal
    else:
        cleaned = re.sub(r"[\[\]\{\}\"']", " ", text)
        raw_parts = re.split(r"[,;|/]+", cleaned)

    parts = []
    for part in raw_parts:
        normalized = re.sub(r"\s+", " ", str(part).strip().upper())
        if normalized:
            parts.append(normalized)
    return parts


def canonicalize_violation(part: str) -> str:
    """Map a raw violation phrase to a canonical atom."""
    text = re.sub(r"\s+", " ", part.strip().upper())
    if not text:
        return "unknown"
    if "DEFECTIVE" in text and "NUMBER" in text:
        return "defective number plate"
    if "TRAFFIC LIGHT" in text or "ZEBRA" in text or "SIGNAL" in text:
        return "parking near traffic light or zebra cross"
    if "ROAD CROSSING" in text or "CROSSING" in text or "JUNCTION" in text:
        return "parking near road crossing"
    if (
        "BUSTOP" in text
        or "BUS STOP" in text
        or "BUSSTOP" in text
        or "SCHOOL" in text
        or "HOSPITAL" in text
        or "COLLEGE" in text
    ):
        return "parking near bus stop school hospital"
    if "MAIN ROAD" in text:
        return "parking in main road"
    if "DOUBLE" in text and "PARK" in text:
        return "double parking"
    if "FOOTPATH" in text or "SIDEWALK" in text:
        return "parking on footpath"
    if "NO PARKING" in text:
        return "no parking"
    if "WRONG PARKING" in text:
        return "wrong parking"
    if "PARK" in text:
        return "other parking violation"
    return text.lower()


def parse_violation_atoms(value: object) -> list[str]:
    """Parse and canonicalize a violation cell."""
    atoms = [canonicalize_violation(part) for part in split_violation_text(value)]
    atoms = [atom for atom in atoms if atom != "unknown"]
    seen = set()
    deduped = []
    for atom in atoms:
        if atom not in seen:
            seen.add(atom)
            deduped.append(atom)
    return deduped


def score_violation_atoms(atoms: list[str]) -> float:
    """Compute severity score from canonical violation atoms."""
    if not atoms:
        return 1.0
    weights = [
        config.VIOLATION_SEVERITY_WEIGHTS.get(
            atom,
            config.VIOLATION_SEVERITY_WEIGHTS["other parking violation"],
        )
        for atom in atoms
    ]
    return float(max(weights) + 0.15 * np.log1p(max(len(atoms) - 1, 0)))


def add_violation_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add parsed violation atoms, flags, and severity columns."""
    out = df.copy()
    if "violation_type" not in out.columns:
        out["violation_type"] = np.nan

    atoms = out["violation_type"].map(parse_violation_atoms)
    out["violation_atoms"] = atoms.map(lambda items: "; ".join(items))
    out["violation_atom_count"] = atoms.map(len).astype("int16")
    out["violation_severity"] = atoms.map(score_violation_atoms)

    flag_map = {
        "has_wrong_parking": "wrong parking",
        "has_no_parking": "no parking",
        "has_main_road": "parking in main road",
        "has_footpath": "parking on footpath",
        "has_crossing": "parking near road crossing",
        "has_signal_or_zebra": "parking near traffic light or zebra cross",
        "has_bus_stop_school_hospital": "parking near bus stop school hospital",
        "has_defective_number_plate": "defective number plate",
        "has_double_parking": "double parking",
    }
    for col, atom in flag_map.items():
        out[col] = atoms.map(lambda items, target=atom: target in items)
    return out

