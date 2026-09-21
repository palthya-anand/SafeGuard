"""
train.py
--------
ML training script for the SafeGuard road safety risk model.

Loads  : data/processed/accidents_clean.csv
         data/processed/hotspots.csv
Saves  : models/accident_risk_model.joblib
         models/preprocessor.joblib
         models/model_metadata.json

Run from the SafeGuard project root:
    python data-science/src/train.py
"""

import json
import sys
import warnings
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Make features.py importable when run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import (  # noqa: E402
    FEATURES,
    _haversine_km,
    build_feature_vector,
    encode_lighting,
    encode_road_type,
    encode_traffic,
    encode_weather,
)

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLEAN_FILE   = PROJECT_ROOT / "data" / "processed" / "accidents_clean.csv"
HOTSPOT_FILE = PROJECT_ROOT / "data" / "processed" / "hotspots.csv"
MODELS_DIR   = PROJECT_ROOT / "models"

MODEL_FILE    = MODELS_DIR / "accident_risk_model.joblib"
PREPROC_FILE  = MODELS_DIR / "preprocessor.joblib"
METADATA_FILE = MODELS_DIR / "model_metadata.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HIGH_RISK_HOTSPOT_RADIUS_KM = 0.5    # 500 m
HIGH_RISK_LEVELS             = {"HIGH", "MODERATE"}
RANDOM_STATE                 = 42


# ---------------------------------------------------------------------------
# Target variable construction
# ---------------------------------------------------------------------------

def build_target(
    accidents: pd.DataFrame,
    hotspots: pd.DataFrame,
) -> pd.Series:
    """
    Binary risk label:
      1 if severity in {severe, fatal}
         OR the accident is within 500 m of a HIGH/MODERATE hotspot
      0 otherwise
    """
    severity_risk = accidents["severity"].isin(["severe", "fatal"])

    # Filter to high-risk hotspots
    hs_risk = hotspots[hotspots["risk_level"].isin(HIGH_RISK_LEVELS)]

    if hs_risk.empty:
        proximity_risk = pd.Series(False, index=accidents.index)
    else:
        hs_lats = hs_risk["latitude"].values
        hs_lons = hs_risk["longitude"].values

        def _near_hotspot(row):
            dists = _haversine_km(
                row["latitude"], row["longitude"], hs_lats, hs_lons
            )
            return bool(np.min(dists) <= HIGH_RISK_HOTSPOT_RADIUS_KM)

        proximity_risk = accidents.apply(_near_hotspot, axis=1)

    return (severity_risk | proximity_risk).astype(int)


# ---------------------------------------------------------------------------
# Feature matrix construction
# ---------------------------------------------------------------------------

def build_feature_matrix(
    accidents: pd.DataFrame,
    hotspots: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construct the full feature matrix for all accident rows.
    Avoids calling build_feature_vector() row-by-row for performance.
    """
    df = accidents.copy()

    # --- Encoded categoricals ------------------------------------------
    df["weather_code"]   = df["weather"].map(encode_weather)
    df["traffic_code"]   = df["traffic_density"].map(encode_traffic)
    df["road_type_code"] = df["road_type"].map(encode_road_type)
    df["lighting_code"]  = df["lighting"].map(encode_lighting)

    # --- Speed ratio -------------------------------------------------------
    df["speed_ratio"] = df["speed_kmh"] / df["speed_limit_kmh"].clip(lower=1)

    # --- Distance to nearest hotspot (vectorised) --------------------------
    if hotspots.empty:
        df["distance_to_hotspot_km"] = np.inf
        df["severity_index"]         = 1.0
    else:
        hs_lats = hotspots["latitude"].values
        hs_lons = hotspots["longitude"].values
        hs_sev  = hotspots["severity_index"].values

        dist_matrix = np.stack([
            _haversine_km(lat, lon, hs_lats, hs_lons)
            for lat, lon in zip(df["latitude"].values, df["longitude"].values)
        ])                                          # shape (n_accidents, n_hotspots)

        nearest_idx = np.argmin(dist_matrix, axis=1)
        df["distance_to_hotspot_km"] = dist_matrix[np.arange(len(df)), nearest_idx]
        df["severity_index"]         = hs_sev[nearest_idx]

    # --- Historical accident count (accidents within 1 km, vectorised) ----
    acc_lats = df["latitude"].values
    acc_lons = df["longitude"].values

    # Pairwise haversine — manageable at 5k rows (25M ops, ~1 s)
    dist_self = np.stack([
        _haversine_km(lat, lon, acc_lats, acc_lons)
        for lat, lon in zip(acc_lats, acc_lons)
    ])
    # Count neighbours within 1 km (excluding self)
    df["historical_accident_count"] = (dist_self <= 1.0).sum(axis=1) - 1

    # --- Rename speed column for feature compatibility --------------------
    df = df.rename(columns={"speed_kmh": "current_speed_kmh"})

    # Ensure all FEATURES exist; fill any gaps with 0
    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0

    return df[FEATURES]


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def evaluate_model(model: Pipeline, X_test, y_test, name: str) -> dict:
    """Evaluate a fitted sklearn Pipeline and print a summary."""
    y_pred  = model.predict(X_test)
    y_prob  = model.predict_proba(X_test)[:, 1]

    prec    = precision_score(y_test, y_pred, zero_division=0)
    rec     = recall_score(y_test, y_pred, zero_division=0)
    f1      = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)
    cm      = confusion_matrix(y_test, y_pred)

    print(f"\n  ── {name} ──")
    print(f"  Precision : {prec:.4f}")
    print(f"  Recall    : {rec:.4f}")
    print(f"  F1        : {f1:.4f}")
    print(f"  ROC-AUC   : {roc_auc:.4f}")
    print(f"  Confusion Matrix:\n{cm}")

    return {"precision": prec, "recall": rec, "f1": f1, "roc_auc": roc_auc}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  SafeGuard Model Training")
    print("=" * 60)

    # ── Load data ─────────────────────────────────────────────────────────
    accidents = pd.read_csv(CLEAN_FILE)
    hotspots  = pd.read_csv(HOTSPOT_FILE)
    print(f"  Accidents loaded   : {len(accidents):,}")
    print(f"  Hotspots loaded    : {len(hotspots):,}")

    # ── Build target ──────────────────────────────────────────────────────
    y = build_target(accidents, hotspots)
    print(f"\n  Class distribution :")
    print(f"    Risk=0 (low)  : {(y == 0).sum():,} ({(y==0).mean()*100:.1f}%)")
    print(f"    Risk=1 (high) : {(y == 1).sum():,} ({(y==1).mean()*100:.1f}%)")

    # ── Build feature matrix ──────────────────────────────────────────────
    print("\n  Building feature matrix …")
    X = build_feature_matrix(accidents, hotspots)
    print(f"  Feature matrix     : {X.shape[0]} rows × {X.shape[1]} cols")

    # ── Train / test split ────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE
    )
    print(f"  Train size         : {len(X_train):,}")
    print(f"  Test  size         : {len(X_test):,}")

    # ── Preprocessor (StandardScaler) ─────────────────────────────────────
    scaler = StandardScaler()

    # ── Pipeline 1: Logistic Regression (baseline) ────────────────────────
    lr_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])
    lr_pipe.fit(X_train, y_train)
    lr_metrics = evaluate_model(lr_pipe, X_test, y_test, "Logistic Regression (baseline)")

    # ── Pipeline 2: Random Forest (main model) ────────────────────────────
    rf_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )),
    ])
    rf_pipe.fit(X_train, y_train)
    rf_metrics = evaluate_model(rf_pipe, X_test, y_test, "Random Forest (main)")

    # ── Comparison table ──────────────────────────────────────────────────
    print("\n  ── Model Comparison ──────────────────────────────")
    header = f"  {'Model':<30} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AUC':>6}"
    print(header)
    print("  " + "-" * 55)
    for name, m in [("Logistic Regression", lr_metrics), ("Random Forest", rf_metrics)]:
        print(f"  {name:<30} {m['precision']:>6.4f} {m['recall']:>6.4f} "
              f"{m['f1']:>6.4f} {m['roc_auc']:>6.4f}")

    # ── Save artefacts ────────────────────────────────────────────────────
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Save best model
    joblib.dump(rf_pipe["clf"], MODEL_FILE)

    # Save preprocessor (scaler fitted on training data)
    fitted_scaler = StandardScaler()
    fitted_scaler.fit(X_train)
    joblib.dump(fitted_scaler, PREPROC_FILE)

    # Metadata
    class_dist = y.value_counts().to_dict()
    metadata = {
        "model_version":    "0.4.0",
        "model_type":       "RandomForestClassifier",
        "features":         FEATURES,
        "training_date":    str(date.today()),
        "training_rows":    int(len(X_train)),
        "metrics": {
            "precision": round(rf_metrics["precision"], 6),
            "recall":    round(rf_metrics["recall"],    6),
            "f1":        round(rf_metrics["f1"],        6),
            "roc_auc":   round(rf_metrics["roc_auc"],  6),
        },
        "class_distribution": {str(k): int(v) for k, v in class_dist.items()},
    }
    with open(METADATA_FILE, "w") as fh:
        json.dump(metadata, fh, indent=2)

    print(f"\n  Saved model        : {MODEL_FILE}")
    print(f"  Saved preprocessor : {PREPROC_FILE}")
    print(f"  Saved metadata     : {METADATA_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
