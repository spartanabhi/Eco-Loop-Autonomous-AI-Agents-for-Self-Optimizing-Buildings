"""
Integration Test Suite for Scientific Evaluation Pipeline.
Verifies fairness checks, baseline & AI runs, comparison artifact generation, and error-free execution.
"""

import sys
import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import (
    BASELINE_OUTPUT_DIR, AI_OUTPUT_DIR, OUTPUTS_EVALUATION_DIR
)
from evaluation.verify_fairness import verify_model_fairness
from communication.tool_registry import default_tool_registry

def test_model_fairness():
    """Verifies that baseline and AI control-ready IDF models are 100% physically identical."""
    passed, summary = verify_model_fairness()
    assert passed, f"Model fairness failed: {summary['discrepancies']}"

def test_evaluation_artifacts_and_metrics():
    """Verifies evaluation artifacts, telemetry consistency, and error-free EnergyPlus execution."""
    # 1. Telemetry files check
    b_csv = BASELINE_OUTPUT_DIR / "live_telemetry.csv"
    ai_csv = AI_OUTPUT_DIR / "live_telemetry.csv"

    assert b_csv.is_file(), f"Baseline telemetry CSV missing: {b_csv}"
    assert ai_csv.is_file(), f"AI telemetry CSV missing: {ai_csv}"

    with open(b_csv, "r", encoding="utf-8") as f:
        b_rows = list(csv.reader(f))
        assert len(b_rows) > 50, "Baseline telemetry has insufficient rows"

    with open(ai_csv, "r", encoding="utf-8") as f:
        ai_rows = list(csv.reader(f))
        assert len(ai_rows) > 50, "AI telemetry has insufficient rows"

    # 2. Check identical evaluation start time
    assert b_rows[1][1] == ai_rows[1][1], f"Evaluation period mismatch! Baseline starts at {b_rows[1][1]}, AI starts at {ai_rows[1][1]}"

    # 3. Artifact files check
    comp_json = OUTPUTS_EVALUATION_DIR / "comparison.json"
    comp_csv = OUTPUTS_EVALUATION_DIR / "comparison.csv"
    comp_md = OUTPUTS_EVALUATION_DIR / "EVALUATION_REPORT.md"

    assert comp_json.is_file(), "comparison.json missing"
    assert comp_csv.is_file(), "comparison.csv missing"
    assert comp_md.is_file(), "EVALUATION_REPORT.md missing"

    with open(comp_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "baseline_metrics" in data and "ai_metrics" in data, "Malformed comparison.json"
        assert "comparisons" in data, "Comparisons missing from comparison.json"

    # 4. EnergyPlus Runtime Errors check (0 fatal errors)
    b_err = BASELINE_OUTPUT_DIR / "eplusout.err"
    ai_err = AI_OUTPUT_DIR / "eplusout.err"

    if b_err.is_file():
        b_summary = default_tool_registry.execute_tool("extract_runtime_errors", err_file_path=str(b_err))
        assert b_summary["fatal_count"] == 0, f"Baseline fatal errors found: {b_summary['fatal_count']}"

    if ai_err.is_file():
        ai_summary = default_tool_registry.execute_tool("extract_runtime_errors", err_file_path=str(ai_err))
        assert ai_summary["fatal_count"] == 0, f"AI fatal errors found: {ai_summary['fatal_count']}"

    print("[PASS] test_evaluation_artifacts_and_metrics")

if __name__ == "__main__":
    test_model_fairness()
    test_evaluation_artifacts_and_metrics()
    print("\nAll evaluation integration tests passed successfully.")
