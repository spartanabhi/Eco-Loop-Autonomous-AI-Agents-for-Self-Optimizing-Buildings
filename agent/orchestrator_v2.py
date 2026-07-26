"""
Agent Orchestrator Module V2 (policy_iter2_candidate).
Orchestrates TelemetrySnapshot processing, dynamic candidate generation with comfort guardrails,
policy-version swappable Qwen LLM reasoning (supporting policy_iter1_frozen and policy_iter2_candidate),
safety validation, tool request generation, and ECM opportunity audit logging.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from energyplus.telemetry import TelemetrySnapshot
from agent.targets import ComfortTarget, PeakDemandTarget, IndoorAirQualityTarget
from agent.carbon import CarbonIntensityTracker
from agent.schemas import BuildingControlDecision, validate_decision_schema
from agent.prompts import SYSTEM_PROMPT as SYSTEM_PROMPT_V1, format_user_prompt as format_user_prompt_v1
from agent.prompts_v2 import SYSTEM_PROMPT_V2, format_user_prompt_v2
from agent.llm_client import LocalQwenLLMClient
from energyplus.control import ControlAction, ControlSafetyValidator

class AgentOrchestratorV2:
    """
    Cognitive Agent Orchestrator V2 supporting both policy_iter1_frozen and policy_iter2_candidate.
    Preserves 100% of deterministic safety validation.
    Candidate Generation: Aligns occupied comfort bounds with ASHRAE 55 (-0.5 <= PMV <= +0.5).
    Adds ECM opportunity audit tracking (ecm_available, ecm_selected, maintain_with_ecm_available).
    """

    MAX_SETPOINT_CHANGE_PER_DECISION = 1.5   # °C maximum change per decision
    COOLDOWN_INTERVALS = 2                   # Minimum intervals before reversing adjustment direction
    
    # Absolute Thermostat Safety Boundaries (100% Preserved)
    MAX_COOLING_CEILING = 28.0               # °C maximum cooling setpoint ceiling
    MIN_COOLING_FLOOR = 23.0                 # °C minimum cooling setpoint floor
    MAX_HEATING_CEILING = 22.0               # °C maximum heating setpoint ceiling
    MIN_HEATING_FLOOR = 18.0                 # °C minimum heating setpoint floor

    def __init__(
        self,
        llm_client: Optional[LocalQwenLLMClient] = None,
        policy_version: str = "policy_iter2_candidate"
    ):
        self.llm_client = llm_client or LocalQwenLLMClient()
        self.policy_version = policy_version
        self.comfort_target = ComfortTarget()
        self.peak_target = PeakDemandTarget()
        self.iaq_target = IndoorAirQualityTarget()
        self.decision_log_path = Path("outputs/evaluation/ai_controlled/agent_decisions.jsonl")
        
        # State tracking for anti-oscillation
        self.last_adjustment_direction: Dict[str, str] = {}
        self.intervals_since_adjustment: Dict[str, int] = {}

    def evaluate_telemetry_state(
        self,
        snapshot: TelemetrySnapshot,
        zone: str = "CORE_ZN",
        current_htg_sp: float = 21.0,
        current_clg_sp: float = 24.0
    ) -> Dict[str, Any]:
        """Processes raw TelemetrySnapshot into evaluated target facts."""
        temp = snapshot.zone_temperatures.get(zone, 21.0)
        co2 = snapshot.zone_co2.get(zone, 400.0)
        pmv = snapshot.zone_pmv.get(zone, 0.0)
        occ = snapshot.zone_occupancy.get(zone, 0.0)
        is_occupied = (occ > 0.1) or (8 <= snapshot.hour <= 17)

        demand_kw = snapshot.facility_demand_kw

        comfort_status = self.comfort_target.evaluate_pmv(pmv)
        co2_status = self.iaq_target.evaluate_co2(co2)
        peak_status = self.peak_target.evaluate_demand(demand_kw)
        carbon_state = CarbonIntensityTracker.get_carbon_intensity(snapshot.hour)

        return {
            "simulation_time": snapshot.simulation_time,
            "zone": zone,
            "temperature": temp,
            "pmv": pmv,
            "hvac_mode": snapshot.hvac_mode,
            "occupancy_count": occ,
            "occupancy_source": snapshot.occupancy_source,
            "is_occupied": is_occupied,
            "occupancy_status": "OCCUPIED" if is_occupied else "UNOCCUPIED",
            "comfort_status": comfort_status,
            "co2_ppm": co2,
            "co2_status": co2_status,
            "demand_kw": demand_kw,
            "peak_status": peak_status,
            "carbon_status": carbon_state.status,
            "carbon_intensity_g_co2_kwh": carbon_state.intensity_g_co2_kwh,
            "current_heating_sp": current_htg_sp,
            "current_cooling_sp": current_clg_sp
        }

    def generate_allowed_candidates(self, eval_state: Dict[str, Any]) -> List[str]:
        """
        Dynamically generates safe, thermodynamically valid candidate actions for current state.
        Enforces ASHRAE 55 comfort guardrails (-0.5 <= PMV <= +0.5).
        """
        pmv = eval_state["pmv"]
        is_occupied = eval_state["is_occupied"]
        hvac_mode = eval_state["hvac_mode"]
        htg_sp = eval_state["current_heating_sp"]
        clg_sp = eval_state["current_cooling_sp"]

        candidates = ["MAINTAIN"]

        if is_occupied:
            # Occupied Comfort Guardrails (ASHRAE 55 Standards)
            if pmv < -0.5:
                if htg_sp + 0.5 <= self.MAX_HEATING_CEILING:
                    candidates.append("RESTORE_HEATING_0_5C")
            elif pmv > +0.5:
                if clg_sp - 0.5 >= self.MIN_COOLING_FLOOR:
                    candidates.append("RESTORE_COOLING_0_5C")
            elif -0.5 <= pmv <= +0.5:
                # Inside ASHRAE 55 Comfort Zone: Energy Optimization ECM candidate available
                if hvac_mode == "HEATING" and htg_sp - 0.5 >= self.MIN_HEATING_FLOOR:
                    candidates.append("RELAX_HEATING_0_5C")
                elif hvac_mode == "COOLING" and clg_sp + 0.5 <= self.MAX_COOLING_CEILING:
                    candidates.append("RELAX_COOLING_0_5C")
        else:
            # Unoccupied Setback Policy
            if hvac_mode == "HEATING" or htg_sp > self.MIN_HEATING_FLOOR:
                if htg_sp - 0.5 >= self.MIN_HEATING_FLOOR:
                    candidates.append("RELAX_HEATING_0_5C")
            if hvac_mode == "COOLING" or clg_sp < self.MAX_COOLING_CEILING:
                if clg_sp + 0.5 <= self.MAX_COOLING_CEILING:
                    candidates.append("RELAX_COOLING_0_5C")

        return candidates

    def translate_candidate_action(
        self,
        candidate_action: str,
        current_htg_sp: float,
        current_clg_sp: float
    ) -> Tuple[str, Optional[float], Optional[float]]:
        """Translates discrete candidate action into exact target setpoints."""
        act = candidate_action.upper().strip()

        if act in ["MAINTAIN", "RELEASE_TO_NATIVE"]:
            return act, None, None
        elif act == "RELAX_HEATING_0_5C":
            new_htg = max(round(current_htg_sp - 0.5, 1), self.MIN_HEATING_FLOOR)
            if new_htg == current_htg_sp:
                return "MAINTAIN", None, None
            return "ADJUST_SETPOINTS", new_htg, current_clg_sp
        elif act == "RESTORE_HEATING_0_5C":
            new_htg = min(round(current_htg_sp + 0.5, 1), self.MAX_HEATING_CEILING)
            if new_htg == current_htg_sp:
                return "MAINTAIN", None, None
            return "ADJUST_SETPOINTS", new_htg, current_clg_sp
        elif act == "RELAX_COOLING_0_5C":
            new_clg = min(round(current_clg_sp + 0.5, 1), self.MAX_COOLING_CEILING)
            if new_clg == current_clg_sp:
                return "MAINTAIN", None, None
            return "ADJUST_SETPOINTS", current_htg_sp, new_clg
        elif act == "RESTORE_COOLING_0_5C":
            new_clg = max(round(current_clg_sp - 0.5, 1), self.MIN_COOLING_FLOOR)
            if new_clg == current_clg_sp:
                return "MAINTAIN", None, None
            return "ADJUST_SETPOINTS", current_htg_sp, new_clg
        else:
            return act, current_htg_sp, current_clg_sp

    def apply_rate_limit_and_cooldown(
        self,
        zone: str,
        current_clg_sp: float,
        proposed_clg_sp: float,
        current_htg_sp: float,
        proposed_htg_sp: float
    ) -> Tuple[float, float, str]:
        """Enforces rate-of-change and anti-oscillation constraints."""
        clg_diff = proposed_clg_sp - current_clg_sp
        htg_diff = proposed_htg_sp - current_htg_sp

        last_dir = self.last_adjustment_direction.get(zone)
        since = self.intervals_since_adjustment.get(zone, 99)

        proposed_dir = "UP" if (clg_diff > 0.05 or htg_diff > 0.05) else ("DOWN" if (clg_diff < -0.05 or htg_diff < -0.05) else "NONE")

        if last_dir and proposed_dir != "NONE" and proposed_dir != last_dir:
            if since < self.COOLDOWN_INTERVALS:
                return current_htg_sp, current_clg_sp, f"Anti-oscillation cooldown active ({since}/{self.COOLDOWN_INTERVALS} intervals)."

        clamped_clg_diff = max(min(clg_diff, self.MAX_SETPOINT_CHANGE_PER_DECISION), -self.MAX_SETPOINT_CHANGE_PER_DECISION)
        clamped_htg_diff = max(min(htg_diff, self.MAX_SETPOINT_CHANGE_PER_DECISION), -self.MAX_SETPOINT_CHANGE_PER_DECISION)

        clamped_clg_sp = round(current_clg_sp + clamped_clg_diff, 1)
        clamped_htg_sp = round(current_htg_sp + clamped_htg_diff, 1)

        if proposed_dir != "NONE":
            self.last_adjustment_direction[zone] = proposed_dir
            self.intervals_since_adjustment[zone] = 0
        else:
            self.intervals_since_adjustment[zone] = since + 1

        return clamped_htg_sp, clamped_clg_sp, "Rate limited"

    def process_snapshot(
        self,
        snapshot: TelemetrySnapshot,
        zone: str = "CORE_ZN",
        current_htg_sp: float = 21.0,
        current_clg_sp: float = 24.0,
        run_id: str = ""
    ) -> Dict[str, Any]:
        """
        Executes cognitive workflow with policy selection and ECM opportunity audit logging.
        """
        eval_state = self.evaluate_telemetry_state(snapshot, zone, current_htg_sp, current_clg_sp)
        allowed_candidates = self.generate_allowed_candidates(eval_state)

        ecm_candidates = [c for c in allowed_candidates if c != "MAINTAIN"]
        ecm_available = len(ecm_candidates) > 0

        # Select prompt based on policy_version
        if self.policy_version == "policy_iter2_candidate":
            sys_prompt = SYSTEM_PROMPT_V2
            user_prompt = format_user_prompt_v2(
                simulation_time=eval_state["simulation_time"],
                zone=eval_state["zone"],
                temperature=eval_state["temperature"],
                pmv=eval_state["pmv"],
                hvac_mode=eval_state["hvac_mode"],
                comfort_status=eval_state["comfort_status"],
                occupancy_status=eval_state["occupancy_status"],
                co2_ppm=eval_state["co2_ppm"],
                co2_status=eval_state["co2_status"],
                demand_kw=eval_state["demand_kw"],
                peak_status=eval_state["peak_status"],
                carbon_status=eval_state["carbon_status"],
                current_heating_sp=eval_state["current_heating_sp"],
                current_cooling_sp=eval_state["current_cooling_sp"],
                allowed_candidates=allowed_candidates
            )
        else:
            sys_prompt = SYSTEM_PROMPT_V1
            user_prompt = format_user_prompt_v1(
                simulation_time=eval_state["simulation_time"],
                zone=eval_state["zone"],
                temperature=eval_state["temperature"],
                pmv=eval_state["pmv"],
                hvac_mode=eval_state["hvac_mode"],
                comfort_status=eval_state["comfort_status"],
                occupancy_status=eval_state["occupancy_status"],
                co2_ppm=eval_state["co2_ppm"],
                co2_status=eval_state["co2_status"],
                demand_kw=eval_state["demand_kw"],
                peak_status=eval_state["peak_status"],
                carbon_status=eval_state["carbon_status"],
                current_heating_sp=eval_state["current_heating_sp"],
                current_cooling_sp=eval_state["current_cooling_sp"],
                allowed_candidates=allowed_candidates
            )

        attempts = 0
        max_attempts = 2
        last_error = ""
        decision_dict: Dict[str, Any] = {}
        total_latency = 0.0
        schema_passed = False
        safety_passed = False

        while attempts < max_attempts:
            attempts += 1
            prompt_to_send = user_prompt if attempts == 1 else f"{user_prompt}\n\nPrevious attempt failed: {last_error}. Select ONE action from {allowed_candidates}."

            success, raw_dict, latency, err_msg = self.llm_client.generate_decision(
                system_prompt=sys_prompt,
                user_prompt=prompt_to_send
            )
            total_latency += latency

            if not success:
                last_error = err_msg
                continue

            s_valid, s_msg = validate_decision_schema(raw_dict)
            if not s_valid:
                last_error = f"Schema error: {s_msg}"
                continue

            raw_candidate_action = str(raw_dict.get("action", "MAINTAIN")).upper().strip()
            
            if raw_candidate_action not in allowed_candidates:
                raw_candidate_action = "MAINTAIN"

            act_type, target_htg, target_clg = self.translate_candidate_action(
                raw_candidate_action, current_htg_sp, current_clg_sp
            )

            raw_dict["action"] = act_type
            raw_dict["heating_setpoint"] = target_htg
            raw_dict["cooling_setpoint"] = target_clg
            schema_passed = True

            decision = BuildingControlDecision.from_dict(raw_dict)

            if decision.action == "ADJUST_SETPOINTS" and target_htg is not None and target_clg is not None:
                c_htg, c_clg, rate_msg = self.apply_rate_limit_and_cooldown(
                    zone=decision.zone,
                    current_clg_sp=current_clg_sp,
                    proposed_clg_sp=target_clg,
                    current_htg_sp=current_htg_sp,
                    proposed_htg_sp=target_htg
                )

                decision.heating_setpoint = c_htg
                decision.cooling_setpoint = c_clg

                control_act = ControlAction(
                    zone=decision.zone,
                    heating_setpoint=decision.heating_setpoint,
                    cooling_setpoint=decision.cooling_setpoint,
                    reason=decision.reason,
                    source="local_qwen_agent"
                )
                safe, safe_msg = ControlSafetyValidator.validate(control_act)
                if not safe:
                    last_error = f"Safety error: {safe_msg}"
                    continue

            safety_passed = True
            decision_dict = decision.to_dict()
            break

        if not schema_passed or not safety_passed:
            decision = BuildingControlDecision(
                action="MAINTAIN",
                zone=zone,
                heating_setpoint=None,
                cooling_setpoint=None,
                reason=f"Fallback triggered: {last_error or 'Unknown error'}",
                confidence=0.0
            )
            decision_dict = decision.to_dict()

        final_decision = BuildingControlDecision.from_dict(decision_dict)
        selected_candidate = raw_dict.get("action", "MAINTAIN") if schema_passed else "MAINTAIN"

        ecm_selected = selected_candidate != "MAINTAIN"
        maintain_with_ecm_available = ecm_available and (selected_candidate == "MAINTAIN")

        if maintain_with_ecm_available:
            maintain_reason_cat = "COMFORT_MARGIN_OR_POLICY_CHOICE"
        elif not ecm_available:
            maintain_reason_cat = "NO_ECM_AVAILABLE"
        else:
            maintain_reason_cat = "OPTIMIZATION_ACCEPTED"

        log_record = {
            "run_id": run_id,
            "policy_version": self.policy_version,
            "timestamp": time.time(),
            "simulation_time": eval_state["simulation_time"],
            "zone": zone,
            "eval_state": eval_state,
            "allowed_candidates": allowed_candidates,
            "ecm_available": ecm_available,
            "ecm_selected": ecm_selected,
            "maintain_with_ecm_available": maintain_with_ecm_available,
            "maintain_reason_category": maintain_reason_cat,
            "attempts": attempts,
            "total_latency_seconds": total_latency,
            "schema_passed": schema_passed,
            "safety_passed": safety_passed,
            "explanation_consistent": final_decision.explanation_consistent,
            "decision": final_decision.to_dict(),
            "proposed_tool": "apply_control_action" if final_decision.action in ["ADJUST_SETPOINTS", "RELEASE_TO_NATIVE"] else "no_action"
        }
        self._log_decision(log_record)

        return {
            "status": "success",
            "evaluated_state": eval_state,
            "allowed_candidates": allowed_candidates,
            "ecm_available": ecm_available,
            "ecm_selected": ecm_selected,
            "maintain_with_ecm_available": maintain_with_ecm_available,
            "maintain_reason_category": maintain_reason_cat,
            "attempts": attempts,
            "total_latency_seconds": total_latency,
            "schema_passed": schema_passed,
            "safety_passed": safety_passed,
            "explanation_consistent": final_decision.explanation_consistent,
            "decision": final_decision.to_dict(),
            "proposed_tool": "apply_control_action" if final_decision.action in ["ADJUST_SETPOINTS", "RELEASE_TO_NATIVE"] else "no_action"
        }

    def _log_decision(self, record: Dict[str, Any]) -> None:
        """Appends structured decision record to JSONL file."""
        self.decision_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.decision_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
