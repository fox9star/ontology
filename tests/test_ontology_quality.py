"""Semantic regression cases for ontology profiles and controlled vocabularies."""

import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, XSD
import pyshacl

import verify_all
from controlled_vocab_check import check_vocabularies
from namespace_policy import check_namespaces
from ontology_loader import load_schema_graph, load_shape_graph
from app import ONTOLOGIES
from rdflib.namespace import SKOS

ROOT = Path(__file__).resolve().parents[1]
MV = Namespace("https://example.org/mv#")
DEVOPS = Namespace("http://example.org/ontology/devops#")
ECOM = Namespace("http://example.org/ontology/ecommerce#")
HEALTH = Namespace("http://example.org/ontology/healthcare#")
AGENT = Namespace("https://example.org/agent#")
PROV = Namespace("http://www.w3.org/ns/prov#")


def validate_graph(domain, graph):
    cfg = verify_all.DOMAINS[domain]
    schema = load_schema_graph(ROOT, cfg["schema"])
    shapes = load_shape_graph(ROOT, cfg["shapes"])
    conforms, _, report = pyshacl.validate(
        graph, shacl_graph=shapes, ont_graph=schema, inference="rdfs"
    )
    return bool(conforms), report


def example_graph(filename):
    return Graph().parse(ROOT / filename, format="turtle")


class TestOntologyQuality(unittest.TestCase):
    def test_all_bundled_profiles_conform(self):
        self.assertTrue(verify_all.run_suite())

    def test_skos_statuses_match_shacl_literals(self):
        self.assertEqual(check_vocabularies(ROOT), [])

    def test_namespace_release_guard_rejects_reserved_examples(self):
        self.assertEqual(check_namespaces(ROOT, release=False), [])
        self.assertTrue(any("placeholder namespace" in error for error in check_namespaces(ROOT, release=True)))

    def test_application_versions_match_canonical_schema_versions(self):
        for profile, config in ONTOLOGIES.items():
            with self.subTest(profile=profile):
                graph = Graph().parse(ROOT / config["schema"], format="turtle")
                ontology = next(graph.subjects(RDF.type, OWL.Ontology))
                version = next(graph.objects(ontology, OWL.versionInfo))
                self.assertEqual(str(version), config["version"])

    def test_controlled_vocabulary_is_loaded_as_a_local_profile_import(self):
        graph = load_schema_graph(ROOT, "mv-schema.ttl")
        self.assertIn((URIRef("https://example.org/ontology/vocab#MVStatusScheme"), RDF.type, SKOS.ConceptScheme), graph)

    def test_mv_rejects_overlapping_shots(self):
        graph = example_graph("mv-example.ttl")
        graph.remove((MV.shot02, MV.startSecond, None))
        graph.add((MV.shot02, MV.startSecond, Literal("29.5", datatype=XSD.decimal)))
        conforms, report = validate_graph(0, graph)
        self.assertFalse(conforms, report)

    def test_mv_rejects_task_dependency_cycles(self):
        graph = example_graph("mv-example.ttl")
        graph.add((MV.audioTask01, MV.dependsOn, MV.renderTask01))
        conforms, report = validate_graph(0, graph)
        self.assertFalse(conforms, report)

    def test_mv_rejects_shots_beyond_audio_duration(self):
        graph = example_graph("mv-example.ttl")
        graph.remove((MV.shot02, MV.endSecond, None))
        graph.add((MV.shot02, MV.endSecond, Literal("61.0", datatype=XSD.decimal)))
        conforms, report = validate_graph(0, graph)
        self.assertFalse(conforms, report)

    def test_devops_rejects_successful_pipeline_with_failed_step(self):
        graph = example_graph("devops-example.ttl")
        graph.remove((DEVOPS.SecScan_01, DEVOPS.executionStatus, None))
        graph.add((DEVOPS.SecScan_01, DEVOPS.executionStatus, Literal("FAILED")))
        conforms, report = validate_graph(2, graph)
        self.assertFalse(conforms, report)

    def test_devops_requires_deployed_artifact_from_successful_build(self):
        graph = example_graph("devops-example.ttl")
        graph.remove((DEVOPS.DeployStep_01, DEVOPS.deploysArtifact, None))
        graph.add((DEVOPS.DeployStep_01, DEVOPS.deploysArtifact, DEVOPS.UnbuiltImage))
        graph.add((DEVOPS.UnbuiltImage, RDF_TYPE, DEVOPS.BuildArtifact))
        conforms, report = validate_graph(2, graph)
        self.assertFalse(conforms, report)

    def test_ecommerce_distinguishes_verified_currency_and_bounds_decimal_precision(self):
        graph = example_graph("ecommerce-example.ttl")
        graph.remove((ECOM.Product_Headphones, ECOM.priceCurrencyStatus, None))
        graph.add((ECOM.Product_Headphones, ECOM.priceCurrencyStatus, Literal("verified")))
        conforms, report = validate_graph(4, graph)
        self.assertFalse(conforms, report)

        graph.add((ECOM.Product_Headphones, ECOM.priceCurrency, Literal("USD")))
        conforms, report = validate_graph(4, graph)
        self.assertTrue(conforms, report)

        graph.remove((ECOM.Product_Headphones, ECOM.price, None))
        graph.add((ECOM.Product_Headphones, ECOM.price, Literal("1.12345", datatype=XSD.decimal)))
        conforms, report = validate_graph(4, graph)
        self.assertFalse(conforms, report)

    def test_ecommerce_rejects_invalid_order_status_transition(self):
        graph = example_graph("ecommerce-example.ttl")
        graph.add((ECOM.invalidEvent, RDF_TYPE, ECOM.OrderStatusEvent))
        graph.add((ECOM.invalidEvent, ECOM.eventOrder, ECOM.Order_88219))
        graph.add((ECOM.invalidEvent, ECOM.fromStatus, Literal("PLACED")))
        graph.add((ECOM.invalidEvent, ECOM.toStatus, Literal("DELIVERED")))
        graph.add((ECOM.invalidEvent, ECOM.changedAt, Literal("2026-10-04T00:00:00Z", datatype=XSD.dateTime)))
        graph.add((ECOM.Order_88219, ECOM.hasStatusEvent, ECOM.invalidEvent))
        conforms, report = validate_graph(4, graph)
        self.assertFalse(conforms, report)

    def test_healthcare_observation_requires_coding_and_value_unit_pair(self):
        graph = example_graph("healthcare-example.ttl")
        graph.add((HEALTH.testObservation, RDF_TYPE, HEALTH.ClinicalObservation))
        graph.add((HEALTH.testObservation, HEALTH.observesRecord, HEALTH.Patient_P9081))
        graph.add((HEALTH.testObservation, HEALTH.codeSystem, URIRef("https://loinc.org")))
        graph.add((HEALTH.testObservation, HEALTH.observationCode, Literal("TEST-CODE")))
        graph.add((HEALTH.testObservation, HEALTH.observedAt, Literal("2026-01-01T00:00:00Z", datatype=XSD.dateTime)))
        graph.add((HEALTH.testObservation, HEALTH.numericValue, Literal("12.5", datatype=XSD.decimal)))
        graph.add((HEALTH.testObservation, HEALTH.unitCode, Literal("mg/dL")))
        graph.add((HEALTH.testObservation, HEALTH.unitCodeSystem, URIRef("http://unitsofmeasure.org")))
        graph.add((HEALTH.testObservation, PROV.wasGeneratedBy, HEALTH.Task_CTScan_9081))
        conforms, report = validate_graph(5, graph)
        self.assertTrue(conforms, report)

        graph.remove((HEALTH.testObservation, HEALTH.unitCode, None))
        conforms, report = validate_graph(5, graph)
        self.assertFalse(conforms, report)

    def test_core_task_run_timestamps_must_be_ordered(self):
        graph = example_graph("agent-example.ttl")
        graph.remove((AGENT.reviewRun01, PROV.startedAtTime, None))
        graph.add((AGENT.reviewRun01, PROV.startedAtTime, Literal("2026-09-16T10:00:00+09:00", datatype=XSD.dateTime)))
        conforms, report = validate_graph(3, graph)
        self.assertFalse(conforms, report)


RDF_TYPE = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#").type


if __name__ == "__main__":
    unittest.main()
