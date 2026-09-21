# Smart Road Safety — Technology Stack Specification

## 1. Architecture style

**Style:** Client–API–ML–Data architecture  
**Primary client:** Android phone  
**Primary backend:** Python/FastAPI  
**Primary analytics:** Python data-science stack  
**MVP dashboard:** Streamlit  
**MVP database:** SQLite

---

## 2. Languages

| Language | Version | Where used |
|---|---:|---|
| Python | 3.13.15 | Data science, ML, API, scripts |
| Kotlin | 2.4.20 | Android application |
| SQL | SQLite/PostgreSQL dialect | Database queries |
| JSON | RFC-compatible JSON payloads | API communication |
| Bash / PowerShell | Host-dependent | Setup and automation |
| Markdown | CommonMark/GFM style | Documentation |

### Version policy

Pin runtime versions in CI/build configuration. Do not use floating dependency versions for the final hackathon release.

---

## 3. Python stack

### Required

```text
Python 3.13.15
FastAPI
Uvicorn
Pydantic
pandas
NumPy
scikit-learn
joblib
Matplotlib
Folium
Streamlit
pytest
httpx
python-dotenv
```

### Optional

```text
XGBoost
imbalanced-learn
SQLAlchemy
PostgreSQL driver
```

### Python roles

- **pandas:** data cleaning, grouping, time features
- **NumPy:** numeric transformations
- **scikit-learn:** preprocessing, models, metrics, clustering
- **DBSCAN:** spatial hotspot discovery
- **joblib:** save/load trained model
- **FastAPI:** inference API
- **Pydantic:** request/response validation
- **Streamlit:** hackathon dashboard
- **Folium:** interactive location visualization
- **pytest:** automated Python tests

---

## 4. Android stack

### Toolchain

```text
Android Studio: Quail 4 2026.1.4 Patch 1
Kotlin: 2.4.20
Android: API 36
AGP: 9.4.0
Gradle: 9.6.0
JDK: 17
```

### Android components

```text
Fused location / Android location APIs
Foreground Service (location)
SensorManager
NotificationManager
TextToSpeech
HTTP client (OkHttp/Retrofit or equivalent)
Firebase Cloud Messaging
Jetpack components
```

### Key permissions/features

```text
ACCESS_COARSE_LOCATION
ACCESS_FINE_LOCATION
FOREGROUND_SERVICE
FOREGROUND_SERVICE_LOCATION
POST_NOTIFICATIONS (Android 13+)
```

Only request permissions needed by enabled features.

---

## 5. Android target strategy

For this project:

```text
compileSdk = 36
targetSdk  = 36
minSdk    = choose after device coverage testing
```

Set `minSdk` only after testing the required location/sensor APIs on the devices available to the team. Do not choose a minimum level solely for presentation reasons.

---

## 6. Backend API contract

### Core endpoint

```text
POST /predict-risk
Content-Type: application/json
```

Request:

```json
{
  "latitude": 17.385,
  "longitude": 78.4867,
  "speed_kmh": 72,
  "speed_limit_kmh": 50,
  "traffic_level": "heavy",
  "weather": "rain",
  "timestamp": "2026-09-21T22:30:00+05:30"
}
```

Response:

```json
{
  "risk_score": 87,
  "risk_level": "HIGH",
  "hotspot": true,
  "recommended_action": "Reduce speed",
  "reasons": [
    "Overspeed",
    "Accident hotspot",
    "Heavy traffic",
    "Rain"
  ]
}
```

---

## 7. Traffic subsystem

Do not couple the ML code directly to a specific traffic vendor.

```text
TrafficProvider
├── get_route_context()
├── get_traffic_level()
└── get_delay()
```

Provider implementation can be changed later.

For the hackathon, one real provider + one mock provider is recommended. The mock provider guarantees that your demo still works if the external API quota/network fails.

---

## 8. Weather subsystem

Normalize all providers to:

```text
weather_code
rainfall_mm
visibility_km
temperature_c
```

Use an adapter:

```text
WeatherProvider
└── get_current_conditions(lat, lon)
```

---

## 9. ML model specification

### Phase 1

```text
Problem: binary risk classification
Baseline: Logistic Regression
Main model: Random Forest
Optional: XGBoost
```

### Features

```text
current_speed
speed_limit
hour
day_of_week
traffic_level
weather
road_type
historical_accident_count
distance_to_hotspot
lighting
```

### Metrics

```text
Precision
Recall
F1
Confusion Matrix
ROC-AUC (when meaningful)
```

### Model artifact

```text
models/accident_risk_model.joblib
models/preprocessor.joblib
models/model_metadata.json
```

`model_metadata.json` should record:

```json
{
  "model_version": "0.4.0",
  "training_dataset_version": "2026-09-01",
  "features": [],
  "training_date": "2026-09-21",
  "metrics": {}
}
```

---

## 10. Data storage specification

### Raw data
Never overwrite source files.

```text
data/raw/
```

### Processed data

```text
data/processed/
```

### Models

```text
models/
```

### Application database

```text
data/app.db
```

---

## 11. Security baseline

- Store API keys in environment variables or a secret manager.
- Keep `.env` out of Git.
- Use HTTPS for non-local deployments.
- Validate all API inputs.
- Add rate limits to public endpoints.
- Do not expose raw device identifiers in dashboard URLs.
- Minimize retention of exact GPS history.
- Provide start/stop monitoring controls.

---

## 12. Observability

Backend logs should include:

```text
request_id
timestamp
endpoint
response_time_ms
model_version
provider_status
```

Do not log full private location history by default.

---

## 13. Reproducibility

Required files for a reproducible build:

```text
requirements.txt
requirements-lock.txt (recommended)
gradle-wrapper files
.env.example
Dockerfile
compose.yaml
dataset README with source/license
model metadata
```

---

## 14. Official platform references

- Python 3.13.15: https://www.python.org/downloads/release/python-31315/
- Python release list: https://www.python.org/getit/source/
- Kotlin releases: https://kotlinlang.org/docs/releases.html
- Android Studio releases: https://developer.android.com/studio/releases
- Android 16 setup / SDK 36: https://developer.android.com/about/versions/16/setup-sdk
- Android 16 API level: https://developer.android.com/about/versions/16/overview
- AGP 9.4.0: https://developer.android.com/build/releases/agp-9-4-0-release-notes
- Android foreground-service types: https://developer.android.com/develop/background-work/services/fgs/service-types
- FCM Android notifications: https://firebase.google.com/docs/cloud-messaging/android/get-started
