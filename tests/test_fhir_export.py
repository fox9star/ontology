"""Privacy and mapping tests for the constrained FHIR R5 export."""

import json
import sys
import unittest
from datetime import datetime, timezone

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as studio
import fhir_export
from healthcare_privacy import HEALTH

RDFS_LABEL = URIRef("http://www.w3.org/2000/01/rdf-schema#label")


def synthetic_clinical_graph(include_report_coding=True):
    graph = Graph()
    patient = HEALTH.SyntheticPatient
    task = HEALTH.SyntheticTask
    observation = HEALTH.SyntheticObservation
    report = HEALTH.SyntheticReport
    graph.add((patient, RDF.type, HEALTH.PatientRecord))
    graph.add((patient, HEALTH.patientId, Literal("PRIVATE-TEST-KEY")))
    graph.add((patient, HEALTH.dataClassification, HEALTH.Synthetic))
    graph.add((patient, RDFS_LABEL, Literal("Synthetic test subject")))
    graph.add((task, RDF.type, HEALTH.DiagnosticTask))
    graph.add((task, HEALTH.associatedWithRecord, patient))
    graph.add((task, HEALTH.diagnosticStatus, Literal("VERIFIED")))
    graph.add((task, PROV.startedAtTime, Literal("2026-10-05T08:00:00Z", datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime"))))
    graph.add((task, PROV.endedAtTime, Literal("2026-10-05T08:01:00Z", datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime"))))
    graph.add((task, HEALTH.generatesObservation, observation))
    graph.add((task, HEALTH.generatesReport, report))
    graph.add((observation, RDF.type, HEALTH.ClinicalObservation))
    graph.add((observation, HEALTH.observesRecord, patient))
    graph.add((observation, HEALTH.codeSystem, URIRef("https://loinc.org")))
    graph.add((observation, HEALTH.observationCode, Literal("29463-7")))
    graph.add((observation, HEALTH.observedAt, Literal("2026-10-05T08:00:00Z", datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime"))))
    graph.add((observation, HEALTH.numericValue, Literal("68.25", datatype=URIRef("http://www.w3.org/2001/XMLSchema#decimal"))))
    graph.add((observation, HEALTH.unitCode, Literal("kg")))
    graph.add((observation, HEALTH.unitCodeSystem, URIRef("http://unitsofmeasure.org")))
    graph.add((observation, PROV.wasGeneratedBy, task))
    graph.add((report, RDF.type, HEALTH.ClinicalReport))
    graph.add((report, HEALTH.findingText, Literal("Synthetic report finding")))
    if include_report_coding:
        graph.add((report, HEALTH.reportStatus, Literal("final")))
        graph.add((report, HEALTH.reportCodeSystem, URIRef("https://loinc.org")))
        graph.add((report, HEALTH.reportCode, Literal("18725-2")))
        graph.add((report, HEALTH.reportResult, observation))
    return graph


class FhirExportTests(unittest.TestCase):
    def test_api_returns_safe_fhir_r5_collection_bundle(self):
        response = studio.app.test_client().get("/api/v1/healthcare/fhir-bundle")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/fhir+json")
        self.assertEqual(response.headers["X-FHIR-Version"], "5.0.0")
        self.assertEqual(response.headers["X-Privacy-Redaction"], "synthetic-only-no-patient-key")
        bundle = response.get_json()
        self.assertEqual((bundle["resourceType"], bundle["type"]), ("Bundle", "collection"))
        payload = response.get_data(as_text=True)
        self.assertNotIn("PRIVATE-TEST-KEY", payload)
        self.assertNotIn("PATIENT-9081", payload)

    def test_synthetic_patient_task_observation_and_report_map_without_local_keys(self):
        bundle = fhir_export.export_healthcare_bundle(
            synthetic_clinical_graph(), timestamp=datetime(2026, 10, 5, tzinfo=timezone.utc)
        )
        self.assertTrue(fhir_export.validate_collection_bundle(bundle)["valid"])
        resources = {entry["resource"]["resourceType"]: entry["resource"]
                     for entry in bundle["entry"]}
        self.assertEqual(set(resources), {"Patient", "Task", "Observation", "DiagnosticReport"})
        self.assertEqual(resources["Task"]["intent"], "unknown")
        self.assertEqual(resources["Task"]["status"], "completed")
        self.assertEqual(resources["Task"]["businessStatus"]["text"], "VERIFIED")
        self.assertEqual(resources["Observation"]["status"], "unknown")
        self.assertEqual(resources["Observation"]["valueQuantity"], {
            "value": 68.25, "unit": "kg", "system": "http://unitsofmeasure.org", "code": "kg"
        })
        self.assertEqual(resources["DiagnosticReport"]["status"], "final")
        self.assertEqual(resources["DiagnosticReport"]["result"][0]["reference"],
                         next(entry["fullUrl"] for entry in bundle["entry"]
                              if entry["resource"]["resourceType"] == "Observation"))
        self.assertNotIn("PRIVATE-TEST-KEY", json.dumps(bundle))
        self.assertNotIn(str(HEALTH.SyntheticPatient), json.dumps(bundle))

    def test_report_without_required_fhir_code_and_status_is_omitted_with_generic_outcome(self):
        bundle = fhir_export.export_healthcare_bundle(synthetic_clinical_graph(include_report_coding=False))
        types = [entry["resource"]["resourceType"] for entry in bundle["entry"]]
        self.assertNotIn("DiagnosticReport", types)
        outcome = next(entry["resource"] for entry in bundle["entry"]
                       if entry["resource"]["resourceType"] == "OperationOutcome")
        self.assertEqual(outcome["issue"][0]["severity"], "warning")
        self.assertNotIn("Synthetic report finding", json.dumps(outcome))
        self.assertTrue(fhir_export.validate_collection_bundle(bundle)["valid"])

    def test_non_synthetic_patient_and_linked_results_are_never_exported(self):
        graph = synthetic_clinical_graph()
        graph.set((HEALTH.SyntheticPatient, HEALTH.dataClassification, HEALTH.Sensitive))
        bundle = fhir_export.export_healthcare_bundle(graph)
        self.assertEqual(bundle.get("entry", []), [])
        self.assertNotIn("entry", bundle)  # FHIR omits empty JSON arrays.


if __name__ == "__main__":
    unittest.main()
