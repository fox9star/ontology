"""Regression coverage for the Korean War ontology profile."""

import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD
import pyshacl

import app
from ontology_loader import load_schema_graph, load_shape_graph

ROOT = Path(__file__).resolve().parents[1]
KWAR = Namespace("http://example.org/ontology/korean-war#")


class KoreanWarOntologyTests(unittest.TestCase):
    def test_korean_war_profile_is_registered_and_example_conforms(self):
        self.assertIn("korean-war", app.ONTOLOGIES)
        self.assertIn((KWAR.MilitaryOperation, RDF.type, None),
                      load_schema_graph(ROOT, "korean-war-schema.ttl"))
        data = Graph().parse(ROOT / "korean-war-example.ttl", format="turtle")
        conforms, _, report = pyshacl.validate(
            data,
            shacl_graph=load_shape_graph(ROOT, "korean-war-shapes.ttl"),
            ont_graph=load_schema_graph(ROOT, "korean-war-schema.ttl"),
            inference="rdfs",
        )
        self.assertTrue(conforms, report)

    def test_korean_war_shape_rejects_negative_casualties(self):
        data = Graph().parse(ROOT / "korean-war-example.ttl", format="turtle")
        # Change combat casualties to a negative integer
        data.remove((KWAR.Cas_Incheon_UN, KWAR.killedInAction, None))
        data.add((KWAR.Cas_Incheon_UN, KWAR.killedInAction, Literal(-5, datatype=XSD.integer)))
        conforms, _, report = pyshacl.validate(
            data,
            shacl_graph=load_shape_graph(ROOT, "korean-war-shapes.ttl"),
            ont_graph=load_schema_graph(ROOT, "korean-war-schema.ttl"),
            inference="rdfs",
        )
        self.assertFalse(conforms, report)

    def test_korean_war_sparql_templates_are_available(self):
        response = app.app.test_client().get("/api/sparql-templates?ont=korean-war")
        self.assertEqual(response.status_code, 200)
        templates = response.get_json()["korean-war"]
        keys = [item["key"] for item in templates]
        self.assertIn("list_operations", keys)
        self.assertIn("list_casualties", keys)
        self.assertIn("list_ai_analyses", keys)


if __name__ == "__main__":
    unittest.main()
