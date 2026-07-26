"""
Seasonal Baseline Simulation Integrity Runner.
Executes the three BASELINE seasonal simulations (Winter, Shoulder, Summer) using explicit generated IDFs.
Audits weather execution, outdoor temperatures, calendar months, fuel metrics, and HVAC mode distributions.
Fails loudly if seasonal weather traces remain identical.
"""

import sys
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import WEATHER_FILE, SEASONS
from evaluation.controller_version import get_frozen_controller_metadata
from energyplus.environment import setup_energyplus_path
from energyplus.telemetry import TelemetryManager

INTEGRITY_DIR = PROJECT_ROOT / "outputs" / "evaluation" / "seasonal_integrity"

def run_integrity_baseline(season_key: str, season_cfg: Dict[str, Any], api: Any) -> Dict[str, Any]:
    """Executes isolated baseline simulation for a single season."""
    run_id = f"{season_key}-baseline-{int(time.time())}"
    out_dir = INTEGRITY_DIR / season_key / "baseline"
    
    # 1. Clear output directory
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    idf_path = PROJECT_ROOT / "models" / "evaluation" / f"{season_key}_baseline.idf"
    assert idf_path.is_file(), f"Seasonal IDF missing: {idf_path}"

    print(f"\n--- Executing Integrity Baseline ({season_key.upper()}) [ID: {run_id}] ---")
    telemetry_mgr = TelemetryManager(run_id=run_id, season=season_key)
    state = api.state_manager.new_state()

    def obs_cb(s):
        if not api.exchange.api_data_fully_ready(s): return
        telemetry_mgr.capture_snapshot(api, s)

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, obs_cb)

    api.runtime.set_console_output_status(state, False)
    exit_code = api.runtime.run_energyplus(state, ["-d", str(out_dir), "-w", str(WEATHER_FILE), str(idf_path)])
    api.state_manager.delete_state(state)

    csv_path = out_dir / "live_telemetry.csv"
    telemetry_mgr.save_telemetry_csv(str(csv_path))

    # Audit captured telemetry (3 days * 24 hours * 6 timesteps/hr = 432 timesteps)
    snapshots = telemetry_mgr.snapshots
    expected_timesteps = 3 * 24 * 6  # 432
    assert len(snapshots) == expected_timesteps, f"Expected {expected_timesteps} timesteps for {season_key}, got {len(snapshots)}"

    out_temps = [s.outdoor_drybulb_c for s in snapshots]
    months = [s.month for s in snapshots]
    elec_kwh = sum(s.facility_electricity_kwh for s in snapshots)
    gas_kwh_eq = sum(s.facility_gas_kwh_eq for s in snapshots)
    site_kwh_eq = elec_kwh + gas_kwh_eq

    mode_counts = {"HEATING": 0, "COOLING": 0, "DEADBAND": 0}
    for s in snapshots:
        mode_counts[s.hvac_mode] = mode_counts.get(s.hvac_mode, 0) + 1

    expected_month = season_cfg["start_month"]
    assert all(m == expected_month for m in months), f"Month integrity mismatch in {season_key}! Expected month {expected_month}, got set {set(months)}"

    res = {
        "season": season_key,
        "run_id": run_id,
        "exit_code": exit_code,
        "snapshots_count": len(snapshots),
        "month": months[0],
        "outdoor_min": min(out_temps),
        "outdoor_mean": sum(out_temps) / len(out_temps),
        "outdoor_max": max(out_temps),
        "electricity_kwh": elec_kwh,
        "natural_gas_kwh_eq": gas_kwh_eq,
        "site_energy_kwh_eq": site_kwh_eq,
        "mode_counts": mode_counts
    }

    print(f" [OK] {season_key.upper()} Baseline Complete:")
    print(f"       Simulated Month:  {res['month']} (Expected: {expected_month})")
    print(f"       Outdoor Temp:     Min={res['outdoor_min']:.1f}°C, Mean={res['outdoor_mean']:.1f}°C, Max={res['outdoor_max']:.1f}°C")
    print(f"       Fuel Breakdown:   Elec={res['electricity_kwh']:.2f} kWh, Gas={res['natural_gas_kwh_eq']:.2f} kWh-eq, Site={res['site_energy_kwh_eq']:.2f} kWh-eq")
    print(f"       HVAC Modes:       {res['mode_counts']}")
    return res

def main() -> int:
    meta = get_frozen_controller_metadata()
    print("=" * 75)
    print("     ECO-LOOP BASELINE SEASONAL INTEGRITY RUNNER")
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

    baseline_results = {}
    for season_key, season_cfg in SEASONS.items():
        baseline_results[season_key] = run_integrity_baseline(season_key, season_cfg, api)

    # Integrity Assertions: Outdoor temperature traces must NOT be identical
    out_means = [baseline_results[s]["outdoor_mean"] for s in SEASONS.keys()]
    elec_totals = [baseline_results[s]["electricity_kwh"] for s in SEASONS.keys()]
    gas_totals = [baseline_results[s]["natural_gas_kwh_eq"] for s in SEASONS.keys()]

    print("\n" + "=" * 75)
    print(" BASELINE SEASONAL SANITY SUMMARY")
    print("=" * 75)
    for s in SEASONS.keys():
        r = baseline_results[s]
        print(f" {s.upper():<10}: Outdoor Mean={r['outdoor_mean']:5.1f}°C | Elec={r['electricity_kwh']:6.2f} kWh | Gas={r['natural_gas_kwh_eq']:6.2f} kWh-eq | Modes={r['mode_counts']}")

    assert len(set(round(m, 1) for m in out_means)) == 3, f"CRITICAL INTEGRITY FAILURE: Outdoor temperature means are identical across seasons! {out_means}"
    assert len(set(round(e, 1) for e in elec_totals)) > 1 or len(set(round(g, 1) for g in gas_totals)) > 1, f"CRITICAL INTEGRITY FAILURE: Energy metrics are identical across seasons!"

    print("=" * 75)
    print(" [PASS] BASELINE SEASONAL INTEGRITY VERIFIED! Outdoor temperatures and energy metrics differ as expected.")
    print("=" * 75)
    return 0

if __name__ == "__main__":
    sys.exit(main())
