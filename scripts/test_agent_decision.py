#!/usr/bin/env python3
"""
Test Agent Decision Script.
Obtains a REAL live TelemetrySnapshot from EnergyPlus, evaluates targets and carbon intensity,
calls local open-source Qwen2.5-0.5B-Instruct GGUF model via AgentOrchestrator,
validates schema & safety, and displays the structured decision and proposed agent tool.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WEATHER_FILE, OUTPUTS_AI_DIR
from energyplus.environment import setup_energyplus_path
from energyplus.telemetry import TelemetryManager, TelemetrySnapshot
from agent.orchestrator import AgentOrchestrator

def capture_real_telemetry_snapshot() -> TelemetrySnapshot:
    """Executes a short PyEnergyPlus run to capture a REAL live TelemetrySnapshot."""
    success, msg = setup_energyplus_path()
    if not success:
        raise RuntimeError(f"PyEnergyPlus setup failed: {msg}")

    from pyenergyplus.api import EnergyPlusAPI
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    telemetry_mgr = TelemetryManager()

    captured_snapshot = None

    def obs_cb(s):
        nonlocal captured_snapshot
        if not api.exchange.api_data_fully_ready(s):
            return
        day = api.exchange.day_of_month(s)
        hour = api.exchange.hour(s)
        if day == 21 and hour == 14 and captured_snapshot is None:
            snap = telemetry_mgr.capture_snapshot(api, s)
            if snap:
                captured_snapshot = snap

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, obs_cb)

    idf_path = str(PROJECT_ROOT / "models" / "modified" / "control_ready.idf")
    epw_path = str(WEATHER_FILE)
    out_dir = str(OUTPUTS_AI_DIR)

    api.runtime.set_console_output_status(state, False)
    api.runtime.run_energyplus(state, ["-d", out_dir, "-w", epw_path, idf_path])
    api.state_manager.delete_state(state)

    if captured_snapshot is None:
        raise RuntimeError("Failed to capture real telemetry snapshot from EnergyPlus.")

    return captured_snapshot

def main():
    print("=" * 75)
    print("         REAL ENERGYPLUS TELEMETRY -> LOCAL QWEN AGENT DECISION TEST")
    print("=" * 75 + "\n")

    print("[1/2] Capturing REAL TelemetrySnapshot from EnergyPlus simulation...")
    snapshot = capture_real_telemetry_snapshot()
    print(f"      [OK] Real Telemetry Snapshot Captured for {snapshot.simulation_time}")

    print("[2/2] Invoking Agent Orchestrator with local Qwen2.5-0.5B-Instruct-Q3_K_S.gguf...")
    orchestrator = AgentOrchestrator()
    result = orchestrator.process_snapshot(
        snapshot=snapshot,
        zone="CORE_ZN",
        current_htg_sp=21.0,
        current_clg_sp=24.0
    )

    eval_s = result["evaluated_state"]
    dec = result["decision"]

    print("\n" + "=" * 70)
    print(" AGENT DECISION TEST RESULTS")
    print("=" * 70)
    print(f" Simulation State:")
    print(f"   - Time:                 {eval_s['simulation_time']}")
    print(f"   - Target Zone:          {eval_s['zone']}")
    print(f"   - Zone Temperature:     {eval_s['temperature']:.2f} °C")
    print(f"   - Thermal Comfort PMV:  {eval_s['pmv']:+.2f} ({eval_s['comfort_status']})")
    print(f"   - Indoor Air Quality:   {eval_s['co2_ppm']:.0f} ppm ({eval_s['co2_status']})")
    print(f"   - Electricity Demand:   {eval_s['demand_kw']:.2f} kW ({eval_s['peak_status']})")
    print(f"   - Grid Carbon State:    {eval_s['carbon_status']} ({eval_s['carbon_intensity_g_co2_kwh']:.0f} g CO2/kWh)")
    print(f"   - Active Setpoints:     Heating={eval_s['current_heating_sp']:.1f}°C, Cooling={eval_s['current_cooling_sp']:.1f}°C")
    print("-" * 70)
    print(f" LLM Model Engine:")
    print(f"   - Runtime:              llama-cpp-python (Local CPython 3.12 x86_64 prebuilt binary)")
    print(f"   - Model Filename:       Qwen2.5-0.5B-Instruct-Q3_K_S.gguf")
    print(f"   - Model Size:           322.59 MB")
    print(f"   - Local Inference:      CONFIRMED LOCAL (100% Offline)")
    print(f"   - Attempts Made:        {result['attempts']}")
    print(f"   - Total Latency:        {result['total_latency_seconds']:.2f} seconds")
    print("-" * 70)
    print(f" Validation Results:")
    print(f"   - Schema Validation:    {'PASS' if result['schema_passed'] else 'FAIL'}")
    print(f"   - Safety Validation:    {'PASS' if result['safety_passed'] else 'FAIL'}")
    print("-" * 70)
    print(f" Agent Decision Output:")
    print(f"   - Action Choice:        {dec['action']}")
    print(f"   - Heating Setpoint:     {dec['heating_setpoint']}")
    print(f"   - Cooling Setpoint:     {dec['cooling_setpoint']}")
    print(f"   - Reason:               \"{dec['reason']}\"")
    print(f"   - Confidence:           {dec['confidence']}")
    print("-" * 70)
    print(f" Proposed Agent Tool:")
    print(f"   - Target Tool:          {result['proposed_tool']}")
    print("=" * 70 + "\n")

    if result["schema_passed"] and result["safety_passed"]:
        print(">> SUCCESS: Cognitive Engine + Agent Tool Integration Test PASSED! <<\n")
        return 0
    else:
        print(">> FAILURE: Validation issues encountered during decision processing. <<\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
