"""Persistent, tamper-evident audit log tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

from flask import Flask, jsonify

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import auth


class PersistentAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "audit.jsonl"
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            ONTOLOGY_AUDIT_LOG_PATH=str(self.path),
            ONTOLOGY_AUDIT_RETENTION_DAYS="0",
            ONTOLOGY_LOCAL_DOCKER="0",
        )
        self.app.before_request(auth.authorize_request)

        @self.app.route("/change", methods=["POST"])
        def change():
            return jsonify({"ok": True})

        @self.app.route("/audit", methods=["GET"])
        def audit():
            return jsonify({"records": auth.get_audit_logs(10), "integrity": auth.verify_audit_integrity()})

        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def test_mutations_persist_without_request_payload_or_ip(self):
        response = self.client.post("/change?private-query=must-not-be-recorded", json={"patient": "secret"})
        self.assertEqual(response.status_code, 200)
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn("private-query", raw)
        self.assertNotIn("secret", raw)
        record = json.loads(raw.splitlines()[0])
        self.assertNotIn("ip", record)
        self.assertEqual(record["action"], "/change")

    def test_api_reads_persistent_records_and_reports_valid_chain(self):
        self.client.post("/change")
        response = self.client.get("/audit")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["integrity"]["valid"])
        self.assertEqual(len(response.json["records"]), 1)
        self.assertEqual(response.json["records"][0]["method"], "POST")

    def test_tampering_is_detected_and_blocks_future_appends(self):
        self.client.post("/change")
        record = json.loads(self.path.read_text(encoding="utf-8"))
        record["action"] = "/tampered"
        self.path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        with self.app.app_context():
            self.assertFalse(auth.verify_audit_integrity()["valid"])
            with self.assertRaises(OSError):
                auth.log_audit_action("/change-again", "local_owner", "admin", "POST")


if __name__ == "__main__":
    unittest.main()
