"""
Centralized Configuration for Eco-Loop Building Agents.
Reads configuration from environment variables (.env file) without hardcoding system paths.
"""

import os
from pathlib import Path

# Base project directory (workspace root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Try loading python-dotenv if installed
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# EnergyPlus System Configuration
ENERGYPLUS_HOME = os.getenv("ENERGYPLUS_HOME", "").strip()
ENERGYPLUS_EXECUTABLE = os.getenv("ENERGYPLUS_EXECUTABLE", "").strip()
ENERGYPLUS_PYTHON_API_PATH = os.getenv("ENERGYPLUS_PYTHON_API_PATH", "").strip()

# Simulation Files Configuration
_baseline_idf = os.getenv("BASELINE_IDF", "models/baseline/baseline.idf").strip()
BASELINE_IDF = Path(_baseline_idf) if os.path.isabs(_baseline_idf) else PROJECT_ROOT / _baseline_idf

_weather_file = os.getenv("WEATHER_FILE", "weather/weather.epw").strip()
WEATHER_FILE = Path(_weather_file) if os.path.isabs(_weather_file) else PROJECT_ROOT / _weather_file

_output_dir = os.getenv("OUTPUT_DIRECTORY", "outputs").strip()
OUTPUT_DIRECTORY = Path(_output_dir) if os.path.isabs(_output_dir) else PROJECT_ROOT / _output_dir

# Directory Structure Paths
MODELS_DIR = PROJECT_ROOT / "models"
BASELINE_MODELS_DIR = MODELS_DIR / "baseline"
MODIFIED_MODELS_DIR = MODELS_DIR / "modified"
WEATHER_DIR = PROJECT_ROOT / "weather"
OUTPUTS_BASELINE_DIR = OUTPUT_DIRECTORY / "baseline"
OUTPUTS_AI_DIR = OUTPUT_DIRECTORY / "ai_controlled"
LOGS_DIR = PROJECT_ROOT / "logs"

def get_summary() -> dict:
    """Return dictionary summary of current settings."""
    return {
        "PROJECT_ROOT": str(PROJECT_ROOT),
        "ENERGYPLUS_HOME": ENERGYPLUS_HOME or "Not Set",
        "ENERGYPLUS_EXECUTABLE": ENERGYPLUS_EXECUTABLE or "Not Set",
        "ENERGYPLUS_PYTHON_API_PATH": ENERGYPLUS_PYTHON_API_PATH or "Not Set",
        "BASELINE_IDF": str(BASELINE_IDF),
        "WEATHER_FILE": str(WEATHER_FILE),
        "OUTPUT_DIRECTORY": str(OUTPUT_DIRECTORY),
    }
