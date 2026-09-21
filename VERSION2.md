# SafeGuard v2.0 Product and Improvement Plan

## 1. Release vision

SafeGuard v2.0 should evolve from a basic analytics dashboard into a
real-time road-safety command center.

The v1.0 system already demonstrates:

- accident-data preprocessing;
- hotspot detection;
- ML risk classification;
- FastAPI inference;
- Android GPS and speed monitoring;
- traffic and weather adapters;
- notifications and voice-alert support;
- Streamlit analytics;
- crash-suspected event handling.

Version 2.0 should improve the product in four dimensions:

1. **Visual quality** — make the dashboard look like a professional safety
   product instead of a plain notebook-style report.
2. **Real-time behavior** — make live risk, alerts, provider state, and device
   status visible immediately.
3. **User value** — add trip history, route intelligence, crash confirmation,
   and personalized safety insights.
4. **Production readiness** — improve reliability, privacy, testing, security,
   observability, and deployment.

Risk must continue to be presented as an estimate. SafeGuard must never claim
that an accident can be predicted with certainty.

---

## 2. v2.0 success criteria

Version 2.0 is complete when:

- the dashboard has a branded, responsive safety-focused interface;
- the overview page communicates current risk within five seconds;
- live backend, model, traffic, weather, and device status are visible;
- the map, alerts, charts, and tables use one consistent visual system;
- the dashboard works in both online and degraded/offline modes;
- the Android app can continue basic overspeed protection without the backend;
- crash detection uses confirmation before emergency-contact notification;
- trips and safety events can be reviewed by the user;
- API responses expose model and provider freshness information;
- user location and device data follow a documented retention policy;
- CI validates Python tests, Android builds, lint, and dashboard startup;
- a clean checkout can reproduce the application build;
- Android emulator and physical-device smoke tests pass.

---

## 3. Dashboard redesign

### 3.1 Product identity

Replace the current placeholder presentation with a local SafeGuard identity:

- shield-based logo;
- dark navy base color;
- safety orange accent;
- green, amber, red, and dark-red risk states;
- consistent icon family;
- readable typography;
- compact status badges;
- local assets instead of external placeholder images.

Recommended colors:

| Purpose | Color |
|---|---|
| Background | `#07111F` |
| Surface | `#102238` |
| Surface elevated | `#18324D` |
| Primary accent | `#FF9F1C` |
| Safe | `#21C77A` |
| Moderate | `#F4B942` |
| High | `#F05D5E` |
| Critical | `#B42318` |
| Text | `#F6F8FB` |
| Muted text | `#9EB0C5` |

### 3.2 New overview layout

The overview page should become a command center:

```text
┌─────────────────────────────────────────────────────────────┐
│ SafeGuard Command Center       Backend ●  Model ●  12:40 PM │
├─────────────────────────────────────────────────────────────┤
│ CURRENT ROAD RISK: HIGH       SPEED 72       LIMIT 50       │
│ Slow down and increase following distance                    │
├──────────────────────────────┬──────────────────────────────┤
│ Live risk map                │ Active alerts                │
│ Current position             │ Heavy traffic                │
│ Hotspots and route           │ Rain detected                │
│                              │ Hotspot nearby               │
├──────────────────────────────┴──────────────────────────────┤
│ Risk trend       Speed trend       Provider health           │
├─────────────────────────────────────────────────────────────┤
│ Recent trip summary          Model confidence               │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Hero risk card

The first screen must show:

- current risk level;
- risk score;
- current speed;
- speed limit;
- distance to nearest hotspot;
- traffic level;
- weather condition;
- last prediction time;
- recommended action;
- source freshness;
- a visible degraded-mode label when applicable.

The card must change color and icon based on risk level.

### 3.4 Status strip

Display small status chips for:

- backend;
- ML model;
- traffic provider;
- weather provider;
- database;
- Android device;
- last update age.

Example:

```text
Backend ONLINE
Model LOADED
Traffic MOCK · 12 s old
Weather LIVE · 38 s old
Device CONNECTED
```

### 3.5 Active alerts panel

Show the latest active events:

- overspeed;
- hotspot proximity;
- high risk;
- dangerous weather;
- crash suspected;
- backend unavailable;
- stale provider data.

Each alert should include:

- severity;
- time;
- location;
- cause;
- recommended action;
- dismissed/active state.

### 3.6 Interactive charts

Replace static Matplotlib-first charts with interactive charts where useful:

- Plotly risk timeline;
- Plotly hourly accident distribution;
- Plotly severity distribution;
- Plotly monthly trends;
- Plotly provider latency;
- Plotly trip risk history.

Charts should include:

- hover values;
- clear legends;
- consistent colors;
- selected filters;
- empty-state messages;
- sample-size labels;
- explanatory captions.

### 3.7 Map redesign

The map should show:

- current driver position;
- route line;
- hotspot circles;
- accident markers;
- risk-colored segments;
- weather overlay when available;
- traffic level;
- map legend;
- selected-event details;
- automatic refresh time.

Use clustering for large accident datasets and avoid rendering thousands of
markers at once.

### 3.8 Navigation redesign

Use grouped navigation:

```text
LIVE
  Command Center
  Live Demo

ANALYTICS
  Accident Map
  Trends
  Risk Analysis
  Model Evaluation

HISTORY
  Trips
  Safety Events

SYSTEM
  Provider Health
  Settings
```

The sidebar should also display:

- application version;
- model version;
- dataset version;
- backend URL;
- last refresh time;
- online/offline state.

---

## 4. Dashboard functional features

### 4.1 Live command center

Add automatic refresh with a configurable interval:

- 5 seconds for active monitoring;
- 30 seconds for normal dashboard use;
- manual refresh button;
- pause refresh option.

Avoid excessive provider requests by caching provider data and separating UI
refresh from external API refresh.

### 4.2 Live simulation mode

Provide safe demo controls:

- normal driving;
- overspeed;
- hotspot approach;
- heavy traffic;
- rain;
- combined high risk;
- suspected crash.

Show clearly when the values are simulated.

### 4.3 Trip history

Add a trip page containing:

- trip date;
- duration;
- distance;
- maximum speed;
- overspeed duration;
- warning count;
- high-risk-zone count;
- average risk;
- route map;
- downloadable summary.

### 4.4 Event history

Allow filtering by:

- event type;
- risk level;
- date range;
- device;
- location;
- provider source.

### 4.5 Model explanation panel

For every prediction, show the actual contributing factors:

- speed relative to limit;
- hotspot proximity;
- traffic;
- weather;
- time-of-day;
- model confidence;
- data freshness.

Do not display explanations that are not derived from model inputs.

### 4.6 Export and sharing

Allow authorized users to export:

- trip summary CSV;
- filtered accident data;
- hotspot list;
- model evaluation report;
- selected chart image.

Do not include raw device identifiers or exact location history by default.

---

## 5. Backend v2 API

### 5.1 API response metadata

Risk responses should include:

```json
{
  "risk_score": 75,
  "risk_level": "CRITICAL",
  "confidence": 0.87,
  "model_version": "risk-model-0.4.0",
  "traffic_source": "mock",
  "weather_source": "openweathermap",
  "data_age_seconds": 18,
  "degraded_mode": false,
  "reasons": [
    "Overspeed",
    "Accident hotspot",
    "Heavy traffic"
  ],
  "recommended_action": "Pull over safely if possible"
}
```

### 5.2 New endpoints

Recommended v2 endpoints:

```text
GET  /api/v2/health
GET  /api/v2/system/status
GET  /api/v2/road-context
POST /api/v2/predict-risk
POST /api/v2/events/telemetry
POST /api/v2/events/crash-suspected
POST /api/v2/events/crash-confirmation
GET  /api/v2/events
POST /api/v2/trips/start
POST /api/v2/trips/{trip_id}/finish
GET  /api/v2/trips
GET  /api/v2/trips/{trip_id}
GET  /api/v2/hotspots/nearby
POST /api/v2/routes/evaluate
GET  /api/v2/model/metadata
```

### 5.3 Provider health

Expose:

- live/fallback/mock status;
- last successful request;
- last error;
- response latency;
- cache age;
- provider quota state where available.

### 5.4 Reliability controls

Add:

- bounded retries;
- request timeouts;
- exponential backoff;
- circuit breaker;
- stale-data limits;
- request IDs;
- structured logs;
- rate limiting;
- API authentication;
- idempotency keys for event creation.

---

## 6. Android v2 features

### 6.1 Improved monitoring screen

Show:

- current speed;
- speed limit;
- current risk;
- hotspot distance;
- traffic;
- weather;
- GPS accuracy;
- network state;
- monitoring state;
- last backend update.

### 6.2 Offline-first mode

When the backend is unavailable:

- continue local overspeed detection;
- use cached speed limits;
- use cached hotspots;
- queue telemetry locally;
- show an offline badge;
- synchronize when connectivity returns.

### 6.3 Crash workflow

Implement:

1. accelerometer impact detection;
2. gyroscope confirmation;
3. sudden-stop verification;
4. false-positive suppression;
5. loud local alarm;
6. countdown timer;
7. cancel button;
8. emergency-contact message;
9. retry queue;
10. incident record.

Emergency communication requires explicit user consent and must not be
described as guaranteed emergency-service delivery.

### 6.4 Driver behavior insights

Measure carefully:

- harsh braking;
- harsh acceleration;
- sudden swerving;
- repeated overspeed;
- long continuous driving;
- possible fatigue indicators.

All behavior metrics need confidence thresholds and false-positive testing.

### 6.5 Android settings

Add settings for:

- speed warning margin;
- risk sensitivity;
- voice-alert language;
- voice volume;
- notification priority;
- quiet hours;
- emergency contacts;
- telemetry sharing;
- data deletion.

---

## 7. Machine-learning v2

### 7.1 Dataset governance

Track:

- dataset version;
- source;
- license;
- geographic coverage;
- date coverage;
- schema version;
- cleaning version;
- label-generation version.

### 7.2 Better validation

Compare:

- random split;
- time split;
- geographic split;
- grouped cross-validation.

Report:

- precision;
- recall;
- F1;
- ROC-AUC;
- PR-AUC;
- calibration;
- Brier score;
- false-positive burden;
- false-negative rate.

### 7.3 Probability calibration

If `risk_score` represents probability, calibrate it and document the
transformation to 0–100. Otherwise name it a composite risk index instead of a
probability.

### 7.4 Model registry

Store:

```text
model version
dataset version
feature schema
training date
training code revision
metrics
calibration result
approval status
deployment status
```

Support model rollback and compatibility checks.

### 7.5 Drift detection

Monitor changes in:

- traffic distribution;
- weather distribution;
- speed distribution;
- geographic coverage;
- class balance;
- missing values;
- provider availability.

---

## 8. Privacy and security

### 8.1 Data minimization

Collect only data required for:

- live risk;
- alerting;
- crash workflow;
- trip summaries explicitly enabled by the user.

### 8.2 Privacy controls

Provide:

- consent screen;
- telemetry toggle;
- crash-sharing toggle;
- history retention choice;
- delete-history action;
- export-history action;
- privacy explanation.

### 8.3 Security controls

Add:

- HTTPS;
- device authentication;
- hashed or pseudonymous device IDs;
- dashboard authentication;
- role-based access;
- secrets outside source control;
- encrypted sensitive storage;
- private logging;
- request rate limiting;
- audit records for administrative access.

Never expose exact GPS history or raw device IDs in URLs, logs, screenshots, or
public dashboard views.

---

## 9. Observability and operations

Track:

- request count;
- error count;
- response latency;
- model latency;
- provider latency;
- fallback count;
- stale-data count;
- active devices;
- active trips;
- crash-event count;
- notification delivery result;
- database health.

Add:

- structured JSON logs;
- correlation IDs;
- health/readiness endpoints;
- metrics endpoint;
- alerting thresholds;
- backup and restore procedure.

---

## 10. Testing strategy for v2

### Python

- unit tests;
- integration tests;
- API contract tests;
- provider failure tests;
- database tests;
- model artifact tests;
- leakage tests;
- calibration tests;
- dashboard startup smoke test.

### Android

- unit tests for speed and risk logic;
- ViewModel tests;
- service lifecycle tests;
- notification tests;
- permission tests;
- offline queue tests;
- crash countdown tests;
- instrumentation tests.

### Browser/dashboard

- startup health test;
- page navigation smoke test;
- empty-data test;
- backend-offline test;
- live-demo test;
- filter interaction test;
- responsive layout test;
- accessibility review.

### Release gates

The v2 release should require:

```text
Python tests: 100% pass
Android build: pass
Android lint: zero errors
Dashboard health: HTTP 200
API contract tests: pass
Device smoke test: pass
No secrets committed
Privacy review: complete
```

---

## 11. Deployment and reproducibility

Add:

- checked-in Gradle wrapper;
- locked Python dependencies;
- reproducible Docker builds;
- health checks;
- database migrations;
- CI workflow;
- environment validation;
- release artifact checksums;
- model artifact checksums;
- documented rollback procedure.

The dashboard and backend must use one canonical data/model directory layout.

---

## 12. Implementation phases

### Phase 1 — Visual foundation

- custom theme;
- local logo;
- command-center overview;
- risk hero card;
- status strip;
- active alerts;
- consistent colors and spacing.

### Phase 2 — Live experience

- automatic refresh;
- live map;
- provider health;
- simulated demo controls;
- degraded-mode indicators;
- dashboard API integration.

### Phase 3 — User safety

- Android monitoring redesign;
- offline mode;
- trip summary;
- event history;
- crash confirmation workflow;
- emergency-contact controls.

### Phase 4 — ML and backend maturity

- calibrated score;
- explainable factors;
- model registry;
- provider freshness;
- API authentication;
- rate limiting;
- observability.

### Phase 5 — Production release

- physical-device testing;
- emulator matrix;
- CI/CD;
- PostgreSQL/PostGIS;
- backups;
- privacy audit;
- security review;
- v2 release candidate.

---

## 13. Recommended v2 dashboard pages

```text
1. Command Center
   Live risk, map, alerts, provider/device status

2. Live Demo
   Safe simulated scenarios and response timeline

3. Accident Map
   Filterable accidents, hotspots, route overlays

4. Trends
   Hour, day, month, weather, road type, severity

5. Risk Analysis
   Hotspot ranking, risk distribution, explanations

6. Model Evaluation
   Metrics, calibration, feature schema, model version

7. Trips
   Trip history, route, warnings, safety score

8. Safety Events
   Overspeed, crash-suspected, weather, provider failures

9. System Health
   API, database, providers, model, latency, errors

10. Settings
    API mode, refresh interval, privacy, demo mode
```

---

## 14. Final v2 product direction

SafeGuard v2.0 should feel like:

> A trusted, real-time road-safety command center that explains risk clearly,
> warns drivers quickly, works during network failures, and protects personal
> location data.

The highest-value sequence is:

1. redesign the dashboard visually;
2. add a live risk command center;
3. expose provider/model freshness;
4. add offline mobile protection;
5. complete crash confirmation;
6. add trip and event history;
7. improve ML calibration and explanations;
8. add security, privacy, observability, and release automation.

