"""
Baseline Evaluation Runner Module.
Executes native baseline EnergyPlus simulation for the 3-day evaluation period (Jan 21 - Jan 23).
No actuator writes or AI overrides.
"""

import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import (
    BASELINE_IDF, WEATHER_FILE, BASELINE_OUTPUT_DIR
)
from energyplus.environment import setup_energyplus_path
from energyplus.telemetry import TelemetryManager
from communication.tool_registry import default_tool_registry

RUN_ID = f"eval-baseline-{int(time.time())}"

def main() -> int:
    print("=" * 75)
    print(f"     ECO-LOOP BASELINE EVALUATION EXECUTION [Run ID: {RUN_ID}]")
    print("=" * 75)
    print(f"  Model:                evaluation_baseline.idf (Native Baseline Operation)")
    print(f"  Weather:              Chicago O'Hare TMY3 (Jan 21 - Jan 23)")
    print(f"  Actuator Overrides:   NONE (0 Overrides)")
    print("=" * 75 + "\n")

    success, msg = setup_energyplus_path()
    if not success:
        print(f"[ERROR] {msg}")
        return 1

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()

    telemetry_mgr = TelemetryManager()
    state = api.state_manager.new_state()

    def obs_cb(s):
        if not api.exchange.api_data_fully_ready(s):
            return
        telemetry_mgr.capture_snapshot(api, s)

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, obs_cb)

    BASELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_dir = str(BASELINE_OUTPUT_DIR)
    idf_path = str(BASELINE_IDF)
    epw_path = str(WEATHER_FILE)

    t0 = time.time()
    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", out_dir, "-w", epw_path, idf_path])
    api.state_manager.delete_state(state)
    sim_runtime = time.time() - t0

    print("\n" + "=" * 75)
    print(" BASELINE EVALUATION SIMULATION COMPLETED")
    print("=" * 75)
    print(f" Exit Code:             {exit_code}")
    print(f" Simulation Runtime:    {sim_runtime:.2f} seconds")
    print(f" Telemetry Snapshots:   {len(telemetry_mgr.snapshots)}")
    print("=" * 75)

    telemetry_mgr.save_telemetry_csv(str(BASELINE_OUTPUT_DIR / "live_telemetry.csv"))
    print(f"[OK] Baseline telemetry CSV saved to: {BASELINE_OUTPUT_DIR / 'live_telemetry.csv'}")

    err_log = BASELINE_OUTPUT_DIR / "eplusout.err"
    if err_log.is_file():
        err_summary = default_tool_registry.execute_tool("extract_runtime_errors", err_file_path=str(err_log))
        print("-" * 75)
        print(" BASELINE RUNTIME ERROR SUMMARY (eplusout.err):")
        print(f"   - Completion Status:  {err_summary.get('completion_message')}")
        print(f"   - Warnings Count:     {err_summary.get('warning_count')}")
        print(f"   - Severe Error Count: {err_summary.get('severe_count')}")
        print(f"   - Fatal Error Count:  {err_summary.get('fatal_count')}")
        print("-" * 75)

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
