import json
import sqlite3
from kafka import KafkaConsumer
from datetime import datetime

def init_db():
    conn = sqlite3.connect('../data/freight_risk.db')
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
    conn.commit()
    return conn

def consume_events():
    conn = init_db()
    cursor = conn.cursor()

    consumer = KafkaConsumer(
        'highway-events',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest',
        group_id='freight-consumer-group'
    )

    print("Consumer started. Waiting for messages...")

    for message in consumer:
        event = message.value
        cursor.execute('''
            INSERT INTO highway_events
            (highway, date, origin_city, destination_city,
             rainfall_mm, temp_c, disruption, event_type, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event['highway'], event['date'],
            event['origin_city'], event['destination_city'],
            event['rainfall_mm'], event['temp_c'],
            event['disruption'], event['event_type'],
            datetime.now().isoformat()
        ))
        conn.commit()
        print(f"Saved: {event['highway']} - {event['event_type']}")

if __name__ == "__main__":
    consume_events()