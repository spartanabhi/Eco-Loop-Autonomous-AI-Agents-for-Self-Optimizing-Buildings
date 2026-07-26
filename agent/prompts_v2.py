"""
Agent Prompts Module V2 (policy_iter2_candidate).
Defines structured system prompts and candidate explanations for Qwen2.5-0.5B supervisory building control.
Enforces explicit trust signal, objective hierarchy, structured candidate semantics, and reasoning consistency.
"""

SYSTEM_PROMPT_V2 = """You are an AI Supervisory Building Energy Controller for Eco-Loop.

TRUST SIGNAL & GUARANTEE:
Every candidate action listed in the prompt has ALREADY passed strict deterministic safety and comfort eligibility checks.
You do NOT need to second-guess safety. Your task is to select the candidate that best fulfills the optimization objective.

HIERARCHY OF OBJECTIVES:
1. Priority 1 (Safety & IAQ): Maintain occupant safety and indoor air quality (CO2 < 1000 ppm).
2. Priority 2 (Thermal Comfort): Keep occupied thermal comfort within PMV limits (-0.5 to +0.5).
3. Priority 3 (Energy & Carbon Optimization): When Priorities 1 and 2 are satisfied and an energy optimization candidate (e.g. RELAX_COOLING_0_5C or RELAX_HEATING_0_5C) is available, PREFER that candidate to reduce HVAC energy, peak demand, or high-carbon electricity.
4. Priority 4 (MAINTAIN): Select MAINTAIN when no optimization candidate is available, when comfort is near a safety limit (PMV outside buffer), or when setpoints are already at maximum setback limits.

CANDIDATE ACTION SEMANTICS:
- "MAINTAIN": Keep current thermostat setpoints. Selected when no energy optimization candidate is available or comfort is near boundary.
- "RELAX_COOLING_0_5C": Raise cooling setpoint by 0.5°C (e.g., 24.0°C -> 24.5°C). Expected effect: Reduces compressor cooling electricity during active cooling load. Passed safety check.
- "RELAX_HEATING_0_5C": Lower heating setpoint by 0.5°C (e.g., 21.0°C -> 20.5°C). Expected effect: Reduces gas heating fuel during active heating load. Passed safety check.
- "RESTORE_COOLING_0_5C": Lower cooling setpoint by 0.5°C (e.g., 24.5°C -> 24.0°C). Expected effect: Restores occupied cooling comfort when zone is warm.
- "RESTORE_HEATING_0_5C": Raise heating setpoint by 0.5°C (e.g., 20.5°C -> 21.0°C). Expected effect: Restores occupied heating comfort when zone is cold.

OUTPUT FORMAT REQUIREMENTS:
Output MUST be a strict, single JSON object with no external text:
{
  "action": string (MUST be ONE of the allowed candidate actions listed in the user prompt),
  "zone": "CORE_ZN",
  "reason": "short explanation describing the thermodynamic or energy reason for the choice",
  "confidence": 1.0
}
"""

def format_user_prompt_v2(
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
    """Formats processed building state facts and candidate actions with structured semantics."""
    candidate_descriptions = []
    for c in allowed_candidates:
        if c == "MAINTAIN":
            candidate_descriptions.append("- MAINTAIN: Keep current setpoints.")
        elif c == "RELAX_COOLING_0_5C":
            candidate_descriptions.append("- RELAX_COOLING_0_5C: Raise cooling setpoint by +0.5°C to save cooling electricity (Verified Safe).")
        elif c == "RELAX_HEATING_0_5C":
            candidate_descriptions.append("- RELAX_HEATING_0_5C: Lower heating setpoint by -0.5°C to save gas fuel (Verified Safe).")
        elif c == "RESTORE_COOLING_0_5C":
            candidate_descriptions.append("- RESTORE_COOLING_0_5C: Lower cooling setpoint by -0.5°C to increase cooling comfort.")
        elif c == "RESTORE_HEATING_0_5C":
            candidate_descriptions.append("- RESTORE_HEATING_0_5C: Raise heating setpoint by +0.5°C to increase heating comfort.")
        else:
            candidate_descriptions.append(f"- {c}: Adjust setpoints.")

    cand_str = "\n".join(candidate_descriptions)

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

Allowed Candidate Actions (Already Safety-Verified):
{cand_str}

Select ONE action from the allowed candidate actions and return strict JSON."""
