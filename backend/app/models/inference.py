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

    def _load_model(self, model_path: str, preprocessor_path: str) -> None:
        if not _SKLEARN_AVAILABLE:
            logger.warning("scikit-learn stack unavailable — skipping model load.")
            return

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
                speed_ratio=speed_ratio,
                hour=hour,
                day_of_week=day_of_week,
                weather_code=weather_code,
                traffic_level=traffic_level,
                road_type=road_type,
                lighting=lighting,
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
        speed_ratio: float,
        hour: int,
        day_of_week: int,
        weather_code: str,
        traffic_level: str,
        road_type: str,
        lighting: str,
        historical_accident_count: int,
    ) -> int:
        import pandas as pd  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415

        row = {
            "latitude": lat,
            "longitude": lon,
            "speed_kmh": speed_kmh,
            "speed_ratio": speed_ratio,
            "hour": hour,
            "day_of_week": day_of_week,
            "weather_rain": int(weather_code == "rain"),
            "weather_heavy_rain": int(weather_code == "heavy_rain"),
            "weather_fog": int(weather_code == "fog"),
            "weather_storm": int(weather_code == "storm"),
            "traffic_moderate": int(traffic_level == "moderate"),
            "traffic_heavy": int(traffic_level == "heavy"),
            "road_urban": int(road_type == "urban"),
            "lighting_night": int(lighting in ("night", "dark")),
            "historical_accident_count": historical_accident_count,
        }
        df = pd.DataFrame([row])

        try:
            X = self._preprocessor.transform(df)
            # Model may output probability or direct score
            if hasattr(self._model, "predict_proba"):
                proba = self._model.predict_proba(X)
                # Assume last column is the "high-risk" probability
                risk_prob = float(np.max(proba[0]))
                return int(round(risk_prob * 100))
            else:
                raw = float(self._model.predict(X)[0])
                # If already 0-100 scale
                if 0 <= raw <= 100:
                    return int(round(raw))
                # If 0-1 probability
                return int(round(min(1.0, max(0.0, raw)) * 100))
        except Exception as exc:  # noqa: BLE001
            logger.warning("ML inference failed (%s) — falling back to rule-based score.", exc)
            return self._rule_based_score(
                speed_kmh=speed_kmh,
                speed_limit_kmh=None,
                weather_code=weather_code,
                traffic_level=traffic_level,
                in_hotspot=False,
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
