"""Reject unsafe retirement and detect semantic breaks across reviewed versions."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, XSD

from namespace_policy import ROOT, SCHEMA_FILES, check_namespaces
from ontology_docs_check import documentation_report
from term_lifecycle import check_lifecycle, compare_snapshots, create_snapshot, main

CORE = "https://example.org/ontology/core#"


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        for filename in SCHEMA_FILES:
            (self.root / filename).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / filename, self.root / filename)

    def tearDown(self):
        self.directory.cleanup()

    def mutate_core(self, mutation):
        path = self.root / "core-schema.ttl"
        graph = Graph().parse(path, format="turtle")
        mutation(graph)
        graph.serialize(path, format="turtle")

    def retirement(self, graph, source="Project", target="Artifact"):
        graph.add((URIRef(CORE + source), OWL.deprecated, Literal(True)))
        graph.add((URIRef(CORE + source), DCTERMS.isReplacedBy, URIRef(CORE + target)))

    def test_existing_bundle_has_no_lifecycle_or_namespace_failures(self):
        self.assertEqual(check_namespaces(self.root), [])
        self.assertEqual(check_lifecycle(self.root), [])

    def test_local_replacement_requires_deprecation_and_same_role(self):
        self.mutate_core(lambda graph: graph.add((URIRef(CORE + "Project"), DCTERMS.isReplacedBy, URIRef(CORE + "taskStatus"))))
        errors = check_lifecycle(self.root)
        self.assertTrue(any("requires owl:deprecated true" in error for error in errors), errors)
        self.assertTrue(any("different term role" in error for error in errors), errors)

    def test_local_same_role_replacement_is_allowed_without_equivalence(self):
        self.mutate_core(self.retirement)
        self.assertEqual(check_lifecycle(self.root), [])

    def test_literal_target_multiple_targets_and_untyped_boolean_are_rejected(self):
        def mutation(graph):
            term = URIRef(CORE + "Project")
            graph.add((term, OWL.deprecated, Literal("true")))
            graph.add((term, DCTERMS.isReplacedBy, Literal(CORE + "Artifact")))
        self.mutate_core(mutation)
        errors = check_lifecycle(self.root)
        self.assertTrue(any("xsd:boolean" in error for error in errors), errors)
        self.assertTrue(any("absolute IRI" in error for error in errors), errors)
        self.mutate_core(lambda graph: graph.add((URIRef(CORE + "Project"), DCTERMS.isReplacedBy, URIRef(CORE + "Artifact"))))
        self.assertTrue(any("exactly one" in error for error in check_lifecycle(self.root)))

    def test_replacement_cycles_and_chains_are_rejected(self):
        def mutation(graph):
            self.retirement(graph)
            self.retirement(graph, "Artifact", "Project")
        self.mutate_core(mutation)
        errors = check_lifecycle(self.root)
        self.assertTrue(any("chain is forbidden" in error for error in errors), errors)
        self.assertTrue(any("Replacement cycle" in error for error in errors), errors)

    def test_external_mapping_requires_iri_role_and_reason(self):
        target = "https://owned.invalid/vocab#Project"
        def mutation(graph):
            graph.add((URIRef(CORE + "Project"), OWL.deprecated, Literal(True)))
            graph.add((URIRef(CORE + "Project"), DCTERMS.isReplacedBy, URIRef(target)))
        self.mutate_core(mutation)
        self.assertTrue(any("explicitly approved" in error for error in check_lifecycle(self.root)))
        policy = {"external_replacements": [{"source": CORE + "Project", "target": target, "role": "class", "reason": "Reviewed migration retains the project class role."}]}
        self.assertEqual(check_lifecycle(self.root, policy), [])
        policy["external_replacements"][0]["role"] = "object_property"
        self.assertTrue(any("mismatched role" in error for error in check_lifecycle(self.root, policy)))

    def test_retirement_without_replacement_requires_reason(self):
        self.mutate_core(lambda graph: graph.add((URIRef(CORE + "Project"), OWL.deprecated, Literal(True))))
        self.assertTrue(any("retirement without replacement" in error for error in check_lifecycle(self.root)))
        self.assertEqual(check_lifecycle(self.root, {"retired_terms": {CORE + "Project": "Retired after consumer review; no successor concept exists."}}), [])

    def test_equivalence_requires_reviewed_assertion_justification(self):
        self.mutate_core(lambda graph: graph.add((URIRef(CORE + "Project"), OWL.equivalentClass, URIRef(CORE + "Artifact"))))
        self.assertTrue(any("reviewed semantic justification" in error for error in check_lifecycle(self.root)))
        policy = {"equivalence_justifications": [{"source": CORE + "Project", "predicate": str(OWL.equivalentClass), "target": CORE + "Artifact", "reason": "Synthetic test approval only; never applied to the repository."}]}
        self.assertEqual(check_lifecycle(self.root, policy), [])

    def test_namespace_gate_detects_undeclared_import_cycles_and_term_collisions(self):
        def mutation(graph):
            ontology = URIRef("https://example.org/ontology/core")
            graph.add((ontology, OWL.imports, URIRef("https://unknown.invalid/ontology")))
            graph.add((ontology, OWL.imports, URIRef("https://example.org/mv")))
            graph.add((URIRef("https://example.org/mv#Shot"), RDF.type, OWL.Class))
        self.mutate_core(mutation)
        errors = check_namespaces(self.root)
        self.assertTrue(any("unresolved import" in error for error in errors), errors)
        self.assertTrue(any("Local import cycle" in error for error in errors), errors)
        self.assertTrue(any("already declared" in error for error in errors), errors)
        self.assertTrue(any("outside its module namespace" in error for error in errors), errors)

    def test_version_iri_imports_resolve_and_semver_identifiers_are_checked(self):
        version_iri = URIRef("https://example.org/ontology/core/1.1.1")
        self.mutate_core(lambda graph: graph.add((URIRef("https://example.org/ontology/core"), OWL.versionIRI, version_iri)))
        path = self.root / "mv-schema.ttl"
        graph = Graph().parse(path, format="turtle")
        graph.remove((URIRef("https://example.org/mv"), OWL.imports, URIRef("https://example.org/ontology/core")))
        graph.add((URIRef("https://example.org/mv"), OWL.imports, version_iri))
        graph.serialize(path, format="turtle")
        self.assertEqual(check_namespaces(self.root), [])
        self.mutate_core(lambda graph: graph.set((URIRef("https://example.org/ontology/core"), OWL.versionInfo, Literal("1.1.1-01"))))
        self.assertTrue(any("semantic version" in error for error in check_namespaces(self.root)))
        self.mutate_core(lambda graph: graph.set((URIRef("https://example.org/ontology/core"), OWL.versionInfo, Literal("1.1.1-rc.1+review.1"))))
        self.assertEqual(check_namespaces(self.root), [])

    def test_duplicate_version_iri_and_conflicting_term_roles_are_rejected(self):
        version_iri = URIRef("https://example.org/version/1")
        def mutation(graph):
            graph.add((URIRef("https://example.org/ontology/core"), OWL.versionIRI, version_iri))
            graph.add((URIRef(CORE + "Project"), RDF.type, OWL.ObjectProperty))
        self.mutate_core(mutation)
        path = self.root / "mv-schema.ttl"
        graph = Graph().parse(path, format="turtle")
        graph.add((URIRef("https://example.org/mv"), OWL.versionIRI, version_iri))
        graph.serialize(path, format="turtle")
        errors = check_namespaces(self.root)
        self.assertTrue(any("version IRI is already declared" in error for error in errors), errors)
        self.assertTrue(any("conflicting roles" in error for error in errors), errors)

    def test_semantic_change_requires_major_bump_but_labels_do_not(self):
        previous = create_snapshot(self.root)
        self.mutate_core(lambda graph: graph.add((URIRef(CORE + "taskStatus"), RDFS.label, Literal("Changed text", lang="en"))))
        self.assertTrue(compare_snapshots(previous, create_snapshot(self.root))["compatible"])
        self.mutate_core(lambda graph: graph.set((URIRef(CORE + "taskStatus"), RDFS.range, XSD.integer)))
        report = compare_snapshots(previous, create_snapshot(self.root))
        self.assertFalse(report["compatible"])
        self.assertIn(CORE + "taskStatus", next(module for module in report["modules"] if module["file"] == "core-schema.ttl")["changed"])
        self.mutate_core(lambda graph: graph.set((URIRef("https://example.org/ontology/core"), OWL.versionInfo, Literal("2.0.0"))))
        self.assertTrue(compare_snapshots(previous, create_snapshot(self.root))["compatible"])

    def test_removed_term_and_anonymous_restriction_changes_are_detected(self):
        previous = create_snapshot(self.root)
        self.mutate_core(lambda graph: graph.remove((URIRef(CORE + "SensitiveRecord"), None, None)))
        report = compare_snapshots(previous, create_snapshot(self.root))
        self.assertFalse(report["compatible"])
        self.assertIn(CORE + "SensitiveRecord", next(module for module in report["modules"] if module["file"] == "core-schema.ttl")["removed"])
        path = self.root / "mv-schema.ttl"
        graph = Graph().parse(path, format="turtle")
        graph.set((next(graph.subjects(OWL.someValuesFrom, URIRef("https://example.org/mv#CreativeBrief"))), OWL.someValuesFrom, URIRef("https://example.org/mv#AudioAsset")))
        graph.serialize(path, format="turtle")
        report = compare_snapshots(previous, create_snapshot(self.root))
        self.assertIn("https://example.org/mv#MusicVideoProject", next(module for module in report["modules"] if module["file"] == "mv-schema.ttl")["changed"])

    def test_blank_node_serialization_does_not_create_false_changes(self):
        previous = create_snapshot(self.root)
        for filename in SCHEMA_FILES:
            path = self.root / filename
            Graph().parse(path, format="turtle").serialize(path, format="turtle")
        self.assertTrue(compare_snapshots(previous, create_snapshot(self.root))["compatible"])

    def test_cli_snapshot_and_compare(self):
        baseline = self.root / "baseline.json"
        report_path = self.root / "comparison.json"
        self.assertEqual(main(["--root", str(self.root), "snapshot", "--output", str(baseline)]), 0)
        self.assertEqual(main(["--root", str(self.root), "compare", "--previous", str(baseline), "--json", str(report_path)]), 0)
        self.assertTrue(json.loads(report_path.read_text(encoding="utf-8"))["compatible"])

    def test_bilingual_coverage_and_narrow_exception_preserve_measured_gap(self):
        report = documentation_report(self.root)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["covered"]["ko"]["definition"], report["total"])
        self.mutate_core(lambda graph: graph.remove((URIRef(CORE + "Project"), RDFS.comment, Literal("공통 목표와 관련 작업을 묶는 범위.", lang="ko"))))
        report = documentation_report(self.root)
        self.assertTrue(any("definition in ko" in error for error in report["errors"]))
        exception = {"file": "core-schema.ttl", "term": CORE + "Project", "field": "definition", "language": "ko", "reason": "Synthetic test only; translation awaiting review."}
        report = documentation_report(self.root, [exception])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["exception_count"], 1)
        self.assertEqual(report["covered"]["ko"]["definition"], report["total"] - 1)
        exception["term"] += "Missing"
        self.assertTrue(any("Stale or unknown" in error for error in documentation_report(self.root, [exception])["errors"]))


if __name__ == "__main__":
    unittest.main()
