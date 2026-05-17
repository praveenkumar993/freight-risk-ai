import os
import shutil
import sqlite3
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ── DB Path — works on both local and Render ──────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_BASE, "data", "freight_risk.db")

def seed_db_if_empty():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        # Check if tables exist and have data
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM highway_predictions")
            count = cursor.fetchone()[0]
            conn.close()
            if count > 0:
                print(f"DB exists with {count} highway predictions. Skipping seed.")
                return
        except Exception:
            pass

    print("Seeding database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS highway_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        highway TEXT, risk_score REAL, ml_risk_score REAL,
        xgb_score REAL, lgb_score REAL, rf_score REAL,
        risk_level TEXT, weather_summary TEXT,
        recommendation TEXT, avg_rainfall REAL,
        avg_temp REAL, disruption_rate REAL,
        avg_congestion REAL, updated_at TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS segment_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        segment TEXT, origin TEXT, destination TEXT,
        highway TEXT, distance_km REAL,
        risk_score REAL, risk_level TEXT, updated_at TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS highway_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        highway TEXT, city TEXT, lat REAL, lon REAL,
        date TEXT, timestamp TEXT, rainfall_mm REAL,
        temp_c REAL, condition TEXT, wind_kph REAL,
        humidity INTEGER, current_speed_kph REAL,
        free_flow_speed_kph REAL, congestion_level REAL,
        news_risk_count INTEGER, headlines TEXT,
        event_type TEXT, disruption INTEGER, ingested_at TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        highway TEXT, origin TEXT, destination TEXT,
        travel_date TEXT, expected_delay_hrs REAL,
        actual_delay_hrs REAL, reported_disruption INTEGER,
        disruption_type TEXT, feedback_date TEXT
    )''')

    now = datetime.now().isoformat()

    # Seed highway predictions
    cursor.execute("DELETE FROM highway_predictions")
    highways_data = [
        ("NH-44",  6.72, 6.72, 7.1, 6.2, 7.0, "LOW", "Clear conditions", "Safe to use", 0.0, 30.8, 0.0, 0.049),
        ("NH-48",  6.90, 6.90, 7.3, 6.4, 7.2, "LOW", "Clear conditions", "Safe to use", 0.0, 30.4, 0.0, 0.016),
        ("NH-16",  6.30, 6.30, 6.7, 5.8, 6.6, "LOW", "Clear conditions", "Safe to use", 0.0, 32.5, 0.0, 0.039),
        ("NH-275", 7.90, 7.90, 8.2, 7.5, 8.0, "LOW", "Clear conditions", "Safe to use", 0.0, 28.2, 0.0, 0.166),
        ("NH-65",  6.78, 6.78, 7.2, 6.3, 7.0, "LOW", "Clear conditions", "Safe to use", 0.0, 34.4, 0.0, 0.073),
        ("NH-544", 7.72, 7.72, 8.0, 7.3, 7.8, "LOW", "Clear conditions", "Safe to use", 0.0, 31.9, 0.0, 0.113),
        ("NH-30",  6.99, 6.99, 7.4, 6.5, 7.2, "LOW", "Clear conditions", "Safe to use", 0.0, 33.8, 0.0, 0.0),
        ("NH-340", 8.69, 8.69, 9.0, 8.2, 8.8, "LOW", "Clear conditions", "Safe to use", 0.0, 31.0, 0.167, 0.182),
    ]
    for hw in highways_data:
        cursor.execute('''INSERT INTO highway_predictions
            (highway,risk_score,ml_risk_score,xgb_score,lgb_score,rf_score,
             risk_level,weather_summary,recommendation,avg_rainfall,
             avg_temp,disruption_rate,avg_congestion,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (*hw, now))

    # Seed segment scores
    cursor.execute("DELETE FROM segment_scores")
    segments = [
        ("Delhi → Nagpur","Delhi","Nagpur","NH-44",1090,0.0,"LOW"),
        ("Nagpur → Hyderabad","Nagpur","Hyderabad","NH-44",500,0.0,"LOW"),
        ("Hyderabad → Bangalore","Hyderabad","Bangalore","NH-44",570,0.0,"LOW"),
        ("Bangalore → Krishnagiri","Bangalore","Krishnagiri","NH-44",90,0.0,"LOW"),
        ("Krishnagiri → Chennai","Krishnagiri","Chennai","NH-44",260,0.0,"LOW"),
        ("Mumbai → Pune","Mumbai","Pune","NH-48",150,0.0,"LOW"),
        ("Pune → Hubli","Pune","Hubli","NH-48",480,0.0,"LOW"),
        ("Hubli → Bangalore","Hubli","Bangalore","NH-48",410,0.0,"LOW"),
        ("Chennai → Nellore","Chennai","Nellore","NH-16",175,0.0,"LOW"),
        ("Nellore → Guntur","Nellore","Guntur","NH-16",150,0.0,"LOW"),
        ("Guntur → Vijayawada","Guntur","Vijayawada","NH-16",30,0.0,"LOW"),
        ("Vijayawada → Rajahmundry","Vijayawada","Rajahmundry","NH-16",160,0.0,"LOW"),
        ("Rajahmundry → Kakinada","Rajahmundry","Kakinada","NH-16",55,0.0,"LOW"),
        ("Kakinada → Visakhapatnam","Kakinada","Visakhapatnam","NH-16",165,0.0,"LOW"),
        ("Bangalore → Mysore","Bangalore","Mysore","NH-275",145,0.0,"LOW"),
        ("Mysore → Coimbatore","Mysore","Coimbatore","NH-275",210,0.0,"LOW"),
        ("Coimbatore → Thrissur","Coimbatore","Thrissur","NH-275",160,6.67,"LOW"),
        ("Thrissur → Kochi","Thrissur","Kochi","NH-275",75,6.67,"LOW"),
        ("Kochi → Kozhikode","Kochi","Kozhikode","NH-275",210,6.67,"LOW"),
        ("Kozhikode → Thiruvananthapuram","Kozhikode","Thiruvananthapuram","NH-275",380,0.0,"LOW"),
        ("Hyderabad → Warangal","Hyderabad","Warangal","NH-65",140,0.0,"LOW"),
        ("Warangal → Nizamabad","Warangal","Nizamabad","NH-65",170,0.0,"LOW"),
        ("Hyderabad → Kurnool","Hyderabad","Kurnool","NH-65",210,0.0,"LOW"),
        ("Kurnool → Solapur","Kurnool","Solapur","NH-65",480,0.0,"LOW"),
        ("Solapur → Pune","Solapur","Pune","NH-65",250,0.0,"LOW"),
        ("Chennai → Vellore","Chennai","Vellore","NH-544",135,0.0,"LOW"),
        ("Vellore → Salem","Vellore","Salem","NH-544",160,0.0,"LOW"),
        ("Salem → Tiruchirappalli","Salem","Tiruchirappalli","NH-544",140,0.0,"LOW"),
        ("Tiruchirappalli → Madurai","Tiruchirappalli","Madurai","NH-544",95,0.0,"LOW"),
        ("Madurai → Coimbatore","Madurai","Coimbatore","NH-544",150,0.0,"LOW"),
        ("Chennai → Tirupati","Chennai","Tirupati","NH-30",135,0.0,"LOW"),
        ("Tirupati → Kadapa","Tirupati","Kadapa","NH-30",130,0.0,"LOW"),
        ("Kadapa → Kurnool","Kadapa","Kurnool","NH-30",140,0.0,"LOW"),
        ("Belgaum → Hubli","Belgaum","Hubli","NH-340",80,0.0,"LOW"),
        ("Hubli → Davangere","Hubli","Davangere","NH-340",75,0.0,"LOW"),
        ("Davangere → Mangalore","Davangere","Mangalore","NH-340",280,0.0,"LOW"),
    ]
    for seg in segments:
        cursor.execute('''INSERT INTO segment_scores
            (segment,origin,destination,highway,distance_km,risk_score,risk_level,updated_at)
            VALUES (?,?,?,?,?,?,?,?)''', (*seg, now))

    conn.commit()
    conn.close()
    print("Database seeded successfully.")

# Run seed on startup
seed_db_if_empty()

load_dotenv()

app = FastAPI(
    title="Freight Risk AI",
    description="AI-powered highway freight risk prediction system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class AnalyzeRequest(BaseModel):
    origin: str
    destination: str
    product_type: str
    quantity_kg: float
    transport_mode: str
    expected_date: str

class ChatRequest(BaseModel):
    message: str

class FeedbackRequest(BaseModel):
    highway: str
    origin: str
    destination: str
    expected_delay_hrs: float
    actual_delay_hrs: float
    disruption_type: str = "unknown"


@app.get("/")
def root():
    return {
        "status": "running",
        "system": "Freight Risk AI",
        "version": "1.0.0",
        "db_path": DB_PATH,
        "db_exists": os.path.exists(DB_PATH),
        "endpoints": ["/highway-risk","/segments","/analyze","/chat","/feedback","/mcp"]
    }


@app.get("/highway-risk")
def get_highway_risk(highway: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if highway:
        cursor.execute("SELECT * FROM highway_predictions WHERE highway = ?", (highway,))
    else:
        cursor.execute("SELECT * FROM highway_predictions")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail="No predictions found")
    return [dict(row) for row in rows]


@app.get("/segments")
def get_segments(highway: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if highway:
        cursor.execute("SELECT * FROM segment_scores WHERE highway = ?", (highway,))
    else:
        cursor.execute("SELECT * FROM segment_scores ORDER BY highway, id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.post("/analyze")
def analyze_route(req: AnalyzeRequest):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from router import recommend_route_with_alternate
    from explainer import explain_highway_risk
    from tolls import calculate_trip_cost
    from datetime import datetime as dt

    try:
        expected = dt.strptime(req.expected_date, "%Y-%m-%d")
        days_ahead = (expected.date() - dt.now().date()).days
        use_forecast = 0 < days_ahead <= 5
        forecast_date = req.expected_date if use_forecast else None
    except Exception:
        use_forecast = False
        forecast_date = None

    result = recommend_route_with_alternate(req.origin, req.destination)

    if not result["primary_route"]:
        raise HTTPException(status_code=404,
            detail=f"No route found between {req.origin} and {req.destination}")

    primary_hw  = result["primary_route"]["primary_highway"]
    explanation = explain_highway_risk(primary_hw)

    delay_probability   = result["primary_route"]["risk_score"]
    expected_delay_days = 0
    if delay_probability >= 60:   expected_delay_days = 3
    elif delay_probability >= 35: expected_delay_days = 1

    primary_path = result["primary_route"]["path"]
    primary_dist = result["primary_route"].get("distance_km") or 0
    primary_dur  = result["primary_route"].get("duration_hours") or 0
    primary_cost = calculate_trip_cost(
        primary_path, primary_dist, primary_dur,
        req.transport_mode, req.quantity_kg
    )

    alternate_cost = None
    if result["alternate_route"]:
        alt_path = result["alternate_route"]["path"]
        alt_dist = result["alternate_route"].get("distance_km") or 0
        alt_dur  = result["alternate_route"].get("duration_hours") or 0
        alternate_cost = calculate_trip_cost(
            alt_path, alt_dist, alt_dur,
            req.transport_mode, req.quantity_kg
        )

    return {
        "origin":                 req.origin,
        "destination":            req.destination,
        "product_type":           req.product_type,
        "quantity_kg":            req.quantity_kg,
        "transport_mode":         req.transport_mode,
        "expected_date":          req.expected_date,
        "forecast_used":          use_forecast,
        "forecast_date":          forecast_date,
        "risk_score":             result["primary_route"]["risk_score"],
        "risk_level":             result["primary_route"]["risk_level"],
        "delay_probability":      round(delay_probability, 2),
        "expected_delay_days":    expected_delay_days,
        "root_cause":             explanation.get("summary", "No disruption factors detected"),
        "confidence": {
            "risk_display":       explanation.get("risk_display", ""),
            "ci_lower":           explanation.get("ci_lower", 0),
            "ci_upper":           explanation.get("ci_upper", 0),
            "confidence_margin":  explanation.get("confidence_margin", 0),
        },
        "primary_route":          result["primary_route"],
        "alternate_route":        result["alternate_route"],
        "overall_recommendation": result["recommendation"],
        "primary_cost":           primary_cost,
        "alternate_cost":         alternate_cost,
        "mitigation": [
            {
                "option":      "Use primary route",
                "detail":      f"via {primary_hw}",
                "time_impact": f"+{expected_delay_days} days",
                "cost_impact": f"₹{primary_cost['total_cost']:,}" if primary_cost else "N/A"
            },
            {
                "option":      "Take alternate route",
                "detail":      result["alternate_route"]["primary_highway"] if result["alternate_route"] else "N/A",
                "time_impact": f"{result['alternate_route']['duration_hours']}hrs" if result["alternate_route"] else "N/A",
                "cost_impact": f"₹{alternate_cost['total_cost']:,}" if alternate_cost else "N/A"
            },
            {
                "option":      "Delay shipment",
                "detail":      "Wait for conditions to improve",
                "time_impact": f"+{expected_delay_days + 1} days",
                "cost_impact": "Storage costs apply"
            }
        ],
        "shap_explanation":       explanation.get("explanation", [])[:3],
        "updated_at":             datetime.now().isoformat()
    }


@app.post("/chat")
def chat(req: ChatRequest):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from agent import run_agent
    response = run_agent(req.message)
    return {"response": response}


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from feedback import submit_feedback as save_feedback
    result = save_feedback(
        req.highway, req.origin, req.destination,
        req.expected_delay_hrs, req.actual_delay_hrs,
        req.disruption_type
    )
    return result


@app.get("/mcp")
def mcp_schema():
    return {
        "name": "freight-risk-mcp",
        "version": "1.0.0",
        "description": "MCP server for Indian highway freight risk intelligence",
        "tools": [
            {
                "name": "get_highway_risk",
                "description": "Get current risk scores for all Indian highways",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "highway": {"type": "string", "description": "Optional e.g. NH-44"}
                    }
                },
                "endpoint": "GET /highway-risk"
            },
            {
                "name": "analyze_route",
                "description": "Analyze freight route risk with Dijkstra routing",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "origin":         {"type": "string"},
                        "destination":    {"type": "string"},
                        "product_type":   {"type": "string"},
                        "quantity_kg":    {"type": "number"},
                        "transport_mode": {"type": "string"},
                        "expected_date":  {"type": "string"}
                    },
                    "required": ["origin", "destination"]
                },
                "endpoint": "POST /analyze"
            },
            {
                "name": "get_segments",
                "description": "Get segment-level risk scores",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "highway": {"type": "string"}
                    }
                },
                "endpoint": "GET /segments"
            },
            {
                "name": "chat",
                "description": "Natural language freight risk queries",
                "input_schema": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"]
                },
                "endpoint": "POST /chat"
            }
        ]
    }