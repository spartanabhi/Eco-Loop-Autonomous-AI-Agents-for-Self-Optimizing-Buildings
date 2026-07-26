"""
Autonomous AI Evaluation Runner Module.
Executes autonomous AI-controlled EnergyPlus simulation for the 3-day evaluation period (Jan 21 - Jan 23).
Uses local Qwen LLM supervisory reasoning inside ONE continuous EnergyPlus process.
"""

import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import (
    AI_CONTROLLED_IDF, WEATHER_FILE, AI_OUTPUT_DIR, AGENT_DECISION_INTERVAL_STEPS, TARGET_ZONE
)
from energyplus.environment import setup_energyplus_path
from agent.autonomous_controller import AutonomousBuildingController
from communication.tool_registry import default_tool_registry

RUN_ID = f"eval-ai-{int(time.time())}"

def main() -> int:
    print("=" * 75)
    print(f"     ECO-LOOP AUTONOMOUS AI EVALUATION EXECUTION [Run ID: {RUN_ID}]")
    print("=" * 75)
    print(f"  Model:                control_ready.idf (Autonomous AI Control Active)")
    print(f"  Engine:               Qwen2.5-0.5B-Instruct-Q3_K_S.gguf (via llama-cpp-python)")
    print(f"  Weather:              Chicago O'Hare TMY3 (Jan 21 - Jan 23)")
    print(f"  Mode:                 100% Autonomous (Zero Human Intervention)")
    print("=" * 75 + "\n")

    success, msg = setup_energyplus_path()
    if not success:
        print(f"[ERROR] {msg}")
        return 1

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()

    # Instantiate Autonomous Controller across the 3-day evaluation period
    controller = AutonomousBuildingController(
        run_id=RUN_ID,
        target_zone=TARGET_ZONE,
        decision_interval_steps=AGENT_DECISION_INTERVAL_STEPS,
        max_decisions=None  # Continuous coverage across evaluation period
    )

    state = api.state_manager.new_state()

    api.runtime.callback_begin_zone_timestep_before_init_heat_balance(
        state, lambda s: controller.control_callback(api, s)
    )
    api.runtime.callback_end_zone_timestep_after_zone_reporting(
        state, lambda s: controller.observation_callback(api, s)
    )

    AI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_dir = str(AI_OUTPUT_DIR)
    idf_path = str(AI_CONTROLLED_IDF)
    epw_path = str(WEATHER_FILE)

    t0 = time.time()
    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", out_dir, "-w", epw_path, idf_path])
    api.state_manager.delete_state(state)
    sim_runtime = time.time() - t0

    print("\n" + "=" * 75)
    print(" AUTONOMOUS AI EVALUATION SIMULATION COMPLETED")
    print("=" * 75)
    print(f" Exit Code:                    {exit_code}")
    print(f" Simulation Runtime:           {sim_runtime:.2f} seconds")
    print(f" Total Autonomous Decisions:   {controller.decision_counter}")
    print(f"   - MAINTAIN Decisions:       {controller.count_maintain}")
    print(f"   - Non-MAINTAIN ECM Actions: {controller.count_non_maintain}")
    print(f"   - Rejected / Fallback:      {controller.count_rejected}")
    print(f"   - Actuator Actions Applied: {controller.count_applied}")
    print(f"   - Post-Action Live Snapshots:{controller.count_post_action_snapshots}")
    print(f"   - Subsequent Decisions:     {controller.count_subsequent_decisions_after_action}")
    print("=" * 75)

    controller.save_all_logs(AI_OUTPUT_DIR)
    print(f"[OK] AI telemetry CSV saved to:       {AI_OUTPUT_DIR / 'live_telemetry.csv'}")
    print(f"[OK] AI control actions CSV saved to: {AI_OUTPUT_DIR / 'control_actions.csv'}")
    print(f"[OK] Agent decisions JSONL saved to:  {AI_OUTPUT_DIR / 'agent_decisions.jsonl'}")

    err_log = AI_OUTPUT_DIR / "eplusout.err"
    if err_log.is_file():
        err_summary = default_tool_registry.execute_tool("extract_runtime_errors", err_file_path=str(err_log))
        print("-" * 75)
        print(" AI RUNTIME ERROR SUMMARY (eplusout.err):")
        print(f"   - Completion Status:  {err_summary.get('completion_message')}")
        print(f"   - Warnings Count:     {err_summary.get('warning_count')}")
        print(f"   - Severe Error Count: {err_summary.get('severe_count')}")
        print(f"   - Fatal Error Count:  {err_summary.get('fatal_count')}")
        print("-" * 75)

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
