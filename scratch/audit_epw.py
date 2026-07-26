"""
Direct EPW Weather File Audit Script.
Parses weather/weather.epw directly without EnergyPlus to extract min, mean, and max
outdoor drybulb temperatures for Jan 21-23, May 15-17, and Jul 21-23.
Generates outputs/evaluation/seasonal_integrity/EPW_PERIOD_AUDIT.md.
"""

import sys
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EPW_FILE = PROJECT_ROOT / "weather" / "weather.epw"
OUTPUT_MD = PROJECT_ROOT / "outputs" / "evaluation" / "seasonal_integrity" / "EPW_PERIOD_AUDIT.md"

def parse_epw_period(start_m: int, start_d: int, end_m: int, end_d: int):
    """Parses EPW file lines for specific month and day range."""
    temps = []
    with open(EPW_FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 10:
                try:
                    month = int(parts[1])
                    day = int(parts[2])
                    hour = int(parts[3])
                    drybulb = float(parts[6]) # Column 6 is Dry Bulb Temperature in deg C
                    if (month == start_m and start_d <= day <= end_d) or (start_m < month < end_m):
                        temps.append(drybulb)
                except ValueError:
                    continue
    return temps

def main():
    periods = {
        "Winter (Jan 21-23)": (1, 21, 1, 23),
        "Shoulder (May 15-17)": (5, 15, 5, 17),
        "Summer (Jul 21-23)": (7, 21, 7, 23)
    }

    results = {}
    for name, (sm, sd, em, ed) in periods.items():
        temps = parse_epw_period(sm, sd, em, ed)
        results[name] = {
            "count": len(temps),
            "min": float(np.min(temps)),
            "mean": float(np.mean(temps)),
            "max": float(np.max(temps))
        }

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)

    md_content = f"""# EPW Direct Weather File Period Audit

## Target Weather File: `weather/weather.epw` (Chicago O'Hare TMY3)

| Period | Record Count | Min Outdoor Temp (°C) | Mean Outdoor Temp (°C) | Max Outdoor Temp (°C) |
|---|---|---|---|---|
| **Winter (Jan 21-23)** | `{results['Winter (Jan 21-23)']['count']}` | `{results['Winter (Jan 21-23)']['min']:.1f} °C` | `{results['Winter (Jan 21-23)']['mean']:.1f} °C` | `{results['Winter (Jan 21-23)']['max']:.1f} °C` |
| **Shoulder (May 15-17)** | `{results['Shoulder (May 15-17)']['count']}` | `{results['Shoulder (May 15-17)']['min']:.1f} °C` | `{results['Shoulder (May 15-17)']['mean']:.1f} °C` | `{results['Shoulder (May 15-17)']['max']:.1f} °C` |
| **Summer (Jul 21-23)** | `{results['Summer (Jul 21-23)']['count']}` | `{results['Summer (Jul 21-23)']['min']:.1f} °C` | `{results['Summer (Jul 21-23)']['mean']:.1f} °C` | `{results['Summer (Jul 21-23)']['max']:.1f} °C` |

## Audit Summary
Direct parsing of `weather/weather.epw` proves that Chicago outdoor weather differs significantly between seasons:
- Winter mean outdoor drybulb: **{results['Winter (Jan 21-23)']['mean']:.1f} °C** (min: {results['Winter (Jan 21-23)']['min']:.1f} °C, max: {results['Winter (Jan 21-23)']['max']:.1f} °C)
- Shoulder mean outdoor drybulb: **{results['Shoulder (May 15-17)']['mean']:.1f} °C** (min: {results['Shoulder (May 15-17)']['min']:.1f} °C, max: {results['Shoulder (May 15-17)']['max']:.1f} °C)
- Summer mean outdoor drybulb: **{results['Summer (Jul 21-23)']['mean']:.1f} °C** (min: {results['Summer (Jul 21-23)']['min']:.1f} °C, max: {results['Summer (Jul 21-23)']['max']:.1f} °C)
"""

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[OK] EPW Period Audit complete. Saved to: {OUTPUT_MD}")
    for name, stats in results.items():
        print(f"  - {name:<22}: Min={stats['min']:5.1f}°C | Mean={stats['mean']:5.1f}°C | Max={stats['max']:5.1f}°C")

if __name__ == "__main__":
    main()
