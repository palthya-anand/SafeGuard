"""
tests/test_demo_scenarios.py
----------------------------
Automated validation of all 6 hackathon demo scenarios described in
docs/DEMO_SCENARIOS.md.

Scenarios:
  A. Normal drive (low risk)
  B. Overspeed (high risk, overspeed reason)
  C. Hotspot approach (hotspot detected)
  D. Heavy traffic & rain (moderate risk)
  E. Combined high risk (critical/high risk)
  F. Simulated crash event (confirmation action returned)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import tempfile
test_db_dir = Path(tempfile.gettempdir()) / "safeguard_test"
test_db_dir.mkdir(parents=True, exist_ok=True)
test_db_file = test_db_dir / "test_app.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{test_db_file.as_posix()}")
os.environ.setdefault("APP_ENV", "testing")

from app.main import app, lifespan


@pytest_asyncio.fixture(scope="module")
async def client() -> AsyncIterator[AsyncClient]:
    async with lifespan(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


@pytest.mark.asyncio
async def test_scenario_a_normal_drive(client: AsyncClient):
    """Scenario A: Normal Drive - clear weather, moderate speed, low risk."""
    payload = {
        "latitude": 17.2000,
        "longitude": 78.2000,
        "speed_kmh": 40.0,
        "speed_limit_kmh": 60.0,
        "traffic_level": "low",
        "weather": "clear",
        "timestamp": "2026-09-21T09:00:00+05:30",
        "device_id": "demo-device",
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] in ["LOW", "MODERATE"]
    assert data["risk_score"] < 60


@pytest.mark.asyncio
async def test_scenario_b_overspeed(client: AsyncClient):
    """Scenario B: Overspeed - 95 km/h in 50 km/h zone."""
    payload = {
        "latitude": 17.3850,
        "longitude": 78.4867,
        "speed_kmh": 95.0,
        "speed_limit_kmh": 50.0,
        "traffic_level": "moderate",
        "weather": "clear",
        "timestamp": "2026-09-21T10:30:00+05:30",
        "device_id": "demo-device",
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] in ["HIGH", "CRITICAL", "MODERATE"]
    assert any("overspeed" in r.lower() or "speed" in r.lower() for r in data["reasons"])


@pytest.mark.asyncio
async def test_scenario_c_hotspot_approach(client: AsyncClient):
    """Scenario C: Hotspot Approach - near Delhi hotspot centre (28.63, 77.22)."""
    payload = {
        "latitude": 28.6300,
        "longitude": 77.2200,
        "speed_kmh": 55.0,
        "speed_limit_kmh": 60.0,
        "traffic_level": "moderate",
        "weather": "cloudy",
        "timestamp": "2026-09-21T14:00:00+05:30",
        "device_id": "demo-device",
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["hotspot"] is True
    assert data["distance_to_hotspot_m"] is not None
    assert data["distance_to_hotspot_m"] <= 1000


@pytest.mark.asyncio
async def test_scenario_d_heavy_traffic(client: AsyncClient):
    """Scenario D: Heavy Traffic & Rain."""
    payload = {
        "latitude": 17.3850,
        "longitude": 78.4867,
        "speed_kmh": 28.0,
        "speed_limit_kmh": 50.0,
        "traffic_level": "heavy",
        "weather": "rain",
        "timestamp": "2026-09-21T18:30:00+05:30",
        "device_id": "demo-device",
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert any("traffic" in r.lower() or "rain" in r.lower() for r in data["reasons"])


@pytest.mark.asyncio
async def test_scenario_e_combined_high_risk(client: AsyncClient):
    """Scenario E: Rain + Overspeed + Hotspot."""
    payload = {
        "latitude": 28.6300,
        "longitude": 77.2200,
        "speed_kmh": 85.0,
        "speed_limit_kmh": 50.0,
        "traffic_level": "heavy",
        "weather": "rain",
        "timestamp": "2026-09-21T20:00:00+05:30",
        "device_id": "demo-device",
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_level"] in ["HIGH", "CRITICAL"]
    assert data["hotspot"] is True
    assert len(data["reasons"]) >= 2


@pytest.mark.asyncio
async def test_scenario_f_simulated_crash_event(client: AsyncClient):
    """Scenario F: Suspected crash event."""
    payload = {
        "device_id": "demo-device",
        "timestamp": "2026-09-21T20:05:00+05:30",
        "latitude": 28.6300,
        "longitude": 77.2200,
        "acceleration_g": 4.2,
        "confidence": 0.85,
    }
    resp = await client.post("/api/v1/events/crash-suspected", json=payload)
    assert resp.status_code in (200, 202)
    data = resp.json()
    assert data["received"] is True
    assert "SHOW_CONFIRMATION_DIALOG" in data["next_action"]
