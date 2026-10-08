"""Protect the boundary between local-copy evidence and unknown originals."""

import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD

import evidence


EV = evidence.EV
MV = evidence.MV
PROV = evidence.PROV
EX = Namespace("https://example.test/evidence/")
ROOT = Path(__file__).resolve().parents[1]


class EvidenceProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ontology-evidence-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "immutable-source.bin"
        self.source.write_bytes(b"immutable fixture source media\n")
        self.project = self.root / "projects" / "fixture"
        (self.project / "assets").mkdir(parents=True)
        self.copy = self.project / "assets" / "audio01.wav"
        self.copy.write_bytes(self.source.read_bytes())
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.manifest = {"project_id": "fixture", "assets": [{
            "id": "audio01", "kind": "audio", "file_name": "audio01.wav", "file_uri": self.copy.as_uri(),
            "source_file": str(self.source), "sha256": self.digest, "size_bytes": self.copy.stat().st_size}],
            "import_info": {"tool_version": "local-importer-known-version", "imported_at": "2026-10-03T21:00:00+09:00"}}
        (self.project / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (self.project / "project.json").write_text('{"id":"fixture","ontology":"mv"}', encoding="utf-8")
        self.data = Graph()
        self.data.add((MV.audio01, RDF.type, MV.AudioAsset))
        self.data.add((MV.audio01, MV.checksum, Literal(self.digest)))
        self.data.add((MV.audio01, MV.fileUri, URIRef(self.copy.as_uri())))
        self.data.add((MV.audio01, PROV.wasGeneratedBy, MV.importRun01))
        self.data.add((MV.importRun01, MV.modelVersion, Literal("local-importer-known-version")))
        self.save_data()
        self.initial = {path: path.read_bytes() for path in
                        (self.source, self.copy, self.project / "manifest.json", self.project / "data.ttl", self.project / "project.json")}

    def save_data(self):
        self.data.serialize(self.project / "data.ttl", format="turtle", encoding="utf-8")

    def saved_graph(self):
        return Graph().parse(self.project / "evidence.ttl", format="turtle")

    def test_importer_metadata_never_verifies_original_generation_or_origin(self):
        report = evidence.refresh_project(self.project)
        self.assertTrue(report["conforms"])
        graph = self.saved_graph()
        local = next(graph.subjects(EV.scope, EV.LocalFileIntegrity))
        self.assertEqual(graph.value(local, EV.status), EV.Observed)
        for scope in (EV.OriginalGeneration, EV.OriginalOrigin):
            claim = next(graph.subjects(EV.scope, scope))
            self.assertEqual(graph.value(claim, EV.status), EV.Unverified)
            self.assertIsNotNone(graph.value(claim, EV.unknownReason))
            for field in (EV.hasEvidence, EV.originalModel, EV.originalPrompt, EV.originalOriginIRI, EV.verifiedAt):
                self.assertIsNone(graph.value(claim, field))
        for path, original in self.initial.items():
            self.assertEqual(path.read_bytes(), original)
        self.assertTrue(evidence.check_project(self.project)["conforms"])

    def test_saved_and_shared_reports_keep_private_details_separate(self):
        report = evidence.refresh_project(self.project)
        private = (self.project / "evidence.json").read_text(encoding="utf-8")
        self.assertIn(self.digest, private)
        public = json.dumps(report)
        for token in (self.digest, "audio01", str(self.root), self.source.as_uri(), "fixture"):
            self.assertNotIn(token, public)
        self.assertEqual(report["claim_count"], 3)

    def test_shared_report_cannot_overwrite_registration_or_source(self):
        report = evidence.refresh_project(self.project)
        for target in (self.project / "manifest.json", self.project / "data.ttl", self.source):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    evidence.write_shared_report(target, report, (self.project, self.source))
        for path, original in self.initial.items():
            self.assertEqual(path.read_bytes(), original)

    def test_saved_graph_metadata_tampering_is_detected_by_its_snapshot_hash(self):
        evidence.refresh_project(self.project)
        graph = self.saved_graph()
        claim = next(graph.subjects(EV.scope, EV.OriginalOrigin))
        graph.set((claim, EV.checkedAt, Literal("2026-10-05T00:00:00Z", datatype=XSD.dateTime)))
        graph.serialize(self.project / "evidence.ttl", format="turtle")
        self.assertTrue(evidence.validate_evidence_graph(graph)[0])
        self.assertFalse(evidence.check_project(self.project)["checks"]["saved_claims_conform"])

    def test_missing_copy_has_no_observed_hash_and_fails_check(self):
        evidence.refresh_project(self.project)
        self.copy.unlink()
        report = evidence.check_project(self.project)
        self.assertFalse(report["conforms"])
        self.assertFalse(report["checks"]["files_conform"])
        refreshed = evidence.refresh_project(self.project)
        self.assertEqual(refreshed["scope_status_counts"]["LocalFileIntegrity"]["Failed"], 1)
        inspection = json.loads((self.project / "evidence.json").read_text(encoding="utf-8"))
        self.assertIsNone(inspection["assets"][0]["copy_sha256"])
        self.assertTrue(evidence.validate_evidence_graph(self.saved_graph())[0])

    def test_tampered_copy_is_detected_and_refresh_does_not_repair_it(self):
        evidence.refresh_project(self.project)
        self.copy.write_bytes(b"changed registered media")
        self.assertFalse(evidence.check_project(self.project)["conforms"])
        report = evidence.refresh_project(self.project)
        self.assertFalse(report["conforms"])
        self.assertEqual(self.copy.read_bytes(), b"changed registered media")
        self.assertEqual(self.source.read_bytes(), self.initial[self.source])

    def test_missing_source_is_reported_without_inventing_origin_or_failing_good_copy(self):
        self.source.unlink()
        report = evidence.refresh_project(self.project)
        self.assertTrue(report["conforms"])
        self.assertEqual(report["source_copy_state_counts"], {"missing": 1})
        graph = self.saved_graph()
        self.assertNotIn(Literal("local-source-copy"), set(graph.objects(None, EV.evidenceRole)))
        self.assertEqual(report["scope_status_counts"]["OriginalOrigin"], {"Unverified": 1})

    def test_changed_source_is_detected_without_rewriting_either_copy(self):
        evidence.refresh_project(self.project)
        self.source.write_bytes(b"source changed independently")
        report = evidence.refresh_project(self.project)
        self.assertFalse(report["conforms"])
        self.assertEqual(report["source_copy_state_counts"], {"mismatch": 1})
        self.assertEqual(self.copy.read_bytes(), self.initial[self.copy])

    def test_manifest_changed_after_baseline_is_detected_and_refresh_refused(self):
        evidence.refresh_project(self.project)
        saved = (self.project / "evidence.ttl").read_bytes()
        self.manifest["new_metadata"] = "review-required"
        (self.project / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        report = evidence.check_project(self.project)
        self.assertFalse(report["checks"]["registration_snapshot_conforms"])
        with self.assertRaisesRegex(ValueError, "Registration inputs changed"):
            evidence.refresh_project(self.project)
        self.assertEqual((self.project / "evidence.ttl").read_bytes(), saved)

    def test_coherent_rewriting_of_manifest_graph_and_bytes_still_breaks_baseline(self):
        evidence.refresh_project(self.project)
        self.copy.write_bytes(b"coherent unauthorized rewrite")
        digest = evidence.file_sha256(self.copy)
        self.manifest["assets"][0]["sha256"] = digest
        self.manifest["assets"][0]["size_bytes"] = self.copy.stat().st_size
        self.manifest["assets"][0].pop("source_file")
        (self.project / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        self.data.set((MV.audio01, MV.checksum, Literal(digest)))
        self.save_data()
        report = evidence.check_project(self.project)
        self.assertTrue(report["checks"]["files_conform"])
        self.assertFalse(report["checks"]["registration_snapshot_conforms"])
        self.assertFalse(report["conforms"])

    def test_graph_manifest_disagreement_and_manifest_omission_are_failures(self):
        self.data.set((MV.audio01, MV.checksum, Literal("0" * 64)))
        self.save_data()
        self.assertFalse(evidence.inspect_project(self.project)["files_conform"])
        self.data.add((MV.omitted, RDF.type, MV.ImageAsset))
        self.save_data()
        inspection = evidence.inspect_project(self.project)
        self.assertEqual(inspection["omitted_graph_assets"], 1)
        self.assertFalse(inspection["files_conform"])

    def test_duplicate_identifier_and_path_traversal_are_rejected(self):
        self.manifest["assets"].append(dict(self.manifest["assets"][0]))
        (self.project / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unique"):
            evidence.inspect_project(self.project)
        self.manifest["assets"].pop()
        self.manifest["assets"][0]["file_name"] = "../../immutable-source.bin"
        (self.project / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "single local filename"):
            evidence.inspect_project(self.project)

    def test_missing_scope_or_changed_evidence_hash_fails_saved_claim_check(self):
        evidence.refresh_project(self.project)
        graph = self.saved_graph()
        record = next(graph.subjects(EV.evidenceRole, Literal("registered-copy")))
        graph.set((record, EV.sha256, Literal("0" * 64)))
        graph.serialize(self.project / "evidence.ttl", format="turtle")
        self.assertFalse(evidence.check_project(self.project)["conforms"])
        evidence.refresh_project(self.project)
        graph = self.saved_graph()
        claim = next(graph.subjects(EV.scope, EV.OriginalOrigin))
        graph.remove((claim, None, None))
        graph.serialize(self.project / "evidence.ttl", format="turtle")
        self.assertFalse(evidence.check_project(self.project)["checks"]["saved_claims_conform"])


class EvidenceConstraintsAndQuestionsTests(unittest.TestCase):
    def fixture(self):
        return Graph().parse(ROOT / "evidence-example.ttl", format="turtle")

    def query(self, number, graph=None):
        source = (ROOT / "EVIDENCE_QUESTIONS.md").read_text(encoding="utf-8")
        queries = re.findall(r"~~~sparql\s*\n(.*?)\n~~~", source, re.S)
        return list((graph if graph is not None else self.fixture()).query(queries[number - 1]))

    def test_synthetic_claims_and_golden_operational_answers(self):
        graph = self.fixture()
        self.assertTrue(evidence.validate_evidence_graph(graph)[0])
        self.assertEqual([str(row.asset) for row in self.query(1, graph)], ["syntheticA", "syntheticB"])
        unknowns = self.query(2, graph)
        self.assertEqual([(str(row.asset), str(row.scope).split("#")[-1]) for row in unknowns],
                         [("syntheticA", "OriginalGeneration"), ("syntheticA", "OriginalOrigin")])
        verified = self.query(3, graph)
        self.assertEqual(len(verified), 2)
        generation = next(row for row in verified if row.scope == EV.OriginalGeneration)
        origin = next(row for row in verified if row.scope == EV.OriginalOrigin)
        self.assertEqual(str(generation.model), "Synthetic fixture model")
        self.assertEqual(str(generation.prompt), "Synthetic fixture prompt")
        self.assertIsNone(generation.origin)
        self.assertEqual(origin.origin, EX["synthetic-original-origin-B"])
        self.assertIsNone(origin.model)

    def test_unknown_original_cannot_carry_invented_model_prompt_or_positive_evidence(self):
        for predicate, value in ((EV.originalModel, Literal("guessed-model")), (EV.originalPrompt, Literal("guessed-prompt")),
                                 (EV.hasEvidence, EX.copyA), (EV.verifiedAt, Literal("2026-10-04T23:00:00Z", datatype=XSD.dateTime))):
            with self.subTest(predicate=predicate):
                graph = self.fixture()
                graph.add((EX.generationA, predicate, value))
                self.assertFalse(evidence.validate_evidence_graph(graph)[0])

    def test_import_copy_evidence_cannot_substitute_for_independently_reviewed_original_evidence(self):
        graph = self.fixture()
        graph.remove((EX.generationB, EV.hasEvidence, None))
        graph.add((EX.generationB, EV.hasEvidence, EX.copyB))
        self.assertFalse(evidence.validate_evidence_graph(graph)[0])
        self.assertEqual([row.scope for row in self.query(3, graph)], [EV.OriginalOrigin])

    def test_scope_status_misuse_and_missing_unknown_reason_fail(self):
        for claim, predicate, value in ((EX.generationA, EV.status, EV.Observed),
                                        (EX.localA, EV.status, EV.Verified),
                                        (EX.originB, EV.originalModel, Literal("misplaced-model"))):
            with self.subTest(claim=claim, predicate=predicate):
                graph = self.fixture()
                graph.set((claim, predicate, value))
                self.assertFalse(evidence.validate_evidence_graph(graph)[0])
        graph = self.fixture()
        graph.remove((EX.originA, EV.unknownReason, None))
        self.assertFalse(evidence.validate_evidence_graph(graph)[0])

    def test_check_time_checker_hash_and_verified_time_constraints(self):
        for subject, predicate in ((EX.localA, EV.checkedAt), (EX.localA, EV.checkedBy), (EX.copyA, EV.sha256),
                                   (EX.generationB, EV.verifiedAt), (EX.generationB, EV.originalPrompt)):
            with self.subTest(subject=subject, predicate=predicate):
                graph = self.fixture()
                graph.remove((subject, predicate, None))
                self.assertFalse(evidence.validate_evidence_graph(graph)[0])
        graph = self.fixture()
        graph.set((EX.generationB, EV.verifiedAt, Literal("2026-10-06T00:00:00Z", datatype=XSD.dateTime)))
        self.assertFalse(evidence.validate_evidence_graph(graph)[0])

    def test_missing_reviewed_document_fails_and_returns_no_verified_answers(self):
        graph = self.fixture()
        graph.remove((EX.reviewB, None, None))
        self.assertEqual(self.query(3, graph), [])
        self.assertFalse(evidence.validate_evidence_graph(graph)[0])

    def test_observed_local_claim_requires_matching_read_copy_and_failures_need_reason(self):
        graph = self.fixture()
        graph.set((EX.copyA, EV.sha256, Literal("0" * 64)))
        self.assertFalse(evidence.validate_evidence_graph(graph)[0])
        graph.set((EX.localA, EV.status, EV.Failed))
        self.assertFalse(evidence.validate_evidence_graph(graph)[0])
        graph.add((EX.localA, EV.unknownReason, Literal("Registered file checksum no longer matches.")))
        self.assertTrue(evidence.validate_evidence_graph(graph)[0])
        self.assertEqual(self.query(1, graph)[0].status, EV.Failed)

    def test_absent_claims_return_no_results_instead_of_invented_unknowns(self):
        for number in (1, 2, 3):
            self.assertEqual(self.query(number, Graph()), [])


if __name__ == "__main__":
    unittest.main()
