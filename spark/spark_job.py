import sqlite3
import os
os.environ['PYSPARK_PYTHON'] = r'C:\Users\dsp96\Desktop\freight-risk-ai\.venv\Scripts\python.exe'
os.environ['PYSPARK_DRIVER_PYTHON'] = r'C:\Users\dsp96\Desktop\freight-risk-ai\.venv\Scripts\python.exe'
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, avg, count
from datetime import datetime

# Init Spark
spark = SparkSession.builder \
    .appName("FreightRiskScoring") \
    .master("local[2]") \
    .config("spark.driver.memory", "1g") \
    .config("spark.executor.memory", "1g") \
    .config("spark.sql.shuffle.partitions", "2") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("Spark started. Reading from SQLite...")

# Read highway_events from SQLite into pandas then Spark
conn = sqlite3.connect("data/freight_risk.db")
import pandas as pd
df_pandas = pd.read_sql_query("SELECT * FROM highway_events", conn)
conn.close()

# Convert to Spark DataFrame
df = spark.createDataFrame(df_pandas)

print(f"Total records loaded: {df.count()}")

# Feature engineering
df = df.withColumn("rain_risk",
    when(col("rainfall_mm") > 100, 3)
    .when(col("rainfall_mm") > 60, 2)
    .when(col("rainfall_mm") > 30, 1)
    .otherwise(0)
)

df = df.withColumn("event_risk",
    when(col("event_type") == "flood", 3)
    .when(col("event_type") == "cyclone", 3)
    .when(col("event_type") == "landslide", 2)
    .when(col("event_type") == "monsoon", 2)
    .when(col("event_type") == "strike", 1)
    .otherwise(0)
)

# Compute risk score per highway (0 to 1)
df = df.withColumn("raw_score",
    (col("rain_risk") * 0.5 + col("event_risk") * 0.5)
)

# Aggregate per highway
highway_risk = df.groupBy("highway").agg(
    avg("raw_score").alias("avg_score"),
    avg("rainfall_mm").alias("avg_rainfall"),
    avg("disruption").alias("disruption_rate"),
    count("*").alias("total_events")
)

# Normalize score to 0-100
from pyspark.sql.functions import round as spark_round

highway_risk = highway_risk.withColumn(
    "risk_score",
    spark_round((col("avg_score") / 3.0) * 100, 2)
)

# Risk level label
highway_risk = highway_risk.withColumn("risk_level",
    when(col("risk_score") >= 60, "HIGH")
    .when(col("risk_score") >= 35, "MEDIUM")
    .otherwise("LOW")
)

# Recommendation
highway_risk = highway_risk.withColumn("recommendation",
    when(col("risk_level") == "HIGH", "Avoid - high disruption risk")
    .when(col("risk_level") == "MEDIUM", "Use with caution - monitor weather")
    .otherwise("Safe to use")
)

# Weather summary
highway_risk = highway_risk.withColumn("weather_summary",
    when(col("avg_rainfall") > 80, "Heavy rainfall on this corridor")
    .when(col("avg_rainfall") > 40, "Moderate rainfall expected")
    .otherwise("Clear conditions")
)

highway_risk.show()

# Write to SQLite
result_pandas = highway_risk.select(
    "highway", "risk_score", "risk_level",
    "weather_summary", "recommendation",
    "avg_rainfall", "disruption_rate"
).toPandas()

result_pandas["updated_at"] = datetime.now().isoformat()

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
        disruption_rate REAL,
        updated_at TEXT
    )
''')

# Clear old predictions and insert fresh
cursor.execute("DELETE FROM highway_predictions")
conn.commit()

result_pandas.to_sql("highway_predictions", conn,
                     if_exists="append", index=False)
conn.close()

print("Risk scores written to SQLite highway_predictions table.")
print(result_pandas[["highway", "risk_score", "risk_level", "recommendation"]])

spark.stop()