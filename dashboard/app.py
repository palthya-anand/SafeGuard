"""
SafeGuard — Streamlit Analytics Dashboard
v1.0.0-hackathon

Pages:
  1. Overview
  2. Accident Heatmap
  3. Accident Trends
  4. Risk Analysis
  5. Model Evaluation
  6. Live Demo
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import folium
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit.components.v1 import html as st_html

# ── Configuration ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data-science" / "data" / "processed"
MODEL_DIR = ROOT / "data-science" / "models"
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="SafeGuard Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Helpers ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_accidents() -> pd.DataFrame:
    path = DATA_DIR / "accidents_clean.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, parse_dates=["datetime"])
    return df


@st.cache_data(ttl=300)
def load_hotspots() -> pd.DataFrame:
    path = DATA_DIR / "hotspots.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_model_metadata() -> dict:
    path = MODEL_DIR / "model_metadata.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def risk_color(level: str) -> str:
    return {"LOW": "#4CAF50", "MODERATE": "#FF9800", "HIGH": "#F44336", "CRITICAL": "#B71C1C"}.get(
        level.upper(), "#9E9E9E"
    )


def api_health() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.json() if r.ok else None
    except Exception:
        return None


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=SafeGuard", use_container_width=True)
    st.title("🛡️ SafeGuard")
    st.caption("AI Road Safety Platform · v1.0.0-hackathon")
    st.divider()
    page = st.radio(
        "Navigation",
        ["📊 Overview", "🗺️ Accident Heatmap", "📈 Accident Trends", "⚠️ Risk Analysis",
         "🤖 Model Evaluation", "🔴 Live Demo"],
        label_visibility="collapsed",
    )
    st.divider()
    health = api_health()
    if health:
        st.success("🟢 Backend online")
        st.caption(f"Model: {'✓' if health.get('model_loaded') else '✗'}")
    else:
        st.warning("🔴 Backend offline")
        st.caption("Start: uvicorn backend.app.main:app")

# ── Data loading ──────────────────────────────────────────────────────────────

df = load_accidents()
hotspots = load_hotspots()
meta = load_model_metadata()

no_data = df.empty


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

if page == "📊 Overview":
    st.title("📊 SafeGuard — Overview")
    st.caption("Smart Road Safety · AI-Based Accident Risk Prediction & Real-Time Driver Warning")

    if no_data:
        st.warning("⚠️ No data loaded. Run `python data-science/src/generate_dataset.py` and preprocessing first.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Accidents", f"{len(df):,}")
        c2.metric("Accident Hotspots", f"{len(hotspots):,}" if not hotspots.empty else "—")
        c3.metric("Fatal Accidents", f"{(df['severity'] == 'fatal').sum():,}")
        c4.metric("Dataset Span",
                  f"{df['datetime'].dt.year.min()}–{df['datetime'].dt.year.max()}" if "datetime" in df.columns else "—")

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Severity Distribution")
            sev = df["severity"].value_counts()
            colors_sev = ["#4CAF50", "#FF9800", "#F44336", "#B71C1C"]
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.pie(sev.values, labels=sev.index.str.capitalize(), colors=colors_sev,
                   autopct="%1.1f%%", startangle=140)
            ax.set_title("Accident Severity")
            st.pyplot(fig)
            plt.close()

        with col_b:
            st.subheader("Weather Conditions")
            weather = df["weather"].value_counts()
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.barh(weather.index.str.replace("_", " ").str.capitalize(), weather.values,
                    color="#1565C0")
            ax.set_xlabel("Count")
            ax.set_title("Accidents by Weather")
            st.pyplot(fig)
            plt.close()

        if meta:
            st.divider()
            st.subheader("🤖 ML Model Info")
            m1, m2, m3, m4 = st.columns(4)
            metrics = meta.get("metrics", {})
            m1.metric("Model", meta.get("model_type", "—"))
            m2.metric("F1 Score", f"{metrics.get('f1', 0):.3f}")
            m3.metric("ROC-AUC", f"{metrics.get('roc_auc', 0):.3f}")
            m4.metric("Training Rows", f"{meta.get('training_rows', 0):,}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: ACCIDENT HEATMAP
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🗺️ Accident Heatmap":
    st.title("🗺️ Accident Heatmap")

    if no_data:
        st.warning("No data available.")
    else:
        severity_filter = st.multiselect(
            "Filter by Severity",
            options=df["severity"].unique().tolist(),
            default=df["severity"].unique().tolist(),
        )
        filtered = df[df["severity"].isin(severity_filter)]

        center_lat = filtered["latitude"].mean()
        center_lon = filtered["longitude"].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles="CartoDB positron")

        # Accident markers (sample 500 for performance)
        sample = filtered.sample(min(500, len(filtered)), random_state=42)
        sev_colors = {"minor": "green", "moderate": "orange", "severe": "red", "fatal": "darkred"}
        for _, row in sample.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=3,
                color=sev_colors.get(row["severity"], "gray"),
                fill=True,
                fill_opacity=0.6,
                popup=f"Severity: {row['severity']}<br>Weather: {row.get('weather', '—')}<br>Speed: {row.get('speed_kmh', '—')} km/h",
            ).add_to(m)

        # Hotspot circles
        if not hotspots.empty:
            rl_colors = {"HIGH": "red", "MODERATE": "orange", "LOW": "green"}
            for _, hs in hotspots.iterrows():
                folium.Circle(
                    location=[hs["latitude"], hs["longitude"]],
                    radius=float(hs.get("radius_m", 500)),
                    color=rl_colors.get(hs.get("risk_level", "LOW"), "gray"),
                    fill=True,
                    fill_opacity=0.15,
                    popup=f"Hotspot #{hs['hotspot_id']}<br>Risk: {hs['risk_level']}<br>Accidents: {hs['accident_count']}",
                ).add_to(m)

        map_html = m._repr_html_()
        st_html(map_html, height=600)

        st.caption(f"Showing {len(sample)} of {len(filtered)} accidents. Circles = hotspot zones.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: ACCIDENT TRENDS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📈 Accident Trends":
    st.title("📈 Accident Trends")

    if no_data:
        st.warning("No data available.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Accidents by Hour of Day")
            hourly = df["hour"].value_counts().sort_index()
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(hourly.index, hourly.values, color="#1565C0", alpha=0.8)
            ax.set_xlabel("Hour (24h)")
            ax.set_ylabel("Accident Count")
            ax.set_xticks(range(0, 24, 2))
            ax.set_title("Peak accident hours")
            st.pyplot(fig)
            plt.close()

        with col2:
            st.subheader("Accidents by Day of Week")
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            dow = df["day_of_week"].value_counts().sort_index()
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar([days[i] for i in dow.index], dow.values, color="#1565C0", alpha=0.8)
            ax.set_ylabel("Accident Count")
            ax.set_title("Day of week pattern")
            st.pyplot(fig)
            plt.close()

        st.divider()

        st.subheader("Monthly Accident Trend")
        if "datetime" in df.columns:
            monthly = df.groupby(df["datetime"].dt.to_period("M")).size().reset_index()
            monthly.columns = ["month", "count"]
            monthly["month"] = monthly["month"].astype(str)
            fig, ax = plt.subplots(figsize=(12, 3))
            ax.plot(monthly["month"], monthly["count"], marker="o", color="#1565C0", linewidth=2)
            ax.fill_between(range(len(monthly)), monthly["count"], alpha=0.1, color="#1565C0")
            ax.set_xticklabels(monthly["month"], rotation=45, ha="right", fontsize=8)
            ax.set_ylabel("Accidents")
            ax.set_title("Accident trend over time")
            st.pyplot(fig)
            plt.close()

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Road Type Breakdown")
            rt = df["road_type"].value_counts()
            fig, ax = plt.subplots(figsize=(5, 3))
            ax.bar(rt.index.str.capitalize(), rt.values, color=["#1565C0", "#0288D1", "#26C6DA", "#4DB6AC"])
            ax.set_ylabel("Count")
            st.pyplot(fig)
            plt.close()

        with col4:
            st.subheader("Lighting Conditions")
            lt = df["lighting"].value_counts()
            fig, ax = plt.subplots(figsize=(5, 3))
            ax.barh(lt.index.str.replace("_", " ").str.capitalize(), lt.values, color="#1565C0", alpha=0.8)
            ax.set_xlabel("Count")
            st.pyplot(fig)
            plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: RISK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "⚠️ Risk Analysis":
    st.title("⚠️ Risk Analysis")

    if hotspots.empty:
        st.warning("No hotspot data. Run hotspot.py first.")
    else:
        st.subheader("Accident Hotspots")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Hotspots", len(hotspots))
        c2.metric("HIGH Risk Zones", (hotspots["risk_level"] == "HIGH").sum())
        c3.metric("Max Accidents/Hotspot", hotspots["accident_count"].max())

        st.dataframe(
            hotspots.sort_values("accident_count", ascending=False).head(20),
            use_container_width=True,
        )

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Risk Level Distribution")
            rl = hotspots["risk_level"].value_counts()
            colors = [risk_color(r) for r in rl.index]
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.pie(rl.values, labels=rl.index, colors=colors, autopct="%1.0f%%", startangle=90)
            st.pyplot(fig)
            plt.close()

        with col_b:
            st.subheader("Hotspot Severity Index")
            fig, ax = plt.subplots(figsize=(5, 4))
            ax.hist(hotspots["severity_index"], bins=20, color="#F44336", alpha=0.7, edgecolor="white")
            ax.set_xlabel("Severity Index")
            ax.set_ylabel("Hotspot Count")
            ax.set_title("Distribution of hotspot severity")
            st.pyplot(fig)
            plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: MODEL EVALUATION
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🤖 Model Evaluation":
    st.title("🤖 Model Evaluation")

    if not meta:
        st.warning("No model metadata found. Run `python data-science/src/train.py` first.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        metrics = meta.get("metrics", {})
        m1.metric("Model Type", meta.get("model_type", "—"))
        m2.metric("F1 Score", f"{metrics.get('f1', 0):.3f}")
        m3.metric("Precision", f"{metrics.get('precision', 0):.3f}")
        m4.metric("Recall", f"{metrics.get('recall', 0):.3f}")

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Training Details")
            st.json({
                "Model Version": meta.get("model_version"),
                "Training Date": meta.get("training_date"),
                "Training Rows": meta.get("training_rows"),
                "Features": len(meta.get("features", [])),
                "ROC-AUC": metrics.get("roc_auc"),
            })

        with col_b:
            st.subheader("Feature List")
            features = meta.get("features", [])
            if features:
                fig, ax = plt.subplots(figsize=(5, 4))
                ax.barh(features, range(len(features), 0, -1), color="#1565C0", alpha=0.7)
                ax.set_xlabel("Feature Index")
                ax.set_title("Model Features")
                st.pyplot(fig)
                plt.close()

        st.subheader("Class Distribution (Training Data)")
        cd = meta.get("class_distribution", {})
        if cd:
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.bar(["Low Risk (0)", "High Risk (1)"], [cd.get("0", 0), cd.get("1", 0)],
                   color=["#4CAF50", "#F44336"], alpha=0.8)
            ax.set_ylabel("Sample Count")
            ax.set_title("Risk class distribution")
            st.pyplot(fig)
            plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6: LIVE DEMO
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔴 Live Demo":
    st.title("🔴 Live Demo — Risk Prediction")
    st.caption("Simulate a real-time risk prediction request to the SafeGuard backend.")

    health = api_health()
    if not health:
        st.error("❌ Backend is not running. Start it first:\n```\nuvicorn backend.app.main:app --reload\n```")

    st.subheader("📍 Scenario Parameters")
    col1, col2, col3 = st.columns(3)

    with col1:
        lat = st.number_input("Latitude", value=17.3850, format="%.4f")
        lon = st.number_input("Longitude", value=78.4867, format="%.4f")

    with col2:
        speed = st.slider("Current Speed (km/h)", 0, 160, 72)
        speed_limit = st.slider("Speed Limit (km/h)", 20, 100, 50)

    with col3:
        weather = st.selectbox("Weather", ["clear", "cloudy", "rain", "heavy_rain", "fog", "storm"])
        traffic = st.selectbox("Traffic", ["low", "moderate", "heavy"])

    st.subheader("🎯 Demo Scenarios")
    scenario = st.radio("Quick scenario", [
        "A — Normal drive",
        "B — Overspeed",
        "C — Hotspot approach",
        "D — Heavy traffic",
        "E — Rain + overspeed + hotspot",
    ], horizontal=True)

    scenario_params = {
        "A — Normal drive":             (17.3850, 78.4867, 40, 60, "clear", "low"),
        "B — Overspeed":                (17.3850, 78.4867, 95, 50, "clear", "moderate"),
        "C — Hotspot approach":         (17.3900, 78.4950, 55, 60, "cloudy", "moderate"),
        "D — Heavy traffic":            (17.3850, 78.4867, 30, 50, "rain", "heavy"),
        "E — Rain + overspeed + hotspot":(17.3900, 78.4950, 85, 50, "rain", "heavy"),
    }
    if scenario in scenario_params:
        lat, lon, speed, speed_limit, weather, traffic = scenario_params[scenario]

    if st.button("🚀 Predict Risk", type="primary", disabled=not bool(health)):
        payload = {
            "latitude": lat,
            "longitude": lon,
            "speed_kmh": float(speed),
            "speed_limit_kmh": float(speed_limit),
            "traffic_level": traffic,
            "weather": weather,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": "dashboard-demo",
        }

        with st.spinner("Calling /predict-risk ..."):
            try:
                resp = requests.post(f"{API_BASE}/predict-risk", json=payload, timeout=10)
                if resp.ok:
                    result = resp.json()
                    level = result.get("risk_level", "LOW")
                    score = result.get("risk_score", 0)

                    st.divider()
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Risk Score", f"{score}/100")
                    c2.metric("Risk Level", level)
                    c3.metric("Near Hotspot", "Yes ⚠️" if result.get("hotspot") else "No ✓")
                    dist = result.get("distance_to_hotspot_m")
                    c4.metric("Hotspot Distance", f"{dist:.0f}m" if dist else "—")

                    color = risk_color(level)
                    st.markdown(
                        f"<div style='background:{color};padding:1rem;border-radius:8px;"
                        f"color:white;font-size:1.2rem;font-weight:bold;text-align:center'>"
                        f"⚠️ {level} RISK — {result.get('message', '')}</div>",
                        unsafe_allow_html=True,
                    )

                    st.subheader("Risk Reasons")
                    for r in result.get("reasons", []):
                        st.markdown(f"- {r}")

                    st.subheader("Recommended Action")
                    st.info(f"👉 {result.get('recommended_action', '—')}")

                    with st.expander("Raw API Response"):
                        st.json(result)
                else:
                    st.error(f"API error {resp.status_code}: {resp.text}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Make sure it's running.")
            except Exception as e:
                st.error(f"Error: {e}")
