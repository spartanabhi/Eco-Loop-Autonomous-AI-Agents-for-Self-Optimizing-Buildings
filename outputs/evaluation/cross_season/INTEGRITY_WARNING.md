# UNVERIFIED SEASONAL EVALUATION WARNING

> **[!CAUTION]**
> The previous seasonal evaluation results in this directory (`outputs/evaluation/cross_season/`) are **UNVERIFIED AND SUSPECT**.

## Root Cause Summary
- **SimulationControl Defect:** In `models/baseline/evaluation_baseline.idf` and `models/modified/control_ready.idf`, the `SimulationControl` object had:
  - `Run Simulation for Sizing Periods = YES`
  - `Run Simulation for Weather File Run Periods = NO`
- **Impact:** EnergyPlus bypassed the weather file `RunPeriod` entirely and executed only the fixed `SizingPeriod:DesignDay` objects. As a result, Winter, Shoulder, and Summer runs executed identical design-day sequences, producing identical metrics (`264.01 kWh` electricity, `728.19 kWh-eq` gas, `PMV = -0.42`).

## Corrective Action
- `SimulationControl` updated across all evaluation IDFs:
  - `Run Simulation for Sizing Periods = NO`
  - `Run Simulation for Weather File Run Periods = YES`
- Explicit, immutable seasonal IDF files generated under `models/evaluation/`.
- Real weather telemetry (`Site Outdoor Air Drybulb Temperature`) added to verify distinct seasonal weather execution.
- Verified cross-season evaluation outputs generated under `outputs/evaluation/cross_season_verified/`.
