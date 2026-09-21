"""
features.py
-----------
Feature engineering module shared between train.py and backend inference.

Provides:
  - FEATURES list (canonical feature order)
  - Encoding functions for categorical variables
  - Haversine distance to nearest hotspot
  - build_feature_vector() for single-row inference
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Union

# ---------------------------------------------------------------------------
# Canonical feature list (must match the order used by the trained model)
# ---------------------------------------------------------------------------
FEATURES = [
    "current_speed_kmh",
    "speed_limit_kmh",
    "speed_ratio",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_night",
    "weather_code",
    "traffic_code",
    "road_type_code",
    "lighting_code",
    "historical_accident_count",
    "severity_index",
    "distance_to_hotspot_km",
]

# ---------------------------------------------------------------------------
# Encoding maps
# ---------------------------------------------------------------------------
_WEATHER_MAP = {
    "clear": 0, "cloudy": 1, "rain": 2, "heavy_rain": 3, "fog": 4, "storm": 5
}
_TRAFFIC_MAP = {"low": 0, "moderate": 1, "heavy": 2}
_ROAD_MAP    = {"urban": 0, "rural": 1, "highway": 2, "expressway": 3}
_LIGHTING_MAP = {"daylight": 0, "dusk_dawn": 1, "night_lit": 2, "night_unlit": 3}

EARTH_RADIUS_KM = 6371.0


# ---------------------------------------------------------------------------
# Encoding functions
# ---------------------------------------------------------------------------

def encode_weather(w: str) -> int:
    """Map weather string to integer code. Returns -1 for unknown."""
    return _WEATHER_MAP.get(str(w).lower().strip(), -1)


def encode_traffic(t: str) -> int:
    """Map traffic density string to integer code. Returns -1 for unknown."""
    return _TRAFFIC_MAP.get(str(t).lower().strip(), -1)


def encode_road_type(r: str) -> int:
    """Map road type string to integer code. Returns -1 for unknown."""
    return _ROAD_MAP.get(str(r).lower().strip(), -1)


def encode_lighting(l: str) -> int:
    """Map lighting condition string to integer code. Returns -1 for unknown."""
    return _LIGHTING_MAP.get(str(l).lower().strip(), -1)


# ---------------------------------------------------------------------------
# Distance helper
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: Union[np.ndarray, float],
                  lon2: Union[np.ndarray, float]) -> Union[np.ndarray, float]:
    """Vectorised haversine distance in km."""
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def distance_to_nearest_hotspot(
    lat: float, lon: float, hotspots_df: pd.DataFrame
) -> float:
    """
    Return the haversine distance in km from (lat, lon) to the nearest
    hotspot centroid in hotspots_df.

    Parameters
    ----------
    lat, lon    : Query coordinates.
    hotspots_df : DataFrame with at least 'latitude' and 'longitude' columns.

    Returns
    -------
    float : Distance in km to the nearest hotspot (inf if hotspots_df is empty).
    """
    if hotspots_df.empty:
        return float("inf")

    hs_lats = hotspots_df["latitude"].values
    hs_lons = hotspots_df["longitude"].values
    dists   = _haversine_km(lat, lon, hs_lats, hs_lons)
    return float(np.min(dists))


# ---------------------------------------------------------------------------
# Historical accident count helper
# ---------------------------------------------------------------------------

def historical_accident_count(
    lat: float, lon: float, accidents_df: pd.DataFrame, radius_km: float = 1.0
) -> int:
    """
    Count accidents in accidents_df within radius_km of (lat, lon).

    Uses vectorised haversine for efficiency.
    """
    if accidents_df.empty:
        return 0

    acc_lats = accidents_df["latitude"].values
    acc_lons = accidents_df["longitude"].values
    dists    = _haversine_km(lat, lon, acc_lats, acc_lons)
    return int((dists <= radius_km).sum())


# ---------------------------------------------------------------------------
# Main feature builder
# ---------------------------------------------------------------------------

def build_feature_vector(
    lat: float,
    lon: float,
    speed_kmh: float,
    speed_limit_kmh: float,
    hour: int,
    day_of_week: int,
    weather: str,
    traffic: str,
    road_type: str,
    lighting: str,
    hotspots_df: pd.DataFrame,
    accidents_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a single-row feature DataFrame for inference or training.

    Parameters
    ----------
    lat, lon         : Coordinates of the accident / query point.
    speed_kmh        : Current speed in km/h.
    speed_limit_kmh  : Posted speed limit in km/h.
    hour             : Hour of day (0-23).
    day_of_week      : Day of week (0=Monday, 6=Sunday).
    weather          : Weather condition string.
    traffic          : Traffic density string.
    road_type        : Road type string.
    lighting         : Lighting condition string.
    hotspots_df      : Hotspot summary DataFrame (from hotspots.csv).
    accidents_df     : Cleaned accidents DataFrame (for local count lookup).

    Returns
    -------
    pd.DataFrame : One row, columns = FEATURES.
    """
    speed_ratio = speed_kmh / max(speed_limit_kmh, 1.0)
    is_weekend  = int(day_of_week in (5, 6))
    is_night    = int(hour < 6 or hour >= 20)

    dist_km = distance_to_nearest_hotspot(lat, lon, hotspots_df)

    # Nearest hotspot severity index (or 1.0 if none)
    if hotspots_df.empty:
        sev_idx = 1.0
    else:
        hs_lats = hotspots_df["latitude"].values
        hs_lons = hotspots_df["longitude"].values
        dists   = _haversine_km(lat, lon, hs_lats, hs_lons)
        nearest = hotspots_df.iloc[int(np.argmin(dists))]
        sev_idx = float(nearest.get("severity_index", 1.0))

    hist_count = historical_accident_count(lat, lon, accidents_df)

    row = {
        "current_speed_kmh":         speed_kmh,
        "speed_limit_kmh":           speed_limit_kmh,
        "speed_ratio":               round(speed_ratio, 4),
        "hour":                      hour,
        "day_of_week":               day_of_week,
        "is_weekend":                is_weekend,
        "is_night":                  is_night,
        "weather_code":              encode_weather(weather),
        "traffic_code":              encode_traffic(traffic),
        "road_type_code":            encode_road_type(road_type),
        "lighting_code":             encode_lighting(lighting),
        "historical_accident_count": hist_count,
        "severity_index":            round(sev_idx, 4),
        "distance_to_hotspot_km":    round(dist_km, 4),
    }

    return pd.DataFrame([row], columns=FEATURES)
