"""
Live Closed-Loop Control Integration Test.
Validates true bidirectional closed-loop control capability (READ -> WRITE -> CONTINUE -> READ CHANGED STATE -> RESET)
within ONE active EnergyPlus simulation process using PyEnergyPlus callbacks.
"""

import os
import sys
import csv
import time
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WEATHER_FILE, OUTPUTS_AI_DIR
from energyplus.environment import setup_energyplus_path, find_energyplus
from energyplus.telemetry import TelemetryManager
from energyplus.control import ControlAction, EnergyPlusControlManager, ControlSafetyValidator

RUN_ID = f"test-run-{int(time.time())}"

def test_control_safety_validator():
    """Test safety validator rejects invalid actions and accepts valid actions."""
    valid_action = ControlAction("CORE_ZN", 19.0, 23.0, "Valid test action")
    is_valid, msg = ControlSafetyValidator.validate(valid_action)
    assert is_valid, f"Valid action rejected: {msg}"

    invalid_actions = [
        ControlAction("CORE_ZN", 24.0, 23.0, "Heating >= Cooling"),
        ControlAction("CORE_ZN", 10.0, 24.0, "Heating below min"),
        ControlAction("CORE_ZN", 20.0, 40.0, "Cooling above max"),
        ControlAction("CORE_ZN", float("nan"), 24.0, "NaN value")
    ]

    for act in invalid_actions:
        val, m = ControlSafetyValidator.validate(act)
        assert not val, f"Invalid action was incorrectly accepted: {act.reason}"

    print("[PASS] test_control_safety_validator")

def test_live_closed_loop_execution():
    """Execute live simulation with control and observation callbacks, proving setpoint override and release."""
    success, msg = setup_energyplus_path()
    assert success, f"PyEnergyPlus setup failed: {msg}"

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()

    telemetry_mgr = TelemetryManager()
    control_mgr = EnergyPlusControlManager(run_id=RUN_ID)

    override_applied = False
    override_released = False
    observed_override_sp = None
    observed_post_release_sp = None

    def ctrl_cb(s):
        nonlocal override_applied, override_released
        if not api.exchange.api_data_fully_ready(s):
            return

        control_mgr.reassert_active_overrides(api, s)

        day = api.exchange.day_of_month(s)
        hour = api.exchange.hour(s)

        if day == 21 and hour == 9 and not override_applied:
            override_applied = True
            act = ControlAction("CORE_ZN", 19.0, 22.5, "Integration Test Override")
            written = control_mgr.apply_control_action(api, s, act, f"Day {day} {hour}:00")
            assert written, "Actuator write failed for valid action"

        if day == 21 and hour == 15 and not override_released:
            override_released = True
            released = control_mgr.reset_zone_override(api, s, "CORE_ZN")
            assert released, "Actuator reset failed"

    def obs_cb(s):
        nonlocal observed_override_sp, observed_post_release_sp
        if not api.exchange.api_data_fully_ready(s):
            return

        telemetry_mgr.capture_snapshot(api, s)
        
        day = api.exchange.day_of_month(s)
        hour = api.exchange.hour(s)
        
        if day == 21 and hour == 10 and observed_override_sp is None:
            _, clg = control_mgr.get_current_setpoints(api, s, "CORE_ZN")
            observed_override_sp = clg

        if day == 21 and hour == 16 and observed_post_release_sp is None:
            _, clg = control_mgr.get_current_setpoints(api, s, "CORE_ZN")
            observed_post_release_sp = clg

    api.runtime.callback_begin_zone_timestep_before_init_heat_balance(state, ctrl_cb)
    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, obs_cb)

    idf_path = str(PROJECT_ROOT / "models" / "modified" / "control_ready.idf")
    epw_path = str(WEATHER_FILE)
    out_dir = str(OUTPUTS_AI_DIR)

    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", out_dir, "-w", epw_path, idf_path])
    api.state_manager.delete_state(state)

    # Verifications
    assert exit_code == 0, f"Simulation failed with exit code: {exit_code}"
    assert override_applied, "Override event was not triggered"
    assert override_released, "Release event was not triggered"
    assert observed_override_sp == 22.5, f"Observed override setpoint mismatch: {observed_override_sp} != 22.5"
    assert observed_post_release_sp == 26.7, f"Observed post-release setpoint mismatch: {observed_post_release_sp} != 26.7"
    assert len(telemetry_mgr.snapshots) > 100, "Insufficient snapshots captured"

    print(f"[PASS] test_live_closed_loop_execution (Run ID: {RUN_ID}, Override SP: {observed_override_sp}°C -> Post-release SP: {observed_post_release_sp}°C)")

def test_control_history_csv():
    """Verify saved control history CSV file exists and contains recorded actions."""
    csv_path = OUTPUTS_AI_DIR / "control_actions.csv"
    assert csv_path.is_file(), "control_actions.csv missing."

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    assert len(rows) > 0, "control_actions.csv is empty."
    assert "applied_cooling_setpoint" in headers, "applied_cooling_setpoint column missing"
    assert "validation_passed" in headers, "validation_passed column missing"
    print(f"[PASS] test_control_history_csv ({len(rows)} control action records verified)")

if __name__ == "__main__":
    test_control_safety_validator()
    test_live_closed_loop_execution()
    test_control_history_csv()
    print("\nAll live closed-loop control integration tests passed successfully.")
