# Eco-Loop Autonomous Closed-Loop System Architecture

## Complete Autonomous Loop Architecture

```
                                  [EnergyPlus 26.1 Simulation]
                                               │
                                 1. SENSE (Observation Callback)
                                               │
                                               ▼
                              TelemetrySnapshot (Temp, PMV, CO2, Occ, Demand)
                                               │
                                 2. THINK (Agent Orchestrator)
                                               │
                                               ▼
                             Evaluated State (Comfort, IAQ, Peak, Carbon)
                                               │
                                               ▼
                         Local Open-Weight LLM (Qwen2.5-0.5B-Instruct-Q3_K_S)
                                               │
                                               ▼
                         BuildingControlDecision (MAINTAIN / ADJUST_SETPOINTS)
                                               │
                                               ▼
                    Schema & Consistency Validation -> Rate Limit (1.5°C) & Anti-Oscillation
                                               │
                                               ▼
                          Deterministic Safety Validation (ControlSafetyValidator)
                                               │
                                 3. ACT (Control Callback)
                                               │
                                               ▼
                           Agent Tool (apply_control_action via ToolRegistry)
                                               │
                                               ▼
                        EnergyPlus Actuator (Zone Temperature Control Setpoints)
                                               │
                                 4. REPEAT (Same Process Continues)
                                               │
                                               └────────────────────────┐
                                                                        ▼
                                                         Next Telemetry Snapshot
```

## Architectural Components

1. **Sense (Observation Callback):**
   - Callback: `callback_end_zone_timestep_after_zone_reporting`.
   - Captures live metrics: `Zone Mean Air Temperature`, `Zone Air CO2 Concentration`, `Zone Thermal Comfort Fanger Model PMV`, `Zone People Occupant Count`, and `Electricity:Building` meter energy.
   - Calculates interval electricity demand in kW: $\Delta E / (900 \text{ s} \times 1000 \text{ W/kW})$.

2. **Think (Local Qwen Cognitive Engine):**
   - Evaluates occupancy awareness (`OCCUPIED` vs `UNOCCUPIED`), comfort status (`TOO_COLD`, `COMFORTABLE`, `TOO_HOT`), peak demand status (`NORMAL`, `NEAR_LIMIT`, `ABOVE_LIMIT`), and time-of-day carbon grid state (`LOW`, `MEDIUM`, `HIGH`).
   - Invokes local `Qwen2.5-0.5B-Instruct-Q3_K_S.gguf` via `llama-cpp-python` with `response_format={"type": "json_object"}`.

3. **Validation, Rate Limiting & Anti-Oscillation:**
   - **Schema Consistency:** Enforces strict alignment (if `MAINTAIN`, setpoints MUST be `null`).
   - **Rate Limiting:** Maximum allowed setpoint shift per decision interval = **$1.5^\circ\text{C}$**.
   - **Anti-Oscillation / Cooldown:** Reversal of setpoint adjustment direction for the same zone requires a minimum of 2 decision intervals (120 simulated minutes).
   - **Safety Constraints:** Enforces absolute heating ($12.0^\circ\text{C} - 26.0^\circ\text{C}$), cooling ($18.0^\circ\text{C} - 32.0^\circ\text{C}$), and minimum deadband ($1.0^\circ\text{C}$) boundaries.

4. **Act (Control Callback & Tool Registry):**
   - Pending decisions are queued and executed at `callback_begin_zone_timestep_before_init_heat_balance`.
   - Executes via `apply_control_action` in `AgentToolRegistry` to set actuator handles (`api.exchange.set_actuator_value`).

5. **Native Control Fallback & Error Handling:**
   - If model output is invalid twice or safety checks fail, the system falls back to `MAINTAIN` or releases actuator overrides (`api.exchange.reset_actuator`), resuming native EnergyPlus thermostat schedules.
   - Automatically parses `eplusout.err` via `extract_runtime_errors` tool upon simulation completion.
