# SafeGuard Demo Scenarios

Six test scenarios for the v1.0.0-hackathon demo.

---

## Scenario A — Normal Drive

**Conditions:** Clear weather, normal speed, no hotspot.

```json
POST /api/v1/predict-risk
{
  "latitude": 17.3850,
  "longitude": 78.4867,
  "speed_kmh": 40,
  "speed_limit_kmh": 60,
  "traffic_level": "low",
  "weather": "clear",
  "timestamp": "2026-09-21T09:00:00+05:30",
  "device_id": "demo-device"
}
```

**Expected:** `risk_level: LOW`, no alert.

---

## Scenario B — Overspeed

**Conditions:** Clear weather, speed 95 km/h in 50 km/h zone.

```json
{
  "latitude": 17.3850,
  "longitude": 78.4867,
  "speed_kmh": 95,
  "speed_limit_kmh": 50,
  "traffic_level": "moderate",
  "weather": "clear",
  "timestamp": "2026-09-21T10:30:00+05:30",
  "device_id": "demo-device"
}
```

**Expected:** `risk_level: HIGH`, overspeed reason, voice alert.

---

## Scenario C — Hotspot Approach

**Conditions:** Within 200m of a HIGH-risk hotspot at moderate speed.

```json
{
  "latitude": 17.3905,
  "longitude": 78.4952,
  "speed_kmh": 55,
  "speed_limit_kmh": 60,
  "traffic_level": "moderate",
  "weather": "cloudy",
  "timestamp": "2026-09-21T14:00:00+05:30",
  "device_id": "demo-device"
}
```

**Expected:** `hotspot: true`, `risk_level: MODERATE/HIGH`, hotspot notification.

---

## Scenario D — Heavy Traffic

**Conditions:** Heavy traffic, rain, low speed but high environment risk.

```json
{
  "latitude": 17.3850,
  "longitude": 78.4867,
  "speed_kmh": 28,
  "speed_limit_kmh": 50,
  "traffic_level": "heavy",
  "weather": "rain",
  "timestamp": "2026-09-21T18:30:00+05:30",
  "device_id": "demo-device"
}
```

**Expected:** `risk_level: MODERATE`, traffic + weather reasons.

---

## Scenario E — Combined High Risk (Rain + Overspeed + Hotspot)

**Conditions:** Rain, speed 85 km/h in 50 km/h zone, near hotspot, heavy traffic.

```json
{
  "latitude": 17.3905,
  "longitude": 78.4952,
  "speed_kmh": 85,
  "speed_limit_kmh": 50,
  "traffic_level": "heavy",
  "weather": "rain",
  "timestamp": "2026-09-21T20:00:00+05:30",
  "device_id": "demo-device"
}
```

**Expected:** `risk_level: CRITICAL`, multiple reasons, voice + vibration alert.

---

## Scenario F — Simulated Crash Event

**Trigger:** POST /api/v1/events/crash-suspected

```json
{
  "device_id": "demo-device",
  "timestamp": "2026-09-21T20:05:00+05:30",
  "latitude": 17.3905,
  "longitude": 78.4952,
  "acceleration_g": 4.2,
  "confidence": 0.85
}
```

**Expected:** `next_action: SHOW_CONFIRMATION_DIALOG`, 10-second user countdown in app.

---

## Demo Checklist

- [ ] Backend running and healthy (`GET /api/v1/health`)
- [ ] Dashboard loaded with accident data
- [ ] Android app running on emulator
- [ ] Location permission granted
- [ ] Monitoring started
- [ ] Scenario A — no alert shown
- [ ] Scenario B — overspeed voice alert fires
- [ ] Scenario C — hotspot notification shown
- [ ] Scenario D — moderate risk notification
- [ ] Scenario E — CRITICAL alert with all reasons
- [ ] Scenario F — crash workflow shown in app
