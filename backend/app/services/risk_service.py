"""
app/services/risk_service.py
-----------------------------
Orchestrator that combines traffic, weather, and ML inference into a single
:class:`~app.schemas.predict.PredictRiskResponse`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timezone

from app.models.inference import RiskPredictor
from app.schemas.predict import PredictRiskRequest, PredictRiskResponse
from app.services.traffic_provider import TrafficProvider
from app.services.weather_provider import WeatherProvider

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Action messages                                                               #
# --------------------------------------------------------------------------- #

_RECOMMENDED_ACTIONS: dict[str, str] = {
    "LOW": "Continue driving safely. Monitor conditions.",
    "MODERATE": "Reduce speed and increase following distance.",
    "HIGH": "Slow down significantly and drive with extra caution.",
    "CRITICAL": "Pull over safely if possible. Conditions are dangerous.",
}

_RISK_MESSAGES: dict[str, str] = {
    "LOW": "Road conditions look good. Stay alert.",
    "MODERATE": "Elevated risk detected. Drive with caution.",
    "HIGH": "High risk zone ahead. Reduce speed immediately.",
    "CRITICAL": "CRITICAL DANGER — take immediate action to ensure safety.",
}


# --------------------------------------------------------------------------- #
# Main orchestration function                                                   #
# --------------------------------------------------------------------------- #

async def compute_risk(
    request: PredictRiskRequest,
    predictor: RiskPredictor,
    traffic_provider: TrafficProvider,
    weather_provider: WeatherProvider,
) -> PredictRiskResponse:
    """Fetch live traffic & weather concurrently, run inference, return response.

    Priority rules
    --------------
    - If the client already sent a non-'unknown' weather / traffic value, that
      value takes precedence over the live provider response.
    """
    # 1. Concurrently fetch traffic and weather
    traffic_data, weather_data = await asyncio.gather(
        traffic_provider.get_traffic(request.latitude, request.longitude),
        weather_provider.get_weather(request.latitude, request.longitude),
        return_exceptions=True,
    )

    # Handle provider errors gracefully — use safe defaults
    if isinstance(traffic_data, Exception):
        logger.warning("Traffic provider error: %s", traffic_data)
        from app.services.traffic_provider import TrafficData  # noqa: PLC0415
        traffic_data = TrafficData(
            traffic_level="unknown", traffic_delay_s=0, speed_ratio=1.0, source="error"
        )

    if isinstance(weather_data, Exception):
        logger.warning("Weather provider error: %s", weather_data)
        from app.services.weather_provider import WeatherData  # noqa: PLC0415
        weather_data = WeatherData(
            weather_code="unknown",
            rainfall_mm=0.0,
            visibility_km=10.0,
            temperature_c=20.0,
            source="error",
        )

    # 2. Client-supplied values override fetched values when present
    effective_weather: str = (
        request.weather
        if request.weather not in ("unknown", "")
        else weather_data.weather_code  # type: ignore[union-attr]
    )
    effective_traffic: str = (
        request.traffic_level
        if request.traffic_level not in ("unknown", "")
        else traffic_data.traffic_level  # type: ignore[union-attr]
    )

    # Timestamp → derived features
    ts = request.timestamp
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    hour = ts.hour
    day_of_week = ts.weekday()   # 0=Monday … 6=Sunday

    # 3. Run predictor
    result = predictor.predict(
        lat=request.latitude,
        lon=request.longitude,
        speed_kmh=request.speed_kmh,
        speed_limit_kmh=request.speed_limit_kmh,
        hour=hour,
        day_of_week=day_of_week,
        weather_code=effective_weather,
        traffic_level=effective_traffic,
    )

    risk_level: str = result["risk_level"]

    # 4. Build response
    return PredictRiskResponse(
        risk_score=result["risk_score"],
        risk_level=risk_level,
        hotspot=result["hotspot"],
        distance_to_hotspot_m=result.get("distance_to_hotspot_m"),
        speed_limit_kmh=request.speed_limit_kmh,
        message=_RISK_MESSAGES.get(risk_level, "Drive safely."),
        reasons=result.get("reasons", []),
        recommended_action=_RECOMMENDED_ACTIONS.get(risk_level, "Drive safely."),
    )
