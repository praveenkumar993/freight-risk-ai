# 🛣 FreightRisk AI — India Highway Intelligence System

> **Production-grade freight risk prediction platform** powered by Kafka, Spark, Airflow, Ensemble ML, LangGraph, and real-time APIs — built for South India's national highway network.

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![Apache Kafka](https://img.shields.io/badge/Kafka-3.7-231F20?style=flat-square&logo=apachekafka)](https://kafka.apache.org)
[![Apache Spark](https://img.shields.io/badge/Spark-3.5-E25A1C?style=flat-square&logo=apachespark)](https://spark.apache.org)
[![Apache Airflow](https://img.shields.io/badge/Airflow-2.9-017CEE?style=flat-square&logo=apacheairflow)](https://airflow.apache.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-0080FF?style=flat-square)](https://xgboost.ai)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph)

---

## 🎯 Problem Statement

Logistics companies shipping freight across South India face unpredictable disruptions — monsoon floods on NH-44, cyclones on the Andhra coast (NH-16), landslides near Karnataka's Western Ghats (NH-275). There is no unified, intelligent system that combines live weather, traffic, and news to predict risk and suggest optimal routes in real time.

**FreightRisk AI solves this.**

---

## 🚀 Live Demo

| Service | URL |
|---------|-----|
| 🌐 Frontend | [freight-risk-ai.vercel.app](https://freight-risk-ai.vercel.app) |
| ⚙️ Backend API | [freight-risk-ai.onrender.com](https://freight-risk-ai.onrender.com) |
| 📖 API Docs | [freight-risk-ai.onrender.com/docs](https://freight-risk-ai.onrender.com/docs) |

> **Note:** Render free tier spins down after inactivity. First request may take 30-60 seconds to wake up.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (Live)                          │
│  OpenWeatherMap API  │  TomTom Traffic API  │  NewsData.io API      │
│  (rain, temp, humid) │  (speed, congestion) │  (flood, strike news) │
└──────────────┬───────────────┬──────────────────────┬───────────────┘
               │               │                      │
               ▼               ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Apache Kafka (KRaft Mode)                        │
│              Topic: highway-events  │  35 city events/run           │
│         Producer.py ──────────────────▶ Consumer.py                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼ SQLite: highway_events
┌─────────────────────────────────────────────────────────────────────┐
│                     Apache Spark (local[2])                         │
│  • Reads highway_events from SQLite                                 │
│  • Feature engineering: rain_risk(40%) + event_risk(30%)            │
│    + congestion_risk(20%) + news_risk(10%)                          │
│  • Loads Ensemble ML → writes highway_predictions                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Ensemble ML Model (Trained on Google Colab)           │
│  XGBoost (50%) + LightGBM (30%) + RandomForest (20%)               │
│  Trained on: 20,000 real NHAI records + 4,000 synthetic seasonal    │
│  Accuracy: 78% │ F1: 82% │ AUC-ROC: 86% │ 5-fold CV F1: 76.6%    │
│  Features: rainfall, temp, humidity, congestion, news_risk,         │
│            month, highway_season_bonus                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
        SQLite: highway_predictions  SQLite: segment_scores
        (8 highways, risk scores)    (36 city-to-city segments)
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Apache Airflow (SequentialExecutor + SQLite)          │
│  ingest_dag   → Every 6h → Kafka producer → consumer               │
│  predict_dag  → Every 6h → Spark job → ML scoring                  │
│  retrain_dag  → Weekly   → Feedback check → Model retrain          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                              │
│  GET  /highway-risk     → All 8 highway risk scores                 │
│  GET  /segments         → 36 segment-level scores                  │
│  POST /analyze          → Full route risk analysis                  │
│  POST /chat             → LangGraph AI agent                        │
│  POST /feedback         → User delay report                         │
│  GET  /mcp              → MCP tool schema descriptor               │
└──────────┬──────────────────────────────────┬───────────────────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────────┐          ┌───────────────────────────────┐
│   Dijkstra Router    │          │     LangGraph AI Agent        │
│  • Risk-weighted     │          │  Node 1: Fetch highway data   │
│    graph of 35 cities│          │  Node 2: Detect city pairs    │
│  • 8 highway edges   │          │  Node 3: Call Dijkstra        │
│  • Segment scores    │          │  Node 4: Groq LLaMA-3.3-70B  │
│  • ORS real distances│          │  Output: Plain English answer │
│  • Alternate routing │          └───────────────────────────────┘
└──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      React + Vite Frontend                          │
│  Dashboard   → Live map + highway cards + donut charts + pipeline   │
│  Analyze     → Shipment form + gauge + route compare + toll costs   │
│  Analytics   → KPIs + bar charts + model metrics + segment table    │
│  Pipeline    → 7-step MLOps architecture walkthrough                │
│  Chat Widget → Floating AI assistant with guardrails               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 ML Model Details

### Dataset
| Source | Records | Type |
|--------|---------|------|
| NHAI Road Incident Data (Kaggle) | 20,000 | Real historical |
| Seasonal synthetic (monsoon-weighted) | 4,000 | Augmented |
| **Total** | **24,000** | **Combined** |

### Features Used
```
rainfall_mm          → Live from OpenWeatherMap
temp_c               → Live from OpenWeatherMap
humidity             → Live from OpenWeatherMap
congestion_level     → Live from TomTom (current_speed/free_flow_speed)
news_risk_count      → Live from NewsData.io (keyword matching)
month                → Seasonal pattern encoding
highway_season_bonus → Domain knowledge (monsoon=0.3, cyclone=0.4, WGhats=0.2)
```

### Model Performance
```
Model           Accuracy    F1 Score    AUC-ROC
─────────────────────────────────────────────────
XGBoost         78.0%       82.2%       86.2%
LightGBM        78.5%       82.6%       86.6%
RandomForest    77.9%       81.8%       86.1%
ENSEMBLE        78.3%       82.2%       86.3%
─────────────────────────────────────────────────
5-fold CV F1:   76.57% ± 1.73%  (stable, no overfitting)
```

### Ensemble Weights
```python
ensemble_proba = xgb_proba * 0.5 + lgb_proba * 0.3 + rf_proba * 0.2
```

---

## 🗺 Coverage

### Highways (8 National Highways)
| Highway | Corridor | Key Cities |
|---------|----------|------------|
| NH-44 | Delhi → Chennai | Delhi, Nagpur, Hyderabad, Bangalore, Chennai |
| NH-48 | Delhi → Bangalore | Mumbai, Pune, Hubli, Bangalore |
| NH-16 | Chennai → Visakhapatnam | Nellore, Vijayawada, Rajahmundry, Kakinada |
| NH-275 | Bangalore → Kochi | Mysore, Coimbatore, Thrissur, Kochi, Kozhikode |
| NH-65 | Hyderabad → Pune | Kurnool, Solapur, Warangal |
| NH-544 | Chennai → Coimbatore | Vellore, Salem, Tiruchirappalli, Madurai |
| NH-30 | Chennai → Kurnool | Tirupati, Kadapa |
| NH-340 | Belgaum → Mangalore | Hubli, Davangere |

### Cities: 35 | Segments: 36 | States: 8

---

## ⚙️ Tech Stack

### Data Engineering
| Tool | Version | Purpose |
|------|---------|---------|
| Apache Kafka | 3.7.0 | Event streaming (KRaft mode, no Zookeeper) |
| Apache Spark | 3.5.1 | Batch processing, feature engineering |
| Apache Airflow | 2.9.1 | Pipeline orchestration (3 DAGs) |
| SQLite | Built-in | Lightweight embedded database |

### Machine Learning
| Tool | Version | Purpose |
|------|---------|---------|
| XGBoost | 2.0.3 | Primary ensemble model (50% weight) |
| LightGBM | 4.3.0 | Secondary model (30% weight) |
| RandomForest | sklearn 1.4 | Tertiary model (20% weight) |
| SHAP | 0.45 | Model explainability |
| MLflow | 2.13 | Experiment tracking |

### AI / Agent
| Tool | Version | Purpose |
|------|---------|---------|
| LangGraph | 0.1.9 | Multi-step AI agent |
| Groq | 0.9.0 | LLM inference (LLaMA-3.3-70B) |
| FastAPI | 0.111 | REST API + MCP schema |

### Routing
| Tool | Purpose |
|------|---------|
| Dijkstra Algorithm | Risk-weighted shortest path |
| OpenRouteService API | Real road distances + ETAs |
| Segment Scoring | 36-segment precision routing |

### Frontend
| Tool | Purpose |
|------|---------|
| React 18 + Vite | UI framework |
| Leaflet + react-leaflet | Interactive India map |
| Custom SVG Charts | Donut, Gauge, Bar, Sparkline |

---

## 🔌 API Endpoints

### `GET /highway-risk`
Returns current risk scores for all 8 highways.
```json
[
  {
    "highway": "NH-44",
    "risk_score": 6.72,
    "risk_level": "LOW",
    "weather_summary": "Clear conditions",
    "recommendation": "Safe to use",
    "updated_at": "2026-05-17T10:30:00"
  }
]
```

### `POST /analyze`
Full route risk analysis with ML prediction, Dijkstra routing, and toll costs.
```json
// Request
{
  "origin": "Hyderabad",
  "destination": "Chennai",
  "product_type": "Electronics",
  "quantity_kg": 500,
  "transport_mode": "Road",
  "expected_date": "2026-05-20"
}

// Response
{
  "risk_score": 6.72,
  "risk_level": "LOW",
  "delay_probability": 6.72,
  "expected_delay_days": 0,
  "root_cause": "NH-16 risk is LOW...",
  "confidence": { "risk_display": "0.68 ± 1.22", "ci_lower": 0, "ci_upper": 1.9 },
  "primary_route": {
    "path": ["Hyderabad", "Bangalore", "Chennai"],
    "highways": ["NH-44"],
    "distance_km": 624.7,
    "duration_hours": 7.9,
    "risk_level": "LOW"
  },
  "primary_cost": {
    "fuel_cost": 18741,
    "toll_cost": 2070,
    "driver_cost": 3002,
    "total_cost": 24063
  },
  "shap_explanation": [...]
}
```

### `POST /chat`
Natural language freight advisory via LangGraph + Groq.
```json
{ "message": "Is NH-44 safe today?" }
// → "NH-44 is currently LOW risk (score: 6.72)..."
```

### `GET /mcp`
MCP tool schema — makes this an MCP-compatible server.

---

## 🚀 Local Setup

### Prerequisites
```bash
Python 3.11+
Docker Desktop
Node.js 18+
Java JDK 11
```

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/freight-risk-ai.git
cd freight-risk-ai
```

### 2. Environment
```bash
cp .env.example .env
# Fill in your API keys
```

### 3. Python setup
```bash
python3.11 -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

### 4. Start Kafka + Airflow
```bash
docker-compose up -d
```

### 5. Run Data Pipeline
```bash
# Ingest live data
python kafka/producer.py
python kafka/consumer.py

# Score with ML
python spark/spark_job.py
python backend/segments.py
```

### 6. Start Backend
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Start Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 🌐 Deployment

### Backend → Render (Free)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml`
5. Add environment variables in Render dashboard:
   - `WEATHER_API_KEY`
   - `TOMTOM_API_KEY`
   - `ORS_API_KEY`
   - `NEWS_API_KEY`
   - `GROQ_API_KEY`
6. Deploy → get your URL: https://freight-risk-ai.onrender.com

### Frontend → Vercel (Free)

1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   - `VITE_API_URL` = https://freight-risk-ai.onrender.com
5. Deploy → get your URL: https://freight-risk-ai.vercel.app/

> **Important:** Update `API` constant in `frontend/src/App.jsx`:
> ```javascript
> const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
> ```

### Deployment Notes

```
Kafka + Airflow + Spark → Run locally only (too heavy for free tiers)
FastAPI → Render free tier (auto-sleep after 15min inactivity)
React   → Vercel free tier (always on, global CDN)
SQLite  → Pre-populated DB committed to repo for demo
```

For production: replace SQLite with PostgreSQL (Supabase free tier), deploy Kafka on Confluent Cloud free tier.

---

## 🔄 MLOps Pipeline

```
User submits feedback (delay report)
         ↓
SQLite: user_feedback table
         ↓
Airflow retrain_dag (runs weekly)
         ↓
Check: feedback_count >= 5?
         ↓ YES
Merge feedback + base training data
         ↓
Retrain XGBoost + LightGBM + RandomForest
         ↓
Log new experiment in MLflow
         ↓
Save updated models/*.pkl
         ↓
Next Spark run uses improved models
```

---

## 📁 Project Structure

```
freight-risk-ai/
├── kafka/
│   ├── producer.py          # Fetches 3 APIs for 35 cities → Kafka
│   └── consumer.py          # Reads Kafka → SQLite highway_events
├── spark/
│   └── spark_job.py         # Reads SQLite → Ensemble ML → predictions
├── airflow/
│   └── dags/
│       ├── ingest_dag.py    # Triggers producer every 6 hours
│       ├── predict_dag.py   # Triggers Spark after ingestion
│       └── retrain_dag.py   # Weekly model retraining from feedback
├── backend/
│   ├── main.py              # FastAPI app — all endpoints
│   ├── agent.py             # LangGraph + Groq AI agent
│   ├── router.py            # Dijkstra + ORS route optimization
│   ├── segments.py          # 36-segment risk scoring
│   ├── explainer.py         # SHAP explainability
│   ├── feedback.py          # User feedback + model retraining
│   └── tolls.py             # NHAI toll cost calculation
├── frontend/
│   ├── src/
│   │   └── App.jsx          # Complete React dashboard
│   ├── package.json
│   └── vite.config.js
├── models/
│   ├── xgb_model_v3.pkl     # XGBoost (trained on Colab)
│   ├── lgb_model_v3.pkl     # LightGBM
│   └── rf_model_v3.pkl      # RandomForest
├── notebooks/
│   └── train_model.ipynb    # Colab training notebook
├── data/
│   └── highway_data.csv     # Seed data for pipeline testing
├── docker-compose.yml       # Kafka + Airflow containers
├── requirements.txt         # Python dependencies
├── render.yaml              # Render deployment config
├── vercel.json              # Vercel deployment config
├── .env.example             # API key template
└── README.md
```

---

## 🎯 Key Design Decisions

### Why Kafka over RabbitMQ?
Kafka's log-based retention means if the consumer crashes, it can replay all missed events. For a freight risk system that runs every 6 hours, this guarantees no data loss. RabbitMQ deletes messages after consumption.

### Why XGBoost Ensemble over a Neural Network?
Tabular data with 7 features → XGBoost/LightGBM consistently outperforms neural networks. The ensemble reduces variance — if one model overfits to a pattern (e.g., monsoon months), the others correct it. Neural networks would require 100x more data to match this performance.

### Why SQLite over PostgreSQL?
For a portfolio system running on 8GB RAM with Kafka + Airflow + Spark already consuming ~4GB, PostgreSQL would add another 500MB. SQLite is zero-overhead, requires no server, and is API-identical to PostgreSQL from FastAPI's perspective. The `to_sql()` call in Spark works identically.

### Why Dijkstra over A\*?
A\* requires a good heuristic (straight-line distance) that works well for geographic routing. But our graph has risk multipliers that make straight-line estimates unreliable — a shorter straight-line path might be 2.5x slower due to HIGH risk. Dijkstra guarantees the optimal weighted path without heuristic assumptions.

### Why Segment Scoring?
NH-44 is 2,300km long. A single risk score for the whole highway is meaningless — Nagpur might be flooded while Chennai is clear. 36 segment scores let Dijkstra route around specific dangerous 100-500km segments rather than avoiding entire highways.

---

## 🗣 Interview Talking Points

**"Tell me about Kafka"**
> "I used Kafka in KRaft mode — no Zookeeper dependency — as the event bus between my weather/news ingestion layer and Spark processing. The producer fetches 3 APIs for 35 cities and pushes 35 JSON events per run. The consumer reads with earliest offset reset, guaranteeing no data loss even if it crashes mid-run."

**"What's MCP?"**
> "Model Context Protocol — Anthropic's standard for exposing tools to AI models. I wrapped my FastAPI endpoints as MCP tools with a /mcp schema descriptor endpoint. My LangGraph agent calls these tools the same way Claude would — structured tool calls with typed inputs and outputs."

**"Explain your MLOps setup"**
> "I have a feedback loop: user delay reports go into a SQLite feedback table. An Airflow retrain_dag runs weekly, checks if there are 5+ new feedback records, merges them with the base training data, retrains all 3 models, and logs a new MLflow experiment. The next Spark run automatically uses the updated models."

**"Why 78% accuracy, not higher?"**
> "78% on 20,000 real NHAI road incident records is genuine. I previously got 98% on purely synthetic data — that's the model memorizing rules, not learning patterns. Real road accidents have noise, confounders, and edge cases that reduce accuracy but make the model actually useful in production. The 5-fold CV stability (76.6% ± 1.7%) confirms it's not overfitting."

**"What's LangGraph?"**
> "LangGraph is a stateful multi-step agent framework. My agent has 4 nodes: fetch highway risk data → detect city pairs in the user's query → call Dijkstra router if cities found → send all context to Groq LLaMA-3.3-70B. It's not just LLM call — it's a reasoning pipeline that pulls live data before answering."

---

---

## 🔮 Future Enhancements

- **Weather Forecast Integration** — Use 5-day forecast instead of current weather for future shipment dates
- **NHAI Real-Time API** — Direct integration with NHAI incident feeds
- **Rail Mode Comparison** — Compare road vs rail risk + cost + time
- **Toll Fare Updates** — Dynamic toll rates via NHAI FASTag data
- **WebSocket Live Updates** — Push risk score changes to all open dashboards simultaneously
- **WhatsApp Alerts** — Proactive HIGH risk alerts via Twilio sandbox
- **Confidence Calibration** — Isotonic regression to calibrate ensemble probabilities

---

## 👨‍💻 Author

Built as a portfolio project demonstrating end-to-end data engineering + MLOps + agentic AI skills.

**Tech keywords for recruiters:** Apache Kafka · Apache Spark · Apache Airflow · XGBoost · LightGBM · Ensemble ML · SHAP · MLflow · LangGraph · Groq · FastAPI · MCP · Dijkstra · React · Docker · Python

---

## 📄 License

MIT License — free to use, modify, and distribute.
