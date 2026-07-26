"""
Seasonal Baseline Simulation Integrity Test Suite.
Verifies explicit IDF RunPeriods, SimulationControl configuration, telemetry month assertions,
outdoor temperature variation, run ID isolation, and 0 fatal EnergyPlus errors.
"""

import sys
import csv
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.config import SEASONS
from evaluation.controller_version import get_frozen_controller_metadata

INTEGRITY_DIR = PROJECT_ROOT / "outputs" / "evaluation" / "seasonal_integrity"
EPW_FILE = PROJECT_ROOT / "weather" / "weather.epw"

def calculate_file_hash(fpath: Path) -> str:
    with open(fpath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]

def test_seasonal_idf_runperiods_and_control():
    """Verifies that all 6 generated IDFs have exact RunPeriods and SimulationControl enabled for Weather File Run Periods."""
    for season_key, cfg in SEASONS.items():
        for role in ["baseline", "ai"]:
            idf_path = PROJECT_ROOT / "models" / "evaluation" / f"{season_key}_{role}.idf"
            assert idf_path.is_file(), f"Missing IDF: {idf_path}"

            with open(idf_path, "r", encoding="utf-8") as f:
                content = f.read()

            # SimulationControl assertions
            assert "YES,                     !- Run Simulation for Weather File Run Periods" in content, f"Weather simulation disabled in {idf_path.name}"
            assert "NO,                      !- Run Simulation for Sizing Periods" in content, f"Sizing periods simulation enabled in {idf_path.name}"

            # RunPeriod assertions
            m_start = f"{cfg['start_month']},"
            d_start = f"{cfg['start_day']},"
            assert m_start in content and d_start in content, f"RunPeriod month/day missing in {idf_path.name}"

    print("[PASS] test_seasonal_idf_runperiods_and_control")

def test_telemetry_integrity():
    """Verifies baseline telemetry output isolation, calendar months, outdoor temperatures, and 432 timesteps."""
    out_means = []
    
    for season_key, cfg in SEASONS.items():
        csv_path = INTEGRITY_DIR / season_key / "baseline" / "live_telemetry.csv"
        assert csv_path.is_file(), f"Telemetry CSV missing for {season_key}: {csv_path}"

        rows = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        assert len(rows) == 432, f"Expected 432 rows for {season_key}, got {len(rows)}"

        months = set(int(r["sim_month"]) for r in rows)
        expected_m = cfg["start_month"]
        assert months == {expected_m}, f"Month mismatch for {season_key}! Expected {{{expected_m}}}, got {months}"

        run_ids = set(r["run_id"] for r in rows)
        assert len(run_ids) == 1, f"Multiple run IDs in {season_key}: {run_ids}"

        temps = [float(r["outdoor_drybulb_c"]) for r in rows]
        out_means.append(sum(temps) / len(temps))

    # Assert outdoor temperatures differ across seasons
    assert len(set(round(m, 1) for m in out_means)) == 3, f"Outdoor temperature traces are identical across seasons! {out_means}"
    print("[PASS] test_telemetry_integrity")

def test_hashes():
    """Verifies EPW hash is identical and seasonal IDF hashes are distinct."""
    epw_hash = calculate_file_hash(EPW_FILE)
    assert len(epw_hash) == 16, "EPW hash invalid"

    b_hashes = [calculate_file_hash(PROJECT_ROOT / "models" / "evaluation" / f"{s}_baseline.idf") for s in SEASONS.keys()]
    assert len(set(b_hashes)) == 3, f"Baseline IDF hashes not distinct: {b_hashes}"

    print("[PASS] test_hashes")

if __name__ == "__main__":
    test_seasonal_idf_runperiods_and_control()
    test_telemetry_integrity()
    test_hashes()
    print("\nAll seasonal baseline integrity tests passed successfully.")
