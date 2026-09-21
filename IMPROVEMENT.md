# SafeGuard Improvement Roadmap

## 1. Purpose

This document records the recommended improvements and future features for
SafeGuard. It is intended to guide the project from the current
`v1.0.0-hackathon` prototype toward a reliable, privacy-aware, production-ready
road-safety platform.

The current system already includes:

- Android GPS and speed monitoring;
- local overspeed warnings;
- FastAPI risk prediction;
- accident-data preprocessing;
- hotspot analysis;
- machine-learning risk classification;
- traffic and weather provider adapters;
- notifications and voice-alert support;
- Streamlit analytics dashboard;
- telemetry and crash-suspected event endpoints.

No risk score should be presented as a guaranteed accident prediction. It should
always be described as an estimate based on available data and conditions.

---

## 2. Priority summary

| Priority | Area | Objective |
|---|---|---|
| P0 | Release validation | Prove that the existing MVP works reproducibly |
| P0 | Data and model correctness | Make labels, metrics, and model artifacts trustworthy |
| P0 | Path and documentation consistency | Ensure the dashboard and services use the same files |
| P1 | Reliability | Continue basic safety behavior during network/provider failures |
| P1 | Privacy and security | Protect location, device, and crash-event data |
| P1 | Mobile safety | Complete crash confirmation and improve alert behavior |
| P1 | ML quality | Improve calibration, leakage prevention, and explainability |
| P2 | User features | Add trip summaries, history, personalization, and maps |
| P2 | Route intelligence | Recommend safer routes using risk-aware aggregation |
| P3 | Production architecture | Scale storage, deployment, monitoring, and retraining |

---

## 3. P0 release validation

These tasks should be completed before declaring `v1.0.0-hackathon` final.

### 3.1 Release status

- Define whether the current release is planned, release-candidate, or final.
- Use an explicit progression such as:
  - `v1.0.0-hackathon-planned`
  - `v1.0.0-rc.1`
  - `v1.0.0-hackathon`
- Tag the final release only after acceptance criteria pass.
- Record the exact source revision used for the build.

### 3.2 End-to-end acceptance testing

Verify the complete flow:

```text
Android GPS
  -> risk request
  -> FastAPI validation
  -> traffic/weather context
  -> model inference
  -> risk response
  -> Android alert
```

Acceptance tests should cover:

- valid low-risk request;
- overspeed request;
- hotspot request;
- high-risk weather and traffic;
- invalid coordinates;
- missing required fields;
- unavailable backend;
- unavailable traffic provider;
- unavailable weather provider;
- stale or mock provider data;
- notification permission denied;
- location permission denied;
- repeated alerts during cooldown;
- monitoring start and stop;
- Android app restart while monitoring;
- dashboard startup from a clean checkout.

### 3.3 Build and environment verification

Confirm that:

- Python version is documented and reproducible;
- Python dependencies are locked;
- Android Gradle wrapper is committed;
- Kotlin, AGP, Gradle, Android SDK, and JDK versions match the build record;
- Docker services start successfully;
- `.env.example` contains every required configuration key;
- no secret is stored in the repository.

---

## 4. P0 path and artifact consistency

The project should use one authoritative location for data and model artifacts.
Current documentation and dashboard paths must be checked against the actual
directory structure.

### 4.1 Standardize paths

Choose and document one layout, for example:

```text
data/
├── raw/
├── processed/
└── app.db

models/
├── accident_risk_model.joblib
├── preprocessor.joblib
└── model_metadata.json
```

Then update all scripts, dashboard code, Docker configuration, and
documentation to use the same layout.

### 4.2 Verify model artifacts

Before release:

- confirm the model files exist;
- load them in a clean environment;
- verify the preprocessor and model feature order;
- test one known prediction;
- verify the model version in metadata;
- verify the training dataset version;
- verify the metadata metrics match the evaluation output;
- verify the backend reports the correct model version.

### 4.3 Add complete build metadata

The build record should include, where available:

```json
{
  "application_version": "1.0.0-hackathon",
  "model_version": "risk-model-0.4.0",
  "dataset_version": "accidents-2026-09-01",
  "schema_version": "1.0",
  "api_version": "v1",
  "git_commit": "commit-sha",
  "provider_mode": "mock",
  "build_date": "2026-09-21"
}
```

---

## 5. P0 data-science improvements

### 5.1 Define the target label

Document exactly:

- what counts as a positive risk sample;
- whether labels represent an accident, severity, hotspot proximity, or a
  composite condition;
- the prediction time window;
- how negative samples are selected;
- how distance to an accident or hotspot is calculated;
- how missing labels are handled;
- whether class weights or resampling are used.

### 5.2 Prevent data leakage

Check that:

- future accident information is not included in current-time features;
- hotspot calculations do not use the test set;
- duplicate or near-duplicate locations do not cross train/test boundaries;
- preprocessing is fitted only on training data;
- target-derived columns are excluded from inference features;
- temporal ordering is respected where appropriate.

Use and compare:

- temporal train/test split;
- geographic or region-based split;
- grouped cross-validation;
- standard random split only as a baseline.

### 5.3 Improve model evaluation

Report:

- precision;
- recall;
- F1 score;
- ROC-AUC where meaningful;
- PR-AUC for imbalanced data;
- confusion matrix;
- class distribution;
- false-positive rate;
- false-negative rate;
- evaluation dataset version;
- train/test split strategy.

For a safety application, recall for dangerous conditions should be reported
alongside the alert burden caused by false positives.

### 5.4 Calibrate risk scores

Clearly define whether `risk_score` is:

- a calibrated probability;
- a model probability scaled to 0–100;
- a heuristic composite score;
- a weighted risk index.

If probabilities are exposed, evaluate:

- calibration curve;
- Brier score;
- reliability diagram;
- threshold-specific performance.

### 5.5 Add model explainability

Return concise, evidence-based reasons such as:

- current speed exceeds the speed limit;
- location is near a known hotspot;
- visibility is low;
- weather is rainy;
- traffic is heavy;
- the risk is elevated during this time period.

The explanation must reflect actual features used by the model and must not
claim unsupported causes.

### 5.6 Add data-quality reporting

Generate a report containing:

- row counts before and after cleaning;
- missing-value counts;
- duplicate counts;
- invalid-coordinate counts;
- outlier speeds;
- date coverage;
- unknown categories;
- severity distribution;
- geographic coverage;
- source and license information.

---

## 6. P1 backend and reliability improvements

### 6.1 Make provider state visible

Risk responses or health information should indicate:

- traffic source;
- weather source;
- live, cached, mock, fallback, or unavailable status;
- timestamp or age of provider data;
- model version.

Users should not be given an apparently live result when mock data was used.

### 6.2 Improve failure handling

Add:

- explicit request timeouts;
- bounded retries;
- exponential backoff;
- circuit breaking for repeatedly failing providers;
- clear degraded-mode responses;
- structured provider error metrics;
- response freshness checks.

Avoid silently converting every failure into a normal-looking success result.

### 6.3 Add API protection

Before any public deployment, add:

- authentication or device registration;
- rate limiting;
- request-size limits;
- API versioning;
- HTTPS enforcement;
- input validation for all event endpoints;
- abuse detection;
- request correlation IDs.

### 6.4 Add observability

Log or measure:

- request ID;
- endpoint;
- response time;
- status code;
- model version;
- provider status;
- fallback count;
- prediction latency;
- error category.

Do not log exact location history or device identifiers by default.

### 6.5 Add database reliability

For the MVP:

- use a clear database schema version;
- add indexes for timestamp, device, and geographic queries;
- separate test and production databases;
- provide migration scripts;
- validate stored event data.

For production:

- migrate to PostgreSQL/PostGIS;
- add backups;
- define retention and deletion jobs;
- test restore procedures.

---

## 7. P1 Android and safety improvements

### 7.1 Offline-first safety mode

The Android app should continue basic safety behavior when the backend or
external providers are unavailable.

Offline mode can use:

- local overspeed checks;
- cached speed-limit information;
- cached hotspot data;
- the last known validated model;
- locally stored alert thresholds.

The app should clearly display that it is operating offline or with stale data.

### 7.2 Complete crash confirmation workflow

Implement:

1. accelerometer-based impact suspicion;
2. gyroscope or orientation validation;
3. vehicle-stop or inactivity verification;
4. false-positive suppression;
5. loud local alarm;
6. 15–30 second countdown;
7. user cancellation;
8. emergency-contact notification after timeout;
9. retry queue for failed delivery;
10. local incident history.

The crash feature should never contact emergency services automatically without
clear user consent and an explicitly documented workflow.

### 7.3 Improve location and speed quality

Add:

- GPS accuracy threshold;
- stale-location detection;
- speed smoothing;
- invalid speed rejection;
- stationary detection;
- GPS loss handling;
- configurable location update interval;
- battery-aware monitoring mode.

### 7.4 Improve alert behavior

Add:

- alert severity prioritization;
- separate channels for informational and urgent alerts;
- configurable alert cooldown;
- risk-transition logic;
- repeat-alert limit;
- voice-alert queue;
- quiet driving mode;
- multilingual text-to-speech support later.

### 7.5 Improve mobile privacy controls

Provide controls for:

- monitoring start and stop;
- telemetry sharing;
- crash-event sharing;
- location history deletion;
- emergency contacts;
- notification and voice preferences;
- data-retention explanation.

---

## 8. P1 privacy and security

Define and document:

- user consent for location collection;
- purpose of each collected field;
- device-ID pseudonymization or hashing;
- retention period for telemetry;
- retention period for crash events;
- deletion and export mechanisms;
- dashboard access control;
- encryption in transit;
- encryption at rest where appropriate;
- secret storage policy;
- privacy-safe logging;
- incident response procedure.

Do not expose raw device identifiers or exact GPS history in dashboard URLs,
logs, screenshots, or demonstration materials.

---

## 9. P1 testing strategy

### Backend tests

Add tests for:

- provider success;
- provider timeout;
- provider fallback;
- stale provider responses;
- client-provided traffic/weather precedence;
- timestamp and timezone handling;
- model-not-loaded state;
- malformed event payloads;
- rate-limit behavior;
- authentication failures;
- database failure behavior.

### Data-science tests

Add tests for:

- required-column validation;
- coordinate validation;
- datetime parsing;
- duplicate removal;
- missing-value handling;
- category normalization;
- feature-schema stability;
- reproducible preprocessing;
- no target leakage;
- model artifact loading.

### Android tests

Add tests for:

- permission handling;
- monitoring start and stop;
- location accuracy filtering;
- speed conversion;
- overspeed threshold;
- cooldown behavior;
- notification permission;
- service restart;
- backend timeout;
- offline mode.

### Integration tests

Verify:

- Android payload matches the backend schema;
- backend response matches Android models;
- model version is propagated;
- provider status is preserved;
- dashboard can read generated artifacts;
- Docker deployment works from a clean checkout.

---

## 10. P2 user-facing features

### 10.1 Trip summary

Show after every trip:

- distance;
- duration;
- maximum speed;
- overspeed duration;
- number of warnings;
- high-risk-zone count;
- harsh braking events;
- weather exposure;
- overall trip safety summary.

### 10.2 Risk history

Provide a history of:

- previous trips;
- risk-level timeline;
- warning locations;
- weather and traffic conditions;
- user-dismissed alerts;
- crash-suspected events.

### 10.3 Personalized settings

Allow configuration of:

- speed-warning margin;
- risk sensitivity;
- notification sound;
- voice-alert language;
- voice volume;
- quiet hours;
- emergency contacts;
- telemetry consent.

### 10.4 Live map

Display:

- current location;
- current speed;
- nearby hotspots;
- current risk level;
- speed limit;
- weather condition;
- traffic level;
- route direction;
- recent alerts.

### 10.5 Driver behavior insights

Potential future indicators:

- harsh acceleration;
- harsh braking;
- sudden swerving;
- repeated overspeeding;
- long driving duration;
- fatigue-risk indicators.

These features require careful testing to avoid unreliable or distracting alerts.

---

## 11. P2 route intelligence

For `v1.2.0`, implement route-level risk analysis.

### Route features

- accident-risk aggregation;
- hotspot exposure;
- expected travel time;
- traffic delay;
- weather exposure;
- number of high-risk segments;
- confidence level;
- alternative-route comparison.

### User-facing explanation

Instead of only ranking routes, explain:

```text
Route A is estimated to be safer because it passes through fewer high-risk
segments and has lower hotspot exposure, although it may take 8 minutes longer.
```

Avoid presenting a route as guaranteed safe.

---

## 12. P3 production architecture

For `v2.0.0`, consider:

- PostgreSQL/PostGIS;
- authenticated users and device management;
- role-based dashboard access;
- database migrations;
- scalable API deployment;
- container health checks;
- CI/CD pipelines;
- model registry;
- model rollback;
- automated retraining;
- dataset and model lineage;
- drift detection;
- centralized logging;
- metrics and tracing;
- backup and disaster recovery;
- multiple traffic providers;
- multiple weather providers;
- regional timezone support;
- stronger privacy controls.

---

## 13. Documentation improvements

Keep the following documents synchronized:

- `README.md`;
- `PROJECT_VERSIONING.md`;
- `TECH_STACK_SPECIFICATION.md`;
- `IMPLEMENTATION_PLAN.md`;
- `CHANGELOG.md`;
- this improvement roadmap.

Documentation should include:

- one canonical setup procedure;
- one canonical directory structure;
- exact commands for preprocessing;
- exact commands for model training;
- exact commands for running the backend;
- exact commands for running the dashboard;
- Android build and installation steps;
- API examples;
- provider configuration;
- mock-mode behavior;
- privacy limitations;
- known limitations;
- release acceptance status.

---

## 14. Recommended implementation order

### Milestone 1 — Stabilize v1.0

- standardize paths;
- verify model artifacts;
- define target labels;
- check leakage;
- run all tests;
- validate Android/backend integration;
- validate dashboard;
- document release acceptance;
- finalize build metadata.

### Milestone 2 — Improve reliability

- offline mode;
- provider-status reporting;
- retries and timeouts;
- stale-data warnings;
- structured logging;
- database validation;
- API rate limiting.

### Milestone 3 — Improve safety

- crash detection prototype;
- confirmation countdown;
- emergency contacts;
- sensor validation;
- alert prioritization;
- GPS quality handling.

### Milestone 4 — Improve intelligence

- calibrated risk scores;
- explainable predictions;
- trip history;
- safety summaries;
- route-risk comparison.

### Milestone 5 — Production readiness

- PostgreSQL/PostGIS;
- authentication;
- CI/CD;
- observability;
- model registry;
- automated retraining;
- privacy and retention enforcement.

---

## 15. Definition of success

SafeGuard should be considered ready for a verified hackathon release when:

- the complete system runs from a clean checkout;
- the dashboard loads the same data and model artifacts used by the backend;
- the model label and evaluation method are documented;
- leakage checks are completed;
- Android warnings work without requiring a backend round trip for overspeed;
- provider failures are visible and safe;
- all critical tests pass;
- privacy behavior is documented;
- limitations are clearly shown to users and evaluators;
- the release metadata identifies the application, model, dataset, schema, API,
  provider mode, and build revision.

