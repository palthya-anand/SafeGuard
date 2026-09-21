"""
tests/test_api.py
------------------
Integration tests for the SafeGuard FastAPI backend.

Run with:
    pytest backend/tests/test_api.py -v
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# --------------------------------------------------------------------------- #
# App fixture                                                                   #
# --------------------------------------------------------------------------- #

@pytest_asyncio.fixture(scope="module")
async def client() -> AsyncIterator[AsyncClient]:
    """Spin up the full FastAPI app and yield an AsyncClient."""
    import os
    import sys
    from pathlib import Path
    backend_dir = str(Path(__file__).resolve().parent.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_app.db")
    os.environ.setdefault("APP_ENV", "testing")

    # Import after env is set so Settings picks them up
    from app.main import app, lifespan  # noqa: PLC0415

    async with lifespan(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


# --------------------------------------------------------------------------- #
# Helper                                                                        #
# --------------------------------------------------------------------------- #

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Tests                                                                         #
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient) -> None:
    """Health endpoint must return 200 with status='ok'."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert isinstance(data["model_loaded"], bool)
    assert isinstance(data["uptime_s"], float)


@pytest.mark.asyncio
async def test_predict_risk_valid_request(client: AsyncClient) -> None:
    """Valid predict-risk payload must return a full risk response."""
    payload = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "speed_kmh": 60.0,
        "speed_limit_kmh": 80.0,
        "traffic_level": "normal",
        "weather": "clear",
        "timestamp": _now_iso(),
        "device_id": "test-device-001",
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
    assert isinstance(data["hotspot"], bool)
    assert isinstance(data["reasons"], list)
    assert isinstance(data["message"], str)
    assert isinstance(data["recommended_action"], str)


@pytest.mark.asyncio
async def test_predict_risk_invalid_coordinates(client: AsyncClient) -> None:
    """Latitude=999 must be rejected with HTTP 422."""
    payload = {
        "latitude": 999.0,   # invalid
        "longitude": 77.2090,
        "speed_kmh": 60.0,
        "timestamp": _now_iso(),
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_predict_risk_missing_fields(client: AsyncClient) -> None:
    """Missing required fields (speed_kmh) must return HTTP 422."""
    payload = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        # speed_kmh missing
        "timestamp": _now_iso(),
    }
    resp = await client.post("/api/v1/predict-risk", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_hotspots_nearby(client: AsyncClient) -> None:
    """Hotspots/nearby must return a list (possibly empty) with correct schema."""
    resp = await client.get(
        "/api/v1/hotspots/nearby",
        params={"lat": 28.6139, "lon": 77.2090, "radius_m": 5000, "limit": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    for item in data:
        assert "hotspot_id" in item
        assert "latitude" in item
        assert "longitude" in item
        assert "distance_m" in item
        assert "risk_level" in item


@pytest.mark.asyncio
async def test_telemetry_post(client: AsyncClient) -> None:
    """Telemetry POST must return 201 with saved=True."""
    payload = {
        "device_id": "device-pytest-001",
        "timestamp": _now_iso(),
        "latitude": 28.6139,
        "longitude": 77.2090,
        "speed_kmh": 45.0,
        "traffic_level": "normal",
        "weather_code": "clear",
    }
    resp = await client.post("/api/v1/events/telemetry", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["saved"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_crash_event_post(client: AsyncClient) -> None:
    """Crash event POST must return 202 with received=True."""
    payload = {
        "device_id": "device-pytest-crash",
        "timestamp": _now_iso(),
        "latitude": 28.6139,
        "longitude": 77.2090,
        "acceleration_g": 6.5,
        "confidence": 0.91,
    }
    resp = await client.post("/api/v1/events/crash-suspected", json=payload)
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["received"] is True
    assert "next_action" in data
    assert "alert_id" in data
