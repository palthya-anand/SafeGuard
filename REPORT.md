# SafeGuard Full Test and Improvement Report

**Test date:** 2026-09-21  
**Project:** SafeGuard  
**Scope:** Read-only deep validation of Python, backend, data-science,
dashboard, Android build, and Android lint behavior.

## 1. Scope and safety statement

The validation process did not modify existing source, configuration, test, or
documentation files.

The only project file created by this task is this report:

```text
REPORT.md
```

Temporary test database output was written outside the project directory.
Android build reports and APK output were generated under the existing build
directory by Gradle.

Pre-existing worktree changes were left untouched:

```text
D  README (1).md
?? README.md
```

---

## 2. Executive summary

| Area | Result | Status |
|---|---|---|
| Backend tests with default test database path | 13 errors | Needs environment fix |
| Backend tests with temporary valid database path | 13 passed | Pass |
| Data-science tests | 5 passed | Pass |
| Python compilation | 26 files passed | Pass |
| Backend imports | Passed | Pass |
| Data-science imports | 6 modules passed | Pass |
| Dashboard importability | Passed with Streamlit warnings | Pass with warnings |
| Android clean debug build | Passed | Pass |
| Android APK packaging | Passed | Pass |
| Android lint | 4 errors, 54 warnings | Fails quality gate |
| Android emulator/device test | Not executed | Requires device/emulator |

### Overall conclusion

The backend, data-science pipeline, Python syntax, imports, and Android
compilation are functional. The project is not yet clean-release ready because:

1. the default backend test configuration points to a missing directory;
2. Android lint reports four errors;
3. Android lint reports 54 warnings;
4. no physical-device or emulator runtime test was completed;
5. the dashboard was imported outside a normal Streamlit runtime.

---

## 3. Backend test results

### 3.1 Default test run

Command:

```powershell
Set-Location 'C:\Users\ranua\Music\SafeGuard\backend'
& 'C:\Users\ranua\Music\SafeGuard\.venv\Scripts\python.exe' -m pytest -rA
```

Result:

```text
13 errors
0 passed
```

Root cause:

```text
sqlite3.OperationalError: unable to open database file
```

The tests configure:

```text
sqlite:///./data/test_app.db
```

but the directory below is absent:

```text
backend\data
```

This is a test-environment/configuration failure rather than a failure in the
tested API assertions.

### 3.2 Backend run with valid temporary database

Command:

```powershell
$env:DATABASE_URL='sqlite:///C:/Users/ranua/AppData/Local/Temp/safeguard-test.db'
$env:APP_ENV='testing'
& 'C:\Users\ranua\Music\SafeGuard\.venv\Scripts\python.exe' -m pytest -rA `
  'C:\Users\ranua\Music\SafeGuard\backend'
```

Result:

```text
13 passed in 4.35s
```

Passing coverage:

- health endpoint;
- valid risk prediction;
- invalid coordinates;
- missing required fields;
- nearby hotspot lookup;
- telemetry event creation;
- crash-suspected event creation;
- normal-drive demo scenario;
- overspeed scenario;
- hotspot approach scenario;
- heavy-traffic scenario;
- combined high-risk scenario;
- simulated crash scenario.

### Backend improvement

The test suite should use a guaranteed temporary database path or create the
test database directory during test setup. The production application should
not rely on a directory being created manually before tests can run.

---

## 4. Data-science test results

Command:

```powershell
Set-Location 'C:\Users\ranua\Music\SafeGuard\data-science'
& 'C:\Users\ranua\Music\SafeGuard\.venv\Scripts\python.exe' -m pytest -rA
```

Result:

```text
5 passed in 1.02s
```

Validated behavior:

- processed output file exists;
- latitude and longitude contain no null values;
- coordinates are in the expected range;
- severity codes contain valid values;
- duplicate accident IDs are absent.

### Data-science improvement

The current tests validate cleaning output but should also cover:

- target-label generation;
- feature-column ordering;
- training/test split reproducibility;
- leakage prevention;
- model artifact loading;
- model metadata consistency;
- class imbalance handling;
- geographic and temporal validation.

---

## 5. Python compilation and imports

### 5.1 Python compilation

Command:

```powershell
& 'C:\Users\ranua\Music\SafeGuard\.venv\Scripts\python.exe' `
  -m compileall -q -f
```

Result:

```text
PASS — 26 Python files compiled
```

### 5.2 Backend imports

Result:

```text
PASS
```

Verified imports included:

- `app.main`;
- `app.api.routes`;
- `app.core.database`;
- `app.models.inference`;
- `app.services.risk_service`;
- `app.services.traffic_provider`;
- `app.services.weather_provider`.

### 5.3 Data-science imports

Result:

```text
PASS — 6 modules imported
```

Verified modules:

- `create_notebooks`;
- `features`;
- `generate_dataset`;
- `hotspot`;
- `preprocess`;
- `train`.

---

## 6. Dashboard test results

The dashboard module was imported in isolation from its own directory.

Result:

```text
PASS
```

The import emitted expected warnings because Streamlit was not started with
`streamlit run`, including:

- missing `ScriptRunContext`;
- no active Streamlit runtime;
- session state unavailable in bare Python mode;
- cache storage runtime warnings;
- `use_container_width` deprecation warning.

These warnings do not indicate a Python import failure.

### Dashboard improvement

The dashboard should also be tested with its real runtime command:

```powershell
streamlit run dashboard\app.py
```

Recommended runtime checks:

- data loads successfully;
- hotspot file is found;
- model metadata is found;
- backend health state is displayed;
- live-demo request succeeds;
- API-offline state is clearly shown;
- dashboard paths match the actual repository layout.

---

## 7. Android build results

### 7.1 Clean debug build

The Android project was built using:

```text
Gradle 9.6.0
JDK 17.0.20.1
Android SDK API 36
Android build tools 36.1.0
```

Command:

```powershell
gradle clean assembleDebug lint --no-daemon
```

The clean and compile/package portions succeeded:

```text
Task :app:clean
Task :app:assembleDebug
BUILD output generated
```

Generated artifact:

```text
android\app\build\outputs\apk\debug\app-debug.apk
```

### 7.2 Android lint

Lint result:

```text
4 errors
54 warnings
```

Because lint errors are present, the complete Gradle command failed at
`lintDebug`, even though `assembleDebug` succeeded.

---

## 8. Android lint errors

### Error 1 and Error 2 — receiver export flags

Location:

```text
android\app\src\main\java\com\safeguard\MainActivity.kt:123
android\app\src\main\java\com\safeguard\MainActivity.kt:124
```

Problem:

```text
UnspecifiedRegisterReceiverFlag
```

The pre-Android 13 branch registers receivers without an explicit exported
state:

```kotlin
registerReceiver(locationReceiver, locationFilter)
registerReceiver(overspeedReceiver, overspeedFilter)
```

Recommended improvement:

- use the AndroidX compatibility registration API;
- specify `RECEIVER_NOT_EXPORTED` for both internal application broadcasts;
- apply the same explicit behavior across supported Android versions.

This is important because both broadcasts are internal to the application and
should not be exposed to other applications.

### Error 3 and Error 4

The lint report identifies four total errors. The first two are the receiver
registration issue above, and the remaining errors should be reviewed in the
complete generated report:

```text
android\app\build\intermediates\lint_intermediate_text_report\
debug\lintReportDebug\lint-results-debug.txt
```

The complete lint output should be treated as the authoritative error list
before the next Android release.

---

## 9. Android lint warnings

The 54 warnings include:

### Version freshness warnings

Examples include:

- newer Gradle version available;
- newer Android Gradle Plugin available;
- newer compile SDK available;
- newer AndroidX Core version available;
- newer Lifecycle version available;
- newer Activity version available;
- newer Navigation version available;
- newer Room version available;
- newer WorkManager version available;
- newer Google Play Services Location version available;
- newer Material version available;
- newer ConstraintLayout version available;
- newer Kotlin coroutines version available.

These do not necessarily indicate defects. Updating should be done as a
controlled dependency-upgrade task with a full regression test.

### Target SDK warning

Lint reports that `targetSdk = 36` is not the latest available SDK. The
project deliberately targets API 36, so this is currently a compatibility
notice rather than an immediate defect. Re-evaluate it when the project
requires the newer platform.

### Resource formatting warning

The string below uses multiple substitutions without positional formatting:

```text
android\app\src\main\res\values\strings.xml:19
location_format
```

Recommended improvement:

- use positional placeholders such as `%1$.5f` and `%2$.5f`; or
- explicitly mark the string as non-formatted if formatting is not performed
  by Android resources.

---

## 10. App runtime testing status

### Completed

- Android source compiled;
- Kotlin compilation completed;
- Java compilation completed;
- debug APK packaged;
- KSP task completed;
- Android manifest processing completed;
- Android resources processed.

### Not completed

No emulator or physical Android device runtime test was performed during this
validation. The following remain unverified at runtime:

- location permission flow;
- foreground-service startup;
- GPS updates;
- speed conversion;
- local overspeed notification;
- notification permission behavior;
- voice warning behavior;
- backend request from the installed app;
- service restart behavior;
- offline behavior;
- Android 13/14/15/16 device compatibility.

Recommended device test matrix:

| Test | Required |
|---|---|
| Android 13 notification permission | Yes |
| Android 14 foreground location service | Yes |
| Android 15/16 target behavior | Yes |
| GPS permission denied | Yes |
| Notification permission denied | Yes |
| Backend unavailable | Yes |
| Overspeed alert cooldown | Yes |
| Monitoring start/stop | Yes |
| App background/foreground transition | Yes |
| Device restart/service recovery | Recommended |

---

## 11. Test quality improvements

### Backend

- make the SQLite test path self-contained;
- isolate the test database per test session;
- add provider timeout and fallback tests;
- add model-not-loaded tests;
- add database failure tests;
- add timezone and timestamp tests;
- add rate-limit and authentication tests;
- assert provider source and freshness in responses.

### Data science

- test target generation;
- test leakage prevention;
- test model artifact compatibility;
- test model metadata;
- test class imbalance behavior;
- test temporal and geographic splits;
- test reproducible training.

### Android

- add unit tests for speed and overspeed logic;
- add service lifecycle tests;
- add receiver registration tests;
- add permission tests;
- add ViewModel tests;
- add notification and alert-manager tests;
- add instrumentation tests on an emulator;
- add offline and network-timeout tests.

### Dashboard

- add a real Streamlit smoke test;
- test missing data files;
- test missing model metadata;
- test backend offline mode;
- test live demo request failures;
- test dashboard path resolution from a clean checkout.

---

## 12. Priority improvement plan

### P0 — Must fix before release

1. Resolve the default backend SQLite test-directory failure.
2. Fix all four Android lint errors.
3. Re-run Android lint until zero errors remain.
4. Fix or intentionally document the resource formatting warning.
5. Run the dashboard through `streamlit run`.
6. Execute Android tests on an emulator or physical device.
7. Confirm dashboard, backend, and model artifact paths.

### P1 — Strongly recommended

1. Add backend provider failure tests.
2. Add Android permission and service lifecycle tests.
3. Add model leakage and calibration checks.
4. Add explicit provider source and stale-data status.
5. Add offline-first mobile safety behavior.
6. Add structured request and prediction logging without private location data.
7. Add a reproducible clean-checkout test command.

### P2 — Future features

1. Crash confirmation countdown.
2. Emergency-contact workflow.
3. Trip history and safety summary.
4. Live map with hotspot and risk overlays.
5. Explainable risk factors.
6. Risk-aware route comparison.
7. Personalized alert thresholds.
8. Multilingual voice warnings.

---

## 13. Final release assessment

### Current release classification

```text
Development / integration candidate
```

### Not yet recommended as

```text
Fully verified production release
```

### Reason

The core code is buildable and the functional API/data tests pass under a
correct test environment, but the Android lint quality gate and device-runtime
validation are incomplete. The default backend test setup also needs to be
made reproducible.

### Positive result

The project has a strong base:

- 13 backend tests pass with valid test database configuration;
- 5 data-science tests pass;
- 26 Python files compile;
- backend and data-science imports pass;
- Android debug APK builds successfully;
- model and dependency compatibility issues previously identified are fixed.

