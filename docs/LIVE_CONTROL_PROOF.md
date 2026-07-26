# Live Closed-Loop Control Proof

> **Status:** LIVE CONTROL PROOF: PASSED

## Overview & Architecture

This document proves **TRUE bidirectional closed-loop control capability** within a single, active EnergyPlus simulation process using PyEnergyPlus runtime callbacks.

```
Active EnergyPlus Simulation Process
    │
    │  1. Observation Callback (callback_end_zone_timestep_after_zone_reporting)
    ▼
TelemetrySnapshot (Zone Temp, CO2, PMV, Electricity kWh)
    │
    │  2. Control Decision (Python Logic / Deterministic Rule)
    ▼
ControlSafetyValidator (Min/Max Bounds & Heating/Cooling Deadband)
    │
    │  3. ControlAction (Validated Setpoint Override)
    ▼
Control Callback (callback_begin_zone_timestep_before_init_heat_balance)
    │
    │  4. PyEnergyPlus Actuator Write (api.exchange.set_actuator_value)
    ▼
Same Active EnergyPlus Process (Simulation Continues & Zone State Responds)
```

## Technical Implementation Details

- **Observation Callback:** `callback_end_zone_timestep_after_zone_reporting`
  - *Rationale:* Executes after heat balance, occupant comfort, CO2 contaminant balance, and HVAC system calculations are fully resolved for each timestep.
- **Control Callback:** `callback_begin_zone_timestep_before_init_heat_balance`
  - *Rationale:* Executes at the beginning of each zone timestep before heat balance initialization, ensuring new setpoints are applied BEFORE EnergyPlus consumes them for the current timestep.
- **Actuator Strategy Selected:** Option B (`Zone Temperature Control` / `Heating Setpoint` & `Cooling Setpoint` per zone) with fallback to Option A (`Schedule:Compact` / `Schedule Value`).
- **Safety Boundaries Enforced:**
  - `MIN_HEATING_SETPOINT`: 12.0 °C
  - `MAX_HEATING_SETPOINT`: 26.0 °C
  - `MIN_COOLING_SETPOINT`: 18.0 °C
  - `MAX_COOLING_SETPOINT`: 32.0 °C
  - `MIN_DEADBAND`: 1.0 °C

## Empirical Closed-Loop Proof Results (Single Simulation Run ID: `test-run-1785062066`)

| Simulation Checkpoint | Timestamp | Zone | Heating Setpoint | Cooling Setpoint | Zone Temperature | Operational State |
|---|---|---|---|---|---|---|
| **Baseline (Pre-Override)** | `Day 21 08:10` | `CORE_ZN` | 21.00 °C | 23.90 °C | 21.00 °C | Native schedule active |
| **Override Applied** | `Day 21 09:00` | `CORE_ZN` | 19.00 °C | 22.50 °C | 21.00 °C | `set_actuator_value` write: SUCCESS |
| **Post-Control Verification** | `Day 21 10:10` | `CORE_ZN` | 19.00 °C | 22.50 °C | 19.00 °C | Thermostat setpoint changed & Temp responded |
| **Override Release Event** | `Day 21 15:00` | `CORE_ZN` | — | — | — | `reset_actuator` reset: SUCCESS |
| **Post-Release Verification** | `Day 21 16:10` | `CORE_ZN` | 21.00 °C | 26.70 °C | 21.00 °C | Native thermostat control resumed |

## Proof Summary
- **READ $\rightarrow$ WRITE $\rightarrow$ CONTINUE $\rightarrow$ READ CHANGED STATE $\rightarrow$ RESET** was executed completely within **ONE single EnergyPlus process** without restarting the simulation or rewriting IDF files.
- Thermostat setpoint changes were observed directly in EnergyPlus output variables, and zone thermal response was verified.
