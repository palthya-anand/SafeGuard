"""
app/services/weather_provider.py
---------------------------------
Abstract weather provider with a mock implementation for development and
an OpenWeatherMap implementation for production.  OWM responses are cached
in-memory for 60 seconds to reduce API quota usage.
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Data model                                                                    #
# --------------------------------------------------------------------------- #

class WeatherData(BaseModel):
    """Normalised weather snapshot for a geographic point."""

    weather_code: str       # clear | cloudy | rain | heavy_rain | fog | storm | unknown
    rainfall_mm: float
    visibility_km: float
    temperature_c: float
    source: str


# --------------------------------------------------------------------------- #
# OWM weather-ID → internal code mapping                                        #
# --------------------------------------------------------------------------- #

# https://openweathermap.org/weather-conditions
_OWM_ID_MAP: dict[tuple[int, int], str] = {
    (200, 299): "storm",
    (300, 321): "rain",
    (500, 501): "rain",
    (502, 531): "heavy_rain",
    (600, 699): "cloudy",   # snow → treat as cloudy for road risk
    (700, 741): "fog",
    (742, 771): "cloudy",
    (781, 781): "storm",
    (800, 800): "clear",
    (801, 804): "cloudy",
}


def _owm_id_to_code(weather_id: int) -> str:
    for (lo, hi), code in _OWM_ID_MAP.items():
        if lo <= weather_id <= hi:
            return code
    return "unknown"


# --------------------------------------------------------------------------- #
# Abstract base                                                                 #
# --------------------------------------------------------------------------- #

class WeatherProvider(ABC):
    """Interface that all weather providers must implement."""

    @abstractmethod
    async def get_weather(self, lat: float, lon: float) -> WeatherData:
        """Return current weather conditions for the given coordinates."""
        ...


# --------------------------------------------------------------------------- #
# Mock provider                                                                 #
# --------------------------------------------------------------------------- #

class MockWeatherProvider(WeatherProvider):
    """Returns realistic, random synthetic weather data."""

    _CONDITIONS = [
        ("clear", 0.0, 10.0, 25.0),
        ("cloudy", 0.0, 6.0, 18.0),
        ("rain", 3.0, 4.0, 14.0),
        ("heavy_rain", 15.0, 1.5, 10.0),
        ("fog", 0.0, 0.5, 12.0),
        ("storm", 25.0, 0.8, 9.0),
    ]
    # weights — clear weather is most probable
    _WEIGHTS = [0.40, 0.25, 0.15, 0.08, 0.07, 0.05]

    async def get_weather(self, lat: float, lon: float) -> WeatherData:
        code, rain_base, vis_base, temp_base = random.choices(
            self._CONDITIONS, weights=self._WEIGHTS, k=1
        )[0]
        return WeatherData(
            weather_code=code,
            rainfall_mm=round(max(0.0, rain_base + random.uniform(-1.0, 2.0)), 1),
            visibility_km=round(max(0.1, vis_base + random.uniform(-0.5, 1.0)), 1),
            temperature_c=round(temp_base + random.uniform(-3.0, 3.0), 1),
            source="mock",
        )


# --------------------------------------------------------------------------- #
# OpenWeatherMap provider                                                       #
# --------------------------------------------------------------------------- #

class OpenWeatherMapProvider(WeatherProvider):
    """Fetches live weather from OpenWeatherMap's Current Weather Data API.

    Reference:
        https://openweathermap.org/current
    Responses are cached per (lat, lon) bucket for 60 seconds.
    Falls back to :class:`MockWeatherProvider` on any error.
    """

    _CACHE_TTL_S: int = 60
    _TIMEOUT_S: float = 5.0
    _BUCKET_PRECISION: int = 2   # round to 2 decimal places for cache key

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._fallback = MockWeatherProvider()
        # cache: {(lat_bucket, lon_bucket): (timestamp, WeatherData)}
        self._cache: dict[tuple[float, float], tuple[float, WeatherData]] = {}

    def _cache_key(self, lat: float, lon: float) -> tuple[float, float]:
        p = self._BUCKET_PRECISION
        return (round(lat, p), round(lon, p))

    def _from_cache(self, lat: float, lon: float) -> Optional[WeatherData]:
        key = self._cache_key(lat, lon)
        if key in self._cache:
            ts, data = self._cache[key]
            if time.monotonic() - ts < self._CACHE_TTL_S:
                logger.debug("Weather cache hit for %s", key)
                return data
        return None

    def _to_cache(self, lat: float, lon: float, data: WeatherData) -> None:
        key = self._cache_key(lat, lon)
        self._cache[key] = (time.monotonic(), data)

    async def get_weather(self, lat: float, lon: float) -> WeatherData:
        cached = self._from_cache(lat, lon)
        if cached is not None:
            return cached

        url = f"{self._base_url}/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self._api_key,
            "units": "metric",
        }
        try:
            async with httpx.AsyncClient(timeout=self._TIMEOUT_S) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                payload: dict = resp.json()

            weather_list: list[dict] = payload.get("weather", [{}])
            weather_id: int = weather_list[0].get("id", 800)
            rain_dict: dict = payload.get("rain", {})
            rainfall_mm: float = float(rain_dict.get("1h", 0.0))
            visibility_m: float = float(payload.get("visibility", 10000))
            temp_c: float = float(payload.get("main", {}).get("temp", 20.0))

            result = WeatherData(
                weather_code=_owm_id_to_code(weather_id),
                rainfall_mm=round(rainfall_mm, 1),
                visibility_km=round(visibility_m / 1000.0, 2),
                temperature_c=round(temp_c, 1),
                source="openweathermap",
            )
            self._to_cache(lat, lon, result)
            return result

        except Exception as exc:  # noqa: BLE001
            logger.warning("OWM request failed (%s). Using mock fallback.", exc)
            fallback = await self._fallback.get_weather(lat, lon)
            return fallback.model_copy(update={"source": "mock-fallback"})


# --------------------------------------------------------------------------- #
# Factory                                                                       #
# --------------------------------------------------------------------------- #

def get_weather_provider(settings: object) -> WeatherProvider:  # type: ignore[type-arg]
    """Return the appropriate :class:`WeatherProvider` based on settings."""
    provider: str = getattr(settings, "WEATHER_PROVIDER", "mock").lower()
    api_key: str = getattr(settings, "WEATHER_API_KEY", "")
    base_url: str = getattr(settings, "OWM_BASE_URL", "https://api.openweathermap.org/data/2.5")

    if provider == "openweathermap" and api_key:
        logger.info("Using OpenWeatherMap weather provider.")
        return OpenWeatherMapProvider(api_key=api_key, base_url=base_url)

    logger.info("Using mock weather provider.")
    return MockWeatherProvider()
