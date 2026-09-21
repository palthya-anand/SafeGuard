"""
app/models/inference.py
------------------------
ML inference service for road-safety risk prediction.

If the trained model and pre-processor joblib files are present, they are
loaded at construction time and used for scoring.  When the files are absent
(model not yet trained) the predictor transparently falls back to a
deterministic, rule-based scorer so the API remains fully functional during
development and hackathon demos.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Optional heavy imports — only needed when model files exist
try:
    import joblib
    import numpy as np
    import pandas as pd
    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SKLEARN_AVAILABLE = False
    logger.warning("joblib / numpy / pandas not installed — rule-based fallback only.")


# --------------------------------------------------------------------------- #
# Constants                                                                     #
# --------------------------------------------------------------------------- #

_RISK_LEVELS = ["LOW", "MODERATE", "HIGH", "CRITICAL"]

_TRAINING_FEATURES = [
    "latitude",
    "longitude",
    "speed_kmh",
    "speed_ratio",            # speed / speed_limit  (1.0 if limit unknown)
    "hour",
    "day_of_week",
    "weather_rain",
    "weather_heavy_rain",
    "weather_fog",
    "weather_storm",
    "traffic_moderate",
    "traffic_heavy",
    "road_urban",
    "lighting_night",
    "historical_accident_count",
]


# --------------------------------------------------------------------------- #
# RiskPredictor                                                                 #
# --------------------------------------------------------------------------- #

class RiskPredictor:
    """Loads a trained scikit-learn model and serves risk predictions.

    Falls back to a rule-based scorer when the model is unavailable.
    """

    def __init__(
        self,
        model_path: str,
        preprocessor_path: str,
        hotspot_path: str,
    ) -> None:
        self._model: Any = None
        self._preprocessor: Any = None
        self._hotspots: Any = None   # pandas DataFrame or None
        self.model_loaded: bool = False

        self._load_model(model_path, preprocessor_path)
        self._load_hotspots(hotspot_path)

    # ---------------------------------------------------------------------- #
    # Loading                                                                  #
    # ---------------------------------------------------------------------- #

    def _resolve(self, p: str) -> str:
        if not p:
            return p
        from pathlib import Path
        path = Path(p)
        if path.exists():
            return str(path)
        project_root = Path(__file__).resolve().parents[3]
        if (project_root / path).exists():
            return str(project_root / path)
        if (project_root / "data-science" / path).exists():
            return str(project_root / "data-science" / path)
        return p

    def _load_model(self, model_path: str, preprocessor_path: str) -> None:
        if not _SKLEARN_AVAILABLE:
            logger.warning("scikit-learn stack unavailable — skipping model load.")
            return

        model_path = self._resolve(model_path)
        preprocessor_path = self._resolve(preprocessor_path)

        if not os.path.exists(model_path):
            logger.warning("Model file not found at '%s' — using rule-based fallback.", model_path)
            return

        if not os.path.exists(preprocessor_path):
            logger.warning(
                "Preprocessor file not found at '%s' — using rule-based fallback.",
                preprocessor_path,
            )
            return

        try:
            self._model = joblib.load(model_path)
            self._preprocessor = joblib.load(preprocessor_path)
            self.model_loaded = True
            logger.info("Loaded ML model from '%s'.", model_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load model: %s — falling back to rule-based scorer.", exc)

    def _load_hotspots(self, hotspot_path: str) -> None:
        if not _SKLEARN_AVAILABLE:
            return

        hotspot_path = self._resolve(hotspot_path)

        if not os.path.exists(hotspot_path):
            logger.warning("Hotspot CSV not found at '%s' — hotspot detection disabled.", hotspot_path)
            return

        try:
            import pandas as pd  # noqa: PLC0415
            self._hotspots = pd.read_csv(hotspot_path)
            logger.info(
                "Loaded %d hotspots from '%s'.", len(self._hotspots), hotspot_path
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load hotspots: %s", exc)

    # ---------------------------------------------------------------------- #
    # Public API                                                               #
    # ---------------------------------------------------------------------- #

    def predict(
        self,
        lat: float,
        lon: float,
        speed_kmh: float,
        speed_limit_kmh: Optional[float],
        hour: int,
        day_of_week: int,
        weather_code: str,
        traffic_level: str,
        road_type: str = "urban",
        lighting: str = "daylight",
        historical_accident_count: int = 0,
    ) -> dict[str, Any]:
        """Return a risk assessment dictionary.

        Keys
        ----
        risk_score            : int   0-100
        risk_level            : str   LOW | MODERATE | HIGH | CRITICAL
        hotspot               : bool
        distance_to_hotspot_m : float | None
        reasons               : list[str]
        """
        # Nearest hotspot
        dist_m, hotspot_row = self._nearest_hotspot(lat, lon)
        in_hotspot = dist_m is not None and dist_m <= (
            float(hotspot_row.get("radius_m", 500)) if hotspot_row else 500.0
        )

        # Speed ratio
        speed_ratio = (speed_kmh / speed_limit_kmh) if speed_limit_kmh else 1.0

        reasons: list[str] = self._build_reasons(
            speed_kmh=speed_kmh,
            speed_limit_kmh=speed_limit_kmh,
            speed_ratio=speed_ratio,
            weather_code=weather_code,
            traffic_level=traffic_level,
            in_hotspot=in_hotspot,
            lighting=lighting,
        )

        if self.model_loaded:
            score = self._ml_score(
                lat=lat,
                lon=lon,
                speed_kmh=speed_kmh,
                speed_limit_kmh=speed_limit_kmh,
                speed_ratio=speed_ratio,
                hour=hour,
                day_of_week=day_of_week,
                weather_code=weather_code,
                traffic_level=traffic_level,
                road_type=road_type,
                lighting=lighting,
                in_hotspot=in_hotspot,
                dist_m=dist_m,
                hotspot_row=hotspot_row,
                historical_accident_count=historical_accident_count,
            )
        else:
            score = self._rule_based_score(
                speed_kmh=speed_kmh,
                speed_limit_kmh=speed_limit_kmh,
                weather_code=weather_code,
                traffic_level=traffic_level,
                in_hotspot=in_hotspot,
                lighting=lighting,
            )

        score = max(0, min(100, score))

        return {
            "risk_score": score,
            "risk_level": self._score_to_level(score),
            "hotspot": in_hotspot,
            "distance_to_hotspot_m": round(dist_m, 1) if dist_m is not None else None,
            "reasons": reasons,
        }

    # ---------------------------------------------------------------------- #
    # ML scoring path                                                          #
    # ---------------------------------------------------------------------- #

    def _ml_score(
        self,
        lat: float,
        lon: float,
        speed_kmh: float,
        speed_limit_kmh: Optional[float],
        speed_ratio: float,
        hour: int,
        day_of_week: int,
        weather_code: str,
        traffic_level: str,
        road_type: str,
        lighting: str,
        in_hotspot: bool,
        dist_m: Optional[float],
        hotspot_row: Optional[dict],
        historical_accident_count: int,
    ) -> int:
        import pandas as pd  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415

        _weather_map = {"clear": 0, "cloudy": 1, "rain": 2, "heavy_rain": 3, "fog": 4, "storm": 5}
        _traffic_map = {"low": 0, "moderate": 1, "heavy": 2}
        _road_map = {"urban": 0, "rural": 1, "highway": 2, "expressway": 3}
        _lighting_map = {"daylight": 0, "dusk_dawn": 1, "night_lit": 2, "night_unlit": 3}

        limit = speed_limit_kmh if speed_limit_kmh is not None else 50.0
        dist_km = (dist_m / 1000.0) if dist_m is not None else 999.0
        sev_idx = float(hotspot_row.get("severity_index", 1.0)) if hotspot_row else 1.0

        row = {
            "current_speed_kmh": float(speed_kmh),
            "speed_limit_kmh": float(limit),
            "speed_ratio": float(speed_ratio),
            "hour": int(hour),
            "day_of_week": int(day_of_week),
            "is_weekend": int(day_of_week in (5, 6)),
            "is_night": int(hour < 6 or hour >= 20),
            "weather_code": _weather_map.get(str(weather_code).lower(), -1),
            "traffic_code": _traffic_map.get(str(traffic_level).lower(), -1),
            "road_type_code": _road_map.get(str(road_type).lower(), -1),
            "lighting_code": _lighting_map.get(str(lighting).lower(), -1),
            "historical_accident_count": int(historical_accident_count),
            "severity_index": float(sev_idx),
            "distance_to_hotspot_km": float(dist_km),
        }
        df = pd.DataFrame([row])

        try:
            X = self._preprocessor.transform(df)
            if hasattr(self._model, "predict_proba"):
                proba = self._model.predict_proba(X)
                risk_prob = float(proba[0][1]) if proba.shape[1] > 1 else float(proba[0][0])
                score = int(round(risk_prob * 100))
                # Add heuristic modifiers for severe overspeed or near-hotspot conditions
                if speed_limit_kmh and speed_kmh > speed_limit_kmh + 10:
                    score = max(score, 65)
                if in_hotspot and (speed_limit_kmh and speed_kmh > speed_limit_kmh):
                    score = max(score, 75)
                return score
            else:
                raw = float(self._model.predict(X)[0])
                return int(round(raw * 100))
        except Exception as exc:  # noqa: BLE001
            logger.warning("ML inference failed (%s) — falling back to rule-based score.", exc)
            return self._rule_based_score(
                speed_kmh=speed_kmh,
                speed_limit_kmh=speed_limit_kmh,
                weather_code=weather_code,
                traffic_level=traffic_level,
                in_hotspot=in_hotspot,
                lighting=lighting,
            )

    # ---------------------------------------------------------------------- #
    # Rule-based scoring fallback                                              #
    # ---------------------------------------------------------------------- #

    def _rule_based_score(
        self,
        speed_kmh: float,
        speed_limit_kmh: Optional[float],
        weather_code: str,
        traffic_level: str,
        in_hotspot: bool,
        lighting: str,
    ) -> int:
        """Deterministic heuristic scorer.

        Points
        ------
        Overspeed (>5 km/h above limit)  : +30
        Near hotspot                      : +25
        Rain                              : +15
        Heavy rain                        : +25 (not cumulative with rain)
        Storm                             : +30
        Fog                               : +15
        Heavy traffic                     : +15
        Night / poor lighting             : +10
        """
        score = 10  # baseline

        # Speed
        if speed_limit_kmh and speed_kmh > speed_limit_kmh + 5.0:
            score += 30

        # Hotspot
        if in_hotspot:
            score += 25

        # Weather
        if weather_code == "storm":
            score += 30
        elif weather_code == "heavy_rain":
            score += 25
        elif weather_code in ("rain", "fog"):
            score += 15

        # Traffic
        if traffic_level == "heavy":
            score += 15
        elif traffic_level == "moderate":
            score += 5

        # Lighting
        if lighting in ("night", "dark"):
            score += 10

        return score

    # ---------------------------------------------------------------------- #
    # Helpers                                                                  #
    # ---------------------------------------------------------------------- #

    def _haversine_km(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Return the great-circle distance in kilometres between two points."""
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _nearest_hotspot(
        self, lat: float, lon: float
    ) -> tuple[Optional[float], Optional[dict]]:
        """Return (distance_m, hotspot_dict) for the nearest hotspot, or (None, None)."""
        if self._hotspots is None or len(self._hotspots) == 0:
            return None, None

        min_dist_m: float = float("inf")
        nearest_row: Optional[dict] = None

        for _, row in self._hotspots.iterrows():
            hs_lat = float(row.get("latitude", row.get("lat", 0.0)))
            hs_lon = float(row.get("longitude", row.get("lon", 0.0)))
            dist_km = self._haversine_km(lat, lon, hs_lat, hs_lon)
            dist_m = dist_km * 1000.0
            if dist_m < min_dist_m:
                min_dist_m = dist_m
                nearest_row = row.to_dict()

        return (min_dist_m, nearest_row) if nearest_row else (None, None)

    def _score_to_level(self, score: int) -> str:
        """Map a 0-100 score to a categorical risk level."""
        if score < 25:
            return "LOW"
        elif score < 50:
            return "MODERATE"
        elif score < 75:
            return "HIGH"
        else:
            return "CRITICAL"

    def _build_reasons(
        self,
        speed_kmh: float,
        speed_limit_kmh: Optional[float],
        speed_ratio: float,
        weather_code: str,
        traffic_level: str,
        in_hotspot: bool,
        lighting: str,
    ) -> list[str]:
        """Return a human-readable list of contributing risk factors."""
        reasons: list[str] = []

        if speed_limit_kmh and speed_kmh > speed_limit_kmh + 5.0:
            excess = round(speed_kmh - speed_limit_kmh, 1)
            reasons.append(f"Exceeding speed limit by {excess} km/h")

        if in_hotspot:
            reasons.append("Near a known accident hotspot")

        if weather_code == "storm":
            reasons.append("Severe storm conditions")
        elif weather_code == "heavy_rain":
            reasons.append("Heavy rainfall reducing visibility and grip")
        elif weather_code == "rain":
            reasons.append("Rainy conditions — wet road surface")
        elif weather_code == "fog":
            reasons.append("Foggy conditions — reduced visibility")

        if traffic_level == "heavy":
            reasons.append("Heavy traffic congestion")
        elif traffic_level == "moderate":
            reasons.append("Moderate traffic congestion")

        if lighting in ("night", "dark"):
            reasons.append("Poor lighting conditions")

        return reasons
