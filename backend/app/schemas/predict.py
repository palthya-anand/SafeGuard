"""
app/schemas/predict.py
-----------------------
Pydantic v2 request / response models for the risk prediction and event
endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# Request models                                                                #
# --------------------------------------------------------------------------- #

class PredictRiskRequest(BaseModel):
    """Payload sent by the mobile client to request a risk assessment."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS-84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS-84 longitude")
    speed_kmh: float = Field(..., ge=0.0, le=300.0, description="Current vehicle speed in km/h")
    speed_limit_kmh: Optional[float] = Field(
        None, ge=0.0, le=300.0, description="Posted speed limit (optional)"
    )
    traffic_level: str = Field("unknown", description="Traffic level hint from device")
    weather: str = Field("unknown", description="Weather condition hint from device")
    timestamp: datetime = Field(..., description="ISO-8601 timestamp of the reading")
    device_id: Optional[str] = Field(None, description="Unique device identifier")

    @field_validator("traffic_level", "weather", mode="before")
    @classmethod
    def _lower(cls, v: object) -> str:
        return str(v).lower().strip() if v is not None else "unknown"


class TelemetryRequest(BaseModel):
    """Lightweight telemetry ping for persistent tracking."""

    device_id: str = Field(..., min_length=1, description="Unique device identifier")
    timestamp: datetime = Field(..., description="ISO-8601 timestamp")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    speed_kmh: float = Field(..., ge=0.0, le=300.0)
    traffic_level: str = Field("unknown")
    weather_code: str = Field("unknown")


class CrashEventRequest(BaseModel):
    """Crash detection event reported from the device accelerometer."""

    device_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(...)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    acceleration_g: float = Field(..., description="Peak acceleration in G-force units")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Crash detection confidence 0-1")


# --------------------------------------------------------------------------- #
# Response models                                                               #
# --------------------------------------------------------------------------- #

class PredictRiskResponse(BaseModel):
    """Full risk assessment returned to the mobile client."""

    risk_score: int = Field(..., ge=0, le=100, description="Composite risk score 0-100")
    risk_level: str = Field(
        ..., description="Categorical risk level: LOW | MODERATE | HIGH | CRITICAL"
    )
    hotspot: bool = Field(..., description="True if device is within a known hotspot radius")
    distance_to_hotspot_m: Optional[float] = Field(
        None, description="Distance in metres to the nearest hotspot centroid"
    )
    speed_limit_kmh: Optional[float] = Field(
        None, description="Resolved speed limit for this location"
    )
    message: str = Field(..., description="Human-readable summary for the driver")
    reasons: List[str] = Field(default_factory=list, description="Contributing risk factors")
    recommended_action: str = Field(..., description="Concise recommended driver action")
    traffic_source: Optional[str] = Field(None, description="Source of traffic data: mock | tomtom | device")
    weather_source: Optional[str] = Field(None, description="Source of weather data: mock | openweathermap | device")
    provider_mode: str = Field("mock", description="Operating mode: mock | live")
    server_time: Optional[datetime] = Field(None, description="Server timestamp of evaluation")


class HotspotResponse(BaseModel):
    """Single hotspot record returned from the nearby-hotspots query."""

    hotspot_id: int
    latitude: float
    longitude: float
    accident_count: int
    severity_index: float
    radius_m: float
    risk_level: str
    distance_m: float = Field(..., description="Distance from query point to hotspot centroid")


class HealthResponse(BaseModel):
    """Server health-check response."""

    status: str = "ok"
    version: str
    model_loaded: bool
    uptime_s: float
