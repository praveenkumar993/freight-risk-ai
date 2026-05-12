import json
import sqlite3
from kafka import KafkaConsumer
from datetime import datetime


def init_db():
    conn = sqlite3.connect('data/freight_risk.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS highway_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            highway TEXT,
            city TEXT,
            lat REAL,
            lon REAL,
            date TEXT,
            timestamp TEXT,
            rainfall_mm REAL,
            temp_c REAL,
            condition TEXT,
            wind_kph REAL,
            humidity INTEGER,
            current_speed_kph REAL,
            free_flow_speed_kph REAL,
            congestion_level REAL,
            news_risk_count INTEGER,
            headlines TEXT,
            event_type TEXT,
            disruption INTEGER,
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
        group_id='freight-consumer-group-v2',
        consumer_timeout_ms=30000
    )

    print("Consumer started. Waiting for messages...")
    count = 0

    for message in consumer:
        event = message.value
        cursor.execute('''
            INSERT INTO highway_events (
                highway, city, lat, lon, date, timestamp,
                rainfall_mm, temp_c, condition, wind_kph, humidity,
                current_speed_kph, free_flow_speed_kph, congestion_level,
                news_risk_count, headlines, event_type, disruption, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event['highway'], event['city'], event['lat'], event['lon'],
            event['date'], event['timestamp'],
            event['rainfall_mm'], event['temp_c'], event['condition'],
            event['wind_kph'], event['humidity'],
            event['current_speed_kph'], event['free_flow_speed_kph'],
            event['congestion_level'], event['news_risk_count'],
            json.dumps(event['headlines']),
            event['event_type'], event['disruption'],
            datetime.now().isoformat()
        ))
        conn.commit()
        count += 1
        print(f"Saved: {event['city']} | {event['highway']} | {event['event_type']}")

    conn.close()
    print(f"Consumer finished. Total saved: {count}")


if __name__ == "__main__":
    consume_events()