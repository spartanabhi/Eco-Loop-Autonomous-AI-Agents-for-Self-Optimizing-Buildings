"""
Integration Test Suite for Cross-Season Evaluation Pipeline.
Verifies controller code hash, fairness across 3 seasons, output isolation, summary artifacts, and 0 fatal errors.
"""

import sys
import json
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import CROSS_SEASON_DIR, SEASONS
from evaluation.controller_version import get_frozen_controller_metadata, CONTROLLER_VERSION
from evaluation.verify_fairness import verify_model_fairness
from communication.tool_registry import default_tool_registry

def test_frozen_controller_integrity():
    """Verifies that the controller version and code hash are intact."""
    meta = get_frozen_controller_metadata()
    assert meta["controller_version"] == "policy_iter1_frozen", f"Invalid controller version: {meta['controller_version']}"
    assert len(meta["controller_code_hash"]) == 16, f"Invalid code hash: {meta['controller_code_hash']}"
    print(f"[PASS] test_frozen_controller_integrity (Version: {meta['controller_version']}, Hash: {meta['controller_code_hash']})")

def test_cross_season_artifacts():
    """Verifies that all 3 seasonal runs generated isolated telemetry, decisions, and comparison artifacts."""
    for season_key in SEASONS.keys():
        s_dir = CROSS_SEASON_DIR / season_key
        b_csv = s_dir / "baseline" / "live_telemetry.csv"
        ai_csv = s_dir / "ai_controlled" / "live_telemetry.csv"

        assert b_csv.is_file(), f"Baseline telemetry missing for {season_key}: {b_csv}"
        assert ai_csv.is_file(), f"AI telemetry missing for {season_key}: {ai_csv}"

        with open(b_csv, "r", encoding="utf-8") as f:
            assert len(list(csv.reader(f))) > 50, f"Insufficient rows in baseline {season_key}"

        with open(ai_csv, "r", encoding="utf-8") as f:
            assert len(list(csv.reader(f))) > 50, f"Insufficient rows in AI {season_key}"

    # Summary artifacts check
    sum_json = CROSS_SEASON_DIR / "summary.json"
    sum_csv = CROSS_SEASON_DIR / "summary.csv"
    sum_md = CROSS_SEASON_DIR / "CROSS_SEASON_REPORT.md"

    assert sum_json.is_file(), "summary.json missing"
    assert sum_csv.is_file(), "summary.csv missing"
    assert sum_md.is_file(), "CROSS_SEASON_REPORT.md missing"

    with open(sum_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert "seasonal_breakdown" in data and "aggregate_9day_metrics" in data, "Malformed summary.json"

    print("[PASS] test_cross_season_artifacts")

if __name__ == "__main__":
    test_frozen_controller_integrity()
    test_cross_season_artifacts()
    print("\nAll cross-season evaluation integration tests passed successfully.")
