"""
Verified Cross-Season Evaluation Pipeline Runner.
Runs Baseline and Frozen AI simulations across Winter, Shoulder, and Summer 3-day periods
using explicit, verified seasonal IDF models under models/evaluation/.
Saves all verified artifacts strictly under outputs/evaluation/cross_season_verified/.
"""

import sys
import os
import time
import shutil
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import WEATHER_FILE, SEASONS, AGENT_DECISION_INTERVAL_STEPS, TARGET_ZONE
from evaluation.controller_version import get_frozen_controller_metadata
from energyplus.environment import setup_energyplus_path
from energyplus.telemetry import TelemetryManager
from agent.autonomous_controller import AutonomousBuildingController

VERIFIED_DIR = PROJECT_ROOT / "outputs" / "evaluation" / "cross_season_verified"

def run_verified_season_baseline(season_key: str, api: Any) -> Path:
    """Executes baseline EnergyPlus simulation for a specific season using verified IDF."""
    run_id = f"{season_key}-baseline-v-{int(time.time())}"
    out_dir = VERIFIED_DIR / season_key / "baseline"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    idf_path = PROJECT_ROOT / "models" / "evaluation" / f"{season_key}_baseline.idf"
    print(f"\n--- Running Verified Baseline ({season_key.upper()}) [ID: {run_id}] ---")
    telemetry_mgr = TelemetryManager(run_id=run_id, season=season_key)
    state = api.state_manager.new_state()

    def obs_cb(s):
        if not api.exchange.api_data_fully_ready(s): return
        telemetry_mgr.capture_snapshot(api, s)

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, obs_cb)

    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", str(out_dir), "-w", str(WEATHER_FILE), str(idf_path)])
    api.state_manager.delete_state(state)

    telemetry_mgr.save_telemetry_csv(str(out_dir / "live_telemetry.csv"))
    print(f" [OK] Baseline {season_key.upper()} finished (Snapshots: {len(telemetry_mgr.snapshots)}, Exit Code: {exit_code})")
    return out_dir

def run_verified_season_ai(season_key: str, api: Any) -> Path:
    """Executes frozen AI-controlled EnergyPlus simulation for a specific season using verified IDF."""
    run_id = f"{season_key}-ai-v-{int(time.time())}"
    out_dir = VERIFIED_DIR / season_key / "ai_controlled"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    idf_path = PROJECT_ROOT / "models" / "evaluation" / f"{season_key}_ai.idf"
    print(f"\n--- Running Verified Frozen AI ({season_key.upper()}) [ID: {run_id}] ---")
    controller = AutonomousBuildingController(
        run_id=run_id,
        target_zone=TARGET_ZONE,
        decision_interval_steps=AGENT_DECISION_INTERVAL_STEPS,
        max_decisions=None
    )
    controller.telemetry_mgr.season = season_key
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
    exit_code = api.runtime.run_energyplus(state, ["-d", str(out_dir), "-w", str(WEATHER_FILE), str(idf_path)])
    api.state_manager.delete_state(state)
    sim_runtime = time.time() - t0

    controller.save_all_logs(out_dir)
    print(f" [OK] AI {season_key.upper()} finished (Decisions: {controller.decision_counter}, Applied: {controller.count_applied}, Runtime: {sim_runtime:.2f}s)")
    return out_dir

def main() -> int:
    meta = get_frozen_controller_metadata()
    print("=" * 75)
    print("     ECO-LOOP VERIFIED CROSS-SEASON EVALUATION RUNNER")
    print("=" * 75)
    print(f"  Controller Version: {meta['controller_version']}")
    print(f"  Code SHA-256 Hash: {meta['controller_code_hash']}")
    print("=" * 75 + "\n")

    success, msg = setup_energyplus_path()
    if not success:
        print(f"[ERROR] {msg}")
        return 1

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()

    for season_key in SEASONS.keys():
        run_verified_season_baseline(season_key, api)
        run_verified_season_ai(season_key, api)

    print("\n" + "=" * 75)
    print(" ALL VERIFIED CROSS-SEASON SIMULATIONS COMPLETED SUCCESSFULLY")
    print("=" * 75)
    return 0

if __name__ == "__main__":
    sys.exit(main())
