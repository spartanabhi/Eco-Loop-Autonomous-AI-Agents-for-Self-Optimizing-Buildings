"""
Policy Unit Test Suite.
Verifies candidate action generation, occupied comfort guardrails, unoccupied setback rules,
restoration availability, and boundary clamping across 8 required policy cases.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator import AgentOrchestrator

def test_policy_cases():
    orchestrator = AgentOrchestrator()

    # Case A: Occupied + Too Cold + Heating -> NO RELAX_HEATING
    state_a = {
        "pmv": -0.81, "is_occupied": True, "hvac_mode": "HEATING",
        "carbon_status": "HIGH", "peak_status": "NORMAL",
        "current_heating_sp": 21.0, "current_cooling_sp": 24.0
    }
    cand_a = orchestrator.generate_allowed_candidates(state_a)
    assert "RELAX_HEATING_0_5C" not in cand_a, f"Case A Failed: RELAX_HEATING offered when too cold! {cand_a}"
    assert "RESTORE_HEATING_0_5C" in cand_a, f"Case A Failed: RESTORE_HEATING missing! {cand_a}"
    print("[PASS] Case A: Occupied + Too Cold + Heating -> NO RELAX_HEATING, RESTORE_HEATING offered")

    # Case B: Occupied + Comfortable + Heating + High Carbon -> RELAX_HEATING allowed
    state_b = {
        "pmv": 0.0, "is_occupied": True, "hvac_mode": "HEATING",
        "carbon_status": "HIGH", "peak_status": "NORMAL",
        "current_heating_sp": 21.0, "current_cooling_sp": 24.0
    }
    cand_b = orchestrator.generate_allowed_candidates(state_b)
    assert "RELAX_HEATING_0_5C" in cand_b, f"Case B Failed: RELAX_HEATING missing! {cand_b}"
    print("[PASS] Case B: Occupied + Comfortable + Heating + High Carbon -> RELAX_HEATING allowed")

    # Case C: Unoccupied + Heating -> RELAX_HEATING allowed
    state_c = {
        "pmv": -0.4, "is_occupied": False, "hvac_mode": "HEATING",
        "carbon_status": "LOW", "peak_status": "NORMAL",
        "current_heating_sp": 21.0, "current_cooling_sp": 24.0
    }
    cand_c = orchestrator.generate_allowed_candidates(state_c)
    assert "RELAX_HEATING_0_5C" in cand_c, f"Case C Failed: RELAX_HEATING missing for unoccupied! {cand_c}"
    print("[PASS] Case C: Unoccupied + Heating -> RELAX_HEATING allowed")

    # Case D: Occupied + Too Hot + Cooling -> NO RELAX_COOLING
    state_d = {
        "pmv": 0.75, "is_occupied": True, "hvac_mode": "COOLING",
        "carbon_status": "HIGH", "peak_status": "NORMAL",
        "current_heating_sp": 21.0, "current_cooling_sp": 24.0
    }
    cand_d = orchestrator.generate_allowed_candidates(state_d)
    assert "RELAX_COOLING_0_5C" not in cand_d, f"Case D Failed: RELAX_COOLING offered when too hot! {cand_d}"
    assert "RESTORE_COOLING_0_5C" in cand_d, f"Case D Failed: RESTORE_COOLING missing! {cand_d}"
    print("[PASS] Case D: Occupied + Too Hot + Cooling -> NO RELAX_COOLING, RESTORE_COOLING offered")

    # Case E: Occupied + Comfortable + Cooling + High Carbon -> RELAX_COOLING allowed
    state_e = {
        "pmv": 0.0, "is_occupied": True, "hvac_mode": "COOLING",
        "carbon_status": "HIGH", "peak_status": "NORMAL",
        "current_heating_sp": 21.0, "current_cooling_sp": 24.0
    }
    cand_e = orchestrator.generate_allowed_candidates(state_e)
    assert "RELAX_COOLING_0_5C" in cand_e, f"Case E Failed: RELAX_COOLING missing! {cand_e}"
    print("[PASS] Case E: Occupied + Comfortable + Cooling + High Carbon -> RELAX_COOLING allowed")

    # Case F: Previous relaxation caused comfort violation -> Restoration action available
    state_f = {
        "pmv": -0.60, "is_occupied": True, "hvac_mode": "HEATING",
        "carbon_status": "HIGH", "peak_status": "NORMAL",
        "current_heating_sp": 20.0, "current_cooling_sp": 24.0
    }
    cand_f = orchestrator.generate_allowed_candidates(state_f)
    assert "RESTORE_HEATING_0_5C" in cand_f, f"Case F Failed: RESTORE_HEATING missing! {cand_f}"
    print("[PASS] Case F: Previous relaxation caused comfort violation -> RESTORE_HEATING available")

    # Case G: Peak Normal -> Peak target does not force action
    state_g = {
        "pmv": 0.0, "is_occupied": True, "hvac_mode": "HEATING",
        "carbon_status": "LOW", "peak_status": "NORMAL",
        "current_heating_sp": 21.0, "current_cooling_sp": 24.0
    }
    cand_g = orchestrator.generate_allowed_candidates(state_g)
    assert cand_g == ["MAINTAIN"], f"Case G Failed: Expected MAINTAIN only, got {cand_g}"
    print("[PASS] Case G: Peak Normal + Low Carbon -> MAINTAIN only")

    # Case H: Setpoint at safety boundary -> Further relaxation unavailable
    state_h = {
        "pmv": 0.0, "is_occupied": False, "hvac_mode": "HEATING",
        "carbon_status": "HIGH", "peak_status": "NORMAL",
        "current_heating_sp": 18.0, "current_cooling_sp": 24.0
    }
    cand_h = orchestrator.generate_allowed_candidates(state_h)
    assert "RELAX_HEATING_0_5C" not in cand_h, f"Case H Failed: RELAX_HEATING offered at min floor! {cand_h}"
    print("[PASS] Case H: Heating setpoint at min floor 18.0°C -> RELAX_HEATING unavailable")

if __name__ == "__main__":
    test_policy_cases()
    print("\nAll 8 Policy Unit Tests Passed Successfully!")
