"""
Agent Schemas & Structured Decision Data Structures.
Defines machine-actionable BuildingControlDecision schema, discrete candidate options,
and schema + explanation consistency validators.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

# Supported Discrete ECM Candidate Actions
SUPPORTED_ACTIONS = [
    "MAINTAIN",
    "RELAX_HEATING_0_5C",
    "RESTORE_HEATING_0_5C",
    "RELAX_COOLING_0_5C",
    "RESTORE_COOLING_0_5C",
    "RELEASE_TO_NATIVE",
    "ADJUST_SETPOINTS"
]

@dataclass
class BuildingControlDecision:
    """
    Machine-actionable structured control decision output by the LLM agent.
    """
    action: str  # One of SUPPORTED_ACTIONS
    zone: str  # e.g., "CORE_ZN"
    heating_setpoint: Optional[float] = None
    cooling_setpoint: Optional[float] = None
    reason: str = ""
    confidence: float = 1.0
    ecm_type: str = "dynamic_thermostat_setpoint"
    target_priority: str = "balanced"
    explanation_consistent: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildingControlDecision":
        action = str(data.get("action", "MAINTAIN")).upper().strip()
        zone = str(data.get("zone", "CORE_ZN")).strip()
        htg = float(data["heating_setpoint"]) if data.get("heating_setpoint") is not None else None
        clg = float(data["cooling_setpoint"]) if data.get("cooling_setpoint") is not None else None
        reason = str(data.get("reason", ""))
        
        # Reason consistency check: flag if reason mentions adjusting when action is MAINTAIN
        consistent = True
        if action in ["MAINTAIN", "RELEASE_TO_NATIVE"] and "adjusting setpoint" in reason.lower() and "not" not in reason.lower():
            consistent = False

        return cls(
            action=action,
            zone=zone,
            heating_setpoint=htg,
            cooling_setpoint=clg,
            reason=reason,
            confidence=float(data.get("confidence", 1.0)),
            ecm_type=str(data.get("ecm_type", "dynamic_thermostat_setpoint")),
            target_priority=str(data.get("target_priority", "balanced")),
            explanation_consistent=consistent
        )

def validate_decision_schema(data: Dict[str, Any]) -> tuple[bool, str]:
    """Validates raw JSON dict against BuildingControlDecision schema rules."""
    if not isinstance(data, dict):
        return False, "Output must be a JSON dictionary."

    action = str(data.get("action", "")).upper().strip()
    if action not in SUPPORTED_ACTIONS:
        return False, f"Invalid action '{action}'. Must be one of {SUPPORTED_ACTIONS}."

    zone = str(data.get("zone", "")).strip()
    valid_zones = ["CORE_ZN", "PERIMETER_ZN_1", "PERIMETER_ZN_2", "PERIMETER_ZN_3", "PERIMETER_ZN_4"]
    if zone not in valid_zones:
        return False, f"Invalid zone '{zone}'. Must be one of {valid_zones}."

    if action == "ADJUST_SETPOINTS":
        htg = data.get("heating_setpoint")
        clg = data.get("cooling_setpoint")

        if htg is None or clg is None:
            return False, "ADJUST_SETPOINTS requires non-null heating_setpoint and cooling_setpoint."

        try:
            float(htg)
            float(clg)
        except (ValueError, TypeError):
            return False, "heating_setpoint and cooling_setpoint must be numeric numbers."

    return True, "Valid"
