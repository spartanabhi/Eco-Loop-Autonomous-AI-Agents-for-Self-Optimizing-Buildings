#!/usr/bin/env python3
"""
Baseline EnergyPlus Simulation Execution Script.
Executes baseline.idf with weather.epw via PyEnergyPlus API and validates output artifacts.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BASELINE_IDF, WEATHER_FILE, OUTPUTS_BASELINE_DIR
from energyplus.environment import find_energyplus
from energyplus.runner import EnergyPlusRunnerFoundation

def main() -> int:
    print("=" * 60)
    print("   Eco-Loop Baseline Simulation Execution")
    print("=" * 60)
    print()

    # 1. Validate EnergyPlus
    ep_info = find_energyplus()
    if not ep_info["installed"]:
        print("[ERROR] EnergyPlus installation not detected.")
        return 1
    print(f"[OK] EnergyPlus detected at: {ep_info['home']}")

    # 2. Validate Baseline IDF
    if not BASELINE_IDF.is_file():
        print(f"[ERROR] Baseline IDF not found at: {BASELINE_IDF}")
        return 1
    print(f"[OK] Baseline IDF verified: {BASELINE_IDF}")

    # 3. Validate EPW Weather File
    if not WEATHER_FILE.is_file():
        print(f"[ERROR] Weather file not found at: {WEATHER_FILE}")
        return 1
    print(f"[OK] Weather file verified: {WEATHER_FILE}")

    # 4. Prepare Output Directory
    os.makedirs(OUTPUTS_BASELINE_DIR, exist_ok=True)
    print(f"[OK] Output directory ready: {OUTPUTS_BASELINE_DIR}")
    print()

    # 5. Execute Simulation
    print("Starting EnergyPlus Baseline Simulation...")
    runner = EnergyPlusRunnerFoundation()
    
    try:
        exit_code = runner.run_simulation(
            idf_path=str(BASELINE_IDF),
            epw_path=str(WEATHER_FILE),
            output_dir=str(OUTPUTS_BASELINE_DIR)
        )
    except Exception as e:
        print(f"[FATAL] Simulation failed with exception: {e}")
        return 1

    print(f"[COMPLETE] Simulation finished with Exit Code: {exit_code}")
    print()

    # 6. Parse and Report Error Log
    err_report = runner.parse_error_log(str(OUTPUTS_BASELINE_DIR))
    print("Execution Log Summary:")
    print(f"  - Summary: {err_report['summary']}")
    print(f"  - Warnings: {err_report['warnings']}")
    print(f"  - Severe Errors: {err_report['severe']}")
    print(f"  - Fatal Errors: {err_report['fatal']}")
    print()

    # 7. Check Generated Artifacts
    csv_file = OUTPUTS_BASELINE_DIR / "eplusout.csv"
    eso_file = OUTPUTS_BASELINE_DIR / "eplusout.eso"
    err_file = OUTPUTS_BASELINE_DIR / "eplusout.err"

    print("Generated Artifacts:")
    for name, path in [("CSV Report", csv_file), ("ESO Data", eso_file), ("Error Log", err_file)]:
        if path.is_file():
            size_kb = path.stat().st_size / 1024.0
            print(f"  [OK] {name}: {path.name} ({size_kb:.1f} KB)")
        else:
            print(f"  [MISSING] {name}: {path.name}")

    if exit_code == 0 and err_report["fatal"] == 0:
        print("\n>> SUCCESS: Baseline simulation completed cleanly! <<")
        return 0
    else:
        print("\n>> FAILURE: Baseline simulation encountered fatal errors. <<")
        return 1

if __name__ == "__main__":
    sys.exit(main())
