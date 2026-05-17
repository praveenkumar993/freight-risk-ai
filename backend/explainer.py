import os
import pickle
import shap
import pandas as pd
import sqlite3
from datetime import datetime
import numpy as np


def load_model():
    with open("models/xgb_model_v3.pkl", "rb") as f:
        return pickle.load(f)


def get_highway_features():
    import os
    _DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "freight_risk.db")
    conn = sqlite3.connect(_DB)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT highway,
               COALESCE(avg_rainfall, 0.0),
               COALESCE(avg_temp, 30.0),
               COALESCE(avg_congestion, 0.0),
               updated_at
        FROM highway_predictions
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows
FEATURES = ['rainfall_mm','temp_c','humidity','congestion_level',
            'news_risk_count','month','highway_season_bonus']

def build_feature_row(highway, avg_rainfall, avg_temp, avg_congestion):
    month = datetime.now().month
    avg_rainfall   = float(avg_rainfall)   if avg_rainfall   and str(avg_rainfall)   != 'nan' else 0.0
    avg_temp       = float(avg_temp)       if avg_temp       and str(avg_temp)       != 'nan' else 30.0
    avg_congestion = float(avg_congestion) if avg_congestion and str(avg_congestion) != 'nan' else 0.0

    highway_season_bonus = 0.0
    if highway == 'NH-44' and month in [6,7,8,9]:
        highway_season_bonus = 0.3
    elif highway == 'NH-16' and month in [10,11]:
        highway_season_bonus = 0.4
    elif highway == 'NH-275' and month in [6,7,8,9]:
        highway_season_bonus = 0.2

    return {
        'rainfall_mm':          avg_rainfall,
        'temp_c':               avg_temp,
        'humidity':             60.0,
        'congestion_level':     avg_congestion,
        'news_risk_count':      0,
        'month':                month,
        'highway_season_bonus': highway_season_bonus,
    }
def explain_highway_risk(highway):
    model = load_model()
    rows = get_highway_features()

    highway_row = next((r for r in rows if r[0] == highway), None)
    if not highway_row:
        return {"error": f"No data found for {highway}"}

    _, avg_rainfall, avg_temp, avg_congestion, _ = highway_row
    features = build_feature_row(highway, avg_rainfall, avg_temp, avg_congestion)
    df = pd.DataFrame([features])[FEATURES]
    df = df.astype(float)

    # SHAP explanation
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(df)

    # For binary classification shap_values is list of 2 arrays
    if isinstance(shap_values, list):
        sv = shap_values[1][0]
    else:
        sv = shap_values[0]

    feature_names = list(df.columns)
    explanation = []
    for fname, fval, sval in zip(feature_names, df.iloc[0].values, sv):
        explanation.append({
            "feature":    fname,
            "value":      round(float(fval), 3),
            "impact":     round(float(sval), 4),
            "direction":  "increases risk" if sval > 0 else "reduces risk"
        })

    # Sort by absolute impact
    explanation.sort(key=lambda x: abs(x["impact"]), reverse=True)

    proba = float(model.predict_proba(df)[0][1])
    risk_score = round(proba * 100, 2)

    # Confidence interval using prediction entropy
    try:
        p = proba
        entropy = -p * np.log(p + 1e-9) - (1-p) * np.log(1-p + 1e-9)
        confidence_margin = round(float(entropy) * 30, 2)
        ci_lower = round(max(0, risk_score - confidence_margin), 2)
        ci_upper = round(min(100, risk_score + confidence_margin), 2)
    except Exception:
        confidence_margin = 5.0
        ci_lower = round(max(0, risk_score - 5), 2)
        ci_upper = round(min(100, risk_score + 5), 2)

    risk_level = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 35 else "LOW"

    # Human readable summary
    top_factors = [
        e for e in explanation[:3] if abs(e["impact"]) > 0.001
    ]
    summary_parts = []
    for f in top_factors:
        if f["feature"] == "rainfall_mm":
            summary_parts.append(f"rainfall of {f['value']}mm")
        elif f["feature"] == "congestion_level":
            summary_parts.append(f"congestion level {f['value']}")
        elif f["feature"] == "month":
            summary_parts.append(f"current month ({int(f['value'])})")
        elif f["feature"] == "highway_season_bonus":
            summary_parts.append("seasonal monsoon pattern")
        elif f["feature"] == "news_risk_count":
            summary_parts.append(f"{int(f['value'])} news alerts")

    if summary_parts:
        summary = f"{highway} risk is {risk_level} due to: {', '.join(summary_parts)}."
    else:
        summary = f"{highway} is currently {risk_level} risk with no major disruption factors."

    return {
        "highway":           highway,
        "risk_score":        risk_score,
        "ci_lower":          ci_lower,
        "ci_upper":          ci_upper,
        "confidence_margin": confidence_margin,
        "risk_display":      f"{risk_score} ± {confidence_margin}",
        "risk_level":        risk_level,
        "summary":           summary,
        "explanation":       explanation[:5],
    }


def explain_all_highways():
    highways = ['NH-44', 'NH-48', 'NH-16', 'NH-275', 'NH-65']
    results = {}
    for hw in highways:
        results[hw] = explain_highway_risk(hw)
    return results


if __name__ == "__main__":
    import json
    print("SHAP Explainability for all highways:\n")
    results = explain_all_highways()
    for hw, result in results.items():
        print(f"\n{'='*50}")
        print(f"Highway: {hw}")
        print(f"Risk Score: {result.get('risk_score')} | Level: {result.get('risk_level')}")
        print(f"Summary: {result.get('summary')}")
        print("Top factors:")
        for e in result.get('explanation', []):
            print(f"  {e['feature']:25} value={e['value']:8.3f}  "
                  f"impact={e['impact']:+.4f}  ({e['direction']})")