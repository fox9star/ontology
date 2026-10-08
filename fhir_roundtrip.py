"""Compare supported synthetic local->FHIR->local semantics and re-export.

Only the immutable constructed repository fixture is accepted. Optional
official validation is offline structural validation of its round-trip export.
"""

import argparse
from decimal import Decimal
from datetime import datetime
import json
from pathlib import Path
import shutil

from rdflib import Graph, RDF
from rdflib.namespace import PROV

import fhir_import
import fhir_validate
from fhir_export import export_healthcare_bundle
from fhir_validation import validate_collection_bundle
from healthcare_privacy import HEALTH

ROOT = Path(__file__).resolve().parent


def supported_signature(graph):
    classes = [HEALTH.PatientRecord, HEALTH.DiagnosticTask, HEALTH.ClinicalObservation, HEALTH.ClinicalReport]
    roles = {subject: str(kind).split("#")[-1] for kind in classes for subject in graph.subjects(RDF.type, kind)}
    predicates = {
        HEALTH.associatedWithRecord, HEALTH.diagnosticStatus, HEALTH.taskIntent,
        PROV.startedAtTime, PROV.endedAtTime, HEALTH.generatesObservation, HEALTH.generatesReport,
        HEALTH.observesRecord, PROV.wasGeneratedBy, HEALTH.observationStatus, HEALTH.codeSystem,
        HEALTH.observationCode, HEALTH.observedAt, HEALTH.numericValue, HEALTH.unitCode,
        HEALTH.unitCodeSystem, HEALTH.textValue, HEALTH.reportStatus, HEALTH.reportCodeSystem,
        HEALTH.reportCode, HEALTH.reportResult, HEALTH.findingText,
    }
    values = [[role, "rdf:type", role] for role in sorted(roles.values())]
    for subject, predicate, obj in graph:
        if subject not in roles or predicate not in predicates:
            continue
        value = roles.get(obj, str(obj))
        if predicate == HEALTH.numericValue:
            value = str(Decimal(str(obj)).normalize())
        if predicate in {HEALTH.observedAt, PROV.startedAtTime, PROV.endedAtTime}:
            value = datetime.fromisoformat(str(obj).replace("Z", "+00:00")).isoformat()
        values.append([roles[subject], str(predicate), value])
    return sorted(values)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".runtime" / "fhir-roundtrip")
    parser.add_argument("--official", choices=["structural"])
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    try:
        # Verify fixture trust before reading it as the semantic baseline.
        result = fhir_import.import_synthetic_fixture()
        original = Graph().parse(fhir_import.FIXTURE, format="turtle")
        expected, actual = supported_signature(original), supported_signature(result.graph)
        bundle = export_healthcare_bundle(result.graph)
        local = validate_collection_bundle(bundle)
        report = {
            "status": "passed" if expected == actual and local["valid"] else "failed",
            "source": "pinned-constructed-synthetic-fixture", "fixture_sha256": fhir_import.FIXTURE_SHA256,
            "supported_semantic_equivalence": expected == actual, "supported_facts": len(expected),
            "expected": expected, "actual": actual, "local_validation": local,
            "complete_clinical_import": False, "lossless_rdf_mapping": False,
            "official": {"status": "not-requested"},
        }
        result.graph.serialize(destination=output / "imported.ttl", format="turtle")
        (output / "import-report.json").write_text(json.dumps(result.report, indent=2) + "\n", encoding="utf-8")
        bundle_path = output / "roundtrip-bundle.json"
        bundle_path.write_text(json.dumps(bundle, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        if args.official and report["status"] == "passed":
            config = json.loads((ROOT / "fhir-validator-config.json").read_text(encoding="utf-8"))
            jar = ROOT / ".runtime/fhir-tools" / f"validator_cli-{config['validator_version']}.jar"
            prepared = fhir_validate.prepare_validator(config, jar)
            if prepared["status"] == "ready":
                prepared = fhir_validate.prepare_core_package(config, jar)
            java = shutil.which("java")
            if not java:
                portable = sorted((ROOT / ".runtime/fhir-tools/java").glob("*/bin/java.exe"))
                java = str(portable[0]) if portable else None
            if prepared["status"] != "ready":
                report["official"] = prepared
            elif not java:
                report["official"] = {"status": "blocked", "reason": "Java is unavailable."}
            else:
                report["official"] = fhir_validate.run_official(config, bundle_path, output, java=java, jar=jar, mode="structural")
                report["official"]["package_verification"] = prepared
            report["status"] = report["official"]["status"]
    except (OSError, ValueError, TypeError) as exc:
        report = {"status": "blocked", "reason": "Constructed round-trip input or local validator setup failed.", "error_type": type(exc).__name__}
    (output / "roundtrip-report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "supported_semantic_equivalence": report.get("supported_semantic_equivalence", False), "report": str(output / "roundtrip-report.json")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
