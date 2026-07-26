"""
Policy Iteration 2 Automated Test Suite.
Verifies policy isolation, prompt construction, trust signal presence, schema validation, and audit log fields.
"""

import sys
import unittest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator import AgentOrchestrator
from agent.orchestrator_v2 import AgentOrchestratorV2
from agent.prompts_v2 import SYSTEM_PROMPT_V2, format_user_prompt_v2
from evaluation.controller_version import calculate_controller_hash

class TestPolicyIter2(unittest.TestCase):

    def test_policy_version_isolation(self):
        """Ensures Policy 1 and Policy 2 remain isolated and distinct."""
        orch_v1 = AgentOrchestrator()
        orch_v2 = AgentOrchestratorV2(policy_version="policy_iter2_candidate")

        self.assertEqual(getattr(orch_v1, "policy_version", "policy_iter1_frozen"), "policy_iter1_frozen")
        self.assertEqual(orch_v2.policy_version, "policy_iter2_candidate")

        # Hashes must be tracked
        hash_v1 = calculate_controller_hash()
        self.assertTrue(len(hash_v1) == 16)

    def test_prompt_v2_trust_signal_and_hierarchy(self):
        """Verifies Prompt V2 includes explicit trust signal and objective hierarchy."""
        self.assertIn("Priority 1 (Safety & IAQ)", SYSTEM_PROMPT_V2)
        self.assertIn("Priority 2 (Thermal Comfort)", SYSTEM_PROMPT_V2)
        self.assertIn("Priority 3 (Energy & Carbon Optimization)", SYSTEM_PROMPT_V2)
        self.assertIn("Every candidate action listed in the prompt has ALREADY passed strict deterministic safety", SYSTEM_PROMPT_V2)

    def test_candidate_generation_ashrae55(self):
        """Verifies candidate generation aligns with ASHRAE 55 (-0.5 <= PMV <= +0.5)."""
        orch = AgentOrchestratorV2(policy_version="policy_iter2_candidate")

        # Summer occupied PMV = -0.40 (COOLING mode) -> should offer RELAX_COOLING_0_5C
        state_cooling = {
            "is_occupied": True,
            "comfort_status": "COMFORTABLE",
            "pmv": -0.40,
            "hvac_mode": "COOLING",
            "co2_ppm": 650,
            "demand_kw": 6.5,
            "carbon_status": "MEDIUM",
            "current_heating_sp": 21.0,
            "current_cooling_sp": 24.0
        }
        candidates = orch.generate_allowed_candidates(state_cooling)
        self.assertIn("RELAX_COOLING_0_5C", candidates)
        self.assertIn("MAINTAIN", candidates)

    def test_decision_log_audit_fields(self):
        """Verifies decision logs contain all required audit fields."""
        log_path = PROJECT_ROOT / "outputs" / "evaluation" / "policy_iter2" / "summer" / "ai_controlled" / "agent_decisions.jsonl"
        self.assertTrue(log_path.is_file())

        with open(log_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            data = json.loads(first_line)

            self.assertIn("ecm_available", data)
            self.assertIn("ecm_selected", data)
            self.assertIn("maintain_with_ecm_available", data)
            self.assertIn("maintain_reason_category", data)
            self.assertEqual(data["policy_version"], "policy_iter2_candidate")

if __name__ == "__main__":
    unittest.main()
