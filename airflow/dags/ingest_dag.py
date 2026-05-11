from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import csv
import json
import sqlite3

default_args = {
    'owner': 'freight-risk',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

def ingest_highway_data():
    import sqlite3
    from datetime import datetime as dt

    conn = sqlite3.connect('/opt/airflow/data/freight_risk.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS highway_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            highway TEXT,
            date TEXT,
            origin_city TEXT,
            destination_city TEXT,
            rainfall_mm REAL,
            temp_c REAL,
            disruption INTEGER,
            event_type TEXT,
            ingested_at TEXT
        )
    ''')

    with open('/opt/airflow/data/highway_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute('''
                INSERT INTO highway_events
                (highway, date, origin_city, destination_city,
                 rainfall_mm, temp_c, disruption, event_type, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['highway'], row['date'],
                row['origin_city'], row['destination_city'],
                float(row['rainfall_mm']), float(row['temp_c']),
                int(row['disruption']), row['event_type'],
                dt.now().isoformat()
            ))

    conn.commit()
    conn.close()
    print("Ingestion complete.")

with DAG(
    dag_id='ingest_dag',
    default_args=default_args,
    description='Ingest highway events into SQLite',
    schedule_interval='0 */6 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['freight', 'ingestion'],
) as dag:

    ingest_task = PythonOperator(
        task_id='ingest_highway_data',
        python_callable=ingest_highway_data,
    )

    ingest_task