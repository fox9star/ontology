"""Bounded, local-only FHIR R5 collection import with protected source retention.

Arbitrary inputs are Unverified. Only the pinned constructed fixture can be
Synthetic. This is an ingestion graph, not a complete clinical record model.
"""

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from rdflib import Graph, Literal, RDF, URIRef
from rdflib.namespace import PROV, XSD

from fhir_export import export_healthcare_bundle
from fhir_validation import validate_collection_bundle
from healthcare_privacy import HEALTH

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "tests" / "fixtures" / "fhir" / "synthetic-clinical.ttl"
FIXTURE_SHA256 = "785fbf4b033bea94310355c2fd803311ac947b7d371466f3a3dd82807ce90166"
MAX_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 10000
LOCAL_STATUSES = {
    "requested": "PENDING", "in-progress": "ANALYZING", "completed": "COMPLETED",
    "failed": "FAILED", "cancelled": "CANCELLED",
}
KINDS = {"Patient", "Task", "Observation", "DiagnosticReport", "OperationOutcome"}
KNOWN_FIELDS = {
    "Patient": {"resourceType", "id"},
    "Task": {"resourceType", "id", "status", "intent", "for", "executionPeriod", "output", "businessStatus"},
    "Observation": {"resourceType", "id", "status", "code", "subject", "effectiveDateTime", "valueQuantity", "valueString", "category"},
    "DiagnosticReport": {"resourceType", "id", "status", "code", "subject", "result", "conclusion"},
    "OperationOutcome": {"resourceType", "id"},
}


class ImportRejected(ValueError):
    """A generic rejection safe to expose without reproducing source values."""


@dataclass
class ImportResult:
    graph: Graph
    report: dict
    source_bytes: bytes
    # Original resource identity -> fresh local URI. Only written in the
    # protected sidecar; never exposed in the report or RDF.
    identity_map: dict


def _json(raw):
    if len(raw) > MAX_BYTES:
        raise ImportRejected("Input exceeds the local import size limit.")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ImportRejected("Duplicate JSON object fields are unsupported.")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ImportRejected("Nonfinite JSON numbers are unsupported.")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ImportRejected("Input is not a supported JSON document.") from exc


def _source(bundle):
    try:
        raw = json.dumps(bundle, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise ImportRejected("Input is not a supported JSON document.") from exc
    return raw


def import_bundle(bundle):
    """Import arbitrary JSON data as Unverified; there is no trust argument."""
    raw = _source(bundle)
    return _import(_json(raw), raw, trusted=False)


def import_file(path):
    """Read one local file without fetching any references or terminology."""
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ImportRejected("Input exceeds the local import size limit.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    return _import(_json(raw), raw, trusted=False)


def import_synthetic_fixture():
    """Only this exact constructed repository fixture obtains Synthetic trust."""
    raw = FIXTURE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ImportRejected("The constructed fixture checksum changed; synthetic trust is blocked.")
    source = Graph().parse(data=raw.decode("utf-8"), format="turtle")
    bundle = export_healthcare_bundle(source, timestamp=datetime(2026, 10, 5, tzinfo=timezone.utc))
    return _import(bundle, _source(bundle), trusted=True)


def _import(bundle, raw, *, trusted):
    if not isinstance(bundle, dict) or not isinstance(bundle.get("entry", []), list):
        raise ImportRejected("Expected a supported collection Bundle.")
    if len(bundle.get("entry", [])) > MAX_ENTRIES:
        raise ImportRejected("Input exceeds the local resource count limit.")
    try:
        checked = validate_collection_bundle(bundle)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ImportRejected("Input is outside the bounded local FHIR contract.") from exc
    if not checked["valid"]:
        # Validator paths can contain untrusted unknown field names. Keep their
        # contents in raw source only; public diagnostics are intentionally fixed.
        raise ImportRejected("Input failed the bounded local FHIR structure/reference/code checks.")
    resources, aliases = [], {}
    for index, entry in enumerate(bundle.get("entry", [])):
        resource = entry["resource"]
        resources.append(resource)
        aliases[entry["fullUrl"]] = index
        aliases[resource["resourceType"] + "/" + resource["id"]] = index
        if "contained" in resource:
            raise ImportRejected("Contained resources are outside the local import mapping.")

    def target(reference, kind):
        value = reference.get("reference") if isinstance(reference, dict) else None
        index = aliases.get(value) if isinstance(value, str) else None
        if index is None or resources[index]["resourceType"] != kind:
            raise ImportRejected("A mapped reference is missing or has the wrong resource type.")
        return index

    subjects = {}
    for index, resource in enumerate(resources):
        kind = resource["resourceType"]
        if kind in {"Task", "Observation", "DiagnosticReport"}:
            subjects[index] = target(resource["for" if kind == "Task" else "subject"], "Patient")
        if kind in {"Observation", "DiagnosticReport"} and len(resource["code"]["coding"]) != 1:
            raise ImportRejected("The local model requires exactly one coding per clinical code.")

    owners = {}
    for task_index, resource in enumerate(resources):
        if resource["resourceType"] != "Task":
            continue
        outputs = resource.get("output", [])
        if not isinstance(outputs, list):
            raise ImportRejected("Task output must be an array.")
        for output in outputs:
            if not isinstance(output, dict):
                raise ImportRejected("Task output must contain typed reference objects.")
            reference = output.get("valueReference")
            if reference is None:
                # Other output choices remain in raw source only.
                continue
            ref = reference.get("reference") if isinstance(reference, dict) else None
            child_index = aliases.get(ref) if isinstance(ref, str) else None
            if child_index is None or resources[child_index]["resourceType"] not in {"Observation", "DiagnosticReport"}:
                raise ImportRejected("A Task output reference has an unsupported target.")
            if subjects[child_index] != subjects[task_index]:
                raise ImportRejected("A Task output belongs to a different subject.")
            if child_index in owners:
                raise ImportRejected("A clinical result must have exactly one Task output association.")
            owners[child_index] = task_index
    for index, resource in enumerate(resources):
        if resource["resourceType"] in {"Observation", "DiagnosticReport"} and index not in owners:
            raise ImportRejected("A clinical result requires an explicit Task output association.")

    graph = Graph()
    graph.bind("health", HEALTH)
    graph.bind("prov", PROV)
    uris = {index: URIRef("urn:uuid:" + str(uuid.uuid4())) for index, resource in enumerate(resources)
            if resource["resourceType"] != "OperationOutcome"}
    classes = {"Patient": HEALTH.PatientRecord, "Task": HEALTH.DiagnosticTask,
               "Observation": HEALTH.ClinicalObservation, "DiagnosticReport": HEALTH.ClinicalReport}
    changes = []
    def note(index, field, action):
        changes.append({"entry": index, "resource_type": resources[index]["resourceType"],
                        "field": field, "action": action, "retained_in_raw_sidecar": True})
    def literal(index, predicate, value, datatype=XSD.string):
        graph.add((uris[index], predicate, Literal(value, datatype=datatype)))
    def extras(index, value, allowed, prefix):
        if isinstance(value, dict) and any(key not in allowed for key in value):
            # No unknown key names or values enter the sanitized report.
            note(index, prefix + ".<unmapped-field>", "sidecar-only")
    for index, resource in enumerate(resources):
        kind = resource["resourceType"]
        note(index, "id/fullUrl", "replaced-with-fresh-local-uri")
        extras(index, resource, KNOWN_FIELDS[kind], "resource")
        if kind == "OperationOutcome":
            note(index, "issue", "sidecar-only")
            continue
        graph.add((uris[index], RDF.type, classes[kind]))
        if kind == "Patient":
            graph.add((uris[index], HEALTH.dataClassification, HEALTH.Synthetic if trusted else HEALTH.Unverified))
            continue
        if kind == "Task":
            graph.add((uris[index], HEALTH.associatedWithRecord, uris[subjects[index]]))
            status = LOCAL_STATUSES.get(resource["status"])
            business = resource.get("businessStatus")
            if resource["status"] == "completed" and isinstance(business, dict) and business.get("text") == "VERIFIED":
                status = "VERIFIED"
            if status is None:
                note(index, "status", "sidecar-only-no-equivalent-local-status")
            else:
                literal(index, HEALTH.diagnosticStatus, status)
            literal(index, HEALTH.taskIntent, resource["intent"])
            period = resource.get("executionPeriod")
            if period:
                literal(index, PROV.startedAtTime, period["start"], XSD.dateTime)
                literal(index, PROV.endedAtTime, period["end"], XSD.dateTime)
                extras(index, period, {"start", "end"}, "executionPeriod")
            if "businessStatus" in resource:
                note(index, "businessStatus", "verified-state-only-remaining-content-in-sidecar")
            for output in resource.get("output", []):
                extras(index, output, {"type", "valueReference"}, "output")
                note(index, "output.type", "sidecar-only")
        else:
            coding = resource["code"]["coding"][0]
            extras(index, resource["code"], {"coding"}, "code")
            extras(index, coding, {"system", "code"}, "code.coding")
            if kind == "Observation":
                graph.add((uris[index], HEALTH.observesRecord, uris[subjects[index]]))
                graph.add((uris[index], PROV.wasGeneratedBy, uris[owners[index]]))
                graph.add((uris[owners[index]], HEALTH.generatesObservation, uris[index]))
                graph.add((uris[index], HEALTH.codeSystem, URIRef(coding["system"])))
                literal(index, HEALTH.observationCode, coding["code"])
                literal(index, HEALTH.observationStatus, resource["status"])
                if "effectiveDateTime" in resource:
                    literal(index, HEALTH.observedAt, resource["effectiveDateTime"], XSD.dateTime)
                if "valueQuantity" in resource:
                    quantity = resource["valueQuantity"]
                    literal(index, HEALTH.numericValue, str(Decimal(str(quantity["value"]))), XSD.decimal)
                    literal(index, HEALTH.unitCode, quantity["code"])
                    graph.add((uris[index], HEALTH.unitCodeSystem, URIRef(quantity["system"])))
                    if quantity.get("unit") != quantity["code"]:
                        note(index, "valueQuantity.unit", "display-sidecar-only-code-preserved")
                    extras(index, quantity, {"value", "unit", "system", "code"}, "valueQuantity")
                elif trusted:
                    literal(index, HEALTH.textValue, resource["valueString"])
                else:
                    note(index, "valueString", "withheld-unverified-free-text")
                if "category" in resource:
                    note(index, "category", "sidecar-only-exporter-reconstructs-known-bodyweight-category")
            else:
                graph.add((uris[owners[index]], HEALTH.generatesReport, uris[index]))
                literal(index, HEALTH.reportStatus, resource["status"])
                graph.add((uris[index], HEALTH.reportCodeSystem, URIRef(coding["system"])))
                literal(index, HEALTH.reportCode, coding["code"])
                if "conclusion" in resource:
                    if trusted and isinstance(resource["conclusion"], str):
                        literal(index, HEALTH.findingText, resource["conclusion"])
                    else:
                        note(index, "conclusion", "withheld-unverified-free-text")
                for reference in resource.get("result", []):
                    child = target(reference, "Observation")
                    if subjects[child] != subjects[index]:
                        raise ImportRejected("A report result belongs to a different subject.")
                    graph.add((uris[index], HEALTH.reportResult, uris[child]))
                    extras(index, reference, {"reference", "type"}, "result")
        extras(index, resource.get("for" if kind == "Task" else "subject"), {"reference", "type"}, "subject-reference")
    counts = {kind: sum(item["resourceType"] == kind for item in resources) for kind in sorted(KINDS)}
    report = {
        "status": "imported", "scope": "bounded-local-fhir-r5-ingestion", "fhir_version": "5.0.0",
        "data_classification": "Synthetic" if trusted else "Unverified",
        "source_origin": "pinned-constructed-fixture" if trusted else "unknown-local-input",
        "source_sha256": hashlib.sha256(raw).hexdigest(), "source_bytes": len(raw),
        "resource_counts": counts, "rdf_triples": len(graph), "network_access": False,
        "terminology_validated": False, "complete_clinical_import": False,
        "lossless_rdf_mapping": False, "changes": changes,
        "studio_shape_gaps": ["Patient display label and internal patient key are not imported.",
                               "Analysis agent and model confidence are not fabricated.",
                               "Unverified free text and unsupported fields remain only in the restricted source sidecar."],
        "source_restore": "protected/source-bundle.json is the exact original input; mapping.json is restricted.",
    }
    identities = {entry["fullUrl"]: str(uris[index]) for index, entry in enumerate(bundle.get("entry", [])) if index in uris}
    identities.update({resource["resourceType"] + "/" + resource["id"]: str(uris[index]) for index, resource in enumerate(resources) if index in uris})
    return ImportResult(graph, report, raw, identities)


def _protect(directory):
    """Restrict the empty staging directory before writing any source data."""
    if os.name != "nt":
        directory.chmod(0o700)
        return "owner-only-posix-mode"
    user = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=15, check=True)
    sid = next(csv.reader(io.StringIO(user.stdout.strip())))[-1]
    if not sid.startswith("S-1-") or not all(part.isdigit() for part in sid[2:].split("-")):
        raise ImportRejected("The Windows account SID could not be verified.")
    subprocess.run(["icacls", str(directory), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"],
                   capture_output=True, timeout=15, check=True)
    return "windows-account-and-system-only-acl"


def write_import(result, output_dir):
    """Publish one complete restricted directory atomically; never overwrite."""
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise ImportRejected("Import output must be a new directory.")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".fhir-import-", dir=output_dir.parent))
    try:
        protection = _protect(stage)
        protected = stage / "protected"
        protected.mkdir(mode=0o700)
        (protected / "source-bundle.json").write_bytes(result.source_bytes)
        (protected / "mapping.json").write_text(json.dumps(result.identity_map, indent=2) + "\n", encoding="utf-8")
        result.graph.serialize(destination=stage / "healthcare-import.ttl", format="turtle")
        report = dict(result.report, storage_protection=protection)
        (stage / "import-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if os.name != "nt":
            for path in stage.rglob("*"):
                if path.is_file():
                    path.chmod(0o600)
        # On Windows rename refuses an existing destination. On POSIX the
        # nonempty destination published by another importer also cannot be
        # replaced. Explicitly reject a preexisting (even empty) directory.
        if output_dir.exists():
            raise ImportRejected("Import output must be a new directory.")
        stage.rename(output_dir)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bundle", type=Path, help="Import a local collection as Unverified; no remote validation.")
    source.add_argument("--synthetic-fixture", action="store_true", help="Import only the checksum-pinned constructed repository fixture.")
    parser.add_argument("--output-dir", type=Path, help="New directory beneath .runtime/fhir-imports; never an existing project.")
    args = parser.parse_args(argv)
    output = (args.output_dir or ROOT / ".runtime" / "fhir-imports" / uuid.uuid4().hex).resolve()
    import_root = (ROOT / ".runtime" / "fhir-imports").resolve()
    if import_root not in output.parents:
        parser.error("Output must be a new directory beneath .runtime/fhir-imports.")
    try:
        result = import_synthetic_fixture() if args.synthetic_fixture else import_file(args.bundle)
        report = write_import(result, output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        # File names, source content, and command output may contain identity.
        reason = str(exc) if isinstance(exc, ImportRejected) else "Local input or protected storage setup failed."
        print(json.dumps({"status": "rejected", "reason": reason}))
        return 1
    print(json.dumps({"status": "imported", "classification": report["data_classification"], "rdf_triples": report["rdf_triples"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
