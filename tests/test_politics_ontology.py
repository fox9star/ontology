"""Regression coverage for the neutral political information ontology."""

import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD
import pyshacl

import app
from ontology_loader import load_schema_graph, load_shape_graph

ROOT = Path(__file__).resolve().parents[1]
POLITICS = Namespace("https://example.org/ontology/politics#")


class PoliticsOntologyTests(unittest.TestCase):
    def validate(self, data):
        return pyshacl.validate(
            data,
            shacl_graph=load_shape_graph(ROOT, "politics-shapes.ttl"),
            ont_graph=load_schema_graph(ROOT, "politics-schema.ttl"),
            inference="rdfs",
        )

    def test_politics_profile_is_registered_and_example_conforms(self):
        self.assertIn("politics", app.ONTOLOGIES)
        schema = load_schema_graph(ROOT, "politics-schema.ttl")
        self.assertIn((POLITICS.Election, RDF.type, None), schema)
        data = Graph().parse(ROOT / "politics-example.ttl", format="turtle")
        conforms, _, report = self.validate(data)
        self.assertTrue(conforms, report)

    def test_negative_vote_count_is_rejected(self):
        data = Graph().parse(ROOT / "politics-example.ttl", format="turtle")
        data.remove((POLITICS.ExampleResult_A, POLITICS.voteCount, None))
        data.add((POLITICS.ExampleResult_A, POLITICS.voteCount, Literal(-1, datatype=XSD.integer)))
        conforms, _, report = self.validate(data)
        self.assertFalse(conforms, report)

    def test_politics_competency_questions_are_available_as_templates(self):
        response = app.app.test_client().get("/api/sparql-templates?ont=politics")
        self.assertEqual(response.status_code, 200)
        templates = response.get_json()["politics"]
        self.assertEqual([item["key"] for item in templates],
                         ["POL-01", "POL-02", "POL-03", "POL-04"])
        for item in templates:
            with self.subTest(question=item["key"]):
                result = app.app.test_client().post(
                    "/api/sparql",
                    json={"ont": "politics", "project": "", "query": item["query"]},
                )
                self.assertEqual(result.status_code, 200, result.get_json())
                self.assertGreater(result.get_json()["count"], 0)


if __name__ == "__main__":
    unittest.main()
