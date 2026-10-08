"""Legacy LLM entrypoints queue Codex work and never return a canned result."""

import unittest
from unittest.mock import patch

import agent_llm
import codex_jobs
from test_codex_jobs import CodexJobTestCase


class TestAgentLLM(CodexJobTestCase):
    def test_status_facade_reports_codex_without_api_key_requirement(self):
        expected = {"provider": "codex", "requires_api_key": False,
                    "auto_run_available": False, "manual_available": True}
        with patch.object(agent_llm, "check_codex_status", return_value=expected):
            self.assertEqual(agent_llm.check_llm_status(), expected)

    def test_status_api_and_legacy_alias_report_codex_without_cli_calls(self):
        for endpoint in ("/api/v1/codex/status", "/api/v1/llm/status"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["provider"], "codex")
                self.assertFalse(response.get_json()["requires_api_key"])
                self.assertFalse(response.get_json()["auto_run_available"])

    def test_generation_facade_returns_durable_pending_job(self):
        result = agent_llm.generate_agent_execution("mv", "Director", "Opening description",
                                                    "Describe a rainy neon city.", "unused-model-name")
        self.assertEqual(result["provider"], "codex")
        self.assertEqual(result["status"], "awaiting_codex")
        self.assertIsNone(result["result"])
        self.assertNotIn("generated_content", result)
        self.assertEqual(result["request"]["agent_name"], "Director")
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_codex_api_returns_202_and_restores_persisted_job(self):
        response = self.client.post("/api/v1/codex/jobs", json={
            "ont": "mv", "prompt": "Describe a rainy city.", "save_to_graph": False,
        })
        self.assertEqual(response.status_code, 202)
        queued = response.get_json()
        self.assertEqual(queued["status"], "awaiting_codex")
        self.assertIsNone(queued["result"])
        job_id = queued["job_id"]
        restored = self.client.get("/api/v1/codex/jobs/" + job_id)
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.get_json()["status"], "awaiting_codex")
        self.assertEqual(restored.get_json()["request"], queued["request"])
        claimed = codex_jobs.claim_job(job_id)
        running = self.client.get("/api/v1/codex/jobs/" + job_id).get_json()
        self.assertEqual(running["status"], "running")
        self.assertNotIn("claim_token", running)
        completed = self.complete(claimed)
        restored_again = self.client.get("/api/v1/codex/jobs/" + job_id)
        self.assertEqual(restored_again.get_json(), completed)
        listed = self.client.get("/api/v1/codex/jobs?ont=mv")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.get_json()["jobs"][0]["job_id"], job_id)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_legacy_generation_alias_queues_and_respects_save_option(self):
        response = self.client.post("/api/v1/llm/generate", json={
            "ont": "mv", "agent_name": "CodexDirector", "task_name": "Scene prose",
            "prompt": "Describe a nighttime city scene.", "save_to_graph": False,
        })
        self.assertEqual(response.status_code, 202)
        queued = response.get_json()
        self.assertEqual(queued["status"], "awaiting_codex")
        self.assertEqual(queued["provider"], "codex")
        self.assertFalse(queued["request"]["save_to_graph"])
        self.assertIsNone(queued["result"])
        self.assertNotIn("generated_content", queued)
        completed = self.complete(codex_jobs.claim_job(queued["job_id"]))
        self.assertFalse(completed["result"]["persisted"]["saved"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_missing_prompt_and_unknown_domain_are_api_errors(self):
        for endpoint in ("/api/v1/codex/jobs", "/api/v1/llm/generate"):
            for payload in ({"ont": "mv"}, {"ont": "unknown", "prompt": "valid"}):
                with self.subTest(endpoint=endpoint, payload=payload):
                    response = self.client.post(endpoint, json=payload)
                    self.assertEqual(response.status_code, 400)
        self.assertEqual(codex_jobs.list_jobs(), [])

    def test_job_lookup_rejects_traversal_and_missing_ids(self):
        invalid = self.client.get("/api/v1/codex/jobs/not-a-job-id")
        self.assertEqual(invalid.status_code, 400)
        missing = self.client.get("/api/v1/codex/jobs/codex_" + "a" * 32)
        self.assertEqual(missing.status_code, 404)

    def test_run_api_preserves_pending_job_when_cli_unavailable(self):
        queued = self.enqueue(save_to_graph=False)
        response = self.client.post("/api/v1/codex/jobs/" + queued["job_id"] + "/run")
        self.assertEqual(response.status_code, 202)
        self.assertFalse(response.get_json()["started"])
        self.assertEqual(response.get_json()["job"]["status"], "awaiting_codex")
        self.assertIsNone(response.get_json()["job"]["result"])


if __name__ == "__main__":
    unittest.main()
