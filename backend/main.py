"""
FastAPI Main Application for Eco-Loop Building Agents.
Provides REST API endpoints serving validated Policy 2 project artifacts.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List

from backend.state import system_state
from backend.data_service import data_service

app = FastAPI(
    title="Eco-Loop Building Agents API",
    description="Autonomous AI Building Optimization Backend",
    version="2.0.0"
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. HEALTH ---
@app.get("/api/health", tags=["System"])
def get_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "project": "Eco-Loop Building Agents",
        "controller": "policy_iter2_candidate",
        "energyplus_available": True,
        "llm_model_available": True
    }

# --- 2. STATUS ---
@app.get("/api/status", tags=["System"])
def get_status() -> Dict[str, Any]:
    return {
        "simulation_status": system_state.simulation_status,
        "current_run_id": system_state.current_run_id,
        "season": system_state.season,
        "progress_percent": 100.0 if system_state.simulation_status == "IDLE" else 50.0,
        "decision_count": 51,
        "effective_action_count": 48,
        "data_mode": system_state.data_mode
    }

# --- 3. LATEST TELEMETRY ---
@app.get("/api/telemetry/latest", tags=["Telemetry"])
def get_latest_telemetry() -> Dict[str, Any]:
    return data_service.get_latest_telemetry()

# --- 4. TELEMETRY HISTORY ---
@app.get("/api/telemetry/history", tags=["Telemetry"])
def get_telemetry_history(limit: int = Query(100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return data_service.get_telemetry_history(limit=limit)

# --- 5. LATEST AI DECISION ---
@app.get("/api/agent/latest", tags=["Agent"])
def get_latest_decision() -> Dict[str, Any]:
    return data_service.get_latest_decision()

# --- 6. AI DECISION HISTORY ---
@app.get("/api/agent/history", tags=["Agent"])
def get_decision_history(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    return data_service.get_decision_history(limit=limit)

# --- 7. CONTROL ACTIONS ---
@app.get("/api/actions", tags=["Actions"])
def get_actions(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    return data_service.get_action_history(limit=limit)

# --- 8. EVALUATION RESULT ---
@app.get("/api/evaluation", tags=["Evaluation"])
def get_evaluation() -> Dict[str, Any]:
    return data_service.get_evaluation_summary()

# --- 9. HERO RESULT ---
@app.get("/api/evaluation/hero", tags=["Evaluation"])
def get_evaluation_hero() -> Dict[str, Any]:
    return data_service.get_hero_evaluation()

# --- 10. DEMO SEASONS ---
@app.get("/api/seasons", tags=["System"])
def get_seasons() -> List[Dict[str, Any]]:
    return [
        {
            "season": "summer",
            "dates": "Jul 21 – Jul 23",
            "description": "Peak Cooling Season (3.51% electricity reduction, 48 active setpoint adjustments)"
        },
        {
            "season": "shoulder",
            "dates": "May 15 – May 17",
            "description": "Mild Shoulder Season (6 active setpoint adjustments)"
        },
        {
            "season": "winter",
            "dates": "Jan 21 – Jan 23",
            "description": "Heating Season (Occupied comfort compliance gain 29.6% -> 75.9%)"
        }
    ]
