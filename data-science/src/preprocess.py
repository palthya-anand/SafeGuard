"""
preprocess.py
-------------
Data cleaning pipeline for the SafeGuard accident dataset.

Loads  : data/raw/accidents_raw.csv
Saves  : data/processed/accidents_clean.csv

Run from the SafeGuard project root:
    python data-science/src/preprocess.py
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE   = PROJECT_ROOT / "data" / "raw"  / "accidents_raw.csv"
OUTPUT_DIR   = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE  = OUTPUT_DIR / "accidents_clean.csv"

# ---------------------------------------------------------------------------
# Expected schema
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "accident_id", "latitude", "longitude", "date", "time",
    "weather", "road_type", "lighting", "traffic_density",
    "vehicle_type", "speed_kmh", "speed_limit_kmh", "severity",
]

LAT_MIN, LAT_MAX = 12.0, 30.0
LON_MIN, LON_MAX = 65.0, 100.0

SEVERITY_MAP = {"minor": 0, "moderate": 1, "severe": 2, "fatal": 3}

CATEGORICAL_COLS = [
    "weather", "road_type", "lighting", "traffic_density",
    "vehicle_type", "severity",
]


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def load_raw(path: Path) -> pd.DataFrame:
    """Load raw CSV and validate required columns exist."""
    df = pd.read_csv(path)
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        print(f"[ERROR] Missing columns: {missing}")
        sys.exit(1)
    return df


def validate_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose lat/lon fall outside the valid India bounding box."""
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    before = len(df)
    mask = (
        df["latitude"].between(LAT_MIN, LAT_MAX) &
        df["longitude"].between(LON_MIN, LON_MAX)
    )
    df = df[mask].copy()
    dropped = before - len(df)
    if dropped:
        print(f"  [coord filter] Dropped {dropped} rows with invalid lat/lon")
    return df


def parse_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date + time into a combined datetime column."""
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["time"] = df["time"].astype(str).str.strip()
    df["datetime"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time"],
        errors="coerce",
    )
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate accident_id rows, keeping first occurrence."""
    before = len(df)
    df = df.drop_duplicates(subset=["accident_id"], keep="first")
    dropped = before - len(df)
    if dropped:
        print(f"  [dedup] Removed {dropped} duplicate accident_id rows")
    return df


def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows missing critical fields (lat, lon, severity, datetime).
    Fill remaining missing categoricals with mode.
    """
    before = len(df)
    df = df.dropna(subset=["latitude", "longitude", "severity", "datetime"])
    dropped = before - len(df)
    if dropped:
        print(f"  [missing] Dropped {dropped} rows missing critical fields")

    # Fill remaining missing categoricals with column mode
    for col in CATEGORICAL_COLS:
        if col in df.columns and df[col].isna().any():
            mode_val = df[col].mode()[0]
            df[col] = df[col].fillna(mode_val)
            print(f"  [missing] Filled '{col}' NaNs with mode='{mode_val}'")

    # Fill numeric NaNs with median
    for col in ["speed_kmh", "speed_limit_kmh"]:
        if df[col].isna().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            print(f"  [missing] Filled '{col}' NaNs with median={median_val:.1f}")

    return df


def normalize_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip all categorical string columns."""
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().str.strip()
    return df


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add temporal and severity-derived feature columns."""
    df["hour"]          = df["datetime"].dt.hour.astype(int)
    df["day_of_week"]   = df["datetime"].dt.dayofweek.astype(int)   # 0=Mon
    df["month"]         = df["datetime"].dt.month.astype(int)
    df["is_weekend"]    = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_night"]      = ((df["hour"] < 6) | (df["hour"] >= 20)).astype(int)
    df["severity_code"] = df["severity"].map(SEVERITY_MAP).fillna(-1).astype(int)
    return df


def save_clean(df: pd.DataFrame, path: Path) -> None:
    """Persist the cleaned DataFrame."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 55)
    print("  Preprocessing Pipeline")
    print("=" * 55)

    df = load_raw(INPUT_FILE)
    rows_in = len(df)
    print(f"  Rows loaded        : {rows_in:,}")

    df = validate_coordinates(df)
    df = parse_datetime(df)
    df = remove_duplicates(df)
    df = handle_missing(df)
    df = normalize_categoricals(df)
    df = add_derived_columns(df)

    rows_out = len(df)
    save_clean(df, OUTPUT_FILE)

    print(f"\n  Rows in            : {rows_in:,}")
    print(f"  Rows out           : {rows_out:,}")
    print(f"  Rows dropped       : {rows_in - rows_out:,}")
    print(f"  Columns            : {len(df.columns)}")
    print(f"  Column list        : {list(df.columns)}")
    print(f"  Saved to           : {OUTPUT_FILE}")
    print("=" * 55)


if __name__ == "__main__":
    main()
