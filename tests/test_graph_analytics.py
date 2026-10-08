"""
Unit tests for Knowledge Graph Analytics, Centrality & Bottleneck Diagnosis.
"""

import unittest
import rdflib
from app import app, load_graph
import graph_analytics


class TestGraphAnalytics(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_build_network_adjacency_and_pagerank(self):
        g = rdflib.Graph()
        n1 = rdflib.URIRef("http://example.org/A")
        n2 = rdflib.URIRef("http://example.org/B")
        n3 = rdflib.URIRef("http://example.org/C")

        g.add((n1, rdflib.URIRef("http://example.org/to"), n2))
        g.add((n2, rdflib.URIRef("http://example.org/to"), n3))
        g.add((n3, rdflib.URIRef("http://example.org/to"), n1))

        nodes, out_edges, in_edges = graph_analytics.build_network_adjacency(g)
        self.assertEqual(len(nodes), 3)

        pr = graph_analytics.compute_pagerank(nodes, out_edges, in_edges)
        self.assertEqual(len(pr), 3)
        for val in pr.values():
            self.assertAlmostEqual(val, 0.333, places=2)

    def test_analyze_graph_topology_mv(self):
        g = load_graph("mv")
        report = graph_analytics.analyze_graph_topology(g, top_k=5)
        self.assertIn("total_nodes", report)
        self.assertIn("density", report)
        self.assertIn("health_score", report)
        self.assertIn("top_hubs", report)
        self.assertIn("top_bottlenecks", report)
        self.assertGreater(report["total_nodes"], 0)
        self.assertGreaterEqual(report["health_score"], 50)

    def test_api_analytics_centrality(self):
        res = self.client.get('/api/v1/analytics/centrality?ont=mv&top_k=3')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("health_score", data)
        self.assertIn("top_hubs", data)
        self.assertIn("top_bottlenecks", data)


if __name__ == "__main__":
    unittest.main()
