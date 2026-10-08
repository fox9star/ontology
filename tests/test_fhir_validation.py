"""Mutation and round-trip checks for the synthetic FHIR exchange contract."""

import copy
from datetime import datetime, timezone
import json
import io
from pathlib import Path
import tempfile
import tarfile
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, RDF, URIRef
from rdflib.namespace import PROV

import fhir_export
import fhir_validate
from fhir_validation import validate_collection_bundle
from healthcare_privacy import HEALTH


def bundle_fixture():
    graph = Graph().parse(fhir_validate.FIXTURE, format="turtle")
    return fhir_export.export_healthcare_bundle(graph, timestamp=datetime(2026, 10, 5, tzinfo=timezone.utc))


def resource(bundle, kind):
    return next(entry["resource"] for entry in bundle["entry"] if entry["resource"]["resourceType"] == kind)


class FhirValidationTests(unittest.TestCase):
    def assert_invalid(self, bundle, text):
        result = validate_collection_bundle(bundle)
        self.assertFalse(result["valid"], result)
        self.assertTrue(any(text in error for error in result["errors"]), result)

    def test_rdf_and_json_roundtrip_retains_values_and_closed_reference_graph(self):
        source = Graph().parse(fhir_validate.FIXTURE, format="turtle")
        restored_graph = Graph().parse(data=source.serialize(format="turtle"), format="turtle")
        bundle = json.loads(json.dumps(fhir_export.export_healthcare_bundle(restored_graph), allow_nan=False))
        self.assertTrue(validate_collection_bundle(bundle)["valid"])
        observation = resource(bundle, "Observation")
        self.assertEqual(observation["code"]["coding"][0], {"system": "http://loinc.org", "code": "29463-7"})
        self.assertEqual(observation["valueQuantity"]["value"], 68.25)
        self.assertEqual(observation["category"][0]["coding"][0]["code"], "vital-signs")
        self.assertEqual(resource(bundle, "Task")["for"], observation["subject"])
        self.assertEqual(resource(bundle, "DiagnosticReport")["subject"], observation["subject"])
        self.assertEqual(len(bundle["entry"]), 4)
        self.assertNotIn("SYNTHETIC-FIXTURE-PRIVATE-KEY", json.dumps(bundle))
        self.assertNotIn(str(HEALTH), json.dumps(bundle))

    def test_reexport_has_no_stable_ids_or_patient_identifiers(self):
        first, second = bundle_fixture(), bundle_fixture()
        self.assertTrue({entry["fullUrl"] for entry in first["entry"]}.isdisjoint({entry["fullUrl"] for entry in second["entry"]}))
        self.assertNotEqual(first["id"], second["id"])

    def test_recursive_references_cover_nested_extensions_and_arrays(self):
        bundle = bundle_fixture()
        resource(bundle, "Patient")["extension"] = [{"url": "urn:fixture:reference", "valueReference": {"reference": "urn:uuid:11111111-1111-4111-8111-111111111111"}}]
        self.assert_invalid(bundle, "extension[0].valueReference.reference")

    def test_relative_references_and_contained_ids_resolve_in_their_own_scope(self):
        bundle = bundle_fixture()
        patient = resource(bundle, "Patient")
        task = resource(bundle, "Task")
        task["for"]["reference"] = "Patient/" + patient["id"]
        task["contained"] = [{"resourceType": "Patient", "id": "local-patient"}]
        task["extension"] = [{"url": "urn:fixture:reference", "valueReference": {"reference": "#local-patient", "type": "Patient"}}]
        self.assertTrue(validate_collection_bundle(bundle)["valid"])
        resource(bundle, "Observation")["subject"]["reference"] = "#local-patient"
        self.assert_invalid(bundle, "unresolved contained")

    def test_external_references_require_opt_in_and_remain_unverified(self):
        bundle = bundle_fixture()
        resource(bundle, "Task")["for"]["reference"] = "https://partner.invalid/Patient/anonymous"
        self.assert_invalid(bundle, "unresolved Bundle")
        result = validate_collection_bundle(bundle, allow_external_references=True)
        self.assertTrue(result["valid"])
        self.assertTrue(result["warnings"])
        self.assertFalse(result["terminology_validated"])

    def test_duplicate_identities_full_urls_and_declared_reference_type_fail(self):
        for mutation, expected in (
            (lambda b: b["entry"].append(copy.deepcopy(b["entry"][0])), "duplicate"),
            (lambda b: resource(b, "Task")["for"].update(type="Observation"), "Reference.type"),
            (lambda b: b["entry"][0].update(fullUrl="urn:uuid:invalid"), "invalid UUID"),
            (lambda b: b["entry"][0]["resource"].update(id="invalid_id"), "id is missing or invalid"),
        ):
            with self.subTest(expected=expected):
                bundle = bundle_fixture()
                mutation(bundle)
                self.assert_invalid(bundle, expected)

    def test_malformed_json_values_fail_without_throwing(self):
        for value in (True, "68.25", None, float("inf"), float("nan"), [], {}):
            with self.subTest(value=value):
                bundle = bundle_fixture()
                resource(bundle, "Observation")["valueQuantity"]["value"] = value
                self.assert_invalid(bundle, "finite JSON number")
        for value in ([], {}, True, None):
            with self.subTest(status=value):
                bundle = bundle_fixture()
                resource(bundle, "Task")["status"] = value
                self.assert_invalid(bundle, "valid status")

    def test_invalid_coding_units_dates_and_multiple_values_fail(self):
        mutations = (
            (lambda b: resource(b, "Observation")["code"]["coding"][0].update(system="loinc.org"), "absolute code system"),
            (lambda b: resource(b, "Observation")["code"]["coding"][0].update(code=" bad "), "requires a code"),
            (lambda b: resource(b, "Observation")["valueQuantity"].pop("system"), "coded unit"),
            (lambda b: resource(b, "Observation").update(effectiveDateTime="2026-02-30T08:00:00Z"), "valid timestamp"),
            (lambda b: resource(b, "Observation").update(valueString="second conflicting value"), "exactly one"),
        )
        for mutation, expected in mutations:
            with self.subTest(expected=expected):
                bundle = bundle_fixture()
                mutation(bundle)
                self.assert_invalid(bundle, expected)

    def test_execution_period_compares_actual_instants_across_offsets(self):
        graph = Graph().parse(fhir_validate.FIXTURE, format="turtle")
        task = HEALTH.FixtureTask
        graph.set((task, PROV.startedAtTime, Literal("2026-10-05T08:00:00+09:00")))
        graph.set((task, PROV.endedAtTime, Literal("2026-10-05T00:00:00Z")))
        bundle = fhir_export.export_healthcare_bundle(graph)
        self.assertIn("executionPeriod", resource(bundle, "Task"))
        self.assertTrue(validate_collection_bundle(bundle)["valid"])
        resource(bundle, "Task")["executionPeriod"] = {"start": "2026-10-05T08:00:00Z", "end": "2026-10-05T08:00:00+09:00"}
        self.assert_invalid(bundle, "ordered timezone-aware")

    def test_observation_of_different_synthetic_subject_is_not_attached_to_task(self):
        graph = Graph().parse(fhir_validate.FIXTURE, format="turtle")
        other = HEALTH.OtherSyntheticPatient
        graph.add((other, RDF.type, HEALTH.PatientRecord))
        graph.add((other, HEALTH.dataClassification, HEALTH.Synthetic))
        graph.set((HEALTH.FixtureObservation, HEALTH.observesRecord, other))
        bundle = fhir_export.export_healthcare_bundle(graph)
        self.assertNotIn("Observation", [entry["resource"]["resourceType"] for entry in bundle["entry"]])
        self.assertTrue(validate_collection_bundle(bundle)["valid"])

    def test_ambiguous_scalar_status_never_defaults_to_unknown(self):
        graph = Graph().parse(fhir_validate.FIXTURE, format="turtle")
        graph.add((HEALTH.FixtureObservation, HEALTH.observationStatus, Literal("preliminary")))
        bundle = fhir_export.export_healthcare_bundle(graph)
        self.assertNotIn("Observation", [entry["resource"]["resourceType"] for entry in bundle["entry"]])

    def test_subject_and_report_result_types_are_part_of_the_export_contract(self):
        bundle = bundle_fixture()
        task_entry = next(entry for entry in bundle["entry"] if entry["resource"]["resourceType"] == "Task")
        resource(bundle, "Observation")["subject"]["reference"] = task_entry["fullUrl"]
        self.assert_invalid(bundle, "requires a Patient")
        bundle = bundle_fixture()
        patient_entry = next(entry for entry in bundle["entry"] if entry["resource"]["resourceType"] == "Patient")
        resource(bundle, "DiagnosticReport")["result"][0]["reference"] = patient_entry["fullUrl"]
        self.assert_invalid(bundle, "requires an Observation")

    def test_empty_bundle_omits_entry_and_naive_export_timestamp_is_rejected(self):
        bundle = fhir_export.export_healthcare_bundle(Graph())
        self.assertNotIn("entry", bundle)
        self.assertTrue(validate_collection_bundle(bundle)["valid"])
        with self.assertRaises(ValueError):
            fhir_export.export_healthcare_bundle(Graph(), timestamp=datetime(2026, 10, 5))

    def test_body_weight_profile_requires_category_effective_time_and_ucum_units(self):
        bundle = bundle_fixture()
        resource(bundle, "Observation").pop("category")
        self.assert_invalid(bundle, "requires the vital-signs category")
        for predicate, replacement in ((HEALTH.observedAt, None), (HEALTH.unitCode, Literal("cm"))):
            with self.subTest(predicate=predicate):
                graph = Graph().parse(fhir_validate.FIXTURE, format="turtle")
                graph.remove((HEALTH.FixtureObservation, predicate, None))
                if replacement is not None:
                    graph.add((HEALTH.FixtureObservation, predicate, replacement))
                exported = fhir_export.export_healthcare_bundle(graph)
                self.assertNotIn("Observation", [entry["resource"]["resourceType"] for entry in exported["entry"]])

    def test_unrepresentable_decimal_does_not_silently_round(self):
        graph = Graph().parse(fhir_validate.FIXTURE, format="turtle")
        graph.set((HEALTH.FixtureObservation, HEALTH.numericValue, Literal("0.123456789012345678901", datatype=URIRef("http://www.w3.org/2001/XMLSchema#decimal"))))
        bundle = fhir_export.export_healthcare_bundle(graph)
        self.assertNotIn("Observation", [entry["resource"]["resourceType"] for entry in bundle["entry"]])


class OfficialValidatorControlTests(unittest.TestCase):
    def test_archive_extraction_is_bounded_and_cached_definition_tampering_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path, cache = root / "package.tgz", root / "cache"
            contents = {"package/package.json": b'{"name":"fixture.package","version":"1.0.0"}', "package/StructureDefinition-fixture.json": b'{"resourceType":"StructureDefinition"}'}
            with tarfile.open(archive_path, "w:gz") as archive:
                for name, data in contents.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            fhir_validate._extract_package(archive_path, cache)
            self.assertTrue(fhir_validate._verify_package_files(archive_path, cache))
            (cache / "package/StructureDefinition-fixture.json").write_text("{}")
            self.assertFalse(fhir_validate._verify_package_files(archive_path, cache))
            with tarfile.open(root / "unsafe.tgz", "w:gz") as archive:
                member = tarfile.TarInfo("package/../../escaped.json")
                member.size = 2
                archive.addfile(member, io.BytesIO(b"{}"))
            with self.assertRaises(ValueError):
                fhir_validate._extract_package(root / "unsafe.tgz", cache)
            self.assertFalse((root / "escaped.json").exists())

    def test_bad_jar_checksum_is_blocked_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "validator.jar"
            jar.write_bytes(b"wrong jar")
            result = fhir_validate.prepare_validator({"validator_sha256": "0" * 64}, jar)
            self.assertEqual(result["status"], "blocked")

    def test_missing_requested_validator_is_skipped_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("builtins.print"):
                exit_code = fhir_validate.main(["--synthetic-fixture", "--official", "structural", "--validator-jar", str(Path(directory) / "absent.jar"), "--output-dir", directory])
            report = json.loads((Path(directory) / "validation-report.json").read_text())
            self.assertEqual(exit_code, 3)
            self.assertEqual(report["status"], "skipped")

    def test_timeout_is_failed_and_cannot_reuse_stale_success_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jar = root / "validator.jar"
            jar.write_bytes(b"test-control-only")
            bundle = root / "bundle.json"
            bundle.write_text(json.dumps(bundle_fixture()))
            stale = root / "structural-outcome.json"
            stale.write_text('{"resourceType":"OperationOutcome","issue":[{"severity":"success","code":"informational"}]}')
            config = json.loads((fhir_validate.ROOT / "fhir-validator-config.json").read_text())
            with patch("fhir_validate.subprocess.run", side_effect=[__import__("subprocess").CompletedProcess([], 0, "java 21", ""), __import__("subprocess").TimeoutExpired([], 1)]):
                result = fhir_validate.run_official(config, bundle, root, java="java", jar=jar, mode="structural", timeout=1)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
