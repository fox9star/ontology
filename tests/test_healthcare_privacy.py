"""Default API redaction and explicit, audited healthcare disclosure tests."""

import json
import unittest

import app as studio
import auth
from unittest.mock import patch


class TestHealthcarePrivacyBoundary(unittest.TestCase):
    def setUp(self):
        self.client = studio.app.test_client()
        self.old_sensitive_setting = studio.app.config.get("ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE", False)
        studio.app.config["ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE"] = False
        auth._AUDIT_LOGS.clear()

    def tearDown(self):
        studio.app.config["ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE"] = self.old_sensitive_setting

    def test_sparql_and_export_redact_unverified_patient_data(self):
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"
        response = self.client.post("/api/sparql", json={"ont": "healthcare", "query": query})
        self.assertEqual(response.status_code, 200)
        result_text = json.dumps(response.get_json())
        for marker in ("PATIENT-9081", "No pulmonary nodules", "Patient_P9081"):
            self.assertNotIn(marker, result_text)

        export = self.client.get("/api/v1/export?ont=healthcare")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.headers.get("X-Privacy-Redaction"), "unverified-and-protected-records")
        for marker in ("PATIENT-9081", "No pulmonary nodules", "Patient_P9081"):
            self.assertNotIn(marker, export.get_data(as_text=True))

    def test_sensitive_read_requires_both_explicit_request_and_server_gate(self):
        denied = self.client.post("/api/sparql", json={
            "ont": "healthcare", "include_sensitive": True,
            "query": "SELECT ?id WHERE { ?s <http://example.org/ontology/healthcare#patientId> ?id }",
        })
        self.assertEqual(denied.status_code, 403)

        studio.app.config["ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE"] = True
        allowed = self.client.post("/api/sparql", json={
            "ont": "healthcare", "include_sensitive": True,
            "query": "SELECT ?id WHERE { ?s <http://example.org/ontology/healthcare#patientId> ?id }",
        })
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("PATIENT-9081", json.dumps(allowed.get_json()))
        self.assertEqual(auth.get_audit_logs(1)[0]["action"], "HEALTHCARE_SENSITIVE_READ")

    def test_graph_views_and_metrics_redact_protected_subjects(self):
        graph = self.client.get("/api/graph-data?ont=healthcare").get_json()
        self.assertNotIn("Patient_P9081", json.dumps(graph))
        explorer = self.client.get("/api/explorer?ont=healthcare").get_json()
        self.assertNotIn("Patient_P9081", json.dumps(explorer))
        metrics = self.client.get("/api/v1/metrics").get_json()
        healthcare = next(domain for domain in metrics["domains"] if domain["key"] == "healthcare")
        self.assertLess(healthcare["data_triples"], 22)

        detail = self.client.get(
            "/api/instance-detail?ont=healthcare&uri=http%3A%2F%2Fexample.org%2Fontology%2Fhealthcare%23Patient_P9081"
        )
        self.assertEqual(detail.status_code, 404)
        self.assertNotIn("PATIENT-9081", detail.get_data(as_text=True))

    def test_validation_failure_does_not_return_sensitive_report_details(self):
        with patch.object(studio.pyshacl, "validate", return_value=(False, None, "patient value: PATIENT-9081")):
            response = self.client.get("/api/validate?ont=healthcare")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("PATIENT-9081", json.dumps(response.get_json()))

    def test_external_fuseki_transfer_is_blocked_without_sensitive_opt_in(self):
        response = self.client.post("/api/v1/fuseki/sync", json={"ont": "healthcare"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
