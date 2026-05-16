import os
import sqlite3
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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

DB_PATH = "data/freight_risk.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Pydantic Models ───────────────────────────────────────────────────────

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


# ── Health Check ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status": "running",
        "system": "Freight Risk AI",
        "version": "1.0.0",
        "endpoints": [
            "/highway-risk",
            "/segments",
            "/analyze",
            "/chat",
            "/feedback",
            "/mcp"
        ]
    }


# ── Highway Risk Scores ───────────────────────────────────────────────────

@app.get("/highway-risk")
def get_highway_risk(highway: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if highway:
        cursor.execute(
            "SELECT * FROM highway_predictions WHERE highway = ?",
            (highway,)
        )
    else:
        cursor.execute("SELECT * FROM highway_predictions")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No predictions found")

    return [dict(row) for row in rows]


# ── Segment Scores ────────────────────────────────────────────────────────

@app.get("/segments")
def get_segments(highway: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if highway:
        cursor.execute(
            "SELECT * FROM segment_scores WHERE highway = ?",
            (highway,)
        )
    else:
        cursor.execute("SELECT * FROM segment_scores ORDER BY highway, id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ── Analyze Route ─────────────────────────────────────────────────────────
@app.post("/analyze")
def analyze_route(req: AnalyzeRequest):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from router import recommend_route_with_alternate
    from explainer import explain_highway_risk
    from tolls import calculate_trip_cost
    from datetime import datetime as dt

    # Check if expected date is in future — use forecast
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
        raise HTTPException(
            status_code=404,
            detail=f"No route found between {req.origin} and {req.destination}"
        )

    primary_hw  = result["primary_route"]["primary_highway"]
    explanation = explain_highway_risk(primary_hw)

    delay_probability   = result["primary_route"]["risk_score"]
    expected_delay_days = 0
    if delay_probability >= 60:
        expected_delay_days = 3
    elif delay_probability >= 35:
        expected_delay_days = 1

    # Toll + trip costs
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
                "detail":      result["alternate_route"]["primary_highway"]
                               if result["alternate_route"] else "N/A",
                "time_impact": f"{result['alternate_route']['duration_hours']}hrs"
                               if result["alternate_route"] else "N/A",
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

# ── Chat Endpoint ─────────────────────────────────────────────────────────

@app.post("/chat")
def chat(req: ChatRequest):
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from agent import run_agent
    response = run_agent(req.message)
    return {"response": response}


# ── Feedback Endpoint ─────────────────────────────────────────────────────

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


# ── MCP Tool Schema ───────────────────────────────────────────────────────

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
                        "highway": {
                            "type": "string",
                            "description": "Optional highway name e.g. NH-44"
                        }
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
                "description": "Get segment-level risk scores for highway corridors",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "highway": {
                            "type": "string",
                            "description": "Optional highway name"
                        }
                    }
                },
                "endpoint": "GET /segments"
            },
            {
                "name": "chat",
                "description": "Ask freight risk questions in natural language",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    },
                    "required": ["message"]
                },
                "endpoint": "POST /chat"
            }
        ]
    }