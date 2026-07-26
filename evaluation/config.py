"""
Cross-Season Evaluation Configuration Module.
Centralized parameters for 3-season representative validation (Winter, Shoulder, Summer).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# File Paths
BASELINE_IDF = PROJECT_ROOT / "models" / "baseline" / "evaluation_baseline.idf"
AI_CONTROLLED_IDF = PROJECT_ROOT / "models" / "modified" / "control_ready.idf"
WEATHER_FILE = PROJECT_ROOT / "weather" / "weather.epw"

OUTPUTS_EVALUATION_DIR = PROJECT_ROOT / "outputs" / "evaluation"
CROSS_SEASON_DIR = OUTPUTS_EVALUATION_DIR / "cross_season"

# Seasonal Period Definitions (Chicago O'Hare TMY3)
SEASONS = {
    "winter": {
        "name": "Winter (Cold / Heating Dominated)",
        "start_month": 1, "start_day": 21,
        "end_month": 1, "end_day": 23,
        "num_days": 3,
        "start_day_of_week": "Tuesday",
        "rationale": "Peak winter cold period (Jan 21-23) testing heating-dominated control and occupied cold comfort guardrails."
    },
    "shoulder": {
        "name": "Shoulder / Mild (Spring Deadband)",
        "start_month": 5, "start_day": 15,
        "end_month": 5, "end_day": 17,
        "num_days": 3,
        "start_day_of_week": "Friday",
        "rationale": "Mild spring period (May 15-17) testing deadband operation, mild weather conditions, and unoccupied setback opportunities."
    },
    "summer": {
        "name": "Summer (Warm / Cooling Dominated)",
        "start_month": 7, "start_day": 21,
        "end_month": 7, "end_day": 23,
        "num_days": 3,
        "start_day_of_week": "Tuesday",
        "rationale": "Warm summer period (Jul 21-23) testing active VAV cooling load, cooling setpoint relaxation, and peak-demand management."
    }
}

# Decision & Benchmark Parameters
AGENT_DECISION_INTERVAL_STEPS = 4  # 60 simulated minutes
MIN_COMFORT_PMV = -0.5
MAX_COMFORT_PMV = +0.5
PEAK_DEMAND_THRESHOLD_KW = 15.0  # kW
CO2_IAQ_THRESHOLD_PPM = 1000.0   # ppm

TARGET_ZONE = "CORE_ZN"
ALL_ZONES = ["CORE_ZN", "PERIMETER_ZN_1", "PERIMETER_ZN_2", "PERIMETER_ZN_3", "PERIMETER_ZN_4"]
