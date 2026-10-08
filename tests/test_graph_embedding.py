"""
Unit tests for Knowledge Graph Embedding & Entity Recommendation Engine.
"""

import unittest
import rdflib
from rdflib import URIRef, Literal, RDF, RDFS
from app import app, load_graph
import graph_embedding


class TestGraphEmbedding(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_tokenize_text(self):
        tokens = graph_embedding.tokenize_text("AI Agent: Music Video Producer - v2.0")
        self.assertIn("agent", tokens)
        self.assertIn("music", tokens)
        self.assertIn("video", tokens)
        self.assertIn("producer", tokens)

    def test_extract_entity_features_and_similarity(self):
        g = rdflib.Graph()
        agent1 = URIRef("http://example.org/Agent1")
        agent2 = URIRef("http://example.org/Agent2")
        agent_type = URIRef("http://example.org/AgentType")
        task_type = URIRef("http://example.org/TaskType")
        task1 = URIRef("http://example.org/Task1")
        task2 = URIRef("http://example.org/Task2")

        g.add((agent1, RDF.type, agent_type))
        g.add((agent1, RDFS.label, Literal("Video Agent 1", lang="en")))
        g.add((agent1, URIRef("http://example.org/performs"), task1))
        g.add((task1, RDF.type, task_type))

        g.add((agent2, RDF.type, agent_type))
        g.add((agent2, RDFS.label, Literal("Video Agent 2", lang="en")))
        g.add((agent2, URIRef("http://example.org/performs"), task2))
        g.add((task2, RDF.type, task_type))

        vec1 = graph_embedding.extract_entity_features(g, agent1)
        vec2 = graph_embedding.extract_entity_features(g, agent2)

        self.assertIn("type:AgentType", vec1)
        self.assertIn("neighbor_type:TaskType", vec1)

        sim, shared = graph_embedding.cosine_similarity(vec1, vec2)
        self.assertGreater(sim, 0.7)
        self.assertGreater(len(shared), 0)

    def test_find_similar_nodes_on_mv_graph(self):
        g = load_graph("mv")
        agents = list(g.subjects(RDF.type, URIRef("https://example.org/mv#Agent")))
        if agents:
            target = str(agents[0])
            recs = graph_embedding.find_similar_nodes(g, target, top_k=3)
            self.assertIsInstance(recs, list)
            if recs:
                self.assertIn("similarity", recs[0])
                self.assertIn("shared_features", recs[0])

    def test_api_recommend_similar(self):
        g = load_graph("mv")
        agents = list(g.subjects(RDF.type, URIRef("https://example.org/mv#Agent")))
        if agents:
            import urllib.parse
            encoded_uri = urllib.parse.quote(str(agents[0]))
            res = self.client.get(f'/api/v1/recommend-similar?ont=mv&uri={encoded_uri}')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("recommendations", data)
            self.assertIn("count", data)
            self.assertEqual(data["target_uri"], str(agents[0]))

    def test_api_recommend_similar_missing_param(self):
        res = self.client.get('/api/v1/recommend-similar')
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
