from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'freight-risk',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

def score_highways():
    import sqlite3
    import pandas as pd
    from datetime import datetime as dt

    conn = sqlite3.connect('/opt/airflow/data/freight_risk.db')
    df = pd.read_sql_query("SELECT * FROM highway_events", conn)

    def compute_risk(row):
        rain_risk = 3 if row['rainfall_mm'] > 100 else 2 if row['rainfall_mm'] > 60 else 1 if row['rainfall_mm'] > 30 else 0
        event_map = {'flood': 3, 'cyclone': 3, 'landslide': 2, 'monsoon': 2, 'strike': 1, 'clear': 0}
        event_risk = event_map.get(row['event_type'], 0)
        return (rain_risk * 0.5 + event_risk * 0.5)

    df['raw_score'] = df.apply(compute_risk, axis=1)

    result = df.groupby('highway').agg(
        avg_score=('raw_score', 'mean'),
        avg_rainfall=('rainfall_mm', 'mean'),
        disruption_rate=('disruption', 'mean')
    ).reset_index()

    result['risk_score'] = (result['avg_score'] / 3.0 * 100).round(2)
    result['risk_level'] = result['risk_score'].apply(
        lambda x: 'HIGH' if x >= 60 else 'MEDIUM' if x >= 35 else 'LOW'
    )
    result['recommendation'] = result['risk_level'].apply(
        lambda x: 'Avoid - high disruption risk' if x == 'HIGH'
        else 'Use with caution - monitor weather' if x == 'MEDIUM'
        else 'Safe to use'
    )
    result['weather_summary'] = result['avg_rainfall'].apply(
        lambda x: 'Heavy rainfall on this corridor' if x > 80
        else 'Moderate rainfall expected' if x > 40
        else 'Clear conditions'
    )
    result['updated_at'] = dt.now().isoformat()

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
    cursor.execute("DELETE FROM highway_predictions")
    conn.commit()

    result[['highway','risk_score','risk_level','weather_summary',
            'recommendation','avg_rainfall','disruption_rate','updated_at']]\
        .to_sql('highway_predictions', conn, if_exists='append', index=False)

    conn.close()
    print("Scoring complete.")
    print(result[['highway','risk_score','risk_level']])

with DAG(
    dag_id='predict_dag',
    default_args=default_args,
    description='Score highway risk into SQLite',
    schedule_interval='30 */6 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['freight', 'prediction'],
) as dag:

    predict_task = PythonOperator(
        task_id='score_highway_risk',
        python_callable=score_highways,
    )

    predict_task