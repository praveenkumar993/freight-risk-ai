from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'freight-risk',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def check_and_retrain():
    import sys
    sys.path.insert(0, '/opt/airflow/backend')
    from feedback import retrain_with_feedback
    import sqlite3

    conn = sqlite3.connect('/opt/airflow/data/freight_risk.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_feedback")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"Total feedback records: {count}")
    if count >= 5:
        print("Enough feedback found. Retraining...")
        retrain_with_feedback()
    else:
        print(f"Need at least 5 feedback records. Have {count}. Skipping retrain.")

with DAG(
    dag_id='retrain_dag',
    default_args=default_args,
    description='Retrain XGBoost model when enough feedback collected',
    schedule_interval='0 0 * * 0',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['freight', 'mlops'],
) as dag:

    retrain_task = PythonOperator(
        task_id='check_and_retrain',
        python_callable=check_and_retrain,
    )

    retrain_task