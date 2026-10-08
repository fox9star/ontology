"""FHIR-to-local semantic round trips, conservative trust, and source fidelity."""

import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, RDF
from rdflib.namespace import PROV

import fhir_export
import fhir_import
from healthcare_privacy import HEALTH, redact_graph
from fhir_validation import validate_collection_bundle


def fixture_bundle():
    return fhir_export.export_healthcare_bundle(Graph().parse(fhir_import.FIXTURE, format="turtle"))


def resource(bundle, kind):
    return next(entry["resource"] for entry in bundle["entry"] if entry["resource"]["resourceType"] == kind)


def signature(graph, include_text=True):
    """Compare supported facts and relationships independent of opaque URIs."""
    classes = [HEALTH.PatientRecord, HEALTH.DiagnosticTask, HEALTH.ClinicalObservation, HEALTH.ClinicalReport]
    roles = {subject: str(kind).split("#")[-1] for kind in classes for subject in graph.subjects(RDF.type, kind)}
    ignored = {RDF.type, HEALTH.patientId, HEALTH.dataClassification}
    if not include_text:
        ignored.add(HEALTH.findingText)
    facts = []
    for subject, predicate, value in graph:
        if subject not in roles or predicate in ignored:
            continue
        actual = roles.get(value, str(value))
        if predicate == HEALTH.numericValue:
            actual = str(Decimal(str(value)).normalize())
        if predicate in {HEALTH.observedAt, PROV.startedAtTime, PROV.endedAtTime}:
            actual = __import__("datetime").datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
        facts.append((roles[subject], str(predicate), actual))
    return sorted(facts)


class FhirImportTests(unittest.TestCase):
    def test_local_fhir_local_roundtrip_preserves_numeric_time_code_status_and_relations(self):
        graph = Graph().parse(fhir_import.FIXTURE, format="turtle")
        exported = json.loads(json.dumps(fhir_export.export_healthcare_bundle(graph)))
        result = fhir_import.import_bundle(exported)
        self.assertEqual(signature(graph, False), signature(result.graph, False))
        self.assertEqual(result.report["data_classification"], "Unverified")
        self.assertEqual(result.report["source_origin"], "unknown-local-input")
        self.assertFalse(result.report["network_access"])
        self.assertFalse(result.report["terminology_validated"])
        self.assertFalse(result.report["complete_clinical_import"])
        self.assertEqual(len(redact_graph(result.graph)), 0)
        self.assertEqual(fhir_export.export_healthcare_bundle(result.graph).get("entry", []), [])

    def test_only_pinned_fixture_is_synthetic_and_reexports_supported_semantics(self):
        original = Graph().parse(fhir_import.FIXTURE, format="turtle")
        result = fhir_import.import_synthetic_fixture()
        self.assertEqual(signature(original), signature(result.graph))
        self.assertEqual(result.report["data_classification"], "Synthetic")
        bundle = fhir_export.export_healthcare_bundle(result.graph)
        self.assertTrue(validate_collection_bundle(bundle)["valid"])
        self.assertEqual(len(bundle["entry"]), 4)
        self.assertEqual(resource(bundle, "Observation")["valueQuantity"]["value"], 68.25)
        second = fhir_import.import_bundle(bundle)
        self.assertEqual(signature(result.graph, False), signature(second.graph, False))
        self.assertEqual(second.report["data_classification"], "Unverified")

    def test_altered_fixture_cannot_obtain_trust(self):
        with patch.object(Path, "read_bytes", return_value=b"untrusted fixture bytes"):
            with self.assertRaisesRegex(fhir_import.ImportRejected, "checksum"):
                fhir_import.import_synthetic_fixture()

    def test_input_labels_and_security_assertions_never_grant_synthetic_trust(self):
        bundle = fixture_bundle()
        patient = resource(bundle, "Patient")
        patient["meta"] = {"security": [{"system": "urn:local:classification", "code": "Synthetic"}]}
        patient["extension"] = [{"url": "urn:local:classification", "valueString": "Synthetic"}]
        result = fhir_import.import_bundle(bundle)
        self.assertEqual(set(result.graph.objects(None, HEALTH.dataClassification)), {HEALTH.Unverified})

    def test_identity_and_free_text_never_enter_arbitrary_import_rdf_or_report(self):
        bundle = fixture_bundle()
        patient = resource(bundle, "Patient")
        patient["name"] = [{"text": "IDENTITY-SENTINEL"}]
        patient["identifier"] = [{"system": "urn:identity:registry", "value": "DIRECT-ID-SENTINEL"}]
        patient["IDENTITY-FIELD-SENTINEL"] = "PRIVATE-CUSTOM-DATA"
        resource(bundle, "DiagnosticReport")["conclusion"] = "IDENTITY-SENTINEL reported DIRECT-ID-SENTINEL"
        observation = resource(bundle, "Observation")
        observation["code"]["coding"][0]["code"] = "1234-5"
        observation.pop("valueQuantity")
        observation["valueString"] = "IDENTITY-SENTINEL"
        result = fhir_import.import_bundle(bundle)
        visible = result.graph.serialize(format="turtle") + json.dumps(result.report)
        for value in ["IDENTITY-SENTINEL", "DIRECT-ID-SENTINEL", "IDENTITY-FIELD-SENTINEL", "PRIVATE-CUSTOM-DATA", patient["id"]]:
            self.assertNotIn(value, visible)
        self.assertIn(b"DIRECT-ID-SENTINEL", result.source_bytes)
        self.assertNotIn(HEALTH.patientId, set(result.graph.predicates()))
        self.assertNotIn(HEALTH.textValue, set(result.graph.predicates()))
        self.assertNotIn(HEALTH.findingText, set(result.graph.predicates()))
        self.assertTrue(any(change["action"] == "withheld-unverified-free-text" for change in result.report["changes"]))

    def test_exact_source_bytes_unknown_fields_and_identity_map_are_restricted_sidecars(self):
        bundle = fixture_bundle()
        patient = resource(bundle, "Patient")
        patient["birthDate"] = "2000-01-01"
        patient["name"] = [{"text": "SOURCE-ONLY-SENTINEL"}]
        raw = ("\ufeff" + json.dumps(bundle, indent=4) + "\n\n").encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            source.write_bytes(raw)
            result = fhir_import.import_file(source)
            output = Path(directory) / "new-import"
            report = fhir_import.write_import(result, output)
            self.assertEqual((output / "protected/source-bundle.json").read_bytes(), raw)
            self.assertEqual(report["source_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(Graph().parse(output / "healthcare-import.ttl", format="turtle").__len__(), len(result.graph))
            restored = json.loads((output / "protected/source-bundle.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(restored, bundle)
            self.assertIn(patient["id"], (output / "protected/mapping.json").read_text())
            self.assertNotIn("SOURCE-ONLY-SENTINEL", (output / "import-report.json").read_text())
            if os.name == "nt":
                self.assertEqual(report["storage_protection"], "windows-account-and-system-only-acl")
            else:
                self.assertEqual((output / "protected/source-bundle.json").stat().st_mode & 0o777, 0o600)

    def test_existing_output_never_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing-patient-dataset"
            output.mkdir()
            marker = output / "marker.ttl"
            marker.write_text("preserved original")
            with self.assertRaisesRegex(fhir_import.ImportRejected, "new directory"):
                fhir_import.write_import(fhir_import.import_bundle(fixture_bundle()), output)
            self.assertEqual(marker.read_text(), "preserved original")
            self.assertEqual(list(output.iterdir()), [marker])

    def test_storage_protection_failure_does_not_publish_raw_data(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-import"
            with patch("fhir_import._protect", side_effect=fhir_import.ImportRejected("Restricted storage unavailable.")):
                with self.assertRaises(fhir_import.ImportRejected):
                    fhir_import.write_import(fhir_import.import_bundle(fixture_bundle()), output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_relative_references_preserve_relationships(self):
        bundle = fixture_bundle()
        aliases = {entry["fullUrl"]: entry["resource"]["resourceType"] + "/" + entry["resource"]["id"] for entry in bundle["entry"]}
        def walk(value):
            if isinstance(value, dict):
                if "reference" in value:
                    value["reference"] = aliases[value["reference"]]
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        original = fhir_import.import_bundle(bundle)
        walk(bundle)
        self.assertEqual(signature(original.graph), signature(fhir_import.import_bundle(bundle).graph))

    def test_rejects_wrong_reference_type_unresolved_and_external_refs(self):
        for change in [lambda b: resource(b, "Task")["for"].update(reference="Patient/missing"),
                       lambda b: resource(b, "Task")["for"].update(reference="https://partner.invalid/Patient/123"),
                       lambda b: resource(b, "Task")["for"].update(type="Observation")]:
            with self.subTest(change=change):
                bundle = fixture_bundle()
                change(bundle)
                with self.assertRaises(fhir_import.ImportRejected):
                    fhir_import.import_bundle(bundle)

    def test_task_and_report_cross_subject_outputs_are_rejected(self):
        for kind in ["Observation", "DiagnosticReport"]:
            bundle = fixture_bundle()
            patient = copy.deepcopy(bundle["entry"][0])
            patient["fullUrl"] = "urn:uuid:11111111-1111-4111-8111-111111111111"
            patient["resource"]["id"] = "11111111-1111-4111-8111-111111111111"
            bundle["entry"].append(patient)
            resource(bundle, kind)["subject"]["reference"] = patient["fullUrl"]
            if kind == "Observation":
                resource(bundle, "DiagnosticReport").pop("result")
            with self.assertRaises(fhir_import.ImportRejected):
                fhir_import.import_bundle(bundle)

    def test_duplicate_coding_and_multiple_value_choices_are_rejected(self):
        for change in [lambda b: resource(b, "Observation")["code"]["coding"].append({"system": "http://loinc.org", "code": "3141-9"}),
                       lambda b: resource(b, "Observation").update(valueString="duplicate choice"),
                       lambda b: resource(b, "Observation")["code"]["coding"][0].update(code=" bad code")]:
            with self.subTest(change=change):
                bundle = fixture_bundle()
                change(bundle)
                with self.assertRaises(fhir_import.ImportRejected):
                    fhir_import.import_bundle(bundle)

    def test_multi_owner_and_missing_task_output_associations_are_rejected(self):
        for change in [lambda task: task["output"].append(copy.deepcopy(task["output"][0])), lambda task: task.pop("output")]:
            bundle = fixture_bundle()
            change(resource(bundle, "Task"))
            with self.assertRaisesRegex(fhir_import.ImportRejected, "Task output association"):
                fhir_import.import_bundle(bundle)

    def test_valid_but_unmapped_task_status_is_retained_without_fabricated_local_state(self):
        bundle = fixture_bundle()
        resource(bundle, "Task")["status"] = "on-hold"
        result = fhir_import.import_bundle(bundle)
        self.assertEqual(list(result.graph.objects(None, HEALTH.diagnosticStatus)), [])
        self.assertIn(b"on-hold", result.source_bytes)
        self.assertTrue(any(change["action"] == "sidecar-only-no-equivalent-local-status" for change in result.report["changes"]))

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            for value in [b'{"resourceType":"Bundle","resourceType":"Patient"}', b'{"value":NaN}']:
                source.write_bytes(value)
                with self.assertRaises(fhir_import.ImportRejected):
                    fhir_import.import_file(source)

    def test_no_network_is_called_for_local_import(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected network access")):
            self.assertEqual(fhir_import.import_bundle(fixture_bundle()).report["status"], "imported")


if __name__ == "__main__":
    unittest.main()
