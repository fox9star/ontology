"""
Unit tests for OpenAPI 3.0 specification and interactive documentation endpoint.
"""

import unittest
from app import app


class TestOpenAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_openapi_json_schema(self):
        res = self.client.get('/api/openapi.json')
        self.assertEqual(res.status_code, 200)
        spec = res.get_json()
        self.assertEqual(spec.get("openapi"), "3.0.3")
        self.assertIn("info", spec)
        self.assertIn("paths", spec)
        paths = spec["paths"]
        self.assertIn("/api/v1/domains", paths)
        self.assertIn("/api/v1/metrics", paths)
        self.assertIn("/api/v1/export", paths)
        self.assertIn("/api/v1/nl-query", paths)
        self.assertIn("/api/v1/instances", paths)
        self.assertIn("/api/v1/simulate", paths)
        self.assertIn("/api/graph-data", paths)
        self.assertIn("/api/sparql", paths)

    def test_docs_ui_page(self):
        res = self.client.get('/api/docs')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn("AI Agent Ontology Ecosystem REST API", html)
        self.assertIn("loadSpecs", html)


if __name__ == '__main__':
    unittest.main()
