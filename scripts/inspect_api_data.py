#!/usr/bin/env python3
"""
EnergyPlus API Data & Actuator Inspection Utility.
Dumps available variables, meters, and actuators exposed by PyEnergyPlus exchange API.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WEATHER_FILE, OUTPUT_DIRECTORY
from energyplus.environment import setup_energyplus_path
from energyplus.runner import EnergyPlusRunnerFoundation

def inspect_callback(state):
    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()

    if not api.exchange.api_data_fully_ready(state):
        return

    # Request EnergyPlus to export CSV of available API data
    api_csv = api.exchange.list_available_api_data_csv(state)
    
    # Check specific variable handles
    zones = ["CORE_ZN", "PERIMETER_ZN_1", "PERIMETER_ZN_2", "PERIMETER_ZN_3", "PERIMETER_ZN_4"]
    
    print("\n" + "=" * 60)
    print("   ENERGYPLUS API HANDLE INSPECTION")
    print("=" * 60)

    print("\n1. TEMPERATURE HANDLES (Zone Mean Air Temperature):")
    for z in zones:
        h = api.exchange.get_variable_handle(state, "Zone Mean Air Temperature", z)
        val = api.exchange.get_variable_value(state, h) if h != -1 else "N/A"
        print(f"  - Key: {z:<18} | Handle: {h:<5} | Value: {val}")

    print("\n2. CO2 HANDLES (Zone Air CO2 Concentration):")
    for z in zones:
        h = api.exchange.get_variable_handle(state, "Zone Air CO2 Concentration", z)
        val = api.exchange.get_variable_value(state, h) if h != -1 else "N/A"
        print(f"  - Key: {z:<18} | Handle: {h:<5} | Value: {val}")

    print("\n3. PMV HANDLES (Zone Thermal Comfort Fanger Model PMV):")
    for z in zones:
        people_key = f"{z} PEOPLE"
        h = api.exchange.get_variable_handle(state, "Zone Thermal Comfort Fanger Model PMV", people_key)
        val = api.exchange.get_variable_value(state, h) if h != -1 else "N/A"
        print(f"  - Key: {people_key:<18} | Handle: {h:<5} | Value: {val}")

    print("\n4. FACILITY ELECTRICITY METER HANDLE:")
    m_h = api.exchange.get_meter_handle(state, "Electricity:Facility")
    m_val = api.exchange.get_meter_value(state, m_h) if m_h != -1 else "N/A"
    print(f"  - Meter: Electricity:Facility | Handle: {m_h:<5} | Value (J): {m_val}")

    print("\n5. ACTUATOR CANDIDATE INSPECTION:")
    # Check schedule actuators
    act_sch_htg = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "HTGSETP_SCH")
    act_sch_clg = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "CLGSETP_SCH")
    print(f"  - Actuator (Schedule:Compact, Schedule Value, HTGSETP_SCH): Handle = {act_sch_htg}")
    print(f"  - Actuator (Schedule:Compact, Schedule Value, CLGSETP_SCH): Handle = {act_sch_clg}")

    # Check Zone Temperature Control actuators
    for z in zones:
        act_ztc_htg = api.exchange.get_actuator_handle(state, "Zone Temperature Control", "Heating Setpoint", z)
        act_ztc_clg = api.exchange.get_actuator_handle(state, "Zone Temperature Control", "Cooling Setpoint", z)
        print(f"  - Actuator (Zone Temperature Control, Heating Setpoint, {z}): Handle = {act_ztc_htg}")
        print(f"  - Actuator (Zone Temperature Control, Cooling Setpoint, {z}): Handle = {act_ztc_clg}")

    print("=" * 60 + "\n")

    # Stop simulation after inspecting one ready callback
    api.runtime.stop_simulation(state)

def main():
    setup_energyplus_path()
    from pyenergyplus.api import EnergyPlusAPI

    api = EnergyPlusAPI()
    runner = EnergyPlusRunnerFoundation()
    
    state = runner.create_state()
    idf_file = str(PROJECT_ROOT / "models" / "modified" / "control_ready.idf")
    epw_file = str(WEATHER_FILE)
    out_dir = str(OUTPUT_DIRECTORY / "ai_controlled")

    os.makedirs(out_dir, exist_ok=True)

    # Register callback at end of zone timestep after zone reporting
    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, inspect_callback)
    
    cmd_args = ["-d", out_dir, "-w", epw_file, idf_file]
    api.runtime.set_console_output_status(state, False)
    api.runtime.run_energyplus(state, cmd_args)
    runner.cleanup()

if __name__ == "__main__":
    main()
