"""
create_notebooks.py
-------------------
Programmatically creates all three Jupyter notebooks using nbformat.

Run from the SafeGuard project root:
    python data-science/src/create_notebooks.py
"""

import nbformat as nbf
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).resolve().parents[2] / "data-science" / "notebooks"
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)


def new_nb():
    """Create a fresh v4 notebook."""
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language":     "python",
            "name":         "python3",
        },
        "language_info": {"name": "python", "version": "3.13.0"},
    }
    return nb


def md(text: str):
    return nbf.v4.new_markdown_cell(text)


def code(src: str):
    return nbf.v4.new_code_cell(src)


# ===========================================================================
# Notebook 1 – EDA
# ===========================================================================

def build_eda_notebook() -> nbf.NotebookNode:
    nb = new_nb()
    nb.cells = [
        md("# 📊 Notebook 01 – Exploratory Data Analysis\n"
           "This notebook explores the cleaned SafeGuard accident dataset to understand "
           "temporal patterns, weather effects, severity distribution, and geographic spread."),

        code(
            "import pandas as pd\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n"
            "import seaborn as sns\n"
            "import folium\n"
            "from folium.plugins import HeatMap\n"
            "from pathlib import Path\n\n"
            "sns.set_theme(style='whitegrid', palette='muted')\n"
            "%matplotlib inline\n\n"
            "DATA_DIR = Path('data/processed')\n"
            "df = pd.read_csv(DATA_DIR / 'accidents_clean.csv')\n"
            "print(f'Shape: {df.shape}')\n"
            "df.head()"
        ),

        md("## 1. Accidents by Hour of Day\n"
           "Peak accident hours reveal when roads are most dangerous. "
           "We expect spikes during morning and evening rush hours."),

        code(
            "fig, ax = plt.subplots(figsize=(12, 5))\n"
            "hour_counts = df['hour'].value_counts().sort_index()\n"
            "ax.bar(hour_counts.index, hour_counts.values, color='steelblue', edgecolor='white')\n"
            "ax.set_xlabel('Hour of Day')\n"
            "ax.set_ylabel('Number of Accidents')\n"
            "ax.set_title('Accidents by Hour of Day')\n"
            "ax.set_xticks(range(24))\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 2. Accidents by Day of Week\n"
           "0 = Monday … 6 = Sunday. Weekends may show different patterns "
           "due to leisure travel and reduced traffic management."),

        code(
            "day_labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']\n"
            "fig, ax = plt.subplots(figsize=(9, 5))\n"
            "day_counts = df['day_of_week'].value_counts().sort_index()\n"
            "ax.bar(day_labels, day_counts.values, color='coral', edgecolor='white')\n"
            "ax.set_xlabel('Day of Week')\n"
            "ax.set_ylabel('Number of Accidents')\n"
            "ax.set_title('Accidents by Day of Week')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 3. Accidents by Weather Condition\n"
           "Adverse weather (rain, fog, storm) significantly increases accident probability."),

        code(
            "fig, ax = plt.subplots(figsize=(10, 5))\n"
            "weather_counts = df['weather'].value_counts()\n"
            "ax.bar(weather_counts.index, weather_counts.values, color='teal', edgecolor='white')\n"
            "ax.set_xlabel('Weather Condition')\n"
            "ax.set_ylabel('Number of Accidents')\n"
            "ax.set_title('Accidents by Weather Condition')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 4. Severity Distribution\n"
           "Understanding the proportion of fatal vs. minor accidents helps prioritise "
           "intervention resources."),

        code(
            "fig, ax = plt.subplots(figsize=(7, 7))\n"
            "sev_counts = df['severity'].value_counts()\n"
            "colors = ['#2ecc71', '#f39c12', '#e74c3c', '#8e44ad']\n"
            "ax.pie(\n"
            "    sev_counts.values,\n"
            "    labels=sev_counts.index,\n"
            "    autopct='%1.1f%%',\n"
            "    colors=colors[:len(sev_counts)],\n"
            "    startangle=140,\n"
            ")\n"
            "ax.set_title('Accident Severity Distribution')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 5. Road Type Breakdown\n"
           "Highways and expressways tend to produce more severe accidents despite "
           "often being better maintained."),

        code(
            "fig, ax = plt.subplots(figsize=(9, 5))\n"
            "road_counts = df['road_type'].value_counts()\n"
            "ax.bar(road_counts.index, road_counts.values, color='mediumpurple', edgecolor='white')\n"
            "ax.set_xlabel('Road Type')\n"
            "ax.set_ylabel('Number of Accidents')\n"
            "ax.set_title('Accidents by Road Type')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 6. Monthly Accident Trend\n"
           "A time-series view of accident counts across the dataset's date range."),

        code(
            "df['date'] = pd.to_datetime(df['date'])\n"
            "monthly = df.groupby(df['date'].dt.to_period('M')).size()\n"
            "fig, ax = plt.subplots(figsize=(14, 5))\n"
            "monthly.plot(ax=ax, color='royalblue', marker='o', linewidth=1.5)\n"
            "ax.set_xlabel('Month')\n"
            "ax.set_ylabel('Number of Accidents')\n"
            "ax.set_title('Monthly Accident Trend')\n"
            "plt.xticks(rotation=45)\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 7. Geographic Heatmap\n"
           "Interactive Folium heatmap showing accident density across India."),

        code(
            "m = folium.Map(location=[20.5, 78.9], zoom_start=5, tiles='CartoDB positron')\n"
            "heat_data = df[['latitude', 'longitude']].dropna().values.tolist()\n"
            "HeatMap(heat_data, radius=8, blur=10).add_to(m)\n"
            "m"
        ),

        md("---\n*End of EDA notebook.*"),
    ]
    return nb


# ===========================================================================
# Notebook 2 – Hotspot Analysis
# ===========================================================================

def build_hotspot_notebook() -> nbf.NotebookNode:
    nb = new_nb()
    nb.cells = [
        md("# 🔴 Notebook 02 – Hotspot Analysis\n"
           "Dive into the DBSCAN-detected accident hotspots, their severity profiles, "
           "and geographic radius distributions."),

        code(
            "import pandas as pd\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n"
            "import seaborn as sns\n"
            "import folium\n"
            "from pathlib import Path\n\n"
            "sns.set_theme(style='whitegrid')\n"
            "%matplotlib inline\n\n"
            "DATA_DIR   = Path('data/processed')\n"
            "df         = pd.read_csv(DATA_DIR / 'accidents_clean.csv')\n"
            "hotspots   = pd.read_csv(DATA_DIR / 'hotspots.csv')\n"
            "print(f'Accidents : {len(df):,}')\n"
            "print(f'Hotspots  : {len(hotspots):,}')\n"
            "hotspots.head(10)"
        ),

        md("## 1. Hotspot Summary Table\n"
           "Top hotspots ranked by accident count."),

        code(
            "hotspots.sort_values('accident_count', ascending=False).head(15).style\\\n"
            "    .background_gradient(subset=['accident_count'], cmap='Reds')\\\n"
            "    .format({'severity_index': '{:.2f}', 'radius_m': '{:.0f}'})"
        ),

        md("## 2. Hotspots Plotted on Map\n"
           "Circle size reflects accident count; colour encodes risk level."),

        code(
            "RISK_COLOR = {'HIGH': 'red', 'MODERATE': 'orange', 'LOW': 'green'}\n\n"
            "m = folium.Map(location=[20.5, 78.9], zoom_start=5, tiles='CartoDB positron')\n"
            "for _, row in hotspots.iterrows():\n"
            "    color = RISK_COLOR.get(row['risk_level'], 'blue')\n"
            "    folium.CircleMarker(\n"
            "        location=[row['latitude'], row['longitude']],\n"
            "        radius=max(5, min(25, row['accident_count'] / 5)),\n"
            "        color=color, fill=True, fill_color=color, fill_opacity=0.6,\n"
            "        popup=f\"{row['hotspot_id']} | {row['risk_level']} | {row['accident_count']} accidents\",\n"
            "        tooltip=row['hotspot_id'],\n"
            "    ).add_to(m)\n"
            "m"
        ),

        md("## 3. Severity Index by Hotspot\n"
           "Higher severity index → more severe/fatal accidents at that cluster."),

        code(
            "top_hs = hotspots.sort_values('accident_count', ascending=False).head(20)\n"
            "fig, ax = plt.subplots(figsize=(14, 5))\n"
            "colors = top_hs['risk_level'].map({'HIGH': '#e74c3c', 'MODERATE': '#f39c12', 'LOW': '#2ecc71'})\n"
            "ax.bar(top_hs['hotspot_id'], top_hs['severity_index'], color=colors, edgecolor='white')\n"
            "ax.set_xlabel('Hotspot ID')\n"
            "ax.set_ylabel('Severity Index')\n"
            "ax.set_title('Severity Index by Hotspot (top 20 by accident count)')\n"
            "plt.xticks(rotation=45)\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 4. Hotspot Radius Distribution\n"
           "The spread of each cluster in metres."),

        code(
            "fig, ax = plt.subplots(figsize=(9, 5))\n"
            "ax.hist(hotspots['radius_m'], bins=20, color='steelblue', edgecolor='white')\n"
            "ax.set_xlabel('Cluster Radius (m)')\n"
            "ax.set_ylabel('Number of Hotspots')\n"
            "ax.set_title('Distribution of Hotspot Radii')\n"
            "ax.axvline(hotspots['radius_m'].mean(), color='red', linestyle='--', label='Mean')\n"
            "ax.legend()\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 5. Risk Level Breakdown"),

        code(
            "risk_summary = hotspots.groupby('risk_level').agg(\n"
            "    hotspot_count=('hotspot_id', 'count'),\n"
            "    total_accidents=('accident_count', 'sum'),\n"
            "    avg_severity=('severity_index', 'mean'),\n"
            ").reset_index()\n"
            "print(risk_summary.to_string(index=False))"
        ),

        md("---\n*End of Hotspot Analysis notebook.*"),
    ]
    return nb


# ===========================================================================
# Notebook 3 – Model Training Walkthrough
# ===========================================================================

def build_training_notebook() -> nbf.NotebookNode:
    nb = new_nb()
    nb.cells = [
        md("# 🤖 Notebook 03 – Model Training Walkthrough\n"
           "Step-by-step reproduction of the SafeGuard accident risk model, "
           "with metrics visualisations, confusion matrix, ROC curve, and feature importance."),

        code(
            "import sys, json, warnings\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n"
            "import seaborn as sns\n"
            "from pathlib import Path\n"
            "from sklearn.ensemble import RandomForestClassifier\n"
            "from sklearn.linear_model import LogisticRegression\n"
            "from sklearn.metrics import (\n"
            "    confusion_matrix, f1_score, precision_score,\n"
            "    recall_score, roc_auc_score, roc_curve,\n"
            ")\n"
            "from sklearn.model_selection import train_test_split\n"
            "from sklearn.pipeline import Pipeline\n"
            "from sklearn.preprocessing import StandardScaler\n\n"
            "warnings.filterwarnings('ignore')\n"
            "sns.set_theme(style='whitegrid')\n"
            "%matplotlib inline\n\n"
            "sys.path.insert(0, str(Path('data-science/src').resolve()))\n"
            "from features import FEATURES, _haversine_km, encode_weather, encode_traffic, encode_road_type, encode_lighting\n\n"
            "RANDOM_STATE = 42\n\n"
            "# Load data\n"
            "accidents = pd.read_csv('data/processed/accidents_clean.csv')\n"
            "hotspots  = pd.read_csv('data/processed/hotspots.csv')\n"
            "print(f'Accidents: {len(accidents):,}  |  Hotspots: {len(hotspots):,}')"
        ),

        md("## 1. Build Target Variable\n"
           "`risk = 1` if severity is **severe/fatal** OR the accident is within **500 m** of a HIGH/MODERATE hotspot."),

        code(
            "# Severity-based risk\n"
            "severity_risk = accidents['severity'].isin(['severe', 'fatal'])\n\n"
            "# Proximity-based risk\n"
            "hs_risk = hotspots[hotspots['risk_level'].isin(['HIGH', 'MODERATE'])]\n"
            "if hs_risk.empty:\n"
            "    proximity_risk = pd.Series(False, index=accidents.index)\n"
            "else:\n"
            "    hs_lats, hs_lons = hs_risk['latitude'].values, hs_risk['longitude'].values\n"
            "    def _near(row):\n"
            "        dists = _haversine_km(row['latitude'], row['longitude'], hs_lats, hs_lons)\n"
            "        return bool(np.min(dists) <= 0.5)\n"
            "    proximity_risk = accidents.apply(_near, axis=1)\n\n"
            "y = (severity_risk | proximity_risk).astype(int)\n"
            "print(f'Risk=0: {(y==0).sum():,}  |  Risk=1: {(y==1).sum():,}')"
        ),

        md("## 2. Feature Engineering\n"
           "Encode categoricals, compute speed ratio, distance to hotspot, and local accident density."),

        code(
            "df = accidents.copy()\n"
            "df['weather_code']   = df['weather'].map(encode_weather)\n"
            "df['traffic_code']   = df['traffic_density'].map(encode_traffic)\n"
            "df['road_type_code'] = df['road_type'].map(encode_road_type)\n"
            "df['lighting_code']  = df['lighting'].map(encode_lighting)\n"
            "df['speed_ratio']    = df['speed_kmh'] / df['speed_limit_kmh'].clip(lower=1)\n\n"
            "# Distance to nearest hotspot\n"
            "hs_lats = hotspots['latitude'].values\n"
            "hs_lons = hotspots['longitude'].values\n"
            "hs_sev  = hotspots['severity_index'].values\n"
            "dist_mat = np.stack([\n"
            "    _haversine_km(lat, lon, hs_lats, hs_lons)\n"
            "    for lat, lon in zip(df['latitude'].values, df['longitude'].values)\n"
            "])\n"
            "nearest_idx = np.argmin(dist_mat, axis=1)\n"
            "df['distance_to_hotspot_km'] = dist_mat[np.arange(len(df)), nearest_idx]\n"
            "df['severity_index']         = hs_sev[nearest_idx]\n\n"
            "# Historical accident count within 1 km\n"
            "acc_lats, acc_lons = df['latitude'].values, df['longitude'].values\n"
            "dist_self = np.stack([\n"
            "    _haversine_km(lat, lon, acc_lats, acc_lons)\n"
            "    for lat, lon in zip(acc_lats, acc_lons)\n"
            "])\n"
            "df['historical_accident_count'] = (dist_self <= 1.0).sum(axis=1) - 1\n"
            "df = df.rename(columns={'speed_kmh': 'current_speed_kmh'})\n\n"
            "X = df[FEATURES]\n"
            "print(f'Feature matrix: {X.shape}')\n"
            "X.head()"
        ),

        md("## 3. Train / Test Split"),

        code(
            "X_train, X_test, y_train, y_test = train_test_split(\n"
            "    X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE\n"
            ")\n"
            "print(f'Train: {len(X_train):,}  |  Test: {len(X_test):,}')"
        ),

        md("## 4. Train Models"),

        code(
            "# Logistic Regression (baseline)\n"
            "lr_pipe = Pipeline([\n"
            "    ('scaler', StandardScaler()),\n"
            "    ('clf',    LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),\n"
            "])\n"
            "lr_pipe.fit(X_train, y_train)\n\n"
            "# Random Forest (main model)\n"
            "rf_pipe = Pipeline([\n"
            "    ('scaler', StandardScaler()),\n"
            "    ('clf',    RandomForestClassifier(\n"
            "        n_estimators=200, max_depth=15,\n"
            "        random_state=RANDOM_STATE, n_jobs=-1\n"
            "    )),\n"
            "])\n"
            "rf_pipe.fit(X_train, y_train)\n"
            "print('Training complete.')"
        ),

        md("## 5. Confusion Matrices"),

        code(
            "fig, axes = plt.subplots(1, 2, figsize=(12, 5))\n"
            "for ax, (name, pipe) in zip(axes, [('Logistic Regression', lr_pipe), ('Random Forest', rf_pipe)]):\n"
            "    y_pred = pipe.predict(X_test)\n"
            "    cm     = confusion_matrix(y_test, y_pred)\n"
            "    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,\n"
            "                xticklabels=['Low Risk','High Risk'],\n"
            "                yticklabels=['Low Risk','High Risk'])\n"
            "    f1 = f1_score(y_test, y_pred, zero_division=0)\n"
            "    ax.set_title(f'{name}\\nF1={f1:.4f}')\n"
            "    ax.set_xlabel('Predicted')\n"
            "    ax.set_ylabel('Actual')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 6. ROC Curves"),

        code(
            "fig, ax = plt.subplots(figsize=(8, 6))\n"
            "for name, pipe, color in [\n"
            "    ('Logistic Regression', lr_pipe, 'royalblue'),\n"
            "    ('Random Forest',       rf_pipe,  'crimson'),\n"
            "]:\n"
            "    y_prob = pipe.predict_proba(X_test)[:, 1]\n"
            "    fpr, tpr, _ = roc_curve(y_test, y_prob)\n"
            "    auc = roc_auc_score(y_test, y_prob)\n"
            "    ax.plot(fpr, tpr, label=f'{name} (AUC={auc:.4f})', color=color, linewidth=2)\n"
            "ax.plot([0, 1], [0, 1], 'k--', linewidth=1)\n"
            "ax.set_xlabel('False Positive Rate')\n"
            "ax.set_ylabel('True Positive Rate')\n"
            "ax.set_title('ROC Curves')\n"
            "ax.legend()\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 7. Feature Importance (Random Forest)"),

        code(
            "importances = rf_pipe['clf'].feature_importances_\n"
            "feat_df = pd.DataFrame({'feature': FEATURES, 'importance': importances})\\\n"
            "            .sort_values('importance', ascending=True)\n\n"
            "fig, ax = plt.subplots(figsize=(9, 7))\n"
            "ax.barh(feat_df['feature'], feat_df['importance'], color='steelblue', edgecolor='white')\n"
            "ax.set_xlabel('Feature Importance (Gini)')\n"
            "ax.set_title('Random Forest – Feature Importance')\n"
            "plt.tight_layout()\n"
            "plt.show()"
        ),

        md("## 8. Summary Metrics"),

        code(
            "rows = []\n"
            "for name, pipe in [('Logistic Regression', lr_pipe), ('Random Forest', rf_pipe)]:\n"
            "    yp   = pipe.predict(X_test)\n"
            "    yprb = pipe.predict_proba(X_test)[:, 1]\n"
            "    rows.append({\n"
            "        'Model':     name,\n"
            "        'Precision': round(precision_score(y_test, yp, zero_division=0), 4),\n"
            "        'Recall':    round(recall_score(y_test, yp, zero_division=0), 4),\n"
            "        'F1':        round(f1_score(y_test, yp, zero_division=0), 4),\n"
            "        'ROC-AUC':   round(roc_auc_score(y_test, yprb), 4),\n"
            "    })\n"
            "pd.DataFrame(rows).set_index('Model')"
        ),

        md("---\n*End of Model Training notebook.*"),
    ]
    return nb


# ===========================================================================
# Write notebooks
# ===========================================================================

def main():
    nb1 = build_eda_notebook()
    nb2 = build_hotspot_notebook()
    nb3 = build_training_notebook()

    for fname, nb in [
        ("01_eda.ipynb",              nb1),
        ("02_hotspot_analysis.ipynb", nb2),
        ("03_model_training.ipynb",   nb3),
    ]:
        path = NOTEBOOKS_DIR / fname
        with open(path, "w", encoding="utf-8") as fh:
            nbf.write(nb, fh)
        print(f"  Saved: {path}")


if __name__ == "__main__":
    main()
