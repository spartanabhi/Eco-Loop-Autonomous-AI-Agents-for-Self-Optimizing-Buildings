"""
Policy Iteration 2 Closed-Loop Execution Runner.
Executes Summer, Winter, and Shoulder AI runs using policy_iter2_candidate.
Saves all outputs under outputs/evaluation/policy_iter2/.
"""

import sys
import os
import time
import json
import shutil
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import WEATHER_FILE, SEASONS, AGENT_DECISION_INTERVAL_STEPS, TARGET_ZONE
from energyplus.environment import setup_energyplus_path
from agent.autonomous_controller import AutonomousBuildingController
from agent.orchestrator_v2 import AgentOrchestratorV2

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "evaluation" / "policy_iter2"

def run_ai_simulation(season_name: str, api: Any) -> Path:
    """Executes a single verified AI simulation run with policy_iter2_candidate."""
    idf_path = PROJECT_ROOT / "models" / "evaluation" / f"{season_name}_ai.idf"
    if not idf_path.is_file():
        raise FileNotFoundError(f"IDF missing: {idf_path}")

    timestamp_str = str(int(time.time()))
    run_id = f"{season_name}-ai-v2-{timestamp_str}"
    run_output_dir = OUTPUT_DIR / season_name / "ai_controlled"
    
    # Use temporary run dir if main dir locked
    actual_out_dir = run_output_dir
    if actual_out_dir.exists():
        try:
            for f in actual_out_dir.glob("*"):
                if f.is_file():
                    f.unlink()
        except Exception:
            actual_out_dir = OUTPUT_DIR / season_name / f"ai_controlled_{timestamp_str}"

    actual_out_dir.mkdir(parents=True, exist_ok=True)

    controller = AutonomousBuildingController(
        run_id=run_id,
        target_zone=TARGET_ZONE,
        decision_interval_steps=AGENT_DECISION_INTERVAL_STEPS,
        max_decisions=None
    )
    controller.telemetry_mgr.season = season_name
    controller.orchestrator = AgentOrchestratorV2(policy_version="policy_iter2_candidate")
    controller.orchestrator.decision_log_path = actual_out_dir / "agent_decisions.jsonl"

    state = api.state_manager.new_state()

    print(f"\n--- Running Policy Iteration 2 ({season_name.upper()}) [ID: {run_id}] ---")
    start_time = time.time()

    api.runtime.callback_begin_zone_timestep_before_init_heat_balance(
        state, lambda s: controller.control_callback(api, s)
    )
    api.runtime.callback_end_zone_timestep_after_zone_reporting(
        state, lambda s: controller.observation_callback(api, s)
    )

    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", str(actual_out_dir), "-w", str(WEATHER_FILE), str(idf_path)])
    api.state_manager.delete_state(state)
    elapsed = time.time() - start_time

    if exit_code == 0:
        controller.save_all_logs(actual_out_dir)
        print(f" [OK] AI {season_name.upper()} finished (Decisions: {controller.decision_counter}, Applied: {controller.count_applied}, Runtime: {elapsed:.2f}s)")
        # Copy logs to canonical run_output_dir if using temporary dir
        if actual_out_dir != run_output_dir:
            run_output_dir.mkdir(parents=True, exist_ok=True)
            for f in actual_out_dir.glob("*"):
                if f.is_file():
                    shutil.copy2(f, run_output_dir / f.name)
    else:
        print(f" [ERROR] AI {season_name.upper()} failed with exit code: {exit_code}")

    return run_output_dir

def main() -> int:
    target_season = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    success, msg = setup_energyplus_path()
    if not success:
        print(f"[ERROR] {msg}")
        return 1

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()

    if target_season in ["summer", "all"]:
        run_ai_simulation("summer", api)

    if target_season in ["winter", "all"]:
        run_ai_simulation("winter", api)

    if target_season in ["shoulder", "all"]:
        run_ai_simulation("shoulder", api)

    return 0

if __name__ == "__main__":
    sys.exit(main())
