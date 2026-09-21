"""
app/core/config.py
------------------
Centralised settings for the SafeGuard backend, loaded from environment
variables / .env file via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration.

    All values can be overridden by environment variables or a .env file
    placed next to the process working directory.
    """

    # ------------------------------------------------------------------ #
    # General                                                              #
    # ------------------------------------------------------------------ #
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret"
    API_BASE_URL: str = "http://localhost:8000"

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # ------------------------------------------------------------------ #
    # Traffic provider                                                     #
    # ------------------------------------------------------------------ #
    TRAFFIC_PROVIDER: str = "mock"        # "mock" | "tomtom"
    TRAFFIC_API_KEY: str = ""

    # ------------------------------------------------------------------ #
    # Weather provider                                                     #
    # ------------------------------------------------------------------ #
    WEATHER_PROVIDER: str = "mock"        # "mock" | "openweathermap"
    WEATHER_API_KEY: str = ""
    OWM_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # ------------------------------------------------------------------ #
    # Map provider                                                         #
    # ------------------------------------------------------------------ #
    MAPBOX_API_KEY: str = ""

    # ------------------------------------------------------------------ #
    # Push notifications                                                   #
    # ------------------------------------------------------------------ #
    FCM_PROJECT_ID: str = ""

    # ------------------------------------------------------------------ #
    # ML / data paths                                                      #
    # ------------------------------------------------------------------ #
    MODEL_PATH: str = "data-science/models/accident_risk_model.joblib"
    PREPROCESSOR_PATH: str = "data-science/models/preprocessor.joblib"
    HOTSPOT_PATH: str = "data-science/data/processed/hotspots.csv"

    # ------------------------------------------------------------------ #
    # Business rules                                                       #
    # ------------------------------------------------------------------ #
    HOTSPOT_RADIUS_M: float = 500.0
    OVERSPEED_TOLERANCE_KMH: float = 5.0
    ALERT_COOLDOWN_SECONDS: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Singleton used throughout the application
settings = Settings()
