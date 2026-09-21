"""
hotspot.py
----------
DBSCAN-based accident hotspot detection for the SafeGuard pipeline.

Loads  : data/processed/accidents_clean.csv
Saves  : data/processed/hotspots.csv
         data/processed/hotspot_map.html

Run from the SafeGuard project root:
    python data-science/src/hotspot.py
"""

import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap
from pathlib import Path
from sklearn.cluster import DBSCAN

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_FILE   = PROJECT_ROOT / "data" / "processed" / "accidents_clean.csv"
OUTPUT_DIR   = PROJECT_ROOT / "data" / "processed"
HOTSPOT_CSV  = OUTPUT_DIR / "hotspots.csv"
MAP_HTML     = OUTPUT_DIR / "hotspot_map.html"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEVERITY_WEIGHT = {"minor": 1, "moderate": 2, "severe": 3, "fatal": 4}
EARTH_RADIUS_KM = 6371.0

# DBSCAN parameters
# eps in radians: 2.0 km / 6371 km ≈ 0.000314 rad
EPS_KM      = 2.0
EPS_RAD     = EPS_KM / EARTH_RADIUS_KM
MIN_SAMPLES = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Scalar haversine distance in km between two (lat, lon) points."""
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(a))


def compute_severity_index(severities: pd.Series) -> float:
    """Weighted-average severity index for a group of accidents."""
    weights = severities.map(SEVERITY_WEIGHT).fillna(1)
    return float(weights.mean())


def risk_level(count: int) -> str:
    if count > 50:
        return "HIGH"
    elif count >= 20:
        return "MODERATE"
    return "LOW"


RISK_COLOR = {"HIGH": "red", "MODERATE": "orange", "LOW": "green"}


# ---------------------------------------------------------------------------
# Hotspot detection
# ---------------------------------------------------------------------------

def detect_hotspots(df: pd.DataFrame) -> pd.DataFrame:
    """Run DBSCAN on lat/lon (haversine metric) and return cluster summary."""
    coords_rad = np.radians(df[["latitude", "longitude"]].values)

    db = DBSCAN(
        eps=EPS_RAD,
        min_samples=MIN_SAMPLES,
        algorithm="ball_tree",
        metric="haversine",
    )
    labels = db.fit_predict(coords_rad)
    df = df.copy()
    df["cluster"] = labels

    records = []
    unique_labels = [l for l in np.unique(labels) if l != -1]

    for label in unique_labels:
        cluster_df = df[df["cluster"] == label]
        clat = cluster_df["latitude"].mean()
        clon = cluster_df["longitude"].mean()

        # Radius: max haversine distance from centroid to any point
        dists = cluster_df.apply(
            lambda row: haversine_km(clat, clon, row["latitude"], row["longitude"]),
            axis=1,
        )
        radius_m = float(dists.max() * 1000)  # km → m

        records.append({
            "hotspot_id":        f"HS{label+1:03d}",
            "latitude":          round(clat, 6),
            "longitude":         round(clon, 6),
            "accident_count":    len(cluster_df),
            "severity_index":    round(compute_severity_index(cluster_df["severity"]), 4),
            "radius_m":          round(radius_m, 1),
            "risk_level":        risk_level(len(cluster_df)),
        })

    if not records:
        cols = ["hotspot_id", "latitude", "longitude", "accident_count", "severity_index", "radius_m", "risk_level"]
        return pd.DataFrame(columns=cols), df

    hotspots = pd.DataFrame(records).sort_values("accident_count", ascending=False).reset_index(drop=True)
    return hotspots, df  # return labelled accidents too


# ---------------------------------------------------------------------------
# Map generation
# ---------------------------------------------------------------------------

def generate_map(df_labelled: pd.DataFrame, hotspots: pd.DataFrame) -> folium.Map:
    """Build a Folium map with heatmap layer and cluster circle markers."""
    center_lat = df_labelled["latitude"].mean()
    center_lon = df_labelled["longitude"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles="CartoDB positron")

    # HeatMap layer (all accidents)
    heat_data = df_labelled[["latitude", "longitude"]].values.tolist()
    HeatMap(heat_data, radius=8, blur=10, max_zoom=13, name="Accident Heatmap").add_to(m)

    # Circle markers for each hotspot
    for _, row in hotspots.iterrows():
        color = RISK_COLOR.get(row["risk_level"], "blue")
        popup_html = (
            f"<b>{row['hotspot_id']}</b><br>"
            f"Risk: <b>{row['risk_level']}</b><br>"
            f"Accidents: {row['accident_count']}<br>"
            f"Severity Index: {row['severity_index']:.2f}<br>"
            f"Radius: {row['radius_m']:.0f} m"
        )
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=max(6, min(20, row["accident_count"] / 5)),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{row['hotspot_id']} ({row['risk_level']})",
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 55)
    print("  Hotspot Detection")
    print("=" * 55)

    df = pd.read_csv(INPUT_FILE)
    print(f"  Accidents loaded   : {len(df):,}")

    hotspots, df_labelled = detect_hotspots(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hotspots.to_csv(HOTSPOT_CSV, index=False)

    fmap = generate_map(df_labelled, hotspots)
    fmap.save(str(MAP_HTML))

    # Summary
    n_noise = (df_labelled["cluster"] == -1).sum()
    print(f"  Hotspots detected  : {len(hotspots)}")
    print(f"  Noise points       : {n_noise:,}")
    print(f"\n  Risk breakdown:")
    for lvl, grp in hotspots.groupby("risk_level"):
        print(f"    {lvl:<10}: {len(grp)} hotspot(s), "
              f"avg accidents={grp['accident_count'].mean():.1f}")
    print(f"\n  Saved CSV          : {HOTSPOT_CSV}")
    print(f"  Saved map          : {MAP_HTML}")
    print("=" * 55)


if __name__ == "__main__":
    main()
