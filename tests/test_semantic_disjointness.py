"""Check declared exclusive roles during OWL-RL reasoning previews."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as studio
import owl_reasoner
from rdflib import RDF, URIRef


class SemanticDisjointnessTests(unittest.TestCase):
    def test_profile_examples_remain_consistent_under_owlrl(self):
        for domain in ("mv", "ecommerce", "healthcare"):
            with self.subTest(domain=domain):
                graph = studio.load_graph(domain)
                result = owl_reasoner.run_owl_deductive_closure(graph)
                self.assertTrue(result["consistent"], result["disjoint_type_violations"])

    def test_audio_and_image_asset_overlap_is_reported(self):
        graph = studio.load_schema_graph("mv")
        individual = URIRef("https://example.test/media/ambiguous")
        graph.add((individual, RDF.type, URIRef(studio.ONTOLOGIES["mv"]["prefix"] + "AudioAsset")))
        graph.add((individual, RDF.type, URIRef(studio.ONTOLOGIES["mv"]["prefix"] + "ImageAsset")))

        result = owl_reasoner.run_owl_deductive_closure(graph)
        self.assertFalse(result["consistent"])
        self.assertEqual(result["disjoint_type_violations"][0]["individual"], str(individual))

    def test_ecommerce_all_disjoint_classes_are_enforced(self):
        graph = studio.load_schema_graph("ecommerce")
        individual = URIRef("http://example.test/item/order")
        prefix = studio.ONTOLOGIES["ecommerce"]["prefix"]
        graph.add((individual, RDF.type, URIRef(prefix + "Product")))
        graph.add((individual, RDF.type, URIRef(prefix + "OrderTask")))

        result = owl_reasoner.run_owl_deductive_closure(graph)
        self.assertFalse(result["consistent"])
        self.assertEqual(len(result["disjoint_type_violations"]), 1)


if __name__ == "__main__":
    unittest.main()
