"""
Fast Backend Test Suite using FastAPI TestClient.
Executes in under 2 seconds without launching EnergyPlus or Qwen inference.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.main import app

class TestBackendQuick(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["controller"], "policy_iter2_candidate")

    def test_status_endpoint(self):
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("simulation_status", data)

    def test_telemetry_latest_endpoint(self):
        res = self.client.get("/api/telemetry/latest")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("data_source"), "validated_policy_iter2_artifact")

    def test_agent_latest_endpoint(self):
        res = self.client.get("/api/agent/latest")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("selected_action", data)

    def test_evaluation_endpoint(self):
        res = self.client.get("/api/evaluation")
        self.assertEqual(res.status_code, 200)

    def test_evaluation_hero_endpoint(self):
        res = self.client.get("/api/evaluation/hero")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertAlmostEqual(data["electricity_reduction_percent"], 3.51, places=1)
        self.assertEqual(data["baseline_electricity_kwh"], 747.11)
        self.assertEqual(data["ecoloop_electricity_kwh"], 720.89)

if __name__ == "__main__":
    unittest.main()
