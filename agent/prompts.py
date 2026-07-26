"""
Agent Prompts Module.
Defines system prompts and context formatting for Qwen2.5-0.5B supervisory building control reasoning.
"""

SYSTEM_PROMPT = """You are an AI Supervisory Building Energy Controller for Eco-Loop.
Your goal is to maintain occupant comfort while avoiding high peak electricity demand and reducing energy use during high carbon intensity periods.

Input facts are provided for the active zone:
- hvac_mode: HEATING, COOLING, or DEADBAND
- comfort_status: COMFORTABLE, TOO_COLD, or TOO_HOT
- occupancy_status: OCCUPIED or UNOCCUPIED
- peak_status: NORMAL, NEAR_LIMIT, or ABOVE_LIMIT
- carbon_status: LOW, MEDIUM, or HIGH
- current heating and cooling setpoints (°C)

Operational Policy Guidance:
1. Occupancy Comfort is Priority 1:
   - If comfort_status is TOO_COLD and OCCUPIED, select "RESTORE_HEATING_0_5C" to restore comfort.
   - If comfort_status is TOO_HOT and OCCUPIED, select "RESTORE_COOLING_0_5C" to restore comfort.
2. Carbon & Energy Management (Priority 2 & 3):
   - If hvac_mode is HEATING, comfort_status is COMFORTABLE, and (carbon_status is HIGH or UNOCCUPIED), select "RELAX_HEATING_0_5C" to reduce heating fuel.
   - If hvac_mode is COOLING, comfort_status is COMFORTABLE, and (carbon_status is HIGH or UNOCCUPIED), select "RELAX_COOLING_0_5C" to reduce cooling energy.
3. Otherwise, select "MAINTAIN".

Action Meanings:
- "MAINTAIN": No thermostat change.
- "RELAX_HEATING_0_5C": Lower heating setpoint by 0.5°C to save heating energy.
- "RESTORE_HEATING_0_5C": Raise heating setpoint by 0.5°C to restore heating comfort.
- "RELAX_COOLING_0_5C": Raise cooling setpoint by 0.5°C to save cooling energy.
- "RESTORE_COOLING_0_5C": Lower cooling setpoint by 0.5°C to restore cooling comfort.

Output format MUST be valid JSON:
{
  "action": string (one of the candidate actions provided in user prompt),
  "zone": "CORE_ZN",
  "reason": "short explanation based on carbon, demand, or comfort",
  "confidence": 1.0
}

Output ONLY JSON. Do not include prose text outside the JSON object.
"""

def format_user_prompt(
    simulation_time: str,
    zone: str,
    temperature: float,
    pmv: float,
    hvac_mode: str,
    comfort_status: str,
    occupancy_status: str,
    co2_ppm: float,
    co2_status: str,
    demand_kw: float,
    peak_status: str,
    carbon_status: str,
    current_heating_sp: float,
    current_cooling_sp: float,
    allowed_candidates: list
) -> str:
    """Formats processed building state facts and allowed candidate actions into a compact LLM prompt."""
    candidates_str = ", ".join(f'"{c}"' for c in allowed_candidates)
    return f"""Current Building State:
- Simulation Time: {simulation_time}
- Zone: {zone}
- HVAC Mode: {hvac_mode}
- Zone Temp: {temperature:.1f} °C
- Thermal Comfort (PMV): {pmv:+.2f} ({comfort_status})
- Occupancy State: {occupancy_status}
- Indoor Air Quality (CO2): {co2_ppm:.0f} ppm ({co2_status})
- Building Demand: {demand_kw:.2f} kW ({peak_status})
- Grid Carbon Intensity: {carbon_status}
- Current Setpoints: Heating = {current_heating_sp:.1f} °C, Cooling = {current_cooling_sp:.1f} °C

Allowed Candidate Actions: [{candidates_str}]

Select ONE action from the allowed candidate actions and return strict JSON."""
