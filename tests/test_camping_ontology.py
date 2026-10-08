"""Regression coverage for the built-in camping ontology profile."""

import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD
import pyshacl

import app
from ontology_loader import load_schema_graph, load_shape_graph

ROOT = Path(__file__).resolve().parents[1]
CAMPING = Namespace("https://example.org/ontology/camping#")


class CampingOntologyTests(unittest.TestCase):
    def test_camping_profile_is_registered_and_example_conforms(self):
        self.assertIn("camping", app.ONTOLOGIES)
        self.assertIn((CAMPING.CampingTrip, RDF.type, None),
                      load_schema_graph(ROOT, "camping-schema.ttl"))
        data = Graph().parse(ROOT / "camping-example.ttl", format="turtle")
        conforms, _, report = pyshacl.validate(
            data,
            shacl_graph=load_shape_graph(ROOT, "camping-shapes.ttl"),
            ont_graph=load_schema_graph(ROOT, "camping-schema.ttl"),
            inference="rdfs",
        )
        self.assertTrue(conforms, report)

    def test_camping_shape_rejects_nonpositive_site_capacity(self):
        data = Graph().parse(ROOT / "camping-example.ttl", format="turtle")
        data.remove((CAMPING.CreeksideSite, CAMPING.siteCapacity, None))
        data.add((CAMPING.CreeksideSite, CAMPING.siteCapacity, Literal(0, datatype=XSD.integer)))
        conforms, _, report = pyshacl.validate(
            data,
            shacl_graph=load_shape_graph(ROOT, "camping-shapes.ttl"),
            ont_graph=load_schema_graph(ROOT, "camping-schema.ttl"),
            inference="rdfs",
        )
        self.assertFalse(conforms, report)

    def test_camping_competency_questions_are_available_as_templates(self):
        response = app.app.test_client().get("/api/sparql-templates?ont=camping")
        self.assertEqual(response.status_code, 200)
        templates = response.get_json()["camping"]
        self.assertEqual([item["key"] for item in templates],
                         ["CAMP-01", "CAMP-02", "CAMP-03", "CAMP-04"])


if __name__ == "__main__":
    unittest.main()
