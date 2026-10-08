"""
Unit tests for Multi-Agent Workflow Simulator.
"""

import unittest
from app import app
from simulation import run_pipeline_step, SIMULATION_STEPS


class TestSimulation(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_run_all_six_steps(self):
        sid = "unit_sim_01"
        for s in range(1, len(SIMULATION_STEPS) + 1):
            data = run_pipeline_step(s, session_id=sid)
            self.assertEqual(data["step"], s)
            self.assertEqual(data["total_steps"], 6)
            self.assertGreater(len(data["triples"]), 0)
            self.assertGreater(len(data["new_nodes"]), 0)
            self.assertGreater(len(data["new_edges"]), 0)
            if s == 6:
                self.assertTrue(data["is_completed"])
            else:
                self.assertFalse(data["is_completed"])

    def test_invalid_step(self):
        with self.assertRaises(ValueError):
            run_pipeline_step(99)

    def test_api_simulate_endpoint(self):
        res = self.client.post('/api/v1/simulate', json={"step": 2, "session_id": "test_api_sim"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["step"], 2)
        self.assertIn("PromptAgent", data["agent"])
        self.assertIn("prompt_master.txt", data["output_asset"])


if __name__ == '__main__':
    unittest.main()
