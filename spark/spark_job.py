import os
import sqlite3
import pandas as pd
from datetime import datetime

os.environ['PYSPARK_PYTHON'] = r'C:\Users\dsp96\Desktop\freight-risk-ai\.venv\Scripts\python.exe'
os.environ['PYSPARK_DRIVER_PYTHON'] = r'C:\Users\dsp96\Desktop\freight-risk-ai\.venv\Scripts\python.exe'

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, avg, max as spark_max

spark = SparkSession.builder \
    .appName("FreightRiskScoring") \
    .master("local[2]") \
    .config("spark.driver.memory", "1g") \
    .config("spark.executor.memory", "1g") \
    .config("spark.sql.shuffle.partitions", "2") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("Spark started. Reading live data from SQLite...")

conn = sqlite3.connect("data/freight_risk.db")
df_pandas = pd.read_sql_query("SELECT * FROM highway_events", conn)
conn.close()

df = spark.createDataFrame(df_pandas)
print(f"Records loaded: {df.count()}")

# Rain risk
df = df.withColumn("rain_risk",
    when(col("rainfall_mm") > 100, 3)
    .when(col("rainfall_mm") > 60, 2)
    .when(col("rainfall_mm") > 30, 1)
    .otherwise(0)
)

# Event risk
df = df.withColumn("event_risk",
    when(col("event_type") == "flood", 3)
    .when(col("event_type") == "cyclone", 3)
    .when(col("event_type") == "landslide", 2)
    .when(col("event_type") == "monsoon", 2)
    .when(col("event_type") == "strike", 1)
    .when(col("event_type") == "congestion", 1)
    .otherwise(0)
)

# Congestion risk
df = df.withColumn("congestion_risk",
    when(col("congestion_level") > 0.7, 3)
    .when(col("congestion_level") > 0.4, 2)
    .when(col("congestion_level") > 0.2, 1)
    .otherwise(0)
)

# News risk already scored 0-3
df = df.withColumn("raw_score",
    (col("rain_risk") * 0.4) +
    (col("event_risk") * 0.3) +
    (col("congestion_risk") * 0.2) +
    (col("news_risk_count") * 0.1)
)

# Aggregate per highway
highway_risk = df.groupBy("highway").agg(
    avg("raw_score").alias("avg_score"),
    avg("rainfall_mm").alias("avg_rainfall"),
    avg("temp_c").alias("avg_temp"),
    avg("disruption").alias("disruption_rate"),
    avg("congestion_level").alias("avg_congestion"),
    spark_max("news_risk_count").alias("max_news_risk")
)

from pyspark.sql.functions import round as spark_round

highway_risk = highway_risk.withColumn(
    "risk_score",
    spark_round((col("avg_score") / 3.0) * 100, 2)
)

highway_risk = highway_risk.withColumn("risk_level",
    when(col("risk_score") >= 60, "HIGH")
    .when(col("risk_score") >= 35, "MEDIUM")
    .otherwise("LOW")
)

highway_risk = highway_risk.withColumn("recommendation",
    when(col("risk_level") == "HIGH", "Avoid - high disruption risk")
    .when(col("risk_level") == "MEDIUM", "Use with caution - monitor weather")
    .otherwise("Safe to use")
)

highway_risk = highway_risk.withColumn("weather_summary",
    when(col("avg_rainfall") > 80, "Heavy rainfall on this corridor")
    .when(col("avg_rainfall") > 40, "Moderate rainfall expected")
    .otherwise("Clear conditions")
)

highway_risk.show()

result = highway_risk.select(
    "highway", "risk_score", "risk_level",
    "weather_summary", "recommendation",
    "avg_rainfall", "avg_temp",
    "disruption_rate", "avg_congestion"
).toPandas()

# Load XGBoost model and re-predict risk scores
# Load ensemble models
import pickle
import pandas as pd

FEATURES = ['rainfall_mm','temp_c','humidity','congestion_level',
            'news_risk_count','month','highway_season_bonus']

xgb_path = "models/xgb_model_v3.pkl"
lgb_path  = "models/lgb_model_v3.pkl"
rf_path   = "models/rf_model_v3.pkl"

if os.path.exists(xgb_path) and os.path.exists(lgb_path) and os.path.exists(rf_path):
    with open(xgb_path, 'rb') as f: xgb_model = pickle.load(f)
    with open(lgb_path, 'rb') as f: lgb_model = pickle.load(f)
    with open(rf_path,  'rb') as f: rf_model  = pickle.load(f)

    highways_list = ['NH-44','NH-48','NH-16','NH-275','NH-65']
    features = []

    for _, row in result.iterrows():
        month = datetime.now().month
        highway = row['highway']
        highway_season_bonus = 0.0
        if highway == 'NH-44' and month in [6,7,8,9]:
            highway_season_bonus = 0.3
        elif highway == 'NH-16' and month in [10,11]:
            highway_season_bonus = 0.4
        elif highway == 'NH-275' and month in [6,7,8,9]:
            highway_season_bonus = 0.2

        features.append({
            'rainfall_mm':          float(row['avg_rainfall'] or 0.0),
            'temp_c':               float(row['avg_temp'] or 30.0),
            'humidity':             60.0,
            'congestion_level':     float(row['avg_congestion'] or 0.0),
            'news_risk_count':      0,
            'month':                month,
            'highway_season_bonus': highway_season_bonus,
        })

    features_df = pd.DataFrame(features)[FEATURES]

    xgb_proba = xgb_model.predict_proba(features_df)[:,1]
    lgb_proba = lgb_model.predict_proba(features_df)[:,1]
    rf_proba  = rf_model.predict_proba(features_df)[:,1]

    ensemble_proba = (xgb_proba * 0.5 + lgb_proba * 0.3 + rf_proba * 0.2)

    result['xgb_score']      = (xgb_proba * 100).round(2)
    result['lgb_score']      = (lgb_proba * 100).round(2)
    result['rf_score']       = (rf_proba  * 100).round(2)
    result['ml_risk_score']  = (ensemble_proba * 100).round(2)
    result['risk_score']     = result['ml_risk_score']
    result['risk_level']     = result['risk_score'].apply(
        lambda x: 'HIGH' if x >= 60 else 'MEDIUM' if x >= 35 else 'LOW'
    )
    result['recommendation'] = result['risk_level'].apply(
        lambda x: 'Avoid - high disruption risk' if x == 'HIGH'
        else 'Use with caution - monitor weather' if x == 'MEDIUM'
        else 'Safe to use'
    )
    print("Ensemble model predictions applied.")
    print(f"XGB: {xgb_proba.mean():.3f} | LGB: {lgb_proba.mean():.3f} | RF: {rf_proba.mean():.3f}")
else:
    print("Ensemble models not found. Using formula scores.")

result["updated_at"] = datetime.now().isoformat()

conn = sqlite3.connect("data/freight_risk.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS highway_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        highway TEXT,
        risk_score REAL,
        risk_level TEXT,
        weather_summary TEXT,
        recommendation TEXT,
        avg_rainfall REAL,
        avg_temp REAL,
        disruption_rate REAL,
        avg_congestion REAL,
        updated_at TEXT
    )
''')
cursor.execute("DROP TABLE IF EXISTS highway_predictions")
conn.commit()
cursor.execute('''
    CREATE TABLE highway_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        highway TEXT,
        risk_score REAL,
        ml_risk_score REAL,
        xgb_score REAL,
        lgb_score REAL,
        rf_score REAL,
        risk_level TEXT,
        weather_summary TEXT,
        recommendation TEXT,
        avg_rainfall REAL,
        avg_temp REAL,
        disruption_rate REAL,
        avg_congestion REAL,
        updated_at TEXT
    )
''')
conn.commit()
result.to_sql("highway_predictions", conn, if_exists="append", index=False)
conn.close()

print("Risk scores written to SQLite.")
print(result[["highway", "risk_score", "risk_level", "recommendation"]])
spark.stop()

conn = sqlite3.connect("data/freight_risk.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS highway_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        highway TEXT,
        risk_score REAL,
        risk_level TEXT,
        weather_summary TEXT,
        recommendation TEXT,
        avg_rainfall REAL,
        avg_temp REAL,
        disruption_rate REAL,
        avg_congestion REAL,
        updated_at TEXT
    )
''')
cursor.execute("DELETE FROM highway_predictions")
conn.commit()
# Fix NaN values before saving
result['avg_temp'] = result['avg_temp'].fillna(30.0)
result['avg_congestion'] = result['avg_congestion'].fillna(0.0)
result['avg_rainfall'] = result['avg_rainfall'].fillna(0.0)
result['disruption_rate'] = result['disruption_rate'].fillna(0.0)
result.to_sql("highway_predictions", conn, if_exists="append", index=False)
conn.close()

print("Risk scores written to SQLite.")
print(result[["highway", "risk_score", "risk_level", "recommendation"]])
spark.stop()