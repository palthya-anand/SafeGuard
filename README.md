# Smart Road Safety — AI-Based Accident Risk Prediction & Real-Time Driver Warning

## Project Version
**Current planned release: v1.0.0-hackathon**

## What this project is
A software-first road-safety system that uses an Android phone as the real-time sensing device and a Python backend for data science, machine learning, traffic/weather integration, accident-hotspot analysis, and risk scoring.

The system is designed to estimate **road/driver risk**, not to claim that an accident can be predicted with certainty.

## Core flow

```text
Android Phone
  ├─ GPS / speed
  ├─ accelerometer / gyroscope
  └─ local notifications + voice
          │
          ▼
      FastAPI Backend
          │
    ┌─────┼───────────────┐
    ▼     ▼               ▼
Accident Traffic       Weather
 Data    Data/API      Data/API
    │     │               │
    └─────┼───────────────┘
          ▼
   Feature Engineering
          ▼
      ML Risk Model
          ▼
   Risk Score / Level
          ▼
 Phone Warning + Dashboard
```

## Quick Start

Run both the FastAPI backend and Streamlit dashboard with a single command:

```powershell
python run_project.py
```

- **Dashboard**: [http://localhost:8501](http://localhost:8501)
- **FastAPI Core**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Connected Live APIs & Providers

SafeGuard integrates live external intelligence feeds:
- **Mapbox Cartography Engine (Primary)**: High-resolution dark-mode (`dark-v11`), navigation-night, streets, and satellite raster `@2x` tiles with dual-layer OpenStreetMap (OSM) fallback switching.
- **TomTom Traffic Flow API**: Real-time traffic delay, congestion levels, and flow speed ratios.
- **OpenWeatherMap API**: Live ambient temperature, rainfall precipitation rates, and atmospheric visibility with caching.

## Main modules
1. Accident data analytics and EDA
2. Accident hotspot detection using GPS coordinates (DBSCAN)
3. ML-based road-risk classification (RandomForestClassifier v0.4.0)
4. Android live speed/location monitoring (Kotlin, Coroutines, Foreground Service)
5. Traffic-awareness integration (TomTom Live Flow API)
6. Weather-awareness integration (OpenWeatherMap Live API)
7. Map & GIS visualization (Mapbox Primary with OpenStreetMap fallback)
8. Real-time phone notifications and voice alerts
9. Emergency crash-detection workflow (15s confirmation dialog with `[I AM OK]`)
10. Analytics command center dashboard (Streamlit)

## Repository structure

```text
smart-road-safety/
├── android/                         # Kotlin Android application
│   ├── app/
│   └── README.md
├── backend/                         # FastAPI REST API
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── core/
│   └── requirements.txt
├── data-science/
│   ├── data/raw/                    # Original datasets, not modified
│   ├── data/processed/              # Cleaned feature datasets
│   ├── notebooks/
│   │   ├── 01_eda.ipynb
│   │   ├── 02_hotspot_analysis.ipynb
│   │   └── 03_model_training.ipynb
│   ├── src/
│   ├── models/
│   └── requirements.txt
├── dashboard/                       # Streamlit dashboard for MVP
├── docs/
│   ├── IMPLEMENTATION_PLAN.md
│   ├── TECH_STACK_SPECIFICATION.md
│   └── CHANGELOG.md
├── .env.example
├── docker-compose.yml
└── README.md
```

## Recommended development strategy
Build in these releases:

```text
v0.1.0  Research + architecture
v0.2.0  Data ingestion + cleaning
v0.3.0  EDA + hotspot analysis
v0.4.0  ML risk model
v0.5.0  FastAPI backend
v0.6.0  Android GPS/speed app
v0.7.0  Traffic + weather
v0.8.0  Notifications + voice
v0.9.0  End-to-end integration
v1.0.0  Hackathon release
v1.1.x  Crash/emergency features
v2.0.0  Production-oriented architecture
```

## Key design principle
Keep safety-critical immediate checks on the phone (for example, overspeed alert), while using the backend for heavier analytics and ML prediction.

## Important limitations
- GPS speed can be noisy and road speed-limit data can be incomplete or stale.
- Traffic and weather APIs depend on provider coverage and network availability.
- Historical accident data can contain reporting bias and missing values.
- Risk scores should be presented as estimates, not guarantees.
- Continuous location collection requires explicit user permission and careful privacy handling.

## Current verified platform choices
- Python **3.13.15** is selected for the project because it is a stable current Python 3.13 maintenance release and is a conservative choice for the data-science stack. Python 3.14.7 is the latest Python 3 release, but the project deliberately targets 3.13 for dependency compatibility. Source: https://www.python.org/downloads/release/python-31315/ and https://www.python.org/getit/source/
- Kotlin **2.4.20** is the current 2.4 release line according to JetBrains. Source: https://kotlinlang.org/docs/releases.html
- Android Studio **Quail 4 2026.1.4 Patch 1** is the current stable channel build listed by Android Developers. Source: https://developer.android.com/studio/releases
- Android **API 36 / Android 16** is the target API for current Android application builds. Source: https://developer.android.com/about/versions/16/setup-sdk
- Android 13+ requires runtime notification permission (`POST_NOTIFICATIONS`) for apps that post notifications. Source: https://firebase.google.com/docs/cloud-messaging/android/get-started
- Android 14+ requires foreground-service type declarations and the corresponding permissions for a location foreground service. Source: https://developer.android.com/develop/background-work/services/fgs/service-types
