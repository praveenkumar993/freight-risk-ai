import os
import sqlite3
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_highway_risk_data():
    try:
        import os
        _DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "freight_risk.db")
        conn = sqlite3.connect(_DB)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT highway, risk_score, risk_level,
                   weather_summary, recommendation, updated_at
            FROM highway_predictions
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "highway":        r[0],
                "risk_score":     r[1],
                "risk_level":     r[2],
                "weather_summary":r[3],
                "recommendation": r[4],
                "updated_at":     r[5]
            }
            for r in rows
        ]
    except Exception as e:
        return []


def get_segment_data():
    try:
        conn = sqlite3.connect("data/freight_risk.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT segment, highway, distance_km,
                   risk_score, risk_level
            FROM segment_scores
            ORDER BY risk_score DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "segment":    r[0],
                "highway":    r[1],
                "distance_km":r[2],
                "risk_score": r[3],
                "risk_level": r[4]
            }
            for r in rows
        ]
    except Exception as e:
        return []


def get_route_recommendation(origin, destination):
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from router import recommend_route_with_alternate
        return recommend_route_with_alternate(origin, destination)
    except Exception as e:
        return {"error": str(e)}


def run_agent(user_message: str) -> str:
    highway_data = get_highway_risk_data()
    segment_data = get_segment_data()

    # Check if user is asking about a specific route
    cities = [
        "Delhi", "Nagpur", "Hyderabad", "Bangalore", "Chennai",
        "Krishnagiri", "Mumbai", "Pune", "Hubli", "Vijayawada",
        "Visakhapatnam", "Nellore", "Guntur", "Rajahmundry",
        "Kakinada", "Mysore", "Coimbatore", "Kochi", "Thrissur",
        "Kozhikode", "Thiruvananthapuram", "Kurnool", "Solapur",
        "Warangal", "Nizamabad", "Salem", "Vellore", "Madurai",
        "Tiruchirappalli", "Tirupati", "Kadapa", "Mangalore",
        "Davangere", "Belgaum"
    ]

    msg_lower = user_message.lower()
    found_cities = [c for c in cities if c.lower() in msg_lower]
    route_info = None

    if len(found_cities) >= 2:
        route_info = get_route_recommendation(found_cities[0], found_cities[1])

    context = f"""
You are a freight logistics AI assistant for Indian highways.
You help logistics managers make decisions about road freight routes.

Current Highway Risk Data:
{json.dumps(highway_data, indent=2)}

Top Risk Segments:
{json.dumps(segment_data, indent=2)}
"""

    if route_info:
        context += f"""
Route Analysis ({found_cities[0]} to {found_cities[1]}):
{json.dumps(route_info, indent=2)}
"""

    context += """
Guidelines:
- Give specific, actionable advice
- Mention risk scores and levels
- Suggest alternate routes when risk is HIGH or MEDIUM
- Be concise - max 4-5 sentences
- Always mention which highway is safest right now
- Use Indian context (monsoon, NH numbers, city names)
"""

    messages = [
        {"role": "system", "content": context},
        {"role": "user", "content": user_message}
    ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.3
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    print("Testing agent...")
    questions = [
        "Is NH-44 safe today?",
        "Best route from Hyderabad to Chennai?",
        "Any disruptions on South India highways?",
        "Compare NH-44 and NH-48 risk levels"
    ]
    for q in questions:
        print(f"\nQ: {q}")
        print(f"A: {run_agent(q)}")