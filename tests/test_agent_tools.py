"""
Unit Tests for Custom Agent Tools.
Verifies file_parser, error_extractor, control_tool translation, and safety rejection.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from communication.tool_registry import default_tool_registry
from agent.schemas import BuildingControlDecision

def test_file_parser_tool():
    """Test file_parser tool with valid project file and invalid out-of-bounds file."""
    idf_path = PROJECT_ROOT / "models" / "modified" / "control_ready.idf"
    res = default_tool_registry.execute_tool("parse_file", file_path=idf_path)
    assert res["status"] == "success", f"File parser failed: {res}"
    assert res["file_type"] == "idf", f"Expected file_type idf, got {res.get('file_type')}"

    # Test path security restriction
    restricted_res = default_tool_registry.execute_tool("parse_file", file_path="C:/Windows/System32/cmd.exe")
    assert restricted_res["status"] == "error", "Security restriction failed to block path outside project"
    print("[PASS] test_file_parser_tool")

def test_error_extractor_tool():
    """Test extract_runtime_errors tool with EnergyPlus eplusout.err file."""
    err_path = PROJECT_ROOT / "outputs" / "ai_controlled" / "eplusout.err"
    if err_path.is_file():
        res = default_tool_registry.execute_tool("extract_runtime_errors", err_file_path=str(err_path))
        assert res["status"] == "success", f"Error extractor failed: {res}"
        assert "warning_count" in res, "warning_count missing"
        assert "fatal_count" in res, "fatal_count missing"
        print(f"[PASS] test_error_extractor_tool ({res['warning_count']} warnings, {res['fatal_count']} fatal errors)")
    else:
        print("[SKIP] test_error_extractor_tool (eplusout.err not yet present)")

def test_control_tool_safety_rejection():
    """Test control_tool rejects unsafe setpoints and accepts valid setpoint actions."""
    from energyplus.control import EnergyPlusControlManager

    ctrl_mgr = EnergyPlusControlManager(run_id="tool_test")
    
    # 1. Unsafe decision: heating >= cooling
    unsafe_decision = BuildingControlDecision(
        action="ADJUST_SETPOINTS",
        zone="CORE_ZN",
        heating_setpoint=25.0,
        cooling_setpoint=24.0,
        reason="Unsafe test"
    )
    success, msg = default_tool_registry.execute_tool(
        "apply_control_action",
        decision=unsafe_decision,
        control_manager=ctrl_mgr,
        api=None,
        state=None,
        simulation_time="Day 21 10:00"
    )
    assert not success, "Control tool failed to reject unsafe setpoints (heating >= cooling)"
    assert "Safety Validation Rejected" in msg, f"Unexpected message: {msg}"

    # 2. Maintain decision
    maintain_decision = BuildingControlDecision(action="MAINTAIN", zone="CORE_ZN")
    m_success, m_msg = default_tool_registry.execute_tool(
        "apply_control_action",
        decision=maintain_decision,
        control_manager=ctrl_mgr,
        api=None,
        state=None,
        simulation_time="Day 21 10:00"
    )
    assert m_success, f"Maintain action failed: {m_msg}"
    print("[PASS] test_control_tool_safety_rejection")

if __name__ == "__main__":
    test_file_parser_tool()
    test_error_extractor_tool()
    test_control_tool_safety_rejection()
    print("\nAll custom agent tool unit tests passed successfully.")
