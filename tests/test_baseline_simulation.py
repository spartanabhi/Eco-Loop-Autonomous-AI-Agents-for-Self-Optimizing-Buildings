"""
Baseline Simulation Integration Test.
Validates baseline building model, weather file, EnergyPlus execution,
error log output (fatal errors == 0), and CSV output data generation.
"""

import os
import sys
import csv
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BASELINE_IDF, WEATHER_FILE, OUTPUTS_BASELINE_DIR
from energyplus.environment import find_energyplus
from energyplus.runner import EnergyPlusRunnerFoundation

def test_prerequisites_exist():
    """Verify baseline IDF, EPW weather file, and EnergyPlus executable exist."""
    assert BASELINE_IDF.is_file(), f"Baseline IDF missing: {BASELINE_IDF}"
    assert WEATHER_FILE.is_file(), f"Weather file missing: {WEATHER_FILE}"
    
    ep_info = find_energyplus()
    assert ep_info["installed"], "EnergyPlus installation not detected."
    assert ep_info["executable"], "EnergyPlus executable not found."
    print("[PASS] test_prerequisites_exist")

def test_baseline_simulation_execution():
    """Execute baseline simulation and verify clean completion with zero fatal errors."""
    runner = EnergyPlusRunnerFoundation()
    exit_code = runner.run_simulation(
        idf_path=str(BASELINE_IDF),
        epw_path=str(WEATHER_FILE),
        output_dir=str(OUTPUTS_BASELINE_DIR)
    )

    assert exit_code == 0, f"Simulation exited with non-zero code: {exit_code}"

    err_report = runner.parse_error_log(str(OUTPUTS_BASELINE_DIR))
    assert err_report["fatal"] == 0, f"Simulation contained fatal errors: {err_report['fatal']}"
    assert err_report["severe"] == 0, f"Simulation contained severe errors: {err_report['severe']}"

    print(f"[PASS] test_baseline_simulation_execution (Exit code: {exit_code}, Warnings: {err_report['warnings']})")

def test_output_artifacts_and_data():
    """Verify CSV and ESO output artifacts exist and contain non-empty simulation data."""
    csv_path = OUTPUTS_BASELINE_DIR / "eplusout.csv"
    eso_path = OUTPUTS_BASELINE_DIR / "eplusout.eso"
    err_path = OUTPUTS_BASELINE_DIR / "eplusout.err"

    assert err_path.is_file(), "Error log eplusout.err missing."
    assert eso_path.is_file(), "ESO data file eplusout.eso missing."
    assert csv_path.is_file(), "CSV output eplusout.csv missing."
    assert csv_path.stat().st_size > 100, "CSV output file is empty."

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    assert len(rows) > 0, "CSV dataframe is empty."
    
    # Check key columns exist
    temp_cols = [c for c in headers if "Zone Mean Air Temperature" in c]
    elec_cols = [c for c in headers if "Electricity:Facility" in c]
    pmv_cols = [c for c in headers if "Fanger Model PMV" in c]

    assert len(temp_cols) > 0, "No Zone Mean Air Temperature columns found in output CSV."
    assert len(elec_cols) > 0, "No Electricity:Facility columns found in output CSV."
    assert len(pmv_cols) > 0, "No Fanger Model PMV columns found in output CSV."

    print(f"[PASS] test_output_artifacts_and_data ({len(rows)} data rows, {len(headers)} columns verified)")

if __name__ == "__main__":
    test_prerequisites_exist()
    test_baseline_simulation_execution()
    test_output_artifacts_and_data()
    print("\nAll baseline simulation integration tests passed successfully.")
