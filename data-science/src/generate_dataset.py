"""
generate_dataset.py
-------------------
Generates a realistic synthetic Indian road accident dataset and saves it to
data/raw/accidents_raw.csv (relative to the project root).

Run from the SafeGuard project root:
    python data-science/src/generate_dataset.py
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RNG = np.random.default_rng(42)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_TOTAL = 5000
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "accidents_raw.csv"

DATE_START = pd.Timestamp("2022-01-01")
DATE_END   = pd.Timestamp("2026-06-30")

# 15 realistic Indian city / highway hotspot centres (lat, lon)
HOTSPOT_CENTRES = [
    (28.63, 77.22),   # Delhi
    (19.07, 72.87),   # Mumbai
    (12.97, 77.59),   # Bengaluru
    (17.38, 78.49),   # Hyderabad
    (13.08, 80.27),   # Chennai
    (22.57, 88.36),   # Kolkata
    (26.85, 80.94),   # Lucknow
    (23.02, 72.57),   # Ahmedabad
    (18.52, 73.86),   # Pune
    (21.14, 79.08),   # Nagpur
    (26.91, 75.79),   # Jaipur
    (22.72, 75.86),   # Indore
    (15.33, 75.13),   # Hubli NH-48
    (25.59, 85.13),   # Patna
    (27.17, 78.00),   # Agra – Yamuna Expressway
]

HOTSPOT_COUNTS = RNG.integers(80, 151, size=len(HOTSPOT_CENTRES))

# Categorical options and their sampling weights
WEATHER_OPTS    = ["clear", "cloudy", "rain", "heavy_rain", "fog", "storm"]
WEATHER_WEIGHTS = [0.40,    0.25,    0.20,  0.07,         0.05,  0.03]

ROAD_OPTS    = ["highway", "urban", "rural", "expressway"]
ROAD_WEIGHTS = [0.35,      0.35,   0.20,   0.10]

LIGHTING_OPTS    = ["daylight", "dusk_dawn", "night_lit", "night_unlit"]
LIGHTING_WEIGHTS = [0.45,       0.10,        0.30,        0.15]

TRAFFIC_OPTS    = ["low", "moderate", "heavy"]
TRAFFIC_WEIGHTS = [0.30,  0.40,       0.30]

VEHICLE_OPTS    = ["car", "motorcycle", "truck", "bus", "auto"]
VEHICLE_WEIGHTS = [0.35,  0.30,         0.20,   0.08,  0.07]

SEVERITY_OPTS    = ["minor", "moderate", "severe", "fatal"]
SEVERITY_WEIGHTS = [0.40,    0.35,        0.18,    0.07]


# ---------------------------------------------------------------------------
# Helper: haversine distance (vectorised)
# ---------------------------------------------------------------------------
def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------
def _weighted_choice(opts, weights, size):
    return RNG.choice(opts, size=size, p=weights)


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------
def generate_dataset() -> pd.DataFrame:
    rows = []

    # ---- 1. Cluster accidents around hotspots --------------------------------
    hotspot_ids_used = []
    for centre, count in zip(HOTSPOT_CENTRES, HOTSPOT_COUNTS):
        clat, clon = centre
        # Gaussian scatter ~ ±0.15 degrees (≈ 15 km radius)
        lats = RNG.normal(clat, 0.15, size=count).clip(12.0, 28.0)
        lons = RNG.normal(clon, 0.15, size=count).clip(72.0, 88.0)
        for lat, lon in zip(lats, lons):
            rows.append({"latitude": lat, "longitude": lon})
        hotspot_ids_used.extend([centre] * count)

    # ---- 2. Remaining random accidents across India -------------------------
    n_random = N_TOTAL - len(rows)
    rand_lats = RNG.uniform(12.0, 28.0, size=n_random)
    rand_lons = RNG.uniform(72.0, 88.0, size=n_random)
    for lat, lon in zip(rand_lats, rand_lons):
        rows.append({"latitude": lat, "longitude": lon})

    df = pd.DataFrame(rows).reset_index(drop=True)
    n = len(df)

    # ---- 3. accident_id ------------------------------------------------------
    df["accident_id"] = [f"ACC{i+1:05d}" for i in range(n)]

    # ---- 4. Dates and times --------------------------------------------------
    total_days = (DATE_END - DATE_START).days
    rand_days  = RNG.integers(0, total_days + 1, size=n)
    df["date"] = [DATE_START + pd.Timedelta(days=int(d)) for d in rand_days]

    # Hour distribution: more accidents during peak hours
    hour_weights = np.array([
        1, 1, 1, 1, 1, 2,          # 0-5
        4, 6, 8, 7, 5, 5,          # 6-11
        5, 5, 5, 6, 8, 9,          # 12-17
        8, 7, 5, 4, 3, 2           # 18-23
    ], dtype=float)
    hour_weights /= hour_weights.sum()
    hours   = RNG.choice(np.arange(24), size=n, p=hour_weights)
    minutes = RNG.integers(0, 60, size=n)
    seconds = RNG.integers(0, 60, size=n)
    df["time"] = [f"{h:02d}:{m:02d}:{s:02d}" for h, m, s in zip(hours, minutes, seconds)]

    # ---- 5. Categoricals (base sampling) ------------------------------------
    df["weather"]         = _weighted_choice(WEATHER_OPTS,  WEATHER_WEIGHTS,  n)
    df["road_type"]       = _weighted_choice(ROAD_OPTS,     ROAD_WEIGHTS,     n)
    df["lighting"]        = _weighted_choice(LIGHTING_OPTS, LIGHTING_WEIGHTS, n)
    df["traffic_density"] = _weighted_choice(TRAFFIC_OPTS,  TRAFFIC_WEIGHTS,  n)
    df["vehicle_type"]    = _weighted_choice(VEHICLE_OPTS,  VEHICLE_WEIGHTS,  n)

    # ---- 6. Correlate lighting with hour ------------------------------------
    is_night = (hours < 6) | (hours >= 20)
    is_dusk  = (hours >= 6) & (hours < 8) | (hours >= 18) & (hours < 20)
    night_mask   = is_night & (RNG.random(n) < 0.8)
    dusk_mask    = is_dusk  & (RNG.random(n) < 0.7)
    df.loc[night_mask, "lighting"] = RNG.choice(
        ["night_lit", "night_unlit"],
        size=night_mask.sum(),
        p=[0.55, 0.45]
    )
    df.loc[dusk_mask, "lighting"] = "dusk_dawn"

    # ---- 7. Speed -----------------------------------------------------------
    base_speed = RNG.uniform(20, 140, size=n)
    # Highway → faster
    highway_mask = df["road_type"].isin(["highway", "expressway"])
    base_speed[highway_mask.values] = RNG.uniform(60, 140, highway_mask.sum())
    # Urban → slower
    urban_mask = df["road_type"] == "urban"
    base_speed[urban_mask.values] = RNG.uniform(20, 80, urban_mask.sum())
    df["speed_kmh"] = np.round(base_speed, 1)

    # Speed limits
    road_limits = {"highway": (60, 100), "expressway": (80, 100),
                   "urban": (30, 60),    "rural": (40, 80)}
    speed_limits = np.zeros(n)
    for rtype, (lo, hi) in road_limits.items():
        mask = (df["road_type"] == rtype).values
        speed_limits[mask] = RNG.integers(lo, hi + 1, size=mask.sum())
    df["speed_limit_kmh"] = speed_limits.astype(int)

    # ---- 8. Severity (with realistic correlations) --------------------------
    # Start with base severity code 0-3
    sev_base = RNG.choice(len(SEVERITY_OPTS), size=n, p=SEVERITY_WEIGHTS)

    # night_unlit + speed > limit → push toward severe/fatal
    unlit_night = (df["lighting"] == "night_unlit").values
    speeding    = (df["speed_kmh"] > df["speed_limit_kmh"] * 1.1).values
    bad_weather = df["weather"].isin(["heavy_rain", "fog", "storm"]).values

    bump_mask = unlit_night & speeding
    sev_base[bump_mask] = np.clip(sev_base[bump_mask] + RNG.integers(1, 3, size=bump_mask.sum()), 0, 3)

    bump_mask2 = bad_weather & highway_mask.values
    sev_base[bump_mask2] = np.clip(sev_base[bump_mask2] + RNG.integers(0, 2, size=bump_mask2.sum()), 0, 3)

    df["severity"] = [SEVERITY_OPTS[s] for s in sev_base]

    # ---- 9. Reorder columns -------------------------------------------------
    df = df[[
        "accident_id", "latitude", "longitude", "date", "time",
        "weather", "road_type", "lighting", "traffic_density",
        "vehicle_type", "speed_kmh", "speed_limit_kmh", "severity"
    ]]

    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_dataset()
    df.to_csv(OUTPUT_FILE, index=False)

    print("=" * 55)
    print("  Dataset Generation Summary")
    print("=" * 55)
    print(f"  Rows generated     : {len(df):,}")
    print(f"  Columns            : {list(df.columns)}")
    print(f"  Date range         : {df['date'].min()} → {df['date'].max()}")
    print(f"  Lat range          : {df['latitude'].min():.4f} – {df['latitude'].max():.4f}")
    print(f"  Lon range          : {df['longitude'].min():.4f} – {df['longitude'].max():.4f}")
    print(f"  Severity dist      :")
    for sev, cnt in df["severity"].value_counts().items():
        print(f"    {sev:<10}: {cnt:>5} ({cnt/len(df)*100:.1f}%)")
    print(f"  Saved to           : {OUTPUT_FILE}")
    print("=" * 55)


if __name__ == "__main__":
    main()
