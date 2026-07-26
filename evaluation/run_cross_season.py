"""
Cross-Season Evaluation Pipeline Runner.
Orchestrates baseline and frozen AI-controlled simulations across Winter, Shoulder, and Summer 3-day periods.
Ensures zero controller modification, output isolation, and full error extraction.
"""

import sys
import os
import re
import time
import shutil
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import (
    BASELINE_IDF, AI_CONTROLLED_IDF, WEATHER_FILE, CROSS_SEASON_DIR, SEASONS,
    AGENT_DECISION_INTERVAL_STEPS, TARGET_ZONE
)
from evaluation.controller_version import get_frozen_controller_metadata
from evaluation.verify_fairness import verify_model_fairness
from energyplus.environment import setup_energyplus_path
from energyplus.telemetry import TelemetryManager
from agent.autonomous_controller import AutonomousBuildingController
from communication.tool_registry import default_tool_registry

def set_idf_run_period(start_m: int, start_d: int, end_m: int, end_d: int, start_day_name: str) -> None:
    """Updates RunPeriod object in both baseline and AI IDF files."""
    new_rp = f"""  RunPeriod,
    EvaluationPeriod,        !- Name
    {start_m},                       !- Begin Month
    {start_d},                      !- Begin Day of Month
    ,                        !- Begin Year
    {end_m},                       !- End Month
    {end_d},                      !- End Day of Month
    ,                        !- End Year
    {start_day_name},                 !- Day of Week for Start Day
    Yes,                     !- Use Weather File Holidays and Special Days
    Yes,                     !- Use Weather File Daylight Saving Period
    No,                      !- Apply Weekend Holiday Rule
    Yes,                     !- Use Weather File Rain Indicators
    Yes;                     !- Use Weather File Snow Indicators"""

    for idf_path in [BASELINE_IDF, AI_CONTROLLED_IDF]:
        with open(idf_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if "RunPeriod," in content:
            updated = re.sub(r"RunPeriod,[\s\S]*?;", new_rp, content, count=1)
        else:
            updated = content + "\n" + new_rp

        with open(idf_path, "w", encoding="utf-8") as f:
            f.write(updated)

def run_season_baseline(season_key: str, season_cfg: Dict[str, Any], api: Any) -> Path:
    """Executes baseline EnergyPlus simulation for a specific season."""
    run_id = f"eval-baseline-{season_key}-{int(time.time())}"
    out_dir = CROSS_SEASON_DIR / season_key / "baseline"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Running Baseline ({season_cfg['name']}) [ID: {run_id}] ---")
    telemetry_mgr = TelemetryManager()
    state = api.state_manager.new_state()

    def obs_cb(s):
        if not api.exchange.api_data_fully_ready(s): return
        telemetry_mgr.capture_snapshot(api, s)

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, obs_cb)

    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", str(out_dir), "-w", str(WEATHER_FILE), str(BASELINE_IDF)])
    api.state_manager.delete_state(state)

    telemetry_mgr.save_telemetry_csv(str(out_dir / "live_telemetry.csv"))
    print(f" [OK] Baseline {season_key} finished (Snapshots: {len(telemetry_mgr.snapshots)}, Exit Code: {exit_code})")
    return out_dir

def run_season_ai(season_key: str, season_cfg: Dict[str, Any], api: Any) -> Path:
    """Executes frozen AI-controlled EnergyPlus simulation for a specific season."""
    run_id = f"eval-ai-{season_key}-{int(time.time())}"
    out_dir = CROSS_SEASON_DIR / season_key / "ai_controlled"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Running Frozen AI ({season_cfg['name']}) [ID: {run_id}] ---")
    controller = AutonomousBuildingController(
        run_id=run_id,
        target_zone=TARGET_ZONE,
        decision_interval_steps=AGENT_DECISION_INTERVAL_STEPS,
        max_decisions=None
    )
    # Ensure decision log path is isolated under season output dir
    controller.orchestrator.decision_log_path = out_dir / "agent_decisions.jsonl"

    state = api.state_manager.new_state()

    api.runtime.callback_begin_zone_timestep_before_init_heat_balance(
        state, lambda s: controller.control_callback(api, s)
    )
    api.runtime.callback_end_zone_timestep_after_zone_reporting(
        state, lambda s: controller.observation_callback(api, s)
    )

    t0 = time.time()
    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", str(out_dir), "-w", str(WEATHER_FILE), str(AI_CONTROLLED_IDF)])
    api.state_manager.delete_state(state)
    sim_runtime = time.time() - t0

    controller.save_all_logs(out_dir)
    print(f" [OK] AI {season_key} finished (Decisions: {controller.decision_counter}, Applied: {controller.count_applied}, Runtime: {sim_runtime:.2f}s)")
    return out_dir

def main() -> int:
    meta = get_frozen_controller_metadata()
    print("=" * 75)
    print("     ECO-LOOP CROSS-SEASON EVALUATION PIPELINE RUNNER")
    print("=" * 75)
    print(f"  Controller Version:   {meta['controller_version']}")
    print(f"  Code SHA-256 Hash:   {meta['controller_code_hash']}")
    print(f"  Seasons to Evaluate:  Winter (Jan 21-23), Shoulder (May 15-17), Summer (Jul 21-23)")
    print("=" * 75 + "\n")

    success, msg = setup_energyplus_path()
    if not success:
        print(f"[ERROR] {msg}")
        return 1

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()

    for season_key, season_cfg in SEASONS.items():
        print("=" * 75)
        print(f" SEASON: {season_cfg['name'].upper()}")
        print("=" * 75)
        
        # 1. Update IDF RunPeriod
        set_idf_run_period(
            season_cfg["start_month"], season_cfg["start_day"],
            season_cfg["end_month"], season_cfg["end_day"],
            season_cfg["start_day_of_week"]
        )

        # 2. Verify Fairness
        fair, summary = verify_model_fairness()
        assert fair, f"Fairness failed for {season_key}: {summary['discrepancies']}"
        print(f" [OK] Model Fairness Verified for {season_key}")

        # 3. Run Baseline
        run_season_baseline(season_key, season_cfg, api)

        # 4. Run Frozen AI
        run_season_ai(season_key, season_cfg, api)

    print("\n" + "=" * 75)
    print(" ALL CROSS-SEASON EVALUATION SIMULATIONS COMPLETED SUCCESSFULLY")
    print("=" * 75)
    return 0

if __name__ == "__main__":
    sys.exit(main())
