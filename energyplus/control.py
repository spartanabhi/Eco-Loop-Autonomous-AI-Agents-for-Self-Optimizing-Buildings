"""
EnergyPlus Closed-Loop Control Module.
Defines ControlAction structures, deterministic safety validation, actuator handles,
actuator value setting via PyEnergyPlus Exchange API, and override reset capabilities.
"""

import math
import csv
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

@dataclass
class ControlAction:
    """Dataclass representing a closed-loop thermostat setpoint override decision."""
    zone: str
    heating_setpoint: float
    cooling_setpoint: float
    reason: str
    source: str = "deterministic_test"
    timestamp: str = ""

@dataclass
class ControlEventRecord:
    """Record of an attempted control action, validation, and actuator write result."""
    simulation_time: str
    zone: str
    previous_heating_setpoint: float
    previous_cooling_setpoint: float
    requested_heating_setpoint: float
    requested_cooling_setpoint: float
    applied_heating_setpoint: float
    applied_cooling_setpoint: float
    validation_passed: bool
    validation_message: str
    actuator_write_success: bool
    reason: str
    source: str
    run_id: str

class ControlSafetyValidator:
    """
    Deterministic safety validator enforcing physical operational boundaries
    and minimum heating/cooling deadbands before actuator writes.
    """
    MIN_HEATING_SETPOINT = 12.0   # °C
    MAX_HEATING_SETPOINT = 26.0   # °C
    MIN_COOLING_SETPOINT = 18.0   # °C
    MAX_COOLING_SETPOINT = 32.0   # °C
    MIN_DEADBAND = 1.0            # °C

    @classmethod
    def validate(cls, action: ControlAction) -> Tuple[bool, str]:
        """
        Validates proposed heating and cooling setpoints.
        Returns (True, "Valid") if action passes all safety constraints.
        """
        htg = action.heating_setpoint
        clg = action.cooling_setpoint

        # 1. Non-numeric or NaN check
        if not isinstance(htg, (int, float)) or not isinstance(clg, (int, float)):
            return False, "Setpoints must be numeric floats/integers."
        
        if math.isnan(htg) or math.isnan(clg) or math.isinf(htg) or math.isinf(clg):
            return False, "Setpoints contain NaN or infinite values."

        # 2. Individual Boundary Checks
        if htg < cls.MIN_HEATING_SETPOINT or htg > cls.MAX_HEATING_SETPOINT:
            return False, f"Heating setpoint {htg:.1f}°C out of bounds [{cls.MIN_HEATING_SETPOINT}, {cls.MAX_HEATING_SETPOINT}]."
        
        if clg < cls.MIN_COOLING_SETPOINT or clg > cls.MAX_COOLING_SETPOINT:
            return False, f"Cooling setpoint {clg:.1f}°C out of bounds [{cls.MIN_COOLING_SETPOINT}, {cls.MAX_COOLING_SETPOINT}]."

        # 3. Heating vs Cooling Deadband Constraint
        if htg >= clg:
            return False, f"Heating setpoint ({htg:.1f}°C) must be strictly less than cooling setpoint ({clg:.1f}°C)."

        if (clg - htg) < cls.MIN_DEADBAND:
            return False, f"Deadband ({clg - htg:.1f}°C) is less than required minimum ({cls.MIN_DEADBAND}°C)."

        return True, "Valid"

class EnergyPlusControlManager:
    """
    Manages PyEnergyPlus actuator handles, safety validation,
    forward injection of setpoint overrides, and override releases.
    """

    ZONES = ["CORE_ZN", "PERIMETER_ZN_1", "PERIMETER_ZN_2", "PERIMETER_ZN_3", "PERIMETER_ZN_4"]

    def __init__(self, run_id: str = "default_run"):
        self.run_id = run_id
        self.handles_initialized: bool = False
        
        # Per-Zone Actuator Handles (Zone Temperature Control)
        self.actuator_htg_handles: Dict[str, int] = {}
        self.actuator_clg_handles: Dict[str, int] = {}
        
        # Schedule Actuator Handles (Fallback / Schedule:Compact)
        self.schedule_htg_handle: int = -1
        self.schedule_clg_handle: int = -1

        # Thermostat Setpoint Reporting Variable Handles
        self.var_htg_sp_handles: Dict[str, int] = {}
        self.var_clg_sp_handles: Dict[str, int] = {}

        # Active Overrides & Event Log
        self.active_overrides: Dict[str, ControlAction] = {}
        self.records: List[ControlEventRecord] = []

    def initialize_handles(self, api: Any, state: Any) -> bool:
        """
        Dynamically resolves PyEnergyPlus actuator handles and setpoint reporting variable handles.
        Never hardcodes handle integers.
        """
        if not api.exchange.api_data_fully_ready(state):
            return False

        all_ok = True

        # 1. Per-Zone Thermostat Control Actuators
        for z in self.ZONES:
            h_htg = api.exchange.get_actuator_handle(state, "Zone Temperature Control", "Heating Setpoint", z)
            h_clg = api.exchange.get_actuator_handle(state, "Zone Temperature Control", "Cooling Setpoint", z)
            
            if h_htg != -1:
                self.actuator_htg_handles[z] = h_htg
            if h_clg != -1:
                self.actuator_clg_handles[z] = h_clg

        # 2. Schedule Actuators (Fallback)
        self.schedule_htg_handle = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "HTGSETP_SCH")
        self.schedule_clg_handle = api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "CLGSETP_SCH")

        # 3. Thermostat Setpoint Reporting Variables
        for z in self.ZONES:
            vh_htg = api.exchange.get_variable_handle(state, "Zone Thermostat Heating Setpoint Temperature", z)
            vh_clg = api.exchange.get_variable_handle(state, "Zone Thermostat Cooling Setpoint Temperature", z)
            if vh_htg != -1:
                self.var_htg_sp_handles[z] = vh_htg
            if vh_clg != -1:
                self.var_clg_sp_handles[z] = vh_clg

        self.handles_initialized = bool(self.actuator_htg_handles or self.schedule_htg_handle != -1)
        return self.handles_initialized

    def get_current_setpoints(self, api: Any, state: Any, zone: str) -> Tuple[float, float]:
        """Returns (heating_setpoint, cooling_setpoint) currently active in EnergyPlus for zone."""
        htg_sp, clg_sp = 0.0, 0.0
        
        vh_htg = self.var_htg_sp_handles.get(zone, -1)
        if vh_htg != -1:
            htg_sp = api.exchange.get_variable_value(state, vh_htg)

        vh_clg = self.var_clg_sp_handles.get(zone, -1)
        if vh_clg != -1:
            clg_sp = api.exchange.get_variable_value(state, vh_clg)

        return htg_sp, clg_sp

    def apply_control_action(self, api: Any, state: Any, action: ControlAction, sim_time: str) -> bool:
        """
        Validates and applies proposed ControlAction to EnergyPlus actuators.
        Reasserts active overrides every control timestep.
        """
        if not self.handles_initialized:
            if not self.initialize_handles(api, state):
                return False

        # Read current thermostat setpoints before override
        prev_htg, prev_clg = self.get_current_setpoints(api, state, action.zone)

        # Validate action
        is_valid, val_msg = ControlSafetyValidator.validate(action)
        
        if not is_valid:
            # Record failed action
            rec = ControlEventRecord(
                simulation_time=sim_time,
                zone=action.zone,
                previous_heating_setpoint=prev_htg,
                previous_cooling_setpoint=prev_clg,
                requested_heating_setpoint=action.heating_setpoint,
                requested_cooling_setpoint=action.cooling_setpoint,
                applied_heating_setpoint=prev_htg,
                applied_cooling_setpoint=prev_clg,
                validation_passed=False,
                validation_message=val_msg,
                actuator_write_success=False,
                reason=action.reason,
                source=action.source,
                run_id=self.run_id
            )
            self.records.append(rec)
            return False

        # Apply setpoints via per-zone actuators
        act_htg_h = self.actuator_htg_handles.get(action.zone, -1)
        act_clg_h = self.actuator_clg_handles.get(action.zone, -1)
        write_success = False

        if act_htg_h != -1 and act_clg_h != -1:
            api.exchange.set_actuator_value(state, act_htg_h, action.heating_setpoint)
            api.exchange.set_actuator_value(state, act_clg_h, action.cooling_setpoint)
            write_success = True
        elif self.schedule_htg_handle != -1 and self.schedule_clg_handle != -1:
            api.exchange.set_actuator_value(state, self.schedule_htg_handle, action.heating_setpoint)
            api.exchange.set_actuator_value(state, self.schedule_clg_handle, action.cooling_setpoint)
            write_success = True

        if write_success:
            self.active_overrides[action.zone] = action

        rec = ControlEventRecord(
            simulation_time=sim_time,
            zone=action.zone,
            previous_heating_setpoint=prev_htg,
            previous_cooling_setpoint=prev_clg,
            requested_heating_setpoint=action.heating_setpoint,
            requested_cooling_setpoint=action.cooling_setpoint,
            applied_heating_setpoint=action.heating_setpoint if write_success else prev_htg,
            applied_cooling_setpoint=action.cooling_setpoint if write_success else prev_clg,
            validation_passed=True,
            validation_message="Valid",
            actuator_write_success=write_success,
            reason=action.reason,
            source=action.source,
            run_id=self.run_id
        )
        self.records.append(rec)
        return write_success

    def reassert_active_overrides(self, api: Any, state: Any) -> None:
        """Reasserts all active zone overrides during each control callback timestep."""
        if not self.handles_initialized:
            return

        for zone, action in self.active_overrides.items():
            act_htg_h = self.actuator_htg_handles.get(zone, -1)
            act_clg_h = self.actuator_clg_handles.get(zone, -1)
            if act_htg_h != -1 and act_clg_h != -1:
                api.exchange.set_actuator_value(state, act_htg_h, action.heating_setpoint)
                api.exchange.set_actuator_value(state, act_clg_h, action.cooling_setpoint)

    def reset_zone_override(self, api: Any, state: Any, zone: str) -> bool:
        """
        Releases actuator override for a zone using api.exchange.reset_actuator(...)
        and resumes native EnergyPlus thermostat schedule control.
        """
        if zone in self.active_overrides:
            del self.active_overrides[zone]

        act_htg_h = self.actuator_htg_handles.get(zone, -1)
        act_clg_h = self.actuator_clg_handles.get(zone, -1)
        
        success = False
        if act_htg_h != -1:
            api.exchange.reset_actuator(state, act_htg_h)
            success = True
        if act_clg_h != -1:
            api.exchange.reset_actuator(state, act_clg_h)
            success = True

        if self.schedule_htg_handle != -1:
            api.exchange.reset_actuator(state, self.schedule_htg_handle)
        if self.schedule_clg_handle != -1:
            api.exchange.reset_actuator(state, self.schedule_clg_handle)

        return success

    def save_control_history_csv(self, file_path: str) -> None:
        """Saves control action history log to CSV."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self.records:
            return

        fieldnames = [
            "run_id", "simulation_time", "zone", "source", "reason",
            "previous_heating_setpoint", "previous_cooling_setpoint",
            "requested_heating_setpoint", "requested_cooling_setpoint",
            "applied_heating_setpoint", "applied_cooling_setpoint",
            "validation_passed", "validation_message", "actuator_write_success"
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            for r in self.records:
                writer.writerow([
                    r.run_id, r.simulation_time, r.zone, r.source, r.reason,
                    f"{r.previous_heating_setpoint:.2f}", f"{r.previous_cooling_setpoint:.2f}",
                    f"{r.requested_heating_setpoint:.2f}", f"{r.requested_cooling_setpoint:.2f}",
                    f"{r.applied_heating_setpoint:.2f}", f"{r.applied_cooling_setpoint:.2f}",
                    r.validation_passed, r.validation_message, r.actuator_write_success
                ])
