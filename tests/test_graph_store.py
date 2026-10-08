"""
tests/test_graph_store.py - Tests for GraphStoreConnector (Fuseki, Neo4j, Neptune, Vector Search)
"""

import unittest
from unittest.mock import patch, MagicMock
from graph_store import GraphStoreConnector


class TestGraphStore(unittest.TestCase):

    def test_default_backend_selection(self):
        connector = GraphStoreConnector()
        self.assertIn(connector.default_backend, ["fuseki", "neo4j", "neptune"])

    @patch("requests.post")
    def test_fuseki_execution(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": {"bindings": []}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        connector = GraphStoreConnector()
        res = connector.execute_query("SELECT * WHERE { ?s ?p ?o } LIMIT 1", backend="fuseki")
        self.assertEqual(res, {"results": {"bindings": []}})
        mock_post.assert_called_once()

    def test_neo4j_unconfigured_raises_runtime_error(self):
        connector = GraphStoreConnector()
        connector.neo4j_driver = None
        with self.assertRaises(RuntimeError):
            connector.execute_query("MATCH (n) RETURN n", backend="neo4j")

    def test_neptune_unconfigured_raises_runtime_error(self):
        connector = GraphStoreConnector()
        connector.neptune_endpoint = None
        with self.assertRaises(RuntimeError):
            connector.execute_query("SELECT * WHERE { ?s ?p ?o }", backend="neptune")

    def test_search_similar_vectors_fallback(self):
        connector = GraphStoreConnector()
        # Query with arbitrary vector
        vec = [0.1, -0.2, 0.5, 0.8]
        results = connector.search_similar_vectors(vec, top_k=3)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)
        for item in results:
            self.assertIn("uri", item)
            self.assertIn("score", item)
            self.assertGreaterEqual(item["score"], 0.0)
            self.assertLessEqual(item["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
