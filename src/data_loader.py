"""Raw data loading and audit utilities."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from . import config


def standardize_column_name(name: str) -> str:
    """Convert a raw column name into snake_case."""
    name = str(name).strip().lower()
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of the frame with standardized column names."""
    out = df.copy()
    out.columns = [standardize_column_name(col) for col in out.columns]
    return out


def load_raw_data(
    path: Path | str | None = None,
    nrows: int | None = None,
    usecols: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Load the Theme 1 CSV with safe defaults."""
    csv_path = Path(path) if path is not None else config.DATASET_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    return pd.read_csv(
        csv_path,
        nrows=nrows,
        usecols=usecols,
        low_memory=False,
        encoding="utf-8",
    )


def build_column_audit(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize dtype, missingness, uniqueness, and examples by column."""
    rows = []
    total = len(df)
    for col in df.columns:
        series = df[col]
        non_null = int(series.notna().sum())
        missing = int(total - non_null)
        examples = (
            series.dropna().astype(str).head(3).str.slice(0, 80).tolist()
            if non_null
            else []
        )
        rows.append(
            {
                "column": col,
                "dtype": str(series.dtype),
                "non_null": non_null,
                "missing": missing,
                "missing_pct": round(missing / total, 6) if total else 0.0,
                "n_unique": int(series.nunique(dropna=True)),
                "examples": " | ".join(examples),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["missing_pct", "column"], ascending=[False, True]
    )


def build_dataset_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create a compact dataset-level summary table."""
    summary = [
        {"metric": "rows", "value": len(df)},
        {"metric": "columns", "value": len(df.columns)},
        {"metric": "memory_mb", "value": round(df.memory_usage(deep=True).sum() / 1e6, 3)},
    ]
    for col in ["police_station", "junction_name", "device_id", "created_by_id"]:
        if col in df.columns:
            summary.append({"metric": f"unique_{col}", "value": int(df[col].nunique(dropna=True))})
    return pd.DataFrame(summary)


def write_initial_audit(df: pd.DataFrame) -> None:
    """Write raw schema and dataset summary tables."""
    config.ensure_directories()
    standardized = standardize_columns(df)
    build_dataset_summary(standardized).to_csv(
        config.TABLES_DIR / "raw_dataset_summary.csv", index=False
    )
    build_column_audit(standardized).to_csv(
        config.TABLES_DIR / "raw_column_audit.csv", index=False
    )


def main() -> None:
    config.ensure_directories()
    df = load_raw_data()
    write_initial_audit(df)
    print(f"Loaded {len(df):,} rows and {len(df.columns):,} columns.")
    print(f"Wrote raw audit tables to {config.TABLES_DIR}")


if __name__ == "__main__":
    main()

