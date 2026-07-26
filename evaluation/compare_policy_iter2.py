"""
Policy Iteration 2 Cross-Season Comparison Compiler (Standard Library Only).
Parses baseline, policy_iter1_frozen, and policy_iter2_candidate outputs across all 3 seasons.
Calculates energy consumption, PMV comfort metrics, and decision/actuation statistics.
"""

import sys
import os
import csv
import json
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_EVAL_DIR = PROJECT_ROOT / "outputs" / "evaluation"
POLICY1_DIR = BASE_EVAL_DIR / "cross_season_verified"
POLICY2_DIR = BASE_EVAL_DIR / "policy_iter2"

SEASONS = ["winter", "shoulder", "summer"]

def parse_eplus_csv(csv_path: Path) -> Dict[str, float]:
    """Parses key metrics from EnergyPlus eplusout.csv using standard csv library."""
    if not csv_path.is_file():
        return {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]

        elec_idx = next((i for i, h in enumerate(header) if "Electricity" in h and "Facility" in h), None)
        gas_idx = next((i for i, h in enumerate(header) if "Gas" in h and "Facility" in h), None)
        pmv_idx = next((i for i, h in enumerate(header) if "Fanger Model PMV" in h and "CORE_ZN" in h), None)
        occ_idx = next((i for i, h in enumerate(header) if "Occupant Count" in h and "CORE_ZN" in h), None)

        elec_sum = 0.0
        gas_sum = 0.0
        occupied_pmvs = []

        for row in reader:
            if not row or len(row) <= max(filter(lambda x: x is not None, [elec_idx, gas_idx, pmv_idx, occ_idx])):
                continue

            try:
                if elec_idx is not None:
                    elec_sum += float(row[elec_idx])
                if gas_idx is not None:
                    gas_sum += float(row[gas_idx])

                occ_val = float(row[occ_idx]) if occ_idx is not None else 0.0
                if occ_val > 0.1 and pmv_idx is not None:
                    occupied_pmvs.append(float(row[pmv_idx]))
            except ValueError:
                continue

        elec_kwh = elec_sum / 3600000.0 if elec_sum > 100000 else (elec_sum * 0.25) / 1000.0
        gas_kwh = gas_sum / 3600000.0 if gas_sum > 100000 else (gas_sum * 0.25) / 1000.0

        mean_pmv = sum(occupied_pmvs) / len(occupied_pmvs) if occupied_pmvs else 0.0
        comfort_compliant = sum(1 for p in occupied_pmvs if -0.5 <= p <= 0.5)
        comfort_pct = (comfort_compliant / len(occupied_pmvs) * 100.0) if occupied_pmvs else 100.0

        return {
            "elec_kwh": round(elec_kwh, 2),
            "gas_kwh": round(gas_kwh, 2),
            "total_site_kwh": round(elec_kwh + gas_kwh, 2),
            "mean_occupied_pmv": round(mean_pmv, 2),
            "comfort_compliance_pct": round(comfort_pct, 2)
        }

def parse_agent_jsonl(jsonl_path: Path) -> Dict[str, Any]:
    """Parses agent decisions from decision log."""
    if not jsonl_path.is_file():
        return {"decisions": 0, "actions_applied": 0, "ecm_available": 0, "ecm_selected": 0}

    total_decisions = 0
    actions_applied = 0
    ecm_available = 0
    ecm_selected = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            total_decisions += 1
            if data.get("proposed_tool") == "apply_control_action" or data.get("decision", {}).get("action") == "ADJUST_SETPOINTS":
                actions_applied += 1
            if data.get("ecm_available"):
                ecm_available += 1
            if data.get("ecm_selected"):
                ecm_selected += 1

    return {
        "decisions": total_decisions,
        "actions_applied": actions_applied,
        "ecm_available": ecm_available,
        "ecm_selected": ecm_selected
    }

def main():
    print("\n--- POLICY ITERATION 2 CROSS-SEASON COMPARISON ---")
    results = {}

    for season in SEASONS:
        p1_base_csv = POLICY1_DIR / season / "baseline" / "eplusout.csv"
        p1_ai_csv = POLICY1_DIR / season / "ai_controlled" / "eplusout.csv"
        p1_ai_jsonl = POLICY1_DIR / season / "ai_controlled" / "agent_decisions.jsonl"

        p2_ai_csv = POLICY2_DIR / season / "ai_controlled" / "eplusout.csv"
        if not p2_ai_csv.is_file(): # Check season dir directly
            p2_ai_csv = POLICY2_DIR / season / "ai_controlled" / "eplusout.csv"
        p2_ai_jsonl = POLICY2_DIR / season / "ai_controlled" / "agent_decisions.jsonl"

        base_metrics = parse_eplus_csv(p1_base_csv)
        p1_metrics = parse_eplus_csv(p1_ai_csv)
        p1_agent = parse_agent_jsonl(p1_ai_jsonl)

        p2_metrics = parse_eplus_csv(p2_ai_csv)
        p2_agent = parse_agent_jsonl(p2_ai_jsonl)

        results[season] = {
            "baseline": base_metrics,
            "policy1": {**p1_metrics, **p1_agent},
            "policy2": {**p2_metrics, **p2_agent}
        }

    out_file = POLICY2_DIR / "comparison_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(json.dumps(results, indent=2))
    print(f"\n[OK] Comparison summary written to {out_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
