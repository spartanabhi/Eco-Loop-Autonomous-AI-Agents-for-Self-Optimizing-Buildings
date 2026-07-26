"""
Autonomous Closed-Loop Controller Module.
Coordinates live PyEnergyPlus observation and control callbacks, Qwen LLM reasoning intervals,
validation, pending action queueing, tool execution, and snapshot manifest generation.
NO HUMAN INTERVENTION.
Date-Agnostic Decision Scheduler.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from energyplus.telemetry import TelemetryManager, TelemetrySnapshot
from energyplus.control import ControlAction, EnergyPlusControlManager
from agent.orchestrator import AgentOrchestrator
from communication.tool_registry import default_tool_registry

class AutonomousBuildingController:
    """
    Autonomous closed-loop controller managing the end-to-end Sense -> Think -> Act -> Repeat loop
    within a SINGLE active EnergyPlus process.
    Date-Agnostic Scheduler: Triggers decisions every N simulation steps during 08:00-18:00 operating window.
    """

    def __init__(
        self,
        run_id: str,
        target_zone: str = "CORE_ZN",
        decision_interval_steps: int = 4,  # Every 4 zone timesteps (60 simulated minutes)
        max_decisions: Optional[int] = None
    ):
        self.run_id = run_id
        self.target_zone = target_zone
        self.decision_interval_steps = decision_interval_steps
        self.max_decisions = max_decisions

        self.telemetry_mgr = TelemetryManager(run_id=run_id)
        self.control_mgr = EnergyPlusControlManager(run_id=run_id)
        self.orchestrator = AgentOrchestrator()

        self.step_counter: int = 0
        self.decision_counter: int = 0
        self.pending_decision: Optional[Dict[str, Any]] = None
        self.active_setpoints: Dict[str, Tuple[float, float]] = {
            target_zone: (21.0, 24.0)
        }

        # Feedback Chain Metrics
        self.count_maintain: int = 0
        self.count_non_maintain: int = 0
        self.count_rejected: int = 0
        self.count_applied: int = 0
        self.count_post_action_snapshots: int = 0
        self.count_subsequent_decisions_after_action: int = 0
        self.last_actuator_action_step: int = -1

        self.decision_history: List[Dict[str, Any]] = []

    def observation_callback(self, api: Any, state: Any) -> None:
        """
        Observation Callback: Fires at end_zone_timestep_after_zone_reporting.
        Captures live telemetry, evaluates targets, and invokes Qwen LLM at decision intervals.
        Date-agnostic decision trigger during daytime operating hours (08:00 to 18:00).
        """
        if not api.exchange.api_data_fully_ready(state):
            return

        # Skip warm-up iterations
        if api.exchange.warmup_flag(state):
            return

        snapshot = self.telemetry_mgr.capture_snapshot(api, state)
        if snapshot is None:
            return

        self.step_counter += 1

        if self.last_actuator_action_step > 0 and self.step_counter > self.last_actuator_action_step:
            self.count_post_action_snapshots += 1

        # Date-Agnostic Decision Trigger: Triggers during operating window (08:00 to 18:00) every decision_interval_steps
        if 8 <= snapshot.hour <= 18 and self.step_counter % self.decision_interval_steps == 0:
            if self.max_decisions is not None and self.decision_counter >= self.max_decisions:
                return

            self.decision_counter += 1
            if self.last_actuator_action_step > 0:
                self.count_subsequent_decisions_after_action += 1

            cur_htg, cur_clg = self.control_mgr.get_current_setpoints(api, state, self.target_zone)
            if cur_htg == 0.0 or cur_clg == 0.0:
                cur_htg, cur_clg = self.active_setpoints.get(self.target_zone, (21.0, 24.0))

            print(f"\n[{snapshot.simulation_time}] OBSERVE ({self.target_zone})")
            print(f"   Temp: {snapshot.zone_temperatures.get(self.target_zone, 0.0):.2f}°C | PMV: {snapshot.zone_pmv.get(self.target_zone, 0.0):+.2f} | CO2: {snapshot.zone_co2.get(self.target_zone, 0.0):.0f} ppm | Demand: {snapshot.facility_demand_kw:.2f} kW | Occupancy: {snapshot.zone_occupancy.get(self.target_zone, 0.0):.0f} ({snapshot.occupancy_source})")

            # Think: Invoke local Qwen agent via orchestrator
            print(f"[{snapshot.simulation_time}] THINK (Invoking Qwen2.5-0.5B-Instruct-Q3_K_S.gguf)...")
            res = self.orchestrator.process_snapshot(
                snapshot=snapshot,
                zone=self.target_zone,
                current_htg_sp=cur_htg,
                current_clg_sp=cur_clg,
                run_id=self.run_id
            )

            dec = res["decision"]
            tool_name = res["proposed_tool"]
            print(f"   Qwen Decision: Action={dec['action']} | Heating={dec['heating_setpoint']}°C | Cooling={dec['cooling_setpoint']}°C | Latency={res['total_latency_seconds']:.2f}s")
            print(f"   Reason: \"{dec['reason']}\"")

            if not res["schema_passed"] or not res["safety_passed"]:
                self.count_rejected += 1

            if dec["action"] in ["ADJUST_SETPOINTS", "RELEASE_TO_NATIVE"]:
                self.count_non_maintain += 1
                self.pending_decision = {
                    "decision": dec,
                    "snapshot": snapshot,
                    "sim_time": snapshot.simulation_time
                }
            else:
                self.count_maintain += 1

            self.decision_history.append(res)

    def control_callback(self, api: Any, state: Any) -> None:
        """
        Control Callback: Fires at begin_zone_timestep_before_init_heat_balance.
        Reasserts active overrides and executes queued pending decisions before heat balance.
        """
        if not api.exchange.api_data_fully_ready(state):
            return

        if api.exchange.warmup_flag(state):
            return

        # 1. Reassert existing active overrides
        self.control_mgr.reassert_active_overrides(api, state)

        # 2. Execute pending decision if queued
        if self.pending_decision is not None:
            dec_data = self.pending_decision
            self.pending_decision = None

            dec = dec_data["decision"]
            sim_time = dec_data["sim_time"]

            print(f"\n[{sim_time}] ACT (Executing Control Action Tool)")
            from agent.schemas import BuildingControlDecision
            b_decision = BuildingControlDecision.from_dict(dec)

            success, msg = default_tool_registry.execute_tool(
                "apply_control_action",
                decision=b_decision,
                control_manager=self.control_mgr,
                api=api,
                state=state,
                simulation_time=sim_time
            )

            print(f"   Tool Execution Result: {msg}")
            if success:
                self.count_applied += 1
                self.last_actuator_action_step = self.step_counter
                if b_decision.action == "ADJUST_SETPOINTS":
                    self.active_setpoints[self.target_zone] = (b_decision.heating_setpoint, b_decision.cooling_setpoint)
                elif b_decision.action == "RELEASE_TO_NATIVE":
                    if self.target_zone in self.active_setpoints:
                        del self.active_setpoints[self.target_zone]
                self.save_snapshot_manifest(sim_time, b_decision)

    def save_snapshot_manifest(self, sim_time: str, decision: Any) -> None:
        """Saves an auditable snapshot manifest under models/modified/snapshots/."""
        snap_dir = Path("models/modified/snapshots")
        snap_dir.mkdir(parents=True, exist_ok=True)
        filename = f"snapshot_{self.run_id}_{int(time.time())}.json"
        filepath = snap_dir / filename

        manifest = {
            "run_id": self.run_id,
            "simulation_time": sim_time,
            "source_model": "models/modified/control_ready.idf",
            "active_override_zone": decision.zone,
            "applied_heating_setpoint": decision.heating_setpoint,
            "applied_cooling_setpoint": decision.cooling_setpoint,
            "agent_reason": decision.reason,
            "timestamp": time.time()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def save_all_logs(self, output_dir: Path) -> None:
        """Saves telemetry CSV, control actions CSV, and agent decision logs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_mgr.save_telemetry_csv(str(output_dir / "live_telemetry.csv"))
        self.control_mgr.save_control_history_csv(str(output_dir / "control_actions.csv"))
