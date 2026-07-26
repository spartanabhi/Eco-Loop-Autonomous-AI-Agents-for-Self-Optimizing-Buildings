"""
EnergyPlus Simulation Runner.
Provides API interface for initializing EnergyPlus API, running simulations,
and parsing execution results and error logs.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Any, Dict

from energyplus.environment import setup_energyplus_path, find_energyplus

class EnergyPlusRunnerFoundation:
    """EnergyPlus API runner foundation and execution manager."""

    def __init__(self):
        self.ep_info = find_energyplus()
        self.api: Optional[Any] = None
        self.state: Optional[Any] = None
        self.is_initialized: bool = False

    def initialize_api(self) -> bool:
        """
        Verify PyEnergyPlus availability and instantiate the EnergyPlusAPI object.
        Returns True if initialization succeeds.
        """
        success, msg = setup_energyplus_path()
        if not success:
            self.is_initialized = False
            return False

        try:
            from pyenergyplus.api import EnergyPlusAPI
            self.api = EnergyPlusAPI()
            self.is_initialized = True
            return True
        except Exception as e:
            self.is_initialized = False
            return False

    def create_state(self) -> Optional[Any]:
        """Create and return a new simulation state if API is initialized."""
        if not self.is_initialized or not self.api:
            return None
        
        try:
            self.state = self.api.state_manager.new_state()
            return self.state
        except Exception:
            return None

    def run_simulation(self, idf_path: str, epw_path: str, output_dir: str) -> int:
        """
        Runs an EnergyPlus simulation using the PyEnergyPlus runtime API.
        Returns exit code (0 = success).
        """
        if not self.is_initialized:
            if not self.initialize_api():
                raise RuntimeError("Failed to initialize EnergyPlus API.")

        abs_idf = str(Path(idf_path).resolve())
        abs_epw = str(Path(epw_path).resolve())
        abs_output = str(Path(output_dir).resolve())

        os.makedirs(abs_output, exist_ok=True)

        state = self.create_state()
        if state is None:
            raise RuntimeError("Failed to create EnergyPlus simulation state.")

        cmd_args = [
            "-d", abs_output,
            "-w", abs_epw,
            abs_idf
        ]

        try:
            # Disable noisy console output from C++ backend
            self.api.runtime.set_console_output_status(state, False)
            exit_code = self.api.runtime.run_energyplus(state, cmd_args)
            return exit_code
        finally:
            self.cleanup()

    def parse_error_log(self, output_dir: str) -> Dict[str, Any]:
        """
        Parses eplusout.err log file from output directory.
        Returns dict containing warning count, severe error count, fatal error count,
        and summary text.
        """
        err_file = Path(output_dir) / "eplusout.err"
        result = {
            "warnings": 0,
            "severe": 0,
            "fatal": 0,
            "summary": "Log file not found",
            "lines": []
        }

        if not err_file.is_file():
            return result

        with open(err_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        result["lines"] = lines

        for line in lines:
            line_str = line.strip()
            if "EnergyPlus Completed Successfully" in line_str or "EnergyPlus Terminated" in line_str or "Fatal" in line_str or "Warning" in line_str:
                result["summary"] = line_str

            # Parse standard EnergyPlus summary line e.g. "EnergyPlus Completed Successfully-- 2 Warning; 0 Severe Errors"
            if "Warning" in line_str and "Severe Error" in line_str:
                try:
                    parts = line_str.split(";")
                    for p in parts:
                        if "Warning" in p:
                            result["warnings"] = int(p.split()[0].replace("*", "").strip())
                        elif "Severe Error" in p:
                            result["severe"] = int(p.split()[0].replace("*", "").strip())
                except Exception:
                    pass

            if "** Fatal **" in line_str:
                result["fatal"] += 1

        return result

    def cleanup(self) -> None:
        """Clean up simulation state."""
        if self.api and self.state:
            try:
                self.api.state_manager.delete_state(self.state)
            except Exception:
                pass
            self.state = None
