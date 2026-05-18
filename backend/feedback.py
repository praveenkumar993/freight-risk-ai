import os
import sqlite3
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "freight_risk.db")

def submit_feedback(
    highway, origin, destination,
    expected_delay_hrs, actual_delay_hrs,
    disruption_type="unknown"
):
    reported_disruption = 1 if actual_delay_hrs > 1.0 else 0

    import os
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_feedback (
            highway, origin, destination, travel_date,
            expected_delay_hrs, actual_delay_hrs,
            reported_disruption, disruption_type, feedback_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        highway, origin, destination,
        datetime.now().strftime("%Y-%m-%d"),
        expected_delay_hrs, actual_delay_hrs,
        reported_disruption, disruption_type,
        datetime.now().isoformat()
    ))
    conn.commit()

    # Check if we have enough new feedback to retrain
    cursor.execute("SELECT COUNT(*) FROM user_feedback")
    total = cursor.fetchone()[0]
    conn.close()

    print(f"Feedback saved. Total feedback records: {total}")
    return {"status": "saved", "total_feedback": total}


def get_feedback_as_training_data():
    conn = sqlite3.connect(DB_PATH)
    feedback_df = pd.read_sql_query(
        "SELECT * FROM user_feedback", conn
    )
    conn.close()

    if feedback_df.empty:
        return pd.DataFrame()

    highways = ['NH-44', 'NH-48', 'NH-16', 'NH-275', 'NH-65']

    records = []
    for _, row in feedback_df.iterrows():
        month = int(row['travel_date'].split('-')[1]) if row['travel_date'] else datetime.now().month
        highway = row['highway']

        highway_season_bonus = 0.0
        if highway == 'NH-44' and month in [6, 7, 8, 9]:
            highway_season_bonus = 0.3
        elif highway == 'NH-16' and month in [10, 11]:
            highway_season_bonus = 0.4
        elif highway == 'NH-275' and month in [6, 7, 8, 9]:
            highway_season_bonus = 0.2

        records.append({
            'rainfall_mm':          0.0,
            'temp_c':               30.0,
            'humidity':             60.0,
            'wind_kph':             10.0,
            'congestion_level':     min(row['actual_delay_hrs'] / 10.0, 1.0),
            'news_risk_count':      1 if row['reported_disruption'] else 0,
            'month':                month,
            'highway_id':           highways.index(highway) if highway in highways else 0,
            'highway_season_bonus': highway_season_bonus,
            'disruption':           int(row['reported_disruption'])
        })

    return pd.DataFrame(records)


def retrain_with_feedback():
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score
    import xgboost as xgb
    import mlflow

    # Load existing training data
    conn = sqlite3.connect(DB_PATH)
    conn.close()

    feedback_df = get_feedback_as_training_data()
    if feedback_df.empty or len(feedback_df) < 5:
        print("Not enough feedback data to retrain. Need at least 5 records.")
        return False

    # Load original model training features
    # Recreate base synthetic data
    np.random.seed(42)
    highways = ['NH-44', 'NH-48', 'NH-16', 'NH-275', 'NH-65']
    records = []
    for _ in range(200):
        highway = np.random.choice(highways)
        month = np.random.randint(1, 13)
        rainfall = np.random.uniform(0, 150)
        congestion = np.random.uniform(0, 1)
        news_risk = np.random.randint(0, 4)
        temp = np.random.uniform(18, 42)
        humidity = np.random.uniform(30, 95)
        wind = np.random.uniform(0, 60)

        highway_season_bonus = 0.0
        if highway == 'NH-44' and month in [6, 7, 8, 9]:
            highway_season_bonus = 0.3
        elif highway == 'NH-16' and month in [10, 11]:
            highway_season_bonus = 0.4
        elif highway == 'NH-275' and month in [6, 7, 8, 9]:
            highway_season_bonus = 0.2

        disruption = 1 if (
            rainfall > 80 or
            (rainfall > 40 and humidity > 75) or
            news_risk >= 2 or
            congestion > 0.7
        ) else 0

        records.append({
            'rainfall_mm': round(rainfall, 2),
            'temp_c': round(temp, 2),
            'humidity': round(humidity, 2),
            'wind_kph': round(wind, 2),
            'congestion_level': round(congestion, 2),
            'news_risk_count': news_risk,
            'month': month,
            'highway_id': highways.index(highway),
            'highway_season_bonus': highway_season_bonus,
            'disruption': disruption
        })

    base_df = pd.DataFrame(records)

    # Combine base + feedback
    combined_df = pd.concat([base_df, feedback_df], ignore_index=True)
    print(f"Retraining on {len(combined_df)} records "
          f"({len(base_df)} base + {len(feedback_df)} feedback)")

    X = combined_df.drop('disruption', axis=1)
    y = combined_df['disruption']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    mlflow.set_experiment("freight-risk-retrain")

    with mlflow.start_run():
        model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.05,
            eval_metric='logloss',
            random_state=42
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        mlflow.log_param("feedback_records", len(feedback_df))
        mlflow.log_param("total_records", len(combined_df))
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)

        print(f"Retrain complete. Accuracy: {acc:.4f} F1: {f1:.4f}")

    with open("models/freight_risk_model_v2.pkl", "wb") as f:
        pickle.dump(model, f)
    print("Model updated and saved.")
    return True


if __name__ == "__main__":
    # Simulate some feedback
    print("Submitting test feedback...")
    submit_feedback("NH-44", "Delhi", "Nagpur", 0.5, 3.5, "flood")
    submit_feedback("NH-44", "Nagpur", "Hyderabad", 0.5, 2.0, "monsoon")
    submit_feedback("NH-16", "Chennai", "Vijayawada", 0.0, 0.0, "clear")
    submit_feedback("NH-275", "Bangalore", "Mysore", 0.0, 0.5, "clear")
    submit_feedback("NH-48", "Mumbai", "Pune", 1.0, 4.0, "congestion")

    print("\nRetraining model with feedback...")
    retrain_with_feedback()