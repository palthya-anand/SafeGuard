"""
app/services/traffic_provider.py
---------------------------------
Abstract traffic provider with a mock implementation for development and
a TomTom Traffic Flow API implementation for production.
"""

from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Data model                                                                    #
# --------------------------------------------------------------------------- #

class TrafficData(BaseModel):
    """Normalised traffic snapshot for a geographic point."""

    traffic_level: str   # normal | moderate | heavy | unknown
    traffic_delay_s: int
    speed_ratio: float   # 0-1  (current speed / free-flow speed)
    source: str


# --------------------------------------------------------------------------- #
# Abstract base                                                                 #
# --------------------------------------------------------------------------- #

class TrafficProvider(ABC):
    """Interface that all traffic providers must implement."""

    @abstractmethod
    async def get_traffic(self, lat: float, lon: float) -> TrafficData:
        """Return current traffic conditions for the given coordinates."""
        ...


# --------------------------------------------------------------------------- #
# Mock provider                                                                 #
# --------------------------------------------------------------------------- #

class MockTrafficProvider(TrafficProvider):
    """Generates realistic synthetic traffic data.

    Simulates heavy congestion during typical morning (08:00-10:00) and
    evening (17:00-20:00) peak hours.
    """

    async def get_traffic(self, lat: float, lon: float) -> TrafficData:
        hour = datetime.now().hour

        # Determine base congestion by time-of-day
        if 8 <= hour < 10:
            base_level = "heavy"
            delay_base, delay_range = 300, 180
            ratio_base, ratio_range = 0.3, 0.2
        elif 17 <= hour < 20:
            base_level = "heavy"
            delay_base, delay_range = 240, 180
            ratio_base, ratio_range = 0.35, 0.2
        elif 7 <= hour < 8 or 10 <= hour < 12 or 16 <= hour < 17:
            base_level = "moderate"
            delay_base, delay_range = 60, 60
            ratio_base, ratio_range = 0.6, 0.2
        else:
            base_level = "normal"
            delay_base, delay_range = 0, 30
            ratio_base, ratio_range = 0.85, 0.1

        # Add some jitter
        traffic_delay_s = max(0, delay_base + random.randint(-delay_range, delay_range))
        speed_ratio = min(1.0, max(0.1, ratio_base + random.uniform(-ratio_range, ratio_range)))

        # Occasionally bump level up by one notch
        bump = random.random() < 0.1
        levels = ["normal", "moderate", "heavy"]
        idx = levels.index(base_level)
        if bump and idx < len(levels) - 1:
            base_level = levels[idx + 1]

        return TrafficData(
            traffic_level=base_level,
            traffic_delay_s=traffic_delay_s,
            speed_ratio=round(speed_ratio, 2),
            source="mock",
        )


# --------------------------------------------------------------------------- #
# TomTom provider                                                               #
# --------------------------------------------------------------------------- #

class TomTomTrafficProvider(TrafficProvider):
    """Fetches live traffic data from the TomTom Traffic Flow API.

    Reference:
        https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data
    Falls back to :class:`MockTrafficProvider` on any HTTP or parsing error.
    """

    _BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
    _TIMEOUT_S = 5.0

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._fallback = MockTrafficProvider()

    async def get_traffic(self, lat: float, lon: float) -> TrafficData:
        params = {
            "key": self._api_key,
            "point": f"{lat},{lon}",
            "unit": "KMPH",
        }
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT_S) as client:
                resp = await client.get(self._BASE_URL, params=params)
                resp.raise_for_status()
                data: dict = resp.json().get("flowSegmentData", {})

                current_speed: float = float(data.get("currentSpeed", 0))
                free_flow_speed: float = float(data.get("freeFlowSpeed", 1)) or 1.0
                delay: int = int(data.get("currentTravelTime", 0) - data.get("freeFlowTravelTime", 0))
                delay = max(0, delay)

                speed_ratio = min(1.0, current_speed / free_flow_speed)

                if speed_ratio >= 0.8:
                    level = "normal"
                elif speed_ratio >= 0.5:
                    level = "moderate"
                else:
                    level = "heavy"

                return TrafficData(
                    traffic_level=level,
                    traffic_delay_s=delay,
                    speed_ratio=round(speed_ratio, 2),
                    source="tomtom",
                )

        except Exception as exc:  # noqa: BLE001
            import re
            safe_msg = re.sub(r"(key|appid)=([a-zA-Z0-9_-]+)", r"\1=REDACTED", str(exc))
            logger.warning("TomTom traffic request failed (%s). Using mock fallback.", safe_msg)
            fallback = await self._fallback.get_traffic(lat, lon)
            return fallback.model_copy(update={"source": "mock-fallback"})


# --------------------------------------------------------------------------- #
# Factory                                                                       #
# --------------------------------------------------------------------------- #

def get_traffic_provider(settings: object) -> TrafficProvider:  # type: ignore[type-arg]
    """Return the appropriate :class:`TrafficProvider` based on settings."""
    provider: str = getattr(settings, "TRAFFIC_PROVIDER", "mock").lower()
    api_key: str = getattr(settings, "TRAFFIC_API_KEY", "")

    if provider == "tomtom" and api_key:
        logger.info("Using TomTom traffic provider.")
        return TomTomTrafficProvider(api_key=api_key)

    logger.info("Using mock traffic provider.")
    return MockTrafficProvider()
