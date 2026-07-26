"""
Control Tool Module.
Translates a validated BuildingControlDecision into a ControlAction and passes it
through the existing EnergyPlusControlManager and safety validation layer.
This is the ONLY tool authorized to interact with live building actuators.
"""

from typing import Dict, Any, Tuple
from agent.schemas import BuildingControlDecision
from energyplus.control import ControlAction, EnergyPlusControlManager, ControlSafetyValidator

def execute_control_action(
    decision: BuildingControlDecision,
    control_manager: EnergyPlusControlManager,
    api: Any,
    state: Any,
    simulation_time: str
) -> Tuple[bool, str]:
    """
    Executes a BuildingControlDecision through existing safety validation and EnergyPlus actuators.
    Returns (success: bool, message: str).
    """
    if decision.action in ["MAINTAIN", "KEEP_OVERRIDE"]:
        return True, f"Action is {decision.action}. Active thermostat setpoints preserved."

    if decision.action == "RELEASE_TO_NATIVE":
        released = control_manager.reset_zone_override(api, state, decision.zone)
        if released:
            return True, f"Released override for {decision.zone}. Native thermostat schedule resumed."
        else:
            return False, f"Failed to release override for {decision.zone}."

    if decision.action != "ADJUST_SETPOINTS":
        return False, f"Unsupported action type '{decision.action}'."

    if decision.heating_setpoint is None or decision.cooling_setpoint is None:
        return False, "ADJUST_SETPOINTS decision missing heating or cooling setpoint."

    # Construct ControlAction
    action = ControlAction(
        zone=decision.zone,
        heating_setpoint=decision.heating_setpoint,
        cooling_setpoint=decision.cooling_setpoint,
        reason=decision.reason or "Agent AI Supervisory Adjustment",
        source="local_qwen_agent",
        timestamp=simulation_time
    )

    # 1. Run deterministic safety validation
    is_safe, msg = ControlSafetyValidator.validate(action)
    if not is_safe:
        return False, f"Safety Validation Rejected: {msg}"

    # 2. Apply via EnergyPlusControlManager
    applied = control_manager.apply_control_action(api, state, action, simulation_time)
    if applied:
        return True, f"Control Action Applied to {decision.zone}: Heating={decision.heating_setpoint}°C, Cooling={decision.cooling_setpoint}°C"
    else:
        return False, f"Failed to apply control action to PyEnergyPlus actuators for zone {decision.zone}."
