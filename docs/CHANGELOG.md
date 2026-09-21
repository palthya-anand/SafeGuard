# Changelog — Smart Road Safety

All notable project changes are documented here.

Versioning follows a simple semantic-style scheme:

- **MAJOR** — major architecture/product change
- **MINOR** — new feature/module
- **PATCH** — fixes, performance, UI, documentation, or compatibility updates

---

## [1.0.0-hackathon] — Planned Release

### Added
- End-to-end software-first road-safety platform.
- Android phone used as the live sensing client.
- GPS-based location and speed monitoring.
- Local overspeed warning.
- Historical accident analytics.
- Accident hotspot detection.
- Machine-learning risk classification.
- FastAPI inference backend.
- Traffic integration through a provider adapter.
- Weather integration through a provider adapter.
- Android notifications.
- Voice warnings using Text-to-Speech.
- Streamlit analytics dashboard.
- Versioned model artifact and metadata.
- End-to-end hackathon demo scenarios.

### Target stack
- Python 3.13.15
- Kotlin 2.4.20
- Android API 36
- Android Studio Quail 4 2026.1.4 Patch 1
- AGP 9.4.0
- Gradle 9.6.0
- JDK 17

---

## [0.9.0] — Integration Candidate

### Added
- Phone → FastAPI telemetry flow.
- `/predict-risk` end-to-end integration.
- Risk score shown in Android app.
- Risk reasons returned by backend.
- Traffic and weather context included in inference request.
- Dashboard live-demo mode.

### Changed
- Added alert cooldown/state management.
- Added provider failure fallbacks.

---

## [0.8.0] — Alerts & Voice

### Added
- Notification channels.
- Overspeed notification.
- Accident-hotspot notification.
- High-risk notification.
- Text-to-Speech driver warnings.
- Notification cooldown and risk-transition logic.
- Android 13+ notification permission handling.

### Compatibility
- Android notification design aligned with current runtime permission behavior.

---

## [0.7.0] — Traffic & Weather

### Added
- Traffic provider adapter.
- Weather provider adapter.
- Normalized traffic categories: `normal`, `moderate`, `heavy`, `unknown`.
- Normalized weather categories.
- Traffic/weather features added to the ML inference schema.

### Changed
- Risk explanation now includes contextual factors when available.

---

## [0.6.0] — Android Live Monitoring

### Added
- Kotlin Android app.
- Location permission flow.
- Live GPS position.
- Live speed display.
- User-controlled monitoring start/stop.
- Location foreground service.
- Local overspeed detection.
- Driver-facing status screen.

### Notes
- Continuous location tracking is user-visible and permission-based.
- Foreground-service configuration follows current Android location-service requirements.

---

## [0.5.0] — FastAPI Backend

### Added
- FastAPI application.
- Health endpoint.
- Risk prediction endpoint.
- Hotspot lookup endpoint.
- Pydantic request/response schemas.
- Model inference service.
- Database abstraction.

### Changed
- ML inference separated from notebooks.

---

## [0.4.0] — ML Risk Engine

### Added
- Feature engineering pipeline.
- Logistic Regression baseline.
- Random Forest main model.
- Optional XGBoost comparison.
- Precision/recall/F1 evaluation.
- Confusion matrix.
- Model serialization with joblib.
- Model metadata file.

### Important
- Risk is defined as a classification/estimate based on the selected historical-data target definition.

---

## [0.3.0] — Accident Analytics & Hotspots

### Added
- EDA notebook.
- Accident counts by time.
- Accident severity analysis.
- Weather/road-condition analysis where fields exist.
- Geographic accident visualization.
- DBSCAN-based hotspot discovery.
- Hotspot dataset export.

---

## [0.2.0] — Data Pipeline

### Added
- Raw-data ingestion.
- CSV schema validation.
- Missing-value handling.
- Duplicate removal.
- Coordinate validation.
- Date/time normalization.
- Processed dataset generation.

### Data policy
- Raw datasets are kept unchanged.
- Derived datasets are stored separately.

---

## [0.1.0] — Project Initialization

### Added
- Project name and problem statement.
- Initial requirements.
- Software-first architecture.
- Android + Python technology direction.
- Repository structure.
- Initial documentation.
- Initial hackathon scope.

### Initial scope
The original concept was a software accident detector focused on:

- overspeed warning;
- accident-prone area warning;
- accident-related data analysis.

The design was subsequently expanded into a predictive road-risk platform.

---

## Development history at a glance

```text
v0.1.0  Concept
   ↓
v0.2.0  Data pipeline
   ↓
v0.3.0  EDA + hotspots
   ↓
v0.4.0  ML model
   ↓
v0.5.0  FastAPI
   ↓
v0.6.0  Android GPS/speed
   ↓
v0.7.0  Traffic + weather
   ↓
v0.8.0  Notifications + voice
   ↓
v0.9.0  Full integration
   ↓
v1.0.0  Hackathon release
   ↓
v1.1.x  Crash + emergency features
   ↓
v2.0.0  Production-oriented expansion
```

---

## [1.1.0] — Planned Advanced Safety Module

### Planned
- Accelerometer + gyroscope crash-suspicion detection.
- Multi-sensor event validation.
- User confirmation countdown.
- Emergency-contact workflow.
- Incident-event storage.
- Improved false-positive suppression.

---

## [1.2.0] — Planned Route Intelligence

### Planned
- Safe-route recommendation.
- Route-level accident-risk aggregation.
- Estimated risk along route.
- Alternative-route comparison without ranking providers.

---

## [2.0.0] — Planned Production Architecture

### Planned
- PostgreSQL/PostGIS.
- Scalable API deployment.
- Authentication and device management.
- Model registry.
- Automated model retraining pipeline.
- CI/CD.
- Monitoring and observability.
- Stronger privacy controls.
- Offline-aware mobile operation.
- Multiple traffic/weather provider implementations.

---

## Unreleased / next work

### Data Science
- Finalize accident dataset source and license.
- Define and document the target-label generation rule.
- Evaluate class imbalance.
- Perform leakage checks.
- Calibrate probability outputs if probabilities are exposed.

### Mobile
- Finish monitoring service.
- Add notification channels.
- Add voice alerts.
- Add crash-sensor prototype.

### Backend
- Complete provider adapters.
- Add integration tests.
- Add authentication and rate limiting before any public deployment.
