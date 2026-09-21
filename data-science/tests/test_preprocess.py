"""
test_preprocess.py
------------------
pytest tests for the preprocess.py output (accidents_clean.csv).

Run from the SafeGuard project root:
    pytest data-science/tests/test_preprocess.py -v
"""

import pytest
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLEAN_FILE   = PROJECT_ROOT / "data" / "processed" / "accidents_clean.csv"

VALID_SEVERITY_CODES = {0, 1, 2, 3}


@pytest.fixture(scope="module")
def clean_df() -> pd.DataFrame:
    """Load the cleaned dataset once per test module."""
    return pd.read_csv(CLEAN_FILE)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_output_file_exists():
    """The cleaned CSV must exist after preprocessing."""
    assert CLEAN_FILE.exists(), f"Expected file not found: {CLEAN_FILE}"


def test_no_null_lat_lon(clean_df):
    """Latitude and longitude must have no missing values."""
    assert clean_df["latitude"].isna().sum()  == 0, "Null values found in 'latitude'"
    assert clean_df["longitude"].isna().sum() == 0, "Null values found in 'longitude'"


def test_valid_coordinate_ranges(clean_df):
    """All coordinates must fall within the valid India bounding box."""
    lat_ok = clean_df["latitude"].between(12.0, 30.0).all()
    lon_ok = clean_df["longitude"].between(65.0, 100.0).all()
    assert lat_ok, "Some latitude values are outside [12.0, 30.0]"
    assert lon_ok, "Some longitude values are outside [65.0, 100.0]"


def test_severity_code_values(clean_df):
    """severity_code must only contain values in {0, 1, 2, 3}."""
    bad = set(clean_df["severity_code"].unique()) - VALID_SEVERITY_CODES
    assert not bad, f"Unexpected severity_code values: {bad}"


def test_no_duplicates(clean_df):
    """accident_id must be unique across all rows."""
    dup_count = clean_df["accident_id"].duplicated().sum()
    assert dup_count == 0, f"Found {dup_count} duplicate accident_id entries"


def test_hotspots_file_valid():
    """Hotspots CSV must exist and contain at least 10 clusters."""
    hotspots_file = PROJECT_ROOT / "data" / "processed" / "hotspots.csv"
    assert hotspots_file.exists(), f"Missing hotspots file: {hotspots_file}"
    df = pd.read_csv(hotspots_file)
    assert len(df) >= 10, f"Expected >=10 hotspots, found {len(df)}"
    for col in ["hotspot_id", "latitude", "longitude", "accident_count", "risk_level"]:
        assert col in df.columns, f"Missing required hotspot column: {col}"


def test_data_quality_report():
    """Data quality report must exist and show 100% retention rate."""
    report_file = PROJECT_ROOT / "data" / "processed" / "data_quality_report.json"
    assert report_file.exists(), f"Missing quality report: {report_file}"
    import json
    with open(report_file) as f:
        data = json.load(f)
    assert data["dataset_integrity"]["retention_rate_pct"] == 100.0
    assert data["compliance"]["model_ready"] is True
