"""
Unit tests for Cross-Domain Alignment & Reasoning Engine.
"""

import unittest
from app import app
import cross_domain_bridge


class TestCrossDomainBridge(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_align_cross_domains(self):
        res = cross_domain_bridge.align_cross_domains()
        self.assertIn("total_fused_triples", res)
        self.assertIn("inferred_count", res)
        self.assertIn("inferred_triples", res)
        self.assertIn("aligned_domains", res)
        self.assertGreater(res["total_fused_triples"], 100)
        self.assertGreaterEqual(res["inferred_count"], 1)

        # Check if the rules produced triples
        rule_names = {t["rule"] for t in res["inferred_triples"]}
        self.assertTrue(len(rule_names) >= 1)

    def test_api_cross_domain_align(self):
        res = self.client.get('/api/v1/cross-domain/align')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_fused_triples", data)
        self.assertIn("inferred_triples", data)
        self.assertIn("aligned_domains", data)
        self.assertIn("inferred_count", data)


if __name__ == "__main__":
    unittest.main()
