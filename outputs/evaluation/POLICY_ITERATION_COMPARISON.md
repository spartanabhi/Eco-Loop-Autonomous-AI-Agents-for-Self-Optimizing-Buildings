# Eco-Loop Policy Iteration Comparison Report

## Policy Iteration #1 Results

| Metric | Baseline | First Unbiased AI | Policy Iteration #1 AI |
|---|---|---|---|
| **Electricity Consumption** | `264.00 kWh` | `264.00 kWh` | **`264.00 kWh`** (`+0.00%`) |
| **Natural Gas Heating** | `728.19 kWh-eq` | N/A | **`728.19 kWh-eq`** (`+0.00%`) |
| **TOTAL SITE ENERGY** | `992.20 kWh-eq` | `264.00 kWh` | **`992.20 kWh-eq`** (**`+0.00%`**) |
| **Peak Electricity Demand** | `7.33 kW` | `7.33 kW` | **`7.33 kW`** (`+0.00%`) |
| **Thermal Comfort Compliance** | `63.7%` | `0.00%` | **`63.7%`** (`+0.0%`) |
| **Mean Occupied PMV** | `-0.42` | `+0.29` | **`-0.42`** |
| **Max Occupied CO2** | `792 ppm` | `784.2 ppm` | **`792 ppm`** |

## Corrected Policy Highlights
- **Thermodynamic Mode Alignment:** Enforced `hvac_mode` awareness (`HEATING`, `COOLING`, `DEADBAND`).
- **Occupied Comfort Guardrails:** Strictly blocked `RELAX_HEATING` when space is cold (`PMV < -0.5`), eliminating cooling relaxation during winter heating operation.
- **Fuel Breakdown Audit:** Captured `NaturalGas:Facility` meter (23.08 MJ/step = 6.41 kWh-eq per timestep) to evaluate true winter site energy reduction.
