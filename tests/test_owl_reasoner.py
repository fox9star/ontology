"""
Unit tests for OWL 2 RL & RDFS Deductive Reasoning Engine.
"""

import unittest
import rdflib
from rdflib import URIRef, RDF, RDFS
from app import app, load_graph
import owl_reasoner


class TestOwlReasoner(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_run_owl_deductive_closure_subclass_inference(self):
        g = rdflib.Graph()
        c_parent = URIRef("http://example.org/ParentClass")
        c_child = URIRef("http://example.org/ChildClass")
        inst = URIRef("http://example.org/Item")

        g.add((c_child, RDFS.subClassOf, c_parent))
        g.add((inst, RDF.type, c_child))

        # Before reasoning: (inst, RDF.type, c_parent) does not exist
        self.assertNotIn((inst, RDF.type, c_parent), g)

        res = owl_reasoner.run_owl_deductive_closure(g, semantics="rdfs")
        self.assertTrue(res["success"])
        self.assertGreater(res["inferred_count"], 0)

        # After reasoning: subclass entailment inferred
        self.assertIn((inst, RDF.type, c_parent), g)

    def test_api_reasoning_expand(self):
        res = self.client.post('/api/v1/reasoning/expand', json={
            "ont": "mv",
            "semantics": "rdfs"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("inferred_count", data)
        self.assertIn("asserted_count", data)


if __name__ == "__main__":
    unittest.main()
