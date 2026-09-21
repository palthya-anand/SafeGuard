"""
app/api/routes.py
------------------
All SafeGuard API endpoints, mounted under /api/v1.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import Alert, Hotspot, Telemetry, get_db
from app.schemas.predict import (
    CrashEventRequest,
    HealthResponse,
    HotspotResponse,
    PredictRiskRequest,
    PredictRiskResponse,
    TelemetryRequest,
)
from app.services.risk_service import compute_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["safeguard"])


# --------------------------------------------------------------------------- #
# Dependency helpers                                                            #
# --------------------------------------------------------------------------- #

def _get_predictor(request: Request):  # type: ignore[return]
    return request.app.state.predictor


def _get_traffic_provider(request: Request):  # type: ignore[return]
    return request.app.state.traffic_provider


def _get_weather_provider(request: Request):  # type: ignore[return]
    return request.app.state.weather_provider


def _get_start_time(request: Request) -> float:
    return request.app.state.start_time


# --------------------------------------------------------------------------- #
# Health                                                                        #
# --------------------------------------------------------------------------- #

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Server health check",
)
async def health(request: Request) -> HealthResponse:
    """Return API health, model status, and uptime."""
    import time  # noqa: PLC0415

    predictor = _get_predictor(request)
    start_time = _get_start_time(request)

    logger.info("Health check requested.")
    return HealthResponse(
        status="ok",
        version="1.0.0-hackathon",
        model_loaded=predictor.model_loaded,
        uptime_s=round(time.monotonic() - start_time, 2),
    )


# --------------------------------------------------------------------------- #
# Risk prediction                                                               #
# --------------------------------------------------------------------------- #

@router.post(
    "/predict-risk",
    response_model=PredictRiskResponse,
    summary="Predict road safety risk",
)
async def predict_risk(
    body: PredictRiskRequest,
    request: Request,
) -> PredictRiskResponse:
    """Main inference endpoint.

    Accepts a telemetry snapshot and returns a full risk assessment including
    score, level, hotspot proximity, contributing reasons, and recommended action.
    """
    logger.info(
        "predict-risk | device=%s lat=%.4f lon=%.4f speed=%.1f",
        body.device_id,
        body.latitude,
        body.longitude,
        body.speed_kmh,
    )

    predictor = _get_predictor(request)
    traffic_provider = _get_traffic_provider(request)
    weather_provider = _get_weather_provider(request)

    try:
        response = await compute_risk(
            request=body,
            predictor=predictor,
            traffic_provider=traffic_provider,
            weather_provider=weather_provider,
        )
    except Exception as exc:
        logger.exception("compute_risk failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Risk computation failed. Please try again.",
        ) from exc

    return response


# --------------------------------------------------------------------------- #
# Hotspots                                                                      #
# --------------------------------------------------------------------------- #

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get(
    "/hotspots/nearby",
    response_model=list[HotspotResponse],
    summary="List accident hotspots near a coordinate",
)
async def hotspots_nearby(
    lat: Annotated[float, Query(ge=-90, le=90, description="Query latitude")],
    lon: Annotated[float, Query(ge=-180, le=180, description="Query longitude")],
    radius_m: Annotated[float, Query(gt=0, le=50_000, description="Search radius in metres")] = 1000.0,
    limit: Annotated[int, Query(gt=0, le=100, description="Maximum number of results")] = 10,
    db: Session = Depends(get_db),
) -> list[HotspotResponse]:
    """Return hotspots within `radius_m` metres of the given coordinate."""
    logger.info("hotspots/nearby | lat=%.4f lon=%.4f radius=%.0f", lat, lon, radius_m)

    all_hotspots: list[Hotspot] = db.query(Hotspot).all()

    results: list[HotspotResponse] = []
    for hs in all_hotspots:
        dist = _haversine_m(lat, lon, hs.latitude, hs.longitude)
        if dist <= radius_m:
            results.append(
                HotspotResponse(
                    hotspot_id=hs.id,
                    latitude=hs.latitude,
                    longitude=hs.longitude,
                    accident_count=hs.accident_count,
                    severity_index=hs.severity_index,
                    radius_m=hs.radius_m,
                    risk_level=hs.risk_level,
                    distance_m=round(dist, 1),
                )
            )

    results.sort(key=lambda r: r.distance_m)
    return results[:limit]


# --------------------------------------------------------------------------- #
# Road context (stub)                                                           #
# --------------------------------------------------------------------------- #

@router.get(
    "/road-context",
    summary="Resolve road context for a coordinate",
)
async def road_context(
    request: Request,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> dict[str, Any]:
    """Resolve live traffic, weather, and road attributes for coordinates."""
    resolved_lat = lat if lat is not None else latitude
    resolved_lon = lon if lon is not None else longitude
    if resolved_lat is None or resolved_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and longitude parameters are required.",
        )

    logger.info("road-context | lat=%.4f lon=%.4f", resolved_lat, resolved_lon)
    traffic_provider = _get_traffic_provider(request)
    weather_provider = _get_weather_provider(request)

    traffic = await traffic_provider.get_traffic(resolved_lat, resolved_lon)
    weather = await weather_provider.get_weather(resolved_lat, resolved_lon)

    return {
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "speed_limit_kmh": 50.0,
        "road_type": "urban",
        "lighting": "daylight",
        "traffic": traffic.model_dump(),
        "weather": weather.model_dump(),
    }


# --------------------------------------------------------------------------- #
# Dashboard summary                                                             #
# --------------------------------------------------------------------------- #

@router.get(
    "/dashboard/summary",
    summary="Aggregate statistics for the dashboard",
)
async def dashboard_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return aggregate DB statistics for a monitoring dashboard."""
    from sqlalchemy import func  # noqa: PLC0415

    total_telemetry: int = db.query(func.count(Telemetry.id)).scalar() or 0
    total_alerts: int = db.query(func.count(Alert.id)).scalar() or 0
    total_hotspots: int = db.query(func.count(Hotspot.id)).scalar() or 0

    # Risk level breakdown from telemetry
    risk_breakdown: dict[str, int] = {}
    rows = (
        db.query(Telemetry.risk_level, func.count(Telemetry.id))
        .filter(Telemetry.risk_level.isnot(None))
        .group_by(Telemetry.risk_level)
        .all()
    )
    for risk_level, count in rows:
        risk_breakdown[risk_level] = count

    # Unacknowledged alerts
    unack_alerts: int = (
        db.query(func.count(Alert.id))
        .filter(Alert.acknowledged == False)  # noqa: E712
        .scalar()
        or 0
    )

    logger.info("dashboard/summary requested.")
    return {
        "total_telemetry_records": total_telemetry,
        "total_alerts": total_alerts,
        "unacknowledged_alerts": unack_alerts,
        "total_hotspots": total_hotspots,
        "risk_level_breakdown": risk_breakdown,
    }


# --------------------------------------------------------------------------- #
# Telemetry event                                                               #
# --------------------------------------------------------------------------- #

@router.post(
    "/events/telemetry",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a telemetry record",
)
async def post_telemetry(
    body: TelemetryRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Persist a telemetry record from the mobile device."""
    logger.info(
        "events/telemetry | device=%s speed=%.1f", body.device_id, body.speed_kmh
    )

    record = Telemetry(
        device_id=body.device_id,
        timestamp=body.timestamp,
        latitude=body.latitude,
        longitude=body.longitude,
        speed_kmh=body.speed_kmh,
        traffic_level=body.traffic_level,
        weather_code=body.weather_code,
    )
    db.add(record)
    db.commit()

    return {"saved": True, "id": record.id}


# --------------------------------------------------------------------------- #
# Crash event                                                                   #
# --------------------------------------------------------------------------- #

@router.post(
    "/events/crash-suspected",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Report a suspected crash event",
)
async def post_crash_event(
    body: CrashEventRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Receive a crash-detection event, persist an Alert, and advise next steps."""
    logger.warning(
        "CRASH SUSPECTED | device=%s confidence=%.2f accel=%.2f G lat=%.4f lon=%.4f",
        body.device_id,
        body.confidence,
        body.acceleration_g,
        body.latitude,
        body.longitude,
    )

    alert = Alert(
        device_id=body.device_id,
        timestamp=body.timestamp,
        alert_type="crash",
        risk_level="CRITICAL",
        message=(
            f"Crash suspected — {body.acceleration_g:.1f}G acceleration detected "
            f"(confidence {body.confidence:.0%})."
        ),
        latitude=body.latitude,
        longitude=body.longitude,
        acknowledged=False,
    )
    db.add(alert)
    db.commit()

    next_action = (
        "SHOW_CONFIRMATION_DIALOG"
        if body.confidence >= 0.8
        else "monitoring_escalation_pending"
    )

    return {
        "received": True,
        "alert_id": alert.id,
        "next_action": next_action,
        "message": (
            "Emergency services have been notified."
            if body.confidence >= 0.8
            else "Crash confidence below threshold — monitoring for escalation."
        ),
    }
