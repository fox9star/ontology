"""Check coverage regression, optional contracts and private-value exclusion."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyshacl
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD

import ontology_quality as quality
from ontology_loader import load_shape_graph

NS = Namespace("https://example.test/coverage#")
ROOT = Path(__file__).resolve().parents[1]


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.schema = Graph()
        self.schema.add((NS.Class, RDF.type, OWL.Class))
        self.schema.add((NS.field, RDF.type, OWL.DatatypeProperty))
        self.schema.add((NS.field, RDFS.domain, NS.Class))
        self.schema.add((NS.field, RDFS.range, XSD.string))
        shapes = Graph()
        shapes.add((NS.Shape, RDF.type, SH.NodeShape))
        shapes.add((NS.Shape, SH.targetClass, NS.Class))
        shapes.add((NS.Shape, SH.property, NS.FieldShape))
        shapes.add((NS.FieldShape, SH.path, NS.field))
        shapes.add((NS.FieldShape, SH.datatype, XSD.string))
        shapes.serialize(self.root / "test-shapes.ttl", format="turtle")
        for filename in ("core-shapes.ttl", "property-contract-shapes.ttl"):
            Graph().serialize(self.root / filename, format="turtle")
        self.data = Graph()
        self.data.add((NS.subject, RDF.type, NS.Class))
        self.data.add((NS.subject, NS.field, Literal("value")))
        self.configs = {"test": {"schema": "test-schema.ttl", "shapes": "test-shapes.ttl", "example": "test-example.ttl"}}
        self.policy = {"exceptions": {}, "cq_backlog": {}}
        (self.root / "COMPETENCY_QUESTIONS.md").write_text(
            '### TEST-01. Coverage\n\n~~~sparql\n'
            'PREFIX ex: <https://example.test/coverage#>\n'
            'SELECT ?value WHERE { ?subject a ex:Class ; ex:field ?value }\n~~~\n', encoding="utf-8")

    def report(self, validate=False):
        self.schema.serialize(self.root / "test-schema.ttl", format="turtle")
        self.data.serialize(self.root / "test-example.ttl", format="turtle")
        with patch.object(quality, "SCHEMA_FILES", ("test-schema.ttl",)):
            return quality.build_report(self.root, self.configs, validate_instances=validate, policy=self.policy)

    def test_complete_mapping_passes_without_claiming_validation_when_disabled(self):
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["summary"]["terms_with_shapes"], 2)
        self.assertEqual(report["summary"]["terms_referenced_by_questions"], 2)
        self.assertIsNone(report["profiles"]["test"]["shacl_conforms"])

    def test_missing_domain_requires_explicit_reason_and_missing_range_is_fatal(self):
        self.schema.remove((NS.field, RDFS.domain, None))
        self.assertFalse(self.report()["valid"])
        self.policy["exceptions"][str(NS.field)] = {"domain": "Intentional generic field shared by distinct categories."}
        self.assertTrue(self.report()["valid"])
        self.schema.remove((NS.field, RDFS.range, None))
        self.assertTrue(any("no range" in error for error in self.report()["errors"]))

    def test_new_query_gap_fails_and_backlog_is_visible_as_incomplete(self):
        self.schema.add((NS.New, RDF.type, OWL.Class))
        self.schema.add((NS.New, RDFS.subClassOf, NS.Class))
        self.assertTrue(any("New competency" in error for error in self.report()["errors"]))
        self.policy["cq_backlog"][str(NS.New)] = "Existing debt reviewed for the next domain question expansion."
        report = self.report()
        row = next(row for row in report["terms"] if row["iri"] == str(NS.New))
        self.assertTrue(report["valid"])
        self.assertEqual(row["gaps"], ["cq"])
        self.assertEqual(report["summary"]["cq_backlog_terms"], 1)

    def test_orphan_shape_path_is_rejected(self):
        shapes = Graph().parse(self.root / "test-shapes.ttl", format="turtle")
        shapes.add((NS.Broken, SH.path, NS.undeclared))
        shapes.serialize(self.root / "test-shapes.ttl", format="turtle")
        self.assertTrue(any("undeclared local property" in error for error in self.report()["errors"]))

    def test_instance_reports_never_export_identifiers_or_values(self):
        secret = "PATIENT-SHOULD-NOT-APPEAR"
        patient = NS[secret]
        health = Namespace(quality.HEALTH)
        self.data.add((patient, RDF.type, health.PatientRecord))
        self.data.add((patient, RDFS.label, Literal(secret)))
        self.data.add((patient, health.dataClassification, NS[secret]))
        encoded = json.dumps(self.report())
        self.assertNotIn(secret, encoded)

    def test_classification_uses_exact_iri_not_a_matching_fragment(self):
        health = Namespace(quality.HEALTH)
        self.data.add((NS.patient, RDF.type, health.PatientRecord))
        self.data.add((NS.patient, health.dataClassification, NS.Synthetic))
        counts = self.report()["profiles"]["test"]["healthcare_classification_counts"]
        self.assertEqual(counts["Synthetic"], 0)
        self.assertEqual(counts["unknown"], 1)

    def test_deactivated_and_unattached_shapes_do_not_count_as_coverage(self):
        shapes = Graph().parse(self.root / "test-shapes.ttl", format="turtle")
        shapes.add((NS.Shape, SH.deactivated, Literal(True)))
        shapes.add((NS.Orphan, SH.path, NS.field))
        shapes.add((NS.Orphan, SH.datatype, XSD.string))
        shapes.serialize(self.root / "test-shapes.ttl", format="turtle")
        report = self.report()
        self.assertEqual(report["summary"]["terms_with_shapes"], 0)
        self.assertFalse(report["valid"])

    def test_empty_shape_does_not_count_as_coverage(self):
        shapes = Graph().parse(self.root / "test-shapes.ttl", format="turtle")
        shapes.remove((NS.FieldShape, SH.datatype, None))
        shapes.serialize(self.root / "test-shapes.ttl", format="turtle")
        self.assertEqual(self.report()["summary"]["terms_with_shapes"], 0)

    def test_included_project_failure_changes_top_level_result(self):
        self.report()
        directory = self.root / "projects" / "fixture"
        directory.mkdir(parents=True)
        (directory / "project.json").write_text('{"ontology": "test"}', encoding="utf-8")
        self.data.set((NS.subject, NS.field, Literal(3)))
        self.data.serialize(directory / "data.ttl", format="turtle")
        with patch.object(quality, "SCHEMA_FILES", ("test-schema.ttl",)):
            report = quality.build_report(self.root, self.configs, include_projects=True, policy=self.policy)
        self.assertFalse(report["valid"])
        self.assertTrue(any("Included project" in error for error in report["errors"]))

    def test_shacl_failing_instances_are_not_reported_as_passed(self):
        self.data.set((NS.subject, NS.field, Literal(3)))
        report = self.report(validate=True)
        self.assertFalse(report["valid"])
        self.assertFalse(report["profiles"]["test"]["shacl_conforms"])

    def test_predicate_contract_rejects_invalid_optional_bpm_and_blank_model(self):
        shapes = load_shape_graph(ROOT, "mv-shapes.ttl")
        mv = Namespace("https://example.org/mv#")
        # No type assertion: targetSubjectsOf must still discover the bad value.
        data = Graph()
        data.add((NS.asset, mv.bpm, Literal(-1)))
        conforms, _, _ = pyshacl.validate(data, shacl_graph=shapes)
        self.assertFalse(conforms)
        data = Graph()
        data.add((NS.task, mv.modelVersion, Literal("")))
        conforms, _, _ = pyshacl.validate(data, shacl_graph=shapes)
        self.assertFalse(conforms)

    def test_absent_model_and_prompt_are_allowed(self):
        conforms, _, _ = pyshacl.validate(Graph(), shacl_graph=load_shape_graph(ROOT, "mv-shapes.ttl"))
        self.assertTrue(conforms)

    def test_parser_ignores_iri_text_in_a_literal(self):
        source = '### TEST-01. Literal\n\n~~~sparql\nSELECT ?s WHERE { ?s ?p "https://example.test/coverage#field" }\n~~~\n'
        _, references = quality.question_references(source)
        self.assertNotIn(NS.field, references)

    def test_parser_collects_sequence_inverse_and_repeated_property_paths(self):
        source = '### TEST-01. Path\n\n~~~sparql\nPREFIX ex: <https://example.test/coverage#>\nSELECT ?s WHERE { ?s (ex:field+/^ex:other) ?o }\n~~~\n'
        _, references = quality.question_references(source)
        self.assertIn(NS.field, references)
        self.assertIn(NS.other, references)


if __name__ == "__main__":
    unittest.main()
