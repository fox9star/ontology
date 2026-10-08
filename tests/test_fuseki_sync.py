"""
Unit tests for Apache Jena Fuseki Live Sync connector and API endpoints.
"""

import unittest
from unittest.mock import patch, MagicMock
import rdflib
from app import app
import fuseki_sync


class TestFusekiSync(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_get_endpoint_url(self):
        self.assertEqual(fuseki_sync.get_endpoint_url("http://localhost:3030/ds/"), "http://localhost:3030/ds")
        self.assertTrue(fuseki_sync.get_endpoint_url().startswith("http"))

    def test_check_fuseki_connection_offline(self):
        # Using a non-existent port should gracefully return False without raising uncaught exceptions
        connected, msg, ping_ms = fuseki_sync.check_fuseki_connection("http://127.0.0.1:59999/ds")
        self.assertFalse(connected)
        self.assertIn("미가동", msg)
        self.assertEqual(ping_ms, 0.0)

    @patch("fuseki_sync.urllib.request.urlopen")
    def test_check_fuseki_connection_online_mock(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        connected, msg, ping_ms = fuseki_sync.check_fuseki_connection("http://localhost:3030/ds")
        self.assertTrue(connected)
        self.assertIn("정상", msg)
        self.assertGreaterEqual(ping_ms, 0.0)

    @patch("fuseki_sync.urllib.request.urlopen")
    def test_sync_graph_to_fuseki_success_mock(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        g = rdflib.Graph()
        g.add((rdflib.URIRef("http://example.org/s"), rdflib.RDF.type, rdflib.URIRef("http://example.org/Type")))

        res = fuseki_sync.sync_graph_to_fuseki(g, graph_name="https://example.org/test")
        self.assertTrue(res["success"])
        self.assertEqual(res["triples_synced"], 1)

    @patch("fuseki_sync.urllib.request.urlopen")
    def test_protected_healthcare_graph_never_syncs_without_opt_in(self, mock_urlopen):
        from rdflib import Graph, Literal, Namespace
        health = Namespace("http://example.org/ontology/healthcare#")
        graph = Graph()
        graph.add((health.Patient01, rdflib.RDF.type, health.PatientRecord))
        graph.add((health.Patient01, health.patientId, Literal("internal-key")))
        graph.add((health.Patient01, health.dataClassification, health.Unverified))
        result = fuseki_sync.sync_graph_to_fuseki(graph, graph_name="healthcare")
        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 403)
        mock_urlopen.assert_not_called()

    def test_api_fuseki_status(self):
        res = self.client.get('/api/v1/fuseki/status')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("connected", data)
        self.assertIn("endpoint", data)
        self.assertIn("ping_ms", data)
        self.assertIn("message", data)

    def test_api_fuseki_sync_offline(self):
        # Offline sync should return structured response with success: False
        res = self.client.post('/api/v1/fuseki/sync', json={"ont": "mv", "endpoint": "http://127.0.0.1:59999/ds"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data.get("success"))

    def test_api_fuseki_healthcare_sync_requires_opt_in_before_network_access(self):
        res = self.client.post('/api/v1/fuseki/sync', json={
            "ont": "healthcare", "endpoint": "http://127.0.0.1:59999/ds"
        })
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
