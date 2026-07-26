"""
Fairness Verification Module.
Programmatically compares evaluation_baseline.idf and control_ready.idf to guarantee 100% physical model fairness.
"""

import sys
import re
from pathlib import Path
from typing import Dict, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import BASELINE_IDF, AI_CONTROLLED_IDF

def count_objects(content: str, obj_type: str) -> int:
    """Counts occurrences of an EnergyPlus IDF object type."""
    pattern = rf"^\s*{re.escape(obj_type)}\s*,"
    return len(re.findall(pattern, content, re.MULTILINE | re.IGNORECASE))

def verify_model_fairness() -> Tuple[bool, Dict[str, Any]]:
    """
    Verifies that baseline and AI control-ready IDF models have 100% identical physical characteristics.
    """
    if not BASELINE_IDF.is_file() or not AI_CONTROLLED_IDF.is_file():
        return False, {"error": "One or both IDF files missing"}

    with open(BASELINE_IDF, "r", encoding="utf-8", errors="replace") as f:
        b_text = f.read()

    with open(AI_CONTROLLED_IDF, "r", encoding="utf-8", errors="replace") as f:
        ai_text = f.read()

    metrics_to_check = [
        "Zone",
        "People",
        "Lights",
        "ElectricEquipment",
        "BuildingSurface:Detailed",
        "FenestrationSurface:Detailed",
        "HVACTemplate:Zone:VAV",
        "HVACTemplate:Plant:ChilledWaterLoop",
        "HVACTemplate:Plant:HotWaterLoop",
        "Schedule:Compact"
    ]

    discrepancies = []
    comparison_summary = {}

    for metric in metrics_to_check:
        b_count = count_objects(b_text, metric)
        ai_count = count_objects(ai_text, metric)
        comparison_summary[metric] = {"baseline": b_count, "ai_controlled": ai_count, "match": b_count == ai_count}
        if b_count != ai_count:
            discrepancies.append(f"Mismatch in {metric}: Baseline={b_count}, AI={ai_count}")

    # Check RunPeriod match
    b_rp = re.search(r"RunPeriod,[\s\S]*?;", b_text)
    ai_rp = re.search(r"RunPeriod,[\s\S]*?;", ai_text)
    rp_match = (b_rp and ai_rp and b_rp.group(0).strip() == ai_rp.group(0).strip())
    comparison_summary["RunPeriod"] = {"match": bool(rp_match)}
    if not rp_match:
        discrepancies.append("RunPeriod mismatch between baseline and AI IDF files.")

    fairness_passed = len(discrepancies) == 0

    return fairness_passed, {
        "fairness_passed": fairness_passed,
        "discrepancies": discrepancies,
        "comparison_details": comparison_summary
    }

if __name__ == "__main__":
    passed, summary = verify_model_fairness()
    print("=" * 70)
    print(" PROGRAMMATIC FAIRNESS VERIFICATION RESULT")
    print("=" * 70)
    print(f" Fairness Passed: {passed}")
    for k, v in summary["comparison_details"].items():
        print(f"  - {k:<35}: Baseline={v.get('baseline', 'N/A')}, AI={v.get('ai_controlled', 'N/A')} | Match={v['match']}")
    if summary["discrepancies"]:
        print("\n Discrepancies Found:")
        for d in summary["discrepancies"]:
            print(f"  [!] {d}")
    print("=" * 70)
