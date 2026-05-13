import os
import json
import time
import requests
from datetime import datetime
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

CITIES = {
    # NH-44
    "Delhi":         {"lat": 28.6139, "lon": 77.2090, "highway": "NH-44"},
    "Nagpur":        {"lat": 21.1458, "lon": 79.0882, "highway": "NH-44"},
    "Hyderabad":     {"lat": 17.3850, "lon": 78.4867, "highway": "NH-44"},
    "Bangalore":     {"lat": 12.9716, "lon": 77.5946, "highway": "NH-44"},
    "Chennai":       {"lat": 13.0827, "lon": 80.2707, "highway": "NH-44"},
    "Krishnagiri":   {"lat": 12.5186, "lon": 78.2137, "highway": "NH-44"},
    # NH-48
    "Mumbai":        {"lat": 19.0760, "lon": 72.8777, "highway": "NH-48"},
    "Pune":          {"lat": 18.5204, "lon": 73.8567, "highway": "NH-48"},
    "Hubli":         {"lat": 15.3647, "lon": 75.1240, "highway": "NH-48"},
    # NH-16
    "Vijayawada":    {"lat": 16.5062, "lon": 80.6480, "highway": "NH-16"},
    "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "highway": "NH-16"},
    "Nellore":       {"lat": 14.4426, "lon": 79.9865, "highway": "NH-16"},
    # NH-275
    "Mysore":        {"lat": 12.2958, "lon": 76.6394, "highway": "NH-275"},
    "Coimbatore":    {"lat": 11.0168, "lon": 76.9558, "highway": "NH-275"},
    "Kochi":         {"lat": 9.9312,  "lon": 76.2673, "highway": "NH-275"},
    # NH-65
    "Kurnool":       {"lat": 15.8281, "lon": 78.0373, "highway": "NH-65"},
    "Solapur":       {"lat": 17.6599, "lon": 75.9064, "highway": "NH-65"},
    "Hyderabad_65":  {"lat": 17.3850, "lon": 78.4867, "highway": "NH-65"},
}

HIGHWAY_KEYWORDS = {
    "NH-44":  "highway flood India",
    "NH-48":  "highway accident Mumbai Pune",
    "NH-16":  "highway flood Andhra Pradesh",
    "NH-275": "highway landslide Karnataka Kerala",
    "NH-65":  "highway strike Hyderabad",
}

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


def fetch_weather(city, lat, lon):
    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
        )
        res = requests.get(url, timeout=10)
        data = res.json()
        rain = data.get("rain", {}).get("1h", 0.0)
        return {
            "rainfall_mm": rain,
            "temp_c": data["main"]["temp"],
            "condition": data["weather"][0]["description"],
            "wind_kph": data["wind"]["speed"] * 3.6,
            "humidity": data["main"]["humidity"],
        }
    except Exception as e:
        print(f"Weather API error for {city}: {e}")
        return {
            "rainfall_mm": 0.0,
            "temp_c": 30.0,
            "condition": "Unknown",
            "wind_kph": 0.0,
            "humidity": 50,
        }


def fetch_tomtom_traffic(highway, lat, lon):
    try:
        url = (
            f"https://api.tomtom.com/traffic/services/4/flowSegmentData/"
            f"absolute/10/json?point={lat},{lon}&key={TOMTOM_API_KEY}"
        )
        res = requests.get(url, timeout=10)
        data = res.json()
        flow = data.get("flowSegmentData", {})
        current_speed = flow.get("currentSpeed", 60)
        free_flow = flow.get("freeFlowSpeed", 60)
        confidence = flow.get("confidence", 1.0)
        congestion = 1 - (current_speed / free_flow) if free_flow > 0 else 0
        return {
            "current_speed_kph": current_speed,
            "free_flow_speed_kph": free_flow,
            "congestion_level": round(congestion, 2),
            "confidence": confidence,
        }
    except Exception as e:
        print(f"TomTom API error for {highway}: {e}")
        return {
            "current_speed_kph": 60,
            "free_flow_speed_kph": 60,
            "congestion_level": 0.0,
            "confidence": 1.0,
        }


def fetch_news(highway):
    try:
        query = HIGHWAY_KEYWORDS[highway]
        url = (
            f"https://newsdata.io/api/1/news?"
            f"apikey={NEWS_API_KEY}&q={query}"
            f"&language=en&country=in"
        )
        res = requests.get(url, timeout=10)
        data = res.json()
        articles = data.get("results", [])
        headlines = [
            a["title"] for a in articles
            if a.get("title")
        ]
        disruption_keywords = [
            "flood", "strike", "accident", "landslide",
            "block", "closed", "delay", "cyclone", "storm"
        ]
        news_risk = 0
        for h in headlines:
            if any(k in h.lower() for k in disruption_keywords):
                news_risk += 1
        return {
            "headlines": headlines[:3],
            "news_risk_count": min(news_risk, 3),
        }
    except Exception as e:
        print(f"NewsAPI error for {highway}: {e}")
        return {"headlines": [], "news_risk_count": 0}


def produce_events():
    print(f"Starting data ingestion at {datetime.now()}")
    news_cache = {}

    for city, info in CITIES.items():
        highway = info["highway"]
        lat = info["lat"]
        lon = info["lon"]

        print(f"Fetching weather for {city} ({highway})...")
        weather = fetch_weather(city, lat, lon)

        print(f"Fetching traffic for {highway}...")
        traffic = fetch_tomtom_traffic(highway, lat, lon)

        if highway not in news_cache:
            print(f"Fetching news for {highway}...")
            news_cache[highway] = fetch_news(highway)

        news = news_cache[highway]

        event_type = "clear"
        if weather["rainfall_mm"] > 50:
            event_type = "flood" if weather["rainfall_mm"] > 100 else "monsoon"
        elif news["news_risk_count"] >= 2:
            event_type = "strike"
        elif traffic["congestion_level"] > 0.5:
            event_type = "congestion"

        event = {
            "highway": highway,
            "city": city,
            "lat": lat,
            "lon": lon,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "rainfall_mm": weather["rainfall_mm"],
            "temp_c": weather["temp_c"],
            "condition": weather["condition"],
            "wind_kph": weather["wind_kph"],
            "humidity": weather["humidity"],
            "current_speed_kph": traffic["current_speed_kph"],
            "free_flow_speed_kph": traffic["free_flow_speed_kph"],
            "congestion_level": traffic["congestion_level"],
            "news_risk_count": news["news_risk_count"],
            "headlines": news["headlines"],
            "event_type": event_type,
            "disruption": 1 if event_type != "clear" else 0,
        }

        producer.send('highway-events', value=event)
        print(f"Produced: {city} | {highway} | {event_type} | rain={weather['rainfall_mm']}mm")
        time.sleep(0.3)

    producer.flush()
    print(f"All {len(CITIES)} city events produced successfully.")


if __name__ == "__main__":
    produce_events()