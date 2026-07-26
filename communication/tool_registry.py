"""
Agent Tool Registry Module.
Provides a unified communication bus and registry interface for all custom agentic tools.
"""

from typing import Dict, Any, Callable
from communication.tools.file_parser import parse_project_file
from communication.tools.error_extractor import extract_runtime_errors
from communication.tools.control_tool import execute_control_action

class AgentToolRegistry:
    """Central registry and dispatch bus for custom agentic tools."""

    def __init__(self):
        self._tools: Dict[str, Callable[..., Any]] = {
            "parse_file": parse_project_file,
            "extract_runtime_errors": extract_runtime_errors,
            "apply_control_action": execute_control_action
        }

    def list_tools(self) -> Dict[str, str]:
        """Returns name and documentation of all registered tools."""
        return {
            "parse_file": "Parse EnergyPlus project files (IDF, ERR, CSV) within project bounds.",
            "extract_runtime_errors": "Extract and summarize warnings, severe errors, and fatal errors from eplusout.err.",
            "apply_control_action": "Pass a validated BuildingControlDecision to safety validator and PyEnergyPlus actuators."
        }

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Executes a registered tool by name with keyword arguments."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' is not registered in AgentToolRegistry.")
        return self._tools[tool_name](**kwargs)

# Global registry instance
default_tool_registry = AgentToolRegistry()
