"""
Foundation Unit Tests for Eco-Loop Building Agents.
Verifies configuration loading, path discovery, and EnergyPlus API runner foundation.
"""

import os
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BASELINE_IDF, WEATHER_FILE, OUTPUT_DIRECTORY
from energyplus.environment import find_energyplus, setup_energyplus_path
from energyplus.runner import EnergyPlusRunnerFoundation

def test_settings_load():
    """Verify settings module initializes without error."""
    assert BASELINE_IDF is not None
    assert WEATHER_FILE is not None
    assert OUTPUT_DIRECTORY is not None
    print("[PASS] test_settings_load")

def test_energyplus_environment_discovery():
    """Test EnergyPlus environment discovery."""
    info = find_energyplus()
    assert isinstance(info, dict)
    assert "installed" in info
    print(f"[PASS] test_energyplus_environment_discovery (installed={info['installed']})")

def test_runner_foundation_instantiation():
    """Test EnergyPlusRunnerFoundation initialization."""
    runner = EnergyPlusRunnerFoundation()
    assert runner is not None
    api_ok = runner.initialize_api()
    print(f"[PASS] test_runner_foundation_instantiation (API available={api_ok})")

if __name__ == "__main__":
    test_settings_load()
    test_energyplus_environment_discovery()
    test_runner_foundation_instantiation()
    print("\nAll foundation tests executed.")
