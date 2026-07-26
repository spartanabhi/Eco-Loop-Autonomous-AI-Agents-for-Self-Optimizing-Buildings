"""
Integration Tests for Local Open-Source Qwen LLM Agent.
Verifies local GGUF inference, JSON schema parsing, safety validation, and latency recording.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.llm_client import LocalQwenLLMClient
from agent.prompts import SYSTEM_PROMPT, format_user_prompt
from agent.orchestrator import AgentOrchestrator
from energyplus.telemetry import TelemetrySnapshot

def test_local_llm_client_inference():
    """Test LocalQwenLLMClient loads GGUF model and generates structured JSON response."""
    client = LocalQwenLLMClient()
    loaded, msg = client.load_model()
    assert loaded, f"Failed to load GGUF model: {msg}"

    user_prompt = format_user_prompt(
        simulation_time="Day 21 14:00",
        zone="CORE_ZN",
        temperature=21.0,
        pmv=0.0,
        comfort_status="COMFORTABLE",
        co2_ppm=500.0,
        co2_status="GOOD",
        demand_kw=8.0,
        peak_status="NORMAL",
        carbon_status="MEDIUM",
        current_heating_sp=21.0,
        current_cooling_sp=24.0
    )

    success, raw_dict, latency, err = client.generate_decision(SYSTEM_PROMPT, user_prompt)
    assert success, f"LLM generation failed: {err}"
    assert isinstance(raw_dict, dict), "Raw response is not a dict"
    assert latency > 0.0, "Latency was not recorded"
    assert any(k.lower() == "action" for k in raw_dict.keys()), f"Action field missing from JSON: {raw_dict}"
    print(f"[PASS] test_local_llm_client_inference (Latency: {latency:.2f}s, Output: {raw_dict})")

def test_agent_orchestrator_decision():
    """Test AgentOrchestrator processes a TelemetrySnapshot and produces a validated decision."""
    orchestrator = AgentOrchestrator()
    snapshot = TelemetrySnapshot(
        callback_index=1,
        simulation_time="Day 21 14:00",
        month=1,
        day=21,
        hour=14,
        minute=0,
        zone_temperatures={"CORE_ZN": 24.5},
        zone_co2={"CORE_ZN": 550.0},
        zone_pmv={"CORE_ZN": 0.2},
        facility_electricity_joules=12500000.0,
        facility_electricity_kwh=3.47
    )

    res = orchestrator.process_snapshot(snapshot, zone="CORE_ZN", current_htg_sp=21.0, current_clg_sp=24.0)
    assert res["status"] == "success", f"Orchestrator failed: {res}"
    assert res["schema_passed"], f"Schema validation failed: {res}"
    assert res["safety_passed"], f"Safety validation failed: {res}"
    assert "decision" in res, "Decision dict missing"
    assert "proposed_tool" in res, "Proposed tool missing"
    print(f"[PASS] test_agent_orchestrator_decision (Action: {res['decision']['action']}, Tool: {res['proposed_tool']}, Latency: {res['total_latency_seconds']:.2f}s)")

if __name__ == "__main__":
    test_local_llm_client_inference()
    test_agent_orchestrator_decision()
    print("\nAll local open-source LLM agent integration tests passed successfully.")
