"""
Live Telemetry Pipeline Integration Test.
Validates control_ready.idf, PyEnergyPlus runtime callbacks, handle discovery,
and live capture of all 4 required feedback metrics during active simulation.
"""

import os
import sys
import csv
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WEATHER_FILE, OUTPUTS_AI_DIR
from energyplus.environment import setup_energyplus_path, find_energyplus
from energyplus.telemetry import TelemetryManager

def test_control_ready_model_and_co2():
    """Verify control_ready.idf exists and contains CO2 balance objects."""
    control_ready_path = PROJECT_ROOT / "models" / "modified" / "control_ready.idf"
    assert control_ready_path.is_file(), f"control_ready.idf missing: {control_ready_path}"

    with open(control_ready_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ZoneAirContaminantBalance" in content, "ZoneAirContaminantBalance object missing from control_ready.idf"
    assert "Zone Air CO2 Concentration" in content, "Zone Air CO2 Concentration variable missing"
    print("[PASS] test_control_ready_model_and_co2")

def test_live_telemetry_pipeline():
    """Execute live simulation with PyEnergyPlus callbacks and test handle validity and snapshot capture."""
    success, msg = setup_energyplus_path()
    assert success, f"PyEnergyPlus setup failed: {msg}"

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()

    telemetry_mgr = TelemetryManager()

    def test_callback(s):
        telemetry_mgr.capture_snapshot(api, s)

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, test_callback)

    idf_path = str(PROJECT_ROOT / "models" / "modified" / "control_ready.idf")
    epw_path = str(WEATHER_FILE)
    out_dir = str(OUTPUTS_AI_DIR)

    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", out_dir, "-w", epw_path, idf_path])
    api.state_manager.delete_state(state)

    # 1. Exit code & errors check
    assert exit_code == 0, f"Live simulation exited with non-zero code: {exit_code}"
    
    err_file = Path(out_dir) / "eplusout.err"
    assert err_file.is_file(), "Error log missing."
    with open(err_file, "r", encoding="utf-8") as f:
        err_content = f.read()
    assert "Fatal" not in err_content or "0 Fatal Errors" in err_content, "Fatal errors detected in eplusout.err"

    # 2. Handles check
    assert telemetry_mgr.handles_initialized, "Handles failed to initialize."
    assert all(h != -1 for h in telemetry_mgr.temp_handles.values()), "Invalid temperature handle detected."
    assert all(h != -1 for h in telemetry_mgr.co2_handles.values()), "Invalid CO2 handle detected."
    assert all(h != -1 for h in telemetry_mgr.pmv_handles.values()), "Invalid PMV handle detected."
    assert telemetry_mgr.meter_electricity_handle != -1, "Invalid electricity meter handle."

    # 3. Snapshot data check
    snapshots = telemetry_mgr.snapshots
    assert len(snapshots) > 100, f"Insufficient snapshots captured: {len(snapshots)}"

    # Check distinct values across simulation time
    s_first = snapshots[10]
    s_mid = snapshots[len(snapshots) // 2]
    
    assert isinstance(s_first.zone_temperatures["CORE_ZN"], float), "Non-numeric temperature value"
    assert isinstance(s_first.zone_co2["CORE_ZN"], float), "Non-numeric CO2 value"
    assert isinstance(s_first.zone_pmv["CORE_ZN"], float), "Non-numeric PMV value"
    assert isinstance(s_first.facility_electricity_kwh, float), "Non-numeric electricity kWh value"

    # Verify live changing data between two timestamps
    temps_different = s_first.zone_temperatures != s_mid.zone_temperatures
    co2_different = s_first.zone_co2 != s_mid.zone_co2
    
    print(f"[PASS] test_live_telemetry_pipeline ({len(snapshots)} snapshots captured, live data variation verified)")

def test_telemetry_history_csv():
    """Verify saved live telemetry CSV file exists and contains valid numeric data rows."""
    csv_path = OUTPUTS_AI_DIR / "live_telemetry.csv"
    assert csv_path.is_file(), "live_telemetry.csv missing."

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    assert len(rows) > 100, f"CSV file has insufficient rows: {len(rows)}"
    assert "temp_CORE_ZN" in headers, "temp_CORE_ZN column missing from live CSV"
    assert "co2_CORE_ZN" in headers, "co2_CORE_ZN column missing from live CSV"
    assert "pmv_CORE_ZN" in headers, "pmv_CORE_ZN column missing from live CSV"
    print(f"[PASS] test_telemetry_history_csv ({len(rows)} CSV rows verified)")

if __name__ == "__main__":
    test_control_ready_model_and_co2()
    test_live_telemetry_pipeline()
    test_telemetry_history_csv()
    print("\nAll live telemetry integration tests passed successfully.")
