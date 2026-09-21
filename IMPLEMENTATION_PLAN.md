# Smart Road Safety — Implementation Plan

**Project:** AI-Based Accident Risk Prediction & Real-Time Driver Warning System  
**Development model:** Software-first, phone-assisted  
**Target release:** v1.0.0-hackathon  
**Document status:** Implementation baseline

---

## 1. Objective

Build a software system that:

- analyzes historical accident data;
- identifies accident-prone locations and patterns;
- predicts a road/driver risk level from historical + current conditions;
- monitors live speed and location using an Android phone;
- checks traffic/weather context;
- warns the driver through Android notifications and voice;
- optionally detects suspected crashes using phone motion sensors;
- provides a data-science dashboard for demonstration and evaluation.

The system predicts **risk**, not a guaranteed accident.

---

## 2. Project category

**Primary:** Data Science / Machine Learning / Artificial Intelligence  
**Secondary:** Android Software / Smart Transportation / GIS / IoT-style sensing

The project is primarily software. Dedicated vehicle hardware is optional and is not required for the hackathon MVP.

---

## 3. System architecture

```text
                    ┌──────────────────────┐
                    │     Android Phone     │
                    │ GPS / Speed / Sensors│
                    └──────────┬───────────┘
                               │ HTTPS/JSON
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI API      │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼─────────────────────┐
          ▼                    ▼                     ▼
 ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
 │ Accident DB    │   │ Traffic API    │   │ Weather API    │
 └───────┬────────┘   └───────┬────────┘   └───────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌──────────────────────┐
                    │ Feature Engineering  │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ ML Risk Model        │
                    │ Random Forest first  │
                    └──────────┬───────────┘
                               ▼
                     Risk score + reasons
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
        Android notification         Web dashboard
        + voice warning              + analytics
```

---

## 4. Technology and specification matrix

| Layer | Technology | Version / baseline | Purpose |
|---|---|---|---|
| Mobile language | Kotlin | 2.4.20 | Android application |
| Android IDE | Android Studio | Quail 4 2026.1.4 Patch 1 | App development |
| Android API | Android 16 | API 36 | compile/target baseline |
| Android build | Android Gradle Plugin | 9.4.0 | Application build |
| Build system | Gradle | 9.6.0 | Android build orchestration |
| JVM | JDK | 17 | Android toolchain |
| Backend language | Python | 3.13.15 | API, ML integration, services |
| Backend framework | FastAPI | pin a tested stable release in lock file | REST API |
| ASGI server | Uvicorn | pin tested stable release | Run FastAPI |
| Data analysis | pandas | pin tested stable release | Cleaning + analytics |
| Numerical computing | NumPy | pin tested stable release | Arrays + feature processing |
| ML | scikit-learn | pin tested stable release | Classification + evaluation |
| Model persistence | joblib | pin tested stable release | Save/load model |
| Visualization | Matplotlib | pin tested stable release | EDA |
| GIS map | Folium / Leaflet | pin tested release | Accident heatmap |
| Dashboard | Streamlit | pin tested stable release | Hackathon analytics UI |
| Database | SQLite for MVP | local | Prototype storage |
| Database | PostgreSQL for later | current supported release | Scalable deployment |
| Notifications | Firebase Cloud Messaging | current Firebase SDK | Push notifications |
| Mobile voice | Android Text-to-Speech | platform API | Driver voice warning |
| Networking | HTTPS + JSON | REST | Phone/backend communication |
| Containerization | Docker | current stable | Reproducible backend deployment |
| Version control | Git + GitHub | current installed versions | Source control |

### Verified platform notes

- Python 3.13.15 was released on August 5, 2026; Python 3.14.7 is the latest Python 3 release. This project chooses 3.13.15 for dependency conservatism. Source: https://www.python.org/downloads/release/python-31315/ and https://www.python.org/getit/source/
- Kotlin 2.4.20 was released September 7, 2026. Source: https://kotlinlang.org/docs/releases.html
- Android Studio Quail 4 2026.1.4 Patch 1 is listed as the current stable release. Source: https://developer.android.com/studio/releases
- Android 16 is API 36. Android Developers document `compileSdk = 36` and `targetSdk = 36` for Android 16. Source: https://developer.android.com/about/versions/16/setup-sdk
- AGP 9.4.0 requires Gradle 9.6.0 and JDK 17; AGP 9.4 supports up to API 37. Source: https://developer.android.com/build/releases/agp-9-4-0-release-notes
- Android 13+ notification posting requires runtime `POST_NOTIFICATIONS` permission. Source: https://firebase.google.com/docs/cloud-messaging/android/get-started
- Android 14+ location foreground services require the location service type and `FOREGROUND_SERVICE_LOCATION` in addition to location runtime permissions. Source: https://developer.android.com/develop/background-work/services/fgs/service-types

---

## 5. Functional modules

### Module A — Historical accident data

Input examples:

```text
accident_id
latitude
longitude
date
time
weather
road_type
lighting
traffic_density
vehicle_type
speed
severity
```

Minimum useful fields:

- latitude
- longitude
- date/time
- severity
- weather or road context if available

Tasks:

1. Import raw CSV/JSON.
2. Validate coordinates.
3. Remove duplicates.
4. Handle missing values.
5. Normalize categorical fields.
6. Save cleaned data.

Output:

```text
data/processed/accidents_clean.csv
```

---

## 6. Data Science workflow

### 6.1 EDA

Create:

- accident count by hour;
- accidents by day of week;
- accidents by weather;
- severity distribution;
- accidents by road type;
- accident trend by month/year;
- geographic accident map.

Example questions:

```text
Which hours show the highest accident frequency?
Which weather categories are associated with more accidents?
Where are the accident clusters?
How does severity vary by road/time conditions?
```

### 6.2 Hotspot detection

Use latitude/longitude as the primary spatial features.

Recommended first algorithm: **DBSCAN**.

Why:

- does not require the number of clusters in advance;
- works naturally with noisy spatial points;
- good for identifying dense accident regions.

Output example:

```text
hotspot_id
latitude
longitude
accident_count
severity_index
risk_zone
```

### 6.3 Feature engineering

Candidate features:

```text
current_speed
speed_limit
hour
is_weekend
weather_code
traffic_code
road_type_code
lighting_code
historical_accident_count
historical_severity_index
distance_to_hotspot
```

Do not use a feature unless the dataset/API actually provides it.

### 6.4 ML target

Start with a binary target:

```text
risk = 0  -> lower historical risk
risk = 1  -> higher historical risk
```

Define the target using a documented spatial/temporal rule from the accident dataset, such as whether an observation falls into a high-accident-density road/time window.

For a later version, move to multi-class risk levels.

### 6.5 Models

Development order:

```text
1. Logistic Regression  -> baseline
2. Random Forest        -> main student-friendly model
3. XGBoost              -> optional comparison
```

Evaluate with:

- precision;
- recall;
- F1 score;
- confusion matrix;
- ROC-AUC where appropriate.

Avoid reporting only accuracy, especially if the classes are imbalanced.

---

## 7. Risk scoring layer

The ML model should return both a model output and human-readable reasons.

Example:

```json
{
  "risk_score": 87,
  "risk_level": "HIGH",
  "reasons": [
    "Vehicle speed is above the road speed limit",
    "Current location is near a historical accident hotspot",
    "Traffic is heavy",
    "Rain is detected"
  ]
}
```

The score should be calibrated/evaluated rather than presented as a guaranteed probability unless the model has been properly calibrated.

---

## 8. FastAPI backend

Suggested endpoints:

```text
GET  /health
POST /predict-risk
GET  /hotspots/nearby
GET  /road-context
GET  /dashboard/summary
POST /events/telemetry
POST /events/crash-suspected
```

### `/predict-risk` request

```json
{
  "latitude": 17.3850,
  "longitude": 78.4867,
  "speed_kmh": 72,
  "timestamp": "2026-09-21T22:30:00+05:30",
  "weather": "rain",
  "traffic": "heavy"
}
```

### `/predict-risk` response

```json
{
  "risk_score": 87,
  "risk_level": "HIGH",
  "speed_limit_kmh": 50,
  "hotspot": true,
  "distance_to_hotspot_m": 140,
  "message": "High road-risk conditions. Reduce speed."
}
```

---

## 9. Android implementation

### 9.1 App screens

```text
Splash
  ↓
Permissions
  ↓
Home
  ├─ Start Monitoring
  ├─ Current Speed
  ├─ Traffic
  ├─ Accident Risk
  ├─ Map
  └─ Emergency Contact
```

### 9.2 Phone data

Collect only what is necessary:

- latitude;
- longitude;
- speed;
- timestamp;
- accelerometer/gyroscope only when crash detection is enabled.

### 9.3 Location monitoring

Use Android location APIs and a visible user-started location foreground service for continuous monitoring.

Android 14+ requires the correct foreground-service type and permission for location services. Apps targeting Android 12+ also face restrictions on starting foreground services from the background, so the project must start the monitoring service from a user-visible app state. Source: https://developer.android.com/develop/background-work/services/fgs/service-types and https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start

### 9.4 Local overspeed check

Perform this locally for fast response:

```text
if current_speed > speed_limit + tolerance:
    trigger_local_warning()
```

Add hysteresis/cooldown so small GPS fluctuations do not spam warnings.

---

## 10. Traffic integration

Design traffic as an external provider adapter:

```text
TrafficProvider interface
        ↓
Google / other provider implementation
```

Required outputs:

```text
traffic_level
traffic_delay
traffic_speed_ratio (if available)
```

For a route-aware implementation, a traffic-aware routing provider can supply current-traffic route conditions. For the hackathon, expose the provider behind an adapter so you can change providers without rewriting the ML layer.

---

## 11. Weather integration

Use a weather API provider and normalize responses into a small feature set:

```text
clear
cloudy
rain
heavy_rain
fog
storm
unknown
```

Optional numeric fields:

```text
rainfall_mm
visibility_km
temperature_c
```

Cache short-lived weather responses to reduce API calls.

---

## 12. Notifications and voice alerts

### Notification categories

1. Overspeed
2. Accident hotspot ahead
3. High risk
4. Severe weather/road condition
5. Suspected crash

### Alert priority

```text
LOW       → silent/in-app
MODERATE  → notification
HIGH      → notification + vibration + voice
CRITICAL  → notification + vibration + voice + crash workflow if applicable
```

Android 13+ requires runtime notification permission. Source: https://firebase.google.com/docs/cloud-messaging/android/get-started

Use Android Text-to-Speech for driver-facing voice prompts.

### Anti-spam rule

Do not send an alert on every telemetry update. Use:

```text
risk transition
+ cooldown
+ significant change
```

Example:

```text
LOW -> MODERATE  => alert
MODERATE -> HIGH => alert
HIGH -> HIGH     => suppress repeated alert
HIGH -> LOW      => reset alert state
```

---

## 13. Crash detection — optional v1.1 module

Use:

```text
accelerometer
+
gyroscope
+
GPS speed change
```

Do not classify a single sensor spike as a confirmed crash.

Prototype decision flow:

```text
Large acceleration spike
       ↓
Check gyroscope change
       ↓
Check rapid speed reduction
       ↓
Check GPS movement after event
       ↓
Multiple signals agree?
   ┌───┴───┐
   NO      YES
   ↓        ↓
ignore   suspected crash
```

Then show a local safety countdown:

```text
Possible crash detected.
Are you okay?

[ I AM OK ]   [ SEND ALERT ]
```

---

## 14. Emergency-contact workflow — optional v1.1

Store user-selected emergency contacts locally and securely.

On a confirmed/suspected event:

```text
Crash event
   ↓
10-second user confirmation window
   ↓
No response
   ↓
Generate alert payload
   ↓
Send through the chosen communication channel
```

The hackathon demo should use test contacts. Do not represent the prototype as a certified emergency-response service.

---

## 15. Dashboard

Recommended MVP: Streamlit.

Dashboard pages:

```text
Overview
Accident Heatmap
Accident Trends
Risk Analysis
Model Evaluation
Live Demo
```

Live-demo widgets:

```text
Current Speed
Speed Limit
Traffic
Weather
Nearest Hotspot
Risk Score
Risk Reasons
```

---

## 16. Database design

### `accidents`

```text
id
latitude
longitude
datetime
weather
road_type
lighting
vehicle_type
severity
source
```

### `hotspots`

```text
id
latitude
longitude
accident_count
severity_index
radius_m
risk_level
```

### `telemetry`

```text
id
device_id
timestamp
latitude
longitude
speed_kmh
traffic_level
weather_code
risk_score
risk_level
```

### `alerts`

```text
id
device_id
timestamp
alert_type
risk_level
message
latitude
longitude
acknowledged
```

For the hackathon prototype, SQLite is enough. Keep the database layer abstract so PostgreSQL can be introduced later.

---

## 17. API security and privacy baseline

Implement:

- HTTPS outside localhost;
- API key or JWT for authenticated mobile sessions;
- rate limiting for public endpoints;
- input validation with Pydantic;
- no hard-coded API keys;
- `.env` for development secrets;
- minimal storage of precise location data;
- clear user consent for location and notification access;
- log redaction for coordinates and device identifiers where not needed.

---

## 18. Environment files

### `.env.example`

```env
APP_ENV=development
API_BASE_URL=http://10.0.2.2:8000
DATABASE_URL=sqlite:///./data/app.db
TRAFFIC_API_KEY=replace_me
WEATHER_API_KEY=replace_me
FCM_PROJECT_ID=replace_me
SECRET_KEY=replace_me
```

Never commit a real `.env`.

---

## 19. Backend setup

Recommended environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r backend/requirements.txt
pip install -r data-science/requirements.txt
```

Run API:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Run dashboard:

```bash
streamlit run dashboard/app.py
```

---

## 20. Android setup

Install:

- Android Studio Quail 4 2026.1.4 Patch 1
- Android SDK Platform 36
- Android SDK Build Tools
- JDK 17

Configure:

```kotlin
android {
    compileSdk = 36

    defaultConfig {
        targetSdk = 36
    }
}
```

Source for Android 16 SDK requirements: https://developer.android.com/about/versions/16/setup-sdk

The project should use the Gradle Wrapper, not a developer-installed Gradle binary, so builds are reproducible.

---

## 21. Development phases

### Phase 1 — v0.1.0
Research, use cases, architecture, repository setup.

### Phase 2 — v0.2.0
Dataset import, cleaning, schema, preprocessing scripts.

### Phase 3 — v0.3.0
EDA, accident heatmap, DBSCAN hotspot detection.

### Phase 4 — v0.4.0
Feature engineering, baseline model, Random Forest, metrics, model artifact.

### Phase 5 — v0.5.0
FastAPI endpoints, database layer, model inference service.

### Phase 6 — v0.6.0
Android application, permissions, GPS, live speed display, local overspeed warning.

### Phase 7 — v0.7.0
Traffic and weather adapters.

### Phase 8 — v0.8.0
Firebase push notifications, notification channels, Text-to-Speech, alert cooldown.

### Phase 9 — v0.9.0
End-to-end phone → backend → risk → alert integration.

### Phase 10 — v1.0.0-hackathon
Polish UI, testing, demo scenarios, documentation, presentation, deployment script.

---

## 22. Testing plan

### Data tests
- schema validation;
- missing-value tests;
- coordinate range tests;
- duplicate detection.

### ML tests
- train/test split;
- class distribution check;
- cross-validation where appropriate;
- confusion matrix;
- precision/recall/F1;
- leakage check.

### API tests
- valid prediction request;
- invalid coordinates;
- missing fields;
- model unavailable;
- traffic provider unavailable;
- weather provider unavailable.

### Android tests
- permission denied;
- GPS disabled;
- no network;
- low battery;
- notification permission denied;
- monitoring start/stop;
- notification cooldown;
- voice alert behavior.

### End-to-end demo tests

```text
Scenario A: Normal drive
Scenario B: Overspeed
Scenario C: Hotspot approach
Scenario D: Heavy traffic
Scenario E: Rain + hotspot + overspeed
Scenario F: Suspected crash
```

---

## 23. Hackathon demo script

1. Start backend.
2. Open Streamlit dashboard.
3. Launch Android app.
4. Grant location + notification permissions.
5. Start Safety Monitoring.
6. Show current GPS/speed.
7. Simulate or drive into an overspeed condition.
8. Show local warning.
9. Move to a hotspot test coordinate.
10. Show hotspot warning.
11. Inject heavy traffic + rain test data.
12. Call `/predict-risk`.
13. Show risk score and reasons.
14. Trigger a controlled simulated crash event.
15. Show emergency workflow.

---

## 24. Definition of done for v1.0.0-hackathon

The release is complete when all are working together:

```text
[✓] Accident dataset loaded
[✓] Data-cleaning pipeline
[✓] EDA notebook
[✓] Accident hotspot map
[✓] ML model trained and evaluated
[✓] Saved model artifact
[✓] FastAPI prediction endpoint
[✓] Android GPS/speed monitoring
[✓] Local overspeed alert
[✓] Traffic integration or demo provider
[✓] Weather integration or demo provider
[✓] Risk warning from backend
[✓] Android notification
[✓] Voice warning
[✓] Dashboard
[✓] End-to-end demo
[✓] README + changelog + architecture docs
```

---

## 25. Recommended B.Tech project deliverables

### Software
- Android APK
- FastAPI backend
- Data-science notebooks
- trained ML model
- dashboard
- database schema
- sample dataset
- test scenarios

### Academic documentation
- Problem statement
- Existing system
- Proposed system
- Objectives
- Literature survey
- Methodology
- System architecture
- Data preprocessing
- EDA results
- ML algorithms
- Model evaluation
- Results
- Limitations
- Future scope

### Presentation message

> **Historical accident data identifies risk patterns. Machine learning estimates current road risk. The Android application combines that prediction with live speed, location, traffic and weather context to provide preventive warnings before a dangerous event escalates.**
