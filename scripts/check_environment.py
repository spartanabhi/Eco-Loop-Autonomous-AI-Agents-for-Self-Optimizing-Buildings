#!/usr/bin/env python3
"""
Eco-Loop Environment Checker Script.
Validates Python runtime, EnergyPlus installation, PyEnergyPlus API access,
and building model / weather file configuration status.
"""

import sys
import os
import platform
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    BASELINE_IDF,
    WEATHER_FILE,
    ENERGYPLUS_HOME,
    ENERGYPLUS_EXECUTABLE,
    ENERGYPLUS_PYTHON_API_PATH
)
from energyplus.environment import find_energyplus, setup_energyplus_path

def main() -> int:
    print("=" * 40)
    print("   Eco-Loop Environment Check")
    print("=" * 40)
    print()

    # 1. Python Check
    py_major = sys.version_info.major
    py_minor = sys.version_info.minor
    py_micro = sys.version_info.micro
    py_str = f"{py_major}.{py_minor}.{py_micro}"
    
    print("Python:")
    if py_major == 3 and py_minor >= 11:
        print(f"  [OK] Python {py_str} (3.11+ preferred requirement met)")
        py_ok = True
    elif py_major == 3:
        print(f"  [OK] Python {py_str}")
        py_ok = True
    else:
        print(f"  [ERROR] Python {py_str} (Python 3.x required)")
        py_ok = False
    print()

    # 2. EnergyPlus Check
    ep_info = find_energyplus()
    print("EnergyPlus:")
    if ep_info["installed"]:
        print(f"  [OK] Installation found at: {ep_info['home']}")
    else:
        print("  [MISSING] Installation not found on system.")

    if ep_info["executable"]:
        print(f"  [OK] Executable found at: {ep_info['executable']}")
    else:
        print("  [MISSING] Executable energyplus not found.")

    if ep_info["version"]:
        print(f"  [OK] Version / Folder: {ep_info['version']}")
    else:
        print("  [MISSING] Version undetectable.")
    print()

    # 3. PyEnergyPlus Import Check
    print("PyEnergyPlus:")
    pyep_ok, import_msg = setup_energyplus_path()
    if pyep_ok:
        print(f"  [OK] {import_msg}")
    else:
        print(f"  [MISSING] {import_msg}")
    print()

    # 4. Building Model Check
    print("Building model:")
    if BASELINE_IDF.is_file():
        print(f"  [OK] Baseline IDF found: {BASELINE_IDF}")
        idf_ok = True
    else:
        print(f"  [WAITING] Baseline IDF file not found at: {BASELINE_IDF}")
        idf_ok = False
    print()

    # 5. Weather File Check
    print("Weather:")
    if WEATHER_FILE.is_file():
        print(f"  [OK] EPW weather file found: {WEATHER_FILE}")
        epw_ok = True
    else:
        print(f"  [WAITING] EPW weather file not found at: {WEATHER_FILE}")
        epw_ok = False
    print()

    # 6. Overall Environment Status
    print("-" * 40)
    print("Environment status:")
    if py_ok and ep_info["installed"] and pyep_ok and idf_ok and epw_ok:
        status = "READY"
        exit_code = 0
    elif py_ok and (ep_info["installed"] or pyep_ok):
        status = "PARTIALLY READY"
        exit_code = 0
    else:
        status = "NOT READY"
        exit_code = 1

    print(f"  >> {status} <<")
    print("-" * 40)

    if not ep_info["installed"] or not pyep_ok:
        print("\n[REQUIREMENT & ACTION REQUIRED]")
        print("EnergyPlus and PyEnergyPlus are required for running live simulations.")
        print("Installation instructions:")
        print("  1. Download EnergyPlus (v23.2.0 or v24.1.0 recommended) from:")
        print("     https://github.com/NREL/EnergyPlus/releases")
        print("  2. Install EnergyPlus to a standard location (e.g., C:\\EnergyPlusV23-2-0 on Windows).")
        print("  3. Set ENERGYPLUS_HOME in your .env file or environment variables if installed in a custom location.")

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
