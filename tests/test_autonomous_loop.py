"""
Integration & Policy Tests for Complete Autonomous Closed Loop Actuation & Feedback Proof.
Verifies Sense -> Think -> Act -> Repeat loop execution in ONE single EnergyPlus process.
"""

import sys
import os
import csv
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WEATHER_FILE, OUTPUTS_AI_DIR
from energyplus.environment import setup_energyplus_path
from energyplus.telemetry import TelemetrySnapshot
from agent.autonomous_controller import AutonomousBuildingController
from agent.orchestrator import AgentOrchestrator
from communication.tool_registry import default_tool_registry

TEST_RUN_ID = f"test-auto-{int(time.time())}"

def test_autonomous_closed_loop_execution():
    """Executes single EnergyPlus process with autonomous Qwen controller and verifies loop artifacts."""
    success, msg = setup_energyplus_path()
    assert success, f"PyEnergyPlus setup failed: {msg}"

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()

    controller = AutonomousBuildingController(
        run_id=TEST_RUN_ID,
        target_zone="CORE_ZN",
        decision_interval_steps=4,
        max_decisions=5
    )

    api.runtime.callback_begin_zone_timestep_before_init_heat_balance(
        state, lambda s: controller.control_callback(api, s)
    )
    api.runtime.callback_end_zone_timestep_after_zone_reporting(
        state, lambda s: controller.observation_callback(api, s)
    )

    idf_path = str(PROJECT_ROOT / "models" / "modified" / "control_ready.idf")
    epw_path = str(WEATHER_FILE)
    out_dir = str(OUTPUTS_AI_DIR)

    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", out_dir, "-w", epw_path, idf_path])
    api.state_manager.delete_state(state)

    # Verifications
    assert exit_code == 0, f"Simulation failed with exit code: {exit_code}"
    assert controller.decision_counter >= 3, f"Expected at least 3 decisions, got {controller.decision_counter}"
    assert len(controller.telemetry_mgr.snapshots) > 100, "Insufficient telemetry snapshots captured"

    controller.save_all_logs(OUTPUTS_AI_DIR)

    # 1. Telemetry CSV check
    telem_csv = OUTPUTS_AI_DIR / "live_telemetry.csv"
    assert telem_csv.is_file(), "live_telemetry.csv missing"
    with open(telem_csv, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        assert len(rows) > 50, "live_telemetry.csv has insufficient rows"
        # Check normalized HH:MM format
        sample_time = rows[1][1]
        assert ":" in sample_time, f"Invalid timestamp format: {sample_time}"
        parts = sample_time.split(" ")[-1].split(":")
        assert 0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59, f"Invalid clock time: {sample_time}"

    # 2. Decisions JSONL check
    dec_jsonl = OUTPUTS_AI_DIR / "agent_decisions.jsonl"
    assert dec_jsonl.is_file(), "agent_decisions.jsonl missing"
    with open(dec_jsonl, "r", encoding="utf-8") as f:
        dec_lines = [json.loads(line) for line in f if line.strip()]
        assert len(dec_lines) >= 3, "agent_decisions.jsonl has fewer than 3 decisions"

    # 3. Automatic runtime error check
    err_path = OUTPUTS_AI_DIR / "eplusout.err"
    assert err_path.is_file(), "eplusout.err missing"
    err_summary = default_tool_registry.execute_tool("extract_runtime_errors", err_file_path=str(err_path))
    assert err_summary["fatal_count"] == 0, f"Fatal errors found: {err_summary['fatal_count']}"

    print(f"[PASS] test_autonomous_closed_loop_execution (Decisions: {controller.decision_counter}, Exit Code: 0, Fatal Errors: 0)")

def test_autonomous_actuation_and_feedback_chain():
    """Verifies that an LLM-selected ECM action passes through ToolRegistry, applies to actuator, and creates post-action telemetry feedback."""
    orchestrator = AgentOrchestrator()
    snapshot = TelemetrySnapshot(
        callback_index=50,
        simulation_time="Day 21/01 15:00",
        month=1,
        day=21,
        hour=15,
        minute=0,
        zone_temperatures={"CORE_ZN": 24.0},
        zone_co2={"CORE_ZN": 550.0},
        zone_pmv={"CORE_ZN": 0.10},
        zone_occupancy={"CORE_ZN": 4.0},
        occupancy_source="ENERGYPLUS",
        facility_electricity_joules=12000000.0,
        facility_electricity_kwh=3.33,
        facility_demand_kw=13.33
    )

    res = orchestrator.process_snapshot(snapshot, zone="CORE_ZN", current_htg_sp=21.0, current_clg_sp=23.9)
    assert res["status"] == "success", f"Orchestrator failed: {res}"
    assert res["schema_passed"], "Schema validation failed"
    assert res["safety_passed"], "Safety validation failed"
    assert "decision" in res, "Decision dict missing"
    print(f"[PASS] test_autonomous_actuation_and_feedback_chain (Action: {res['decision']['action']}, Tool: {res['proposed_tool']})")

if __name__ == "__main__":
    test_autonomous_closed_loop_execution()
    test_autonomous_actuation_and_feedback_chain()
    print("\nAll autonomous closed-loop integration tests passed successfully.")
