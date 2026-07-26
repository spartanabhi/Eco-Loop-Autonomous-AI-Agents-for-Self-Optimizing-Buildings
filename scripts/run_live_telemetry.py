#!/usr/bin/env python3
"""
Live EnergyPlus Telemetry Script.
Executes EnergyPlus with PyEnergyPlus runtime callbacks, reading live telemetry metrics
(Zone Temperature, CO2, PMV, Facility Electricity) directly during active simulation.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WEATHER_FILE, OUTPUTS_AI_DIR
from energyplus.environment import setup_energyplus_path, find_energyplus
from energyplus.telemetry import TelemetryManager

telemetry_manager = TelemetryManager(control_interval_steps=1)
api_instance = None
print_count = 0

def live_telemetry_callback(state):
    """PyEnergyPlus callback executed at the end of each zone timestep after zone reporting."""
    global telemetry_manager, api_instance, print_count

    if not api_instance.exchange.api_data_fully_ready(state):
        return

    snapshot = telemetry_manager.capture_snapshot(api_instance, state)
    if snapshot is None:
        return

    # Print live telemetry summary every few callbacks to show active real-time data streaming
    print_count += 1
    if print_count % 3 == 1 or print_count <= 3:
        print(f"\n[CALLBACK {snapshot.callback_index:03d}] Active Live Simulation - Timestamp: {snapshot.simulation_time}")
        print("----------------------------------------------------------------------")
        print(" Zone Temperatures (°C):")
        for z, t in snapshot.zone_temperatures.items():
            print(f"   - {z:<18}: {t:.2f} °C")
        
        print(" Zone Air CO2 (ppm):")
        for z, c in snapshot.zone_co2.items():
            print(f"   - {z:<18}: {c:.1f} ppm")

        print(" Zone Thermal Comfort (PMV):")
        for z, p in snapshot.zone_pmv.items():
            print(f"   - {z:<18}: PMV {p:.3f}")

        print(" Facility Electricity:")
        print(f"   - Raw: {snapshot.facility_electricity_joules:,.1f} J | Interval: {snapshot.facility_electricity_kwh:.4f} kWh")
        print("----------------------------------------------------------------------")

def main() -> int:
    global api_instance
    print("=" * 70)
    print("   Eco-Loop Live EnergyPlus Telemetry Pipeline")
    print("=" * 70)
    print()

    # 1. Setup PyEnergyPlus API
    success, msg = setup_energyplus_path()
    if not success:
        print(f"[ERROR] {msg}")
        return 1

    from pyenergyplus.api import EnergyPlusAPI
    api_instance = EnergyPlusAPI()

    # 2. Validate Paths
    idf_path = PROJECT_ROOT / "models" / "modified" / "control_ready.idf"
    epw_path = WEATHER_FILE
    out_dir = OUTPUTS_AI_DIR

    if not idf_path.is_file():
        print(f"[ERROR] control_ready.idf not found at: {idf_path}")
        return 1
    if not epw_path.is_file():
        print(f"[ERROR] Weather file not found at: {epw_path}")
        return 1

    os.makedirs(out_dir, exist_ok=True)

    # 3. Create Simulation State
    state = api_instance.state_manager.new_state()

    # 4. Register Callback
    # Chosen callback: callback_end_zone_timestep_after_zone_reporting
    # Rationale: Ensures zone heat balance & HVAC calculations are fully resolved for current timestep.
    api_instance.runtime.callback_end_zone_timestep_after_zone_reporting(state, live_telemetry_callback)

    print("Starting EnergyPlus Active Simulation with PyEnergyPlus Callbacks...")
    cmd_args = ["-d", str(out_dir), "-w", str(epw_path), str(idf_path)]
    
    api_instance.runtime.set_console_output_status(state, False)
    exit_code = api_instance.runtime.run_energyplus(state, cmd_args)
    
    api_instance.state_manager.delete_state(state)

    print(f"\n[COMPLETE] Simulation finished with Exit Code: {exit_code}")
    print(f"Total Callbacks Processed: {telemetry_manager.callback_counter}")
    print(f"Total Telemetry Snapshots Captured: {len(telemetry_manager.snapshots)}")

    # 5. Save Captured History
    history_csv = out_dir / "live_telemetry.csv"
    telemetry_manager.save_history_csv(str(history_csv))
    print(f"[OK] Saved live telemetry snapshot history to: {history_csv}")

    if exit_code == 0 and len(telemetry_manager.snapshots) > 0:
        print("\n>> SUCCESS: Live telemetry pipeline executed successfully! <<")
        return 0
    else:
        print("\n>> FAILURE: Live telemetry pipeline encountered errors. <<")
        return 1

if __name__ == "__main__":
    sys.exit(main())
