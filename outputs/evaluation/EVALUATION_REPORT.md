# Eco-Loop Evaluation Report

## Experimental Setup
- **Building Model:** DOE RefBldgSmallOfficeNew2004 (Chicago O'Hare TMY3)
- **Evaluation Period:** Jan 21 to Jan 23 (3 Consecutive Days, 288 Timesteps)
- **Decision Interval:** 60 simulated minutes (Every 4 Zone Timesteps)
- **LLM Engine:** Local Qwen2.5-0.5B-Instruct-Q3_K_S.gguf (via llama-cpp-python)

## Fairness Controls
- **Physical Parity:** Programmatically verified 100% identical geometry, envelope, zones, equipment, occupancy, and weather between baseline and AI control-ready IDF models.
- **Sensor Alignment:** Both runs utilized identical reporting variables (`Zone Mean Air Temperature`, `Zone Air CO2 Concentration`, `Zone Thermal Comfort Fanger Model PMV`, `Zone People Occupant Count`, `Electricity:Building`).

## Quantitative Results Summary

| Metric | Baseline | AI Controlled | Difference / Reduction |
|---|---|---|---|
| **Total Electricity Consumption** | `264.00 kWh` | `264.00 kWh` | **`+0.00%`** |
| **Peak Electricity Demand** | `7.33 kW` | `7.33 kW` | **`+0.00%`** |
| **Thermal Comfort Compliance (-0.5 <= PMV <= +0.5)** | `63.7%` | `0.0%` | **`-63.7%`** |
| **Mean Occupied PMV** | `-0.42` | `+0.29` | -- |
| **Mean Occupied Zone Temperature** | `23.13 °C` | `25.51 °C` | -- |
| **Max Occupied CO2 Concentration** | `792 ppm` | `784 ppm` | -- |
| **Simulated Carbon-Intensity Score (PoC Metric)** | `92733 g` | `92733 g` | **`+0.00%`** |

## Agent Behaviour Analysis
- **Total Qwen Decisions:** `257`
- **Action Distribution:** `{"MAINTAIN": 211, "ADJUST_SETPOINTS": 46}`
- **Actuator Writes Applied:** `8`
- **Inference Latency:** Mean = `7.86s`, Median = `6.69s`, Max = `44.49s`

## Limitations
- Evaluation executed over a representative 3-day winter period (Chicago TMY3).
- Carbon grid intensity is derived from a local simulated time-of-day profile (PoC metric).
