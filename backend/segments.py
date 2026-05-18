import os
import sqlite3
from datetime import datetime
import os
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "freight_risk.db")

# Each segment: (origin, destination, highway, distance_km)
HIGHWAY_SEGMENTS = [
    # NH-44
    ("Delhi",           "Nagpur",           "NH-44",  1090),
    ("Nagpur",          "Hyderabad",        "NH-44",   500),
    ("Hyderabad",       "Bangalore",        "NH-44",   570),
    ("Bangalore",       "Krishnagiri",      "NH-44",    90),
    ("Krishnagiri",     "Chennai",          "NH-44",   260),
    # NH-48
    ("Mumbai",          "Pune",             "NH-48",   150),
    ("Pune",            "Hubli",            "NH-48",   480),
    ("Hubli",           "Bangalore",        "NH-48",   410),
    # NH-16
    ("Chennai",         "Nellore",          "NH-16",   175),
    ("Nellore",         "Guntur",           "NH-16",   150),
    ("Guntur",          "Vijayawada",       "NH-16",    30),
    ("Vijayawada",      "Rajahmundry",      "NH-16",   160),
    ("Rajahmundry",     "Kakinada",         "NH-16",    55),
    ("Kakinada",        "Visakhapatnam",    "NH-16",   165),
    # NH-275
    ("Bangalore",       "Mysore",           "NH-275",  145),
    ("Mysore",          "Coimbatore",       "NH-275",  210),
    ("Coimbatore",      "Thrissur",         "NH-275",  160),
    ("Thrissur",        "Kochi",            "NH-275",   75),
    ("Kochi",           "Kozhikode",        "NH-275",  210),
    ("Kozhikode",       "Thiruvananthapuram","NH-275", 380),
    # NH-65
    ("Hyderabad",       "Warangal",         "NH-65",   140),
    ("Warangal",        "Nizamabad",        "NH-65",   170),
    ("Hyderabad",       "Kurnool",          "NH-65",   210),
    ("Kurnool",         "Solapur",          "NH-65",   480),
    ("Solapur",         "Pune",             "NH-65",   250),
    # NH-544
    ("Chennai",         "Vellore",          "NH-544",  135),
    ("Vellore",         "Salem",            "NH-544",  160),
    ("Salem",           "Tiruchirappalli",  "NH-544",  140),
    ("Tiruchirappalli", "Madurai",          "NH-544",   95),
    ("Madurai",         "Coimbatore",       "NH-544",  150),
    # NH-30
    ("Chennai",         "Tirupati",         "NH-30",   135),
    ("Tirupati",        "Kadapa",           "NH-30",   130),
    ("Kadapa",          "Kurnool",          "NH-30",   140),
    # NH-340
    ("Belgaum",         "Hubli",            "NH-340",   80),
    ("Hubli",           "Davangere",        "NH-340",   75),
    ("Davangere",       "Mangalore",        "NH-340",  280),
]


def get_city_weather():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT city, rainfall_mm, temp_c, congestion_level,
               news_risk_count, event_type, humidity
        FROM highway_events
        ORDER BY ingested_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    city_data = {}
    for row in rows:
        city = row[0]
        if city not in city_data:
            city_data[city] = {
                "rainfall_mm":      row[1],
                "temp_c":           row[2],
                "congestion_level": row[3],
                "news_risk_count":  row[4],
                "event_type":       row[5],
                "humidity":         row[6],
            }
    return city_data


def score_segment(origin_data, dest_data, highway):
    month = datetime.now().month

    avg_rain = (origin_data["rainfall_mm"] + dest_data["rainfall_mm"]) / 2
    avg_congestion = (origin_data["congestion_level"] + dest_data["congestion_level"]) / 2
    avg_news = (origin_data["news_risk_count"] + dest_data["news_risk_count"]) / 2
    avg_humidity = (origin_data["humidity"] + dest_data["humidity"]) / 2

    # Rain risk
    if avg_rain > 100:
        rain_risk = 3
    elif avg_rain > 60:
        rain_risk = 2
    elif avg_rain > 30:
        rain_risk = 1
    else:
        rain_risk = 0

    # Event risk
    event_risk = 0
    for event in [origin_data["event_type"], dest_data["event_type"]]:
        if event in ["flood", "cyclone"]:
            event_risk = max(event_risk, 3)
        elif event in ["landslide", "monsoon"]:
            event_risk = max(event_risk, 2)
        elif event in ["strike", "congestion"]:
            event_risk = max(event_risk, 1)

    # Seasonal bonus
    season_bonus = 0
    if highway == "NH-44" and month in [6, 7, 8, 9]:
        season_bonus = 1
    elif highway == "NH-16" and month in [10, 11]:
        season_bonus = 1.5
    elif highway == "NH-275" and month in [6, 7, 8, 9]:
        season_bonus = 0.8

    # Congestion risk
    if avg_congestion > 0.7:
        congestion_risk = 3
    elif avg_congestion > 0.4:
        congestion_risk = 2
    elif avg_congestion > 0.2:
        congestion_risk = 1
    else:
        congestion_risk = 0

    raw_score = (
        rain_risk * 0.35 +
        event_risk * 0.25 +
        congestion_risk * 0.2 +
        avg_news * 0.1 +
        season_bonus * 0.1
    )

    risk_score = round((raw_score / 3.0) * 100, 2)
    risk_level = "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 35 else "LOW"

    return risk_score, risk_level


def compute_segment_scores():
    city_data = get_city_weather()
    results = []

    for origin, destination, highway, distance_km in HIGHWAY_SEGMENTS:
        origin_key = origin if origin in city_data else None
        dest_key = destination if destination in city_data else None

        # Use Hyderabad data for Hyderabad_65
        if origin == "Hyderabad" and origin not in city_data:
            origin_key = "Hyderabad_65"
        if destination == "Hyderabad" and destination not in city_data:
            dest_key = "Hyderabad_65"

        if not origin_key or not dest_key:
            risk_score, risk_level = 0.0, "LOW"
        else:
            risk_score, risk_level = score_segment(
                city_data[origin_key],
                city_data[dest_key],
                highway
            )

        results.append({
            "segment": f"{origin} → {destination}",
            "origin": origin,
            "destination": destination,
            "highway": highway,
            "distance_km": distance_km,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "updated_at": datetime.now().isoformat()
        })

    return results


def save_segment_scores(results):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS segment_scores")
    cursor.execute('''
        CREATE TABLE segment_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            segment TEXT,
            origin TEXT,
            destination TEXT,
            highway TEXT,
            distance_km REAL,
            risk_score REAL,
            risk_level TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()

    for r in results:
        cursor.execute('''
            INSERT INTO segment_scores
            (segment, origin, destination, highway,
             distance_km, risk_score, risk_level, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            r["segment"], r["origin"], r["destination"],
            r["highway"], r["distance_km"],
            r["risk_score"], r["risk_level"], r["updated_at"]
        ))
    conn.commit()
    conn.close()
    print(f"Saved {len(results)} segment scores to SQLite.")


if __name__ == "__main__":
    results = compute_segment_scores()
    save_segment_scores(results)
    print("\nSegment Scores:")
    for r in results:
        print(f"{r['segment']:35} | {r['highway']:6} | "
              f"{r['distance_km']:5}km | "
              f"Score: {r['risk_score']:5.2f} | {r['risk_level']}")