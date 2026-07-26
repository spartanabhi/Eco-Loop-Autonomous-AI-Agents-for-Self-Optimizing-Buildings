"""
Explicit Seasonal IDF Generator Script.
Generates 6 distinct, immutable IDF files under models/evaluation/:
- winter_baseline.idf, winter_ai.idf
- shoulder_baseline.idf, shoulder_ai.idf
- summer_baseline.idf, summer_ai.idf

Ensures SimulationControl has:
  Run Simulation for Sizing Periods = NO
  Run Simulation for Weather File Run Periods = YES
and exact, immutable RunPeriod objects.
"""

import sys
import re
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_EVAL_DIR = PROJECT_ROOT / "models" / "evaluation"
MODELS_EVAL_DIR.mkdir(parents=True, exist_ok=True)

BASE_BASELINE_IDF = PROJECT_ROOT / "models" / "baseline" / "evaluation_baseline.idf"
BASE_AI_IDF = PROJECT_ROOT / "models" / "modified" / "control_ready.idf"

SEASONS = {
    "winter": {"start_m": 1, "start_d": 21, "end_m": 1, "end_d": 23, "start_day": "Tuesday"},
    "shoulder": {"start_m": 5, "start_d": 15, "end_m": 5, "end_d": 17, "start_day": "Friday"},
    "summer": {"start_m": 7, "start_d": 21, "end_m": 7, "end_d": 23, "start_day": "Tuesday"}
}

def update_sim_control(content: str) -> str:
    """Updates SimulationControl to run Weather File RunPeriods and skip Sizing Periods."""
    new_sim_control = """  SimulationControl,
    YES,                     !- Do Zone Sizing Calculation
    YES,                     !- Do System Sizing Calculation
    YES,                     !- Do Plant Sizing Calculation
    NO,                      !- Run Simulation for Sizing Periods
    YES,                     !- Run Simulation for Weather File Run Periods
    No,                      !- Do HVAC Sizing Simulation for Sizing Periods
    1;                       !- Maximum Number of HVAC Sizing Simulation Passes"""

    if "SimulationControl," in content:
        content = re.sub(r"SimulationControl,[\s\S]*?;", new_sim_control, content, count=1)
    else:
        content = new_sim_control + "\n\n" + content
    return content

def set_run_period(content: str, start_m: int, start_d: int, end_m: int, end_d: int, start_day: str) -> str:
    """Sets exact RunPeriod in IDF string."""
    new_rp = f"""  RunPeriod,
    EvaluationPeriod,        !- Name
    {start_m},                       !- Begin Month
    {start_d},                      !- Begin Day of Month
    ,                        !- Begin Year
    {end_m},                       !- End Month
    {end_d},                      !- End Day of Month
    ,                        !- End Year
    {start_day},                 !- Day of Week for Start Day
    Yes,                     !- Use Weather File Holidays and Special Days
    Yes,                     !- Use Weather File Daylight Saving Period
    No,                      !- Apply Weekend Holiday Rule
    Yes,                     !- Use Weather File Rain Indicators
    Yes;                     !- Use Weather File Snow Indicators"""

    if "RunPeriod," in content:
        content = re.sub(r"RunPeriod,[\s\S]*?;", new_rp, content, count=1)
    else:
        content = content + "\n\n" + new_rp
    return content

def calculate_sha256(fpath: Path) -> str:
    with open(fpath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]

def main():
    print("=" * 65)
    print(" GENERATING EXPLICIT SEASONAL EVALUATION IDFS")
    print("=" * 65)

    hashes = {}

    for season, cfg in SEASONS.items():
        # Baseline IDF
        with open(BASE_BASELINE_IDF, "r", encoding="utf-8", errors="replace") as f:
            b_content = f.read()

        b_content = update_sim_control(b_content)
        b_content = set_run_period(b_content, cfg["start_m"], cfg["start_d"], cfg["end_m"], cfg["end_d"], cfg["start_day"])

        b_out = MODELS_EVAL_DIR / f"{season}_baseline.idf"
        with open(b_out, "w", encoding="utf-8") as f:
            f.write(b_content)

        # AI IDF
        with open(BASE_AI_IDF, "r", encoding="utf-8", errors="replace") as f:
            ai_content = f.read()

        ai_content = update_sim_control(ai_content)
        ai_content = set_run_period(ai_content, cfg["start_m"], cfg["start_d"], cfg["end_m"], cfg["end_d"], cfg["start_day"])

        ai_out = MODELS_EVAL_DIR / f"{season}_ai.idf"
        with open(ai_out, "w", encoding="utf-8") as f:
            f.write(ai_content)

        hashes[f"{season}_baseline"] = calculate_sha256(b_out)
        hashes[f"{season}_ai"] = calculate_sha256(ai_out)

        print(f" [OK] Generated {b_out.name:<20} (SHA256: {hashes[f'{season}_baseline']})")
        print(f" [OK] Generated {ai_out.name:<20} (SHA256: {hashes[f'{season}_ai']})")

    print("\nVerified distinct IDF hashes:")
    b_hashes = [hashes[f"{s}_baseline"] for s in SEASONS.keys()]
    ai_hashes = [hashes[f"{s}_ai"] for s in SEASONS.keys()]
    assert len(set(b_hashes)) == 3, f"Baseline IDF hashes are not distinct: {b_hashes}"
    assert len(set(ai_hashes)) == 3, f"AI IDF hashes are not distinct: {ai_hashes}"
    print(" [PASS] All 3 seasonal Baseline IDF hashes are 100% distinct.")
    print(" [PASS] All 3 seasonal AI IDF hashes are 100% distinct.")

if __name__ == "__main__":
    main()
