#!/usr/bin/env python3
"""
Autonomous Closed-Loop EnergyPlus Simulation Runner.
Executes the COMPLETE Sense -> Think -> Act -> Repeat loop inside ONE single EnergyPlus process.
NO HUMAN INTERVENTION.
"""

import sys
import os
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WEATHER_FILE, OUTPUTS_AI_DIR
from energyplus.environment import setup_energyplus_path
from agent.autonomous_controller import AutonomousBuildingController
from communication.tool_registry import default_tool_registry

RUN_ID = f"auto-run-{int(time.time())}"

def main() -> int:
    print("=" * 75)
    print(f"     ECO-LOOP AUTONOMOUS CLOSED-LOOP EXECUTION [Run ID: {RUN_ID}]")
    print("=" * 75)
    print("  Engine:               Qwen2.5-0.5B-Instruct-Q3_K_S.gguf (via llama-cpp-python)")
    print("  Simulation:           DOE RefBldgSmallOfficeNew2004 (Chicago TMY3)")
    print("  Mode:                 100% Autonomous (Zero Human Intervention)")
    print("=" * 75 + "\n")

    # 1. Verify PyEnergyPlus Path
    success, msg = setup_energyplus_path()
    if not success:
        print(f"[ERROR] {msg}")
        return 1

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()

    # 2. Instantiate Autonomous Controller
    # Configure decision cycles across representative occupied daytime hours
    controller = AutonomousBuildingController(
        run_id=RUN_ID,
        target_zone="CORE_ZN",
        decision_interval_steps=4,
        max_decisions=8
    )

    # 3. Create SINGLE EnergyPlus Simulation State
    state = api.state_manager.new_state()

    # 4. Register Callbacks inside SAME process
    api.runtime.callback_begin_zone_timestep_before_init_heat_balance(
        state, lambda s: controller.control_callback(api, s)
    )
    api.runtime.callback_end_zone_timestep_after_zone_reporting(
        state, lambda s: controller.observation_callback(api, s)
    )

    idf_path = str(PROJECT_ROOT / "models" / "modified" / "control_ready.idf")
    epw_path = str(WEATHER_FILE)
    out_dir = str(OUTPUTS_AI_DIR)
    os.makedirs(out_dir, exist_ok=True)

    print("Beginning Continuous Single-Process EnergyPlus Simulation...\n")
    t0 = time.time()
    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", out_dir, "-w", epw_path, idf_path])
    api.state_manager.delete_state(state)
    sim_runtime = time.time() - t0

    print("\n" + "=" * 75)
    print(" SIMULATION RUN COMPLETED")
    print("=" * 75)
    print(f" Exit Code:                    {exit_code}")
    print(f" Total Runtime:                 {sim_runtime:.2f} seconds")
    print(f" Autonomous Decisions:          {controller.decision_counter}")
    print(f"   - MAINTAIN Decisions:        {controller.count_maintain}")
    print(f"   - Non-MAINTAIN ECM Decisions:{controller.count_non_maintain}")
    print(f"   - Rejected / Fallback:       {controller.count_rejected}")
    print(f"   - Actuator Actions Applied:  {controller.count_applied}")
    print(f"   - Post-Action Live Snapshots:{controller.count_post_action_snapshots}")
    print(f"   - Subsequent Decisions:      {controller.count_subsequent_decisions_after_action}")
    print("=" * 75)

    # 5. Save Logs
    controller.save_all_logs(OUTPUTS_AI_DIR)
    print(f"[OK] Telemetry CSV saved to:       {OUTPUTS_AI_DIR / 'live_telemetry.csv'}")
    print(f"[OK] Control Actions CSV saved to: {OUTPUTS_AI_DIR / 'control_actions.csv'}")
    print(f"[OK] Agent Decisions log saved to: {OUTPUTS_AI_DIR / 'agent_decisions.jsonl'}")

    # 6. Automatic Runtime Error Extraction via Agent Tool
    err_log = OUTPUTS_AI_DIR / "eplusout.err"
    if err_log.is_file():
        err_summary = default_tool_registry.execute_tool("extract_runtime_errors", err_file_path=str(err_log))
        print("-" * 75)
        print(" AUTOMATIC RUNTIME ERROR SUMMARY (eplusout.err):")
        print(f"   - Completion Status:  {err_summary.get('completion_message')}")
        print(f"   - Warnings Count:     {err_summary.get('warning_count')}")
        print(f"   - Severe Error Count: {err_summary.get('severe_count')}")
        print(f"   - Fatal Error Count:  {err_summary.get('fatal_count')}")
        print("-" * 75)

    if exit_code == 0 and controller.decision_counter >= 3:
        print(f"\n>> AUTONOMOUS CLOSED LOOP VERIFIED! [Run ID: {RUN_ID}] <<\n")
        return 0
    else:
        print(f"\n>> FAILURE: AUTONOMOUS CLOSED LOOP ENCOUNTERED ISSUES! [Run ID: {RUN_ID}] <<\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
