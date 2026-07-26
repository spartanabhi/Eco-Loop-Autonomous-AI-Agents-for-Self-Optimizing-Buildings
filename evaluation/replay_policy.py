"""
Fast Offline Policy Replay Module.
Replays recorded telemetry snapshots from policy_iter1_frozen through policy_iter2_candidate
without EnergyPlus actuation to evaluate LLM behavioral responses and ECM selection rates.
"""

import sys
import json
import csv
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from energyplus.telemetry import TelemetrySnapshot
from agent.orchestrator_v2 import AgentOrchestratorV2

VERIFIED_DIR = PROJECT_ROOT / "outputs" / "evaluation" / "cross_season_verified"
REPLAY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "evaluation" / "policy_iter2" / "replay"

def load_sample_telemetry(season: str, limit: int) -> List[TelemetrySnapshot]:
    """Loads sample telemetry rows from verified telemetry CSV files."""
    csv_path = VERIFIED_DIR / season / "ai_controlled" / "live_telemetry.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"Telemetry CSV missing for replay: {csv_path}")

    snapshots = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        # Select evenly distributed rows during daytime operating hours (08:00 to 18:00)
        daytime_rows = [r for r in rows if 8 <= int(r["sim_hour"]) <= 18]
        step = max(1, len(daytime_rows) // limit)
        selected_rows = daytime_rows[::step][:limit]

        for r in selected_rows:
            snap = TelemetrySnapshot(
                run_id=r.get("run_id", "replay"),
                season=season,
                controller_version="policy_iter2_candidate",
                callback_index=int(r.get("callback_index", 0)),
                simulation_time=r["simulation_time"],
                month=int(r["sim_month"]),
                day=int(r["sim_day"]),
                hour=int(r["sim_hour"]),
                minute=int(r["sim_minute"]),
                outdoor_drybulb_c=float(r["outdoor_drybulb_c"]),
                outdoor_rh_pct=float(r["outdoor_rh_pct"]),
                zone_temperatures={"CORE_ZN": float(r["core_zn_temp"])},
                zone_co2={"CORE_ZN": float(r["core_zn_co2"])},
                zone_pmv={"CORE_ZN": float(r["core_zn_pmv"])},
                zone_occupancy={"CORE_ZN": float(r["core_zn_occ"])},
                occupancy_source=r.get("occupancy_source", "ENERGYPLUS"),
                facility_electricity_joules=float(r.get("electricity_meter_joules", 0.0)),
                facility_electricity_kwh=float(r["electricity_meter_kwh"]),
                facility_demand_kw=float(r["facility_demand_kw"]),
                facility_gas_joules=float(r.get("gas_meter_joules", 0.0)),
                facility_gas_kwh_eq=float(r.get("gas_meter_kwh_eq", 0.0)),
                total_site_energy_kwh_eq=float(r.get("total_site_energy_kwh_eq", r["electricity_meter_kwh"])),
                hvac_mode=r.get("hvac_mode", "COOLING")
            )
            snapshots.append(snap)
    return snapshots

def main() -> int:
    print("=" * 70)
    print(" FAST OFFLINE POLICY REPLAY: policy_iter2_candidate")
    print("=" * 70)

    # 1. Load snapshots: 10 Winter, 10 Shoulder, 20 Summer
    winter_snaps = load_sample_telemetry("winter", 10)
    shoulder_snaps = load_sample_telemetry("shoulder", 10)
    summer_snaps = load_sample_telemetry("summer", 20)

    all_snaps = [("WINTER", s) for s in winter_snaps] + [("SHOULDER", s) for s in shoulder_snaps] + [("SUMMER", s) for s in summer_snaps]

    orchestrator = AgentOrchestratorV2(policy_version="policy_iter2_candidate")
    REPLAY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    orchestrator.decision_log_path = REPLAY_OUTPUT_DIR / "replay_decisions.jsonl"

    if orchestrator.decision_log_path.is_file():
        orchestrator.decision_log_path.unlink()

    total_decisions = 0
    maintain_count = 0
    ecm_available_count = 0
    ecm_selected_count = 0
    action_distribution = {}
    schema_failures = 0
    safety_failures = 0

    print(f"Loaded {len(all_snaps)} replay snapshots. Executing Qwen inference...")

    for season, snap in all_snaps:
        res = orchestrator.process_snapshot(
            snapshot=snap,
            zone="CORE_ZN",
            current_htg_sp=21.0,
            current_clg_sp=24.0,
            run_id=f"replay_{season.lower()}"
        )

        total_decisions += 1
        dec = res["decision"]
        act = dec["action"]

        action_distribution[act] = action_distribution.get(act, 0) + 1

        if res["ecm_available"]:
            ecm_available_count += 1
        if res["ecm_selected"]:
            ecm_selected_count += 1
        if act == "MAINTAIN":
            maintain_count += 1

        if not res["schema_passed"]:
            schema_failures += 1
        if not res["safety_passed"]:
            safety_failures += 1

        print(f"[{season} | {snap.simulation_time}] Temp={snap.zone_temperatures['CORE_ZN']:.1f}°C PMV={snap.zone_pmv['CORE_ZN']:+.2f} Mode={snap.hvac_mode} | Candidates={res['allowed_candidates']} -> Qwen Chosen={act}")
        print(f"   Reason: \"{dec['reason']}\"")

    selection_rate = (ecm_selected_count / ecm_available_count * 100.0) if ecm_available_count > 0 else 0.0

    summary = {
        "policy_version": "policy_iter2_candidate",
        "total_replay_decisions": total_decisions,
        "maintain_count": maintain_count,
        "ecm_available_count": ecm_available_count,
        "ecm_selected_count": ecm_selected_count,
        "ecm_selection_rate_pct": selection_rate,
        "action_distribution": action_distribution,
        "schema_failures": schema_failures,
        "safety_failures": safety_failures
    }

    with open(REPLAY_OUTPUT_DIR / "replay_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print(" REPLAY SUMMARY RESULTS")
    print("=" * 70)
    print(f" Total Decisions:       {total_decisions}")
    print(f" MAINTAIN Count:        {maintain_count}")
    print(f" ECM Available Count:   {ecm_available_count}")
    print(f" ECM Selected Count:    {ecm_selected_count}")
    print(f" ECM Selection Rate:    {selection_rate:.1f}%")
    print(f" Action Distribution:   {action_distribution}")
    print("=" * 70)

    # Validation Guard
    if maintain_count == total_decisions:
        print("\n[CRITICAL FAILURE] policy_iter2_candidate still chose MAINTAIN 100% of the time!")
        return 1

    print("[SUCCESS] Replay behavioral validation PASSED! Ready for Summer proof run.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
