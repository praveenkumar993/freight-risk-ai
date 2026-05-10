import csv
import json
import time
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def produce_events():
    with open('../data/highway_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            event = {
                'highway': row['highway'],
                'date': row['date'],
                'origin_city': row['origin_city'],
                'destination_city': row['destination_city'],
                'rainfall_mm': float(row['rainfall_mm']),
                'temp_c': float(row['temp_c']),
                'disruption': int(row['disruption']),
                'event_type': row['event_type']
            }
            producer.send('highway-events', value=event)
            print(f"Produced: {event['highway']} - {event['event_type']}")
            time.sleep(0.5)

    producer.flush()
    print("All events produced.")

if __name__ == "__main__":
    produce_events()