"""
app/main.py
-----------
FastAPI application factory for the SafeGuard road-safety backend.

Startup sequence
----------------
1. init_db()        — create SQLite tables
2. RiskPredictor()  — load ML model / hotspots (graceful if absent)
3. Traffic & weather providers — selected based on Settings
4. All providers are stored on app.state for injection via routes
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.database import init_db
from app.models.inference import RiskPredictor
from app.services.traffic_provider import get_traffic_provider
from app.services.weather_provider import get_weather_provider

# --------------------------------------------------------------------------- #
# Logging setup                                                                 #
# --------------------------------------------------------------------------- #

logging.basicConfig(
    level=logging.DEBUG if settings.APP_ENV == "development" else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Lifespan                                                                      #
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared resources on startup; clean up on shutdown."""
    logger.info("=== SafeGuard API starting (env=%s) ===", settings.APP_ENV)

    # Database
    init_db()

    # ML predictor
    predictor = RiskPredictor(
        model_path=settings.MODEL_PATH,
        preprocessor_path=settings.PREPROCESSOR_PATH,
        hotspot_path=settings.HOTSPOT_PATH,
    )
    app.state.predictor = predictor
    logger.info("RiskPredictor ready | model_loaded=%s", predictor.model_loaded)

    # External providers
    app.state.traffic_provider = get_traffic_provider(settings)
    app.state.weather_provider = get_weather_provider(settings)

    # Uptime clock
    app.state.start_time = time.monotonic()

    logger.info(
        "=== SafeGuard API ready | version=1.0.0-hackathon | model=%s ===",
        "ML" if predictor.model_loaded else "rule-based",
    )

    yield  # <-- application runs here

    logger.info("=== SafeGuard API shutting down ===")


# --------------------------------------------------------------------------- #
# Application                                                                   #
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="SafeGuard API",
    description=(
        "AI-based road safety risk prediction API.\n\n"
        "Provides real-time risk scoring, accident hotspot detection, "
        "telemetry ingestion, and crash event reporting for the SafeGuard "
        "mobile application."
    ),
    version="1.0.0-hackathon",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --------------------------------------------------------------------------- #
# CORS                                                                          #
# --------------------------------------------------------------------------- #
# Allow the Android emulator (10.0.2.2), localhost, and common dev origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://10.0.2.2",
        "http://10.0.2.2:8000",
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# Routers                                                                       #
# --------------------------------------------------------------------------- #

app.include_router(router)
