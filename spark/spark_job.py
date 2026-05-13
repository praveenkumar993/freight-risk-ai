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
cursor.execute("DELETE FROM highway_predictions")
conn.commit()
result.to_sql("highway_predictions", conn, if_exists="append", index=False)
conn.close()

print("Risk scores written to SQLite.")
print(result[["highway", "risk_score", "risk_level", "recommendation"]])
spark.stop()