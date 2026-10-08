"""Privacy-filtered FHIR R5 collection export for synthetic healthcare data."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import uuid

from rdflib import RDF, URIRef
from rdflib.namespace import PROV

from healthcare_privacy import HEALTH, redact_graph
from fhir_validation import absolute_uri, parse_instant, valid_code

FHIR_TASK_INTENTS = {
    "unknown", "proposal", "plan", "order", "original-order", "reflex-order",
    "filler-order", "instance-order", "option",
}
FHIR_TASK_STATUSES = {
    "PENDING": "requested",
    "ANALYZING": "in-progress",
    "COMPLETED": "completed",
    "VERIFIED": "completed",
    "FAILED": "failed",
    "CANCELLED": "cancelled",
}
FHIR_OBSERVATION_STATUSES = {
    "registered", "preliminary", "final", "amended", "corrected", "cancelled",
    "entered-in-error", "unknown",
}
FHIR_REPORT_STATUSES = {
    "registered", "partial", "preliminary", "modified", "final", "amended",
    "corrected", "appended", "cancelled", "entered-in-error", "unknown",
}
FHIR_TASK_STATUS_SYSTEM = "http://hl7.org/fhir/task-status"
FHIR_TASK_INTENT_SYSTEM = "http://hl7.org/fhir/task-intent"
FHIR_OBSERVATION_STATUS_SYSTEM = "http://hl7.org/fhir/observation-status"
FHIR_REPORT_STATUS_SYSTEM = "http://hl7.org/fhir/diagnostic-report-status"


def _one(graph, subject, predicate):
    values = list(graph.objects(subject, predicate))
    return values[0] if len(values) == 1 else None


def _resource_id(resource_type, uri):
    # Use a fresh id per export so two Bundles cannot be correlated through
    # stable hashes derived from local RDF subject IRIs.
    return str(uuid.uuid4())


def _entry(resource):
    full_url = "urn:uuid:" + resource["id"]
    return {"fullUrl": full_url, "resource": resource}, full_url


def _fhir_datetime(value):
    if value is None:
        return None
    parsed = parse_instant(str(value))
    return parsed.isoformat() if parsed is not None else None


def _coding_system(value):
    if not isinstance(value, URIRef) or not absolute_uri(str(value)):
        return None
    # These known aliases are spellings of the canonical exchange identifiers.
    return {"https://loinc.org": "http://loinc.org", "https://unitsofmeasure.org": "http://unitsofmeasure.org"}.get(str(value), str(value))


def _ambiguous(graph, subject, predicates):
    return any(len(list(graph.objects(subject, predicate))) > 1 for predicate in predicates)


def _fhir_decimal(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            return None
        if number == number.to_integral_value():
            return int(number)
        rounded = float(number)
        if Decimal(str(rounded)) != number:
            return None
        return rounded
    except (InvalidOperation, ValueError, OverflowError):
        return None


def _patient_context(graph):
    synthetic_records = set(graph.subjects(RDF.type, HEALTH.PatientRecord))
    synthetic_records = {
        record for record in synthetic_records
        if set(graph.objects(record, HEALTH.dataClassification)) == {HEALTH.Synthetic}
    }
    patient_ids, entries, full_urls = {}, [], {}
    for record in sorted(synthetic_records, key=str):
        resource_id = _resource_id("Patient", record)
        resource = {"resourceType": "Patient", "id": resource_id}
        entry, full_url = _entry(resource)
        entries.append(entry)
        patient_ids[record] = resource_id
        full_urls[record] = full_url
    return synthetic_records, patient_ids, entries, full_urls


def export_healthcare_bundle(source_graph, *, timestamp=None):
    """Return a FHIR R5 Bundle and safe, generic notes for incomplete mappings.

    Only records explicitly classified Synthetic are eligible. Internal patient
    keys, source URIs, model confidence scores, and unmapped clinical text are not
    emitted. A clinical report requires an explicit FHIR status and coded type.
    """
    if timestamp is not None and (not isinstance(timestamp, datetime) or timestamp.tzinfo is None):
        raise ValueError("Export timestamp must be a timezone-aware datetime.")
    graph = redact_graph(source_graph)
    records, patient_ids, entries, patient_full_urls = _patient_context(graph)
    tasks = {}
    task_full_urls = {}
    task_observations, task_reports = {}, {}
    included_observations, included_reports = {}, {}
    notes = []

    for task in sorted(set(graph.subjects(RDF.type, HEALTH.DiagnosticTask)), key=str):
        if _ambiguous(graph, task, (HEALTH.associatedWithRecord, HEALTH.diagnosticStatus, HEALTH.taskIntent, PROV.startedAtTime, PROV.endedAtTime)):
            notes.append("A diagnostic task was omitted because scalar exchange fields were ambiguous.")
            continue
        record = _one(graph, task, HEALTH.associatedWithRecord)
        raw_status = _one(graph, task, HEALTH.diagnosticStatus)
        fhir_status = FHIR_TASK_STATUSES.get(str(raw_status)) if raw_status is not None else None
        if record not in records or fhir_status is None:
            notes.append("A diagnostic task was omitted because its synthetic subject or status was missing or invalid.")
            continue
        intent = _one(graph, task, HEALTH.taskIntent)
        intent = str(intent) if intent is not None else "unknown"
        if intent not in FHIR_TASK_INTENTS:
            notes.append("A diagnostic task was omitted because its intent was not a FHIR R5 code.")
            continue
        resource_id = _resource_id("Task", task)
        resource = {
            "resourceType": "Task", "id": resource_id,
            "status": fhir_status, "intent": intent,
            "for": {"reference": patient_full_urls[record]},
        }
        if str(raw_status) == "VERIFIED":
            resource["businessStatus"] = {"text": "VERIFIED"}
        start = _fhir_datetime(_one(graph, task, PROV.startedAtTime))
        end = _fhir_datetime(_one(graph, task, PROV.endedAtTime))
        if start and end and parse_instant(start) <= parse_instant(end):
            resource["executionPeriod"] = {"start": start, "end": end}
        elif start or end:
            notes.append("A diagnostic task execution period was omitted because its times were incomplete or invalid.")
        entry, full_url = _entry(resource)
        entries.append(entry)
        tasks[task] = resource
        task_full_urls[task] = full_url
        task_observations[task] = []
        task_reports[task] = []

    for observation in sorted(set(graph.subjects(RDF.type, HEALTH.ClinicalObservation)), key=str):
        if _ambiguous(graph, observation, (HEALTH.observesRecord, HEALTH.codeSystem, HEALTH.observationCode, PROV.wasGeneratedBy, HEALTH.observationStatus, HEALTH.observedAt, HEALTH.numericValue, HEALTH.textValue, HEALTH.unitCode, HEALTH.unitCodeSystem)):
            notes.append("A clinical observation was omitted because scalar exchange fields were ambiguous.")
            continue
        record = _one(graph, observation, HEALTH.observesRecord)
        code_system = _one(graph, observation, HEALTH.codeSystem)
        code = _one(graph, observation, HEALTH.observationCode)
        generated_by = _one(graph, observation, PROV.wasGeneratedBy)
        status = _one(graph, observation, HEALTH.observationStatus)
        status = str(status) if status is not None else "unknown"
        if (record not in records or not _coding_system(code_system) or not valid_code(str(code))
                or code is None or status not in FHIR_OBSERVATION_STATUSES or generated_by not in tasks
                or record != _one(graph, generated_by, HEALTH.associatedWithRecord)):
            notes.append("A clinical observation was omitted because its coded value, synthetic subject, or status was incomplete.")
            continue
        resource_id = _resource_id("Observation", observation)
        resource = {
            "resourceType": "Observation", "id": resource_id,
            "status": status,
            "code": {"coding": [{"system": _coding_system(code_system), "code": str(code)}]},
            "subject": {"reference": patient_full_urls[record]},
        }
        # R5 requires its bodyweight profile when this LOINC code is used;
        # category is prescribed by that profile, rather than guessed from a
        # generic local observation class.
        if _coding_system(code_system) == "http://loinc.org" and str(code) == "29463-7":
            resource["category"] = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}]
        observed_at = _fhir_datetime(_one(graph, observation, HEALTH.observedAt))
        if observed_at:
            resource["effectiveDateTime"] = observed_at
        numeric = _one(graph, observation, HEALTH.numericValue)
        text = _one(graph, observation, HEALTH.textValue)
        if numeric is not None:
            unit = _one(graph, observation, HEALTH.unitCode)
            unit_system = _one(graph, observation, HEALTH.unitCodeSystem)
            number = _fhir_decimal(numeric)
            if number is None or unit is None or not valid_code(str(unit)) or not _coding_system(unit_system) or text is not None:
                notes.append("A numeric observation was omitted because its number or coded unit was incomplete.")
                continue
            resource["valueQuantity"] = {
                "value": number, "unit": str(unit),
                "system": _coding_system(unit_system), "code": str(unit),
            }
        elif text is not None and str(text).strip():
            resource["valueString"] = str(text)
        else:
            notes.append("A clinical observation was omitted because it had no supported value.")
            continue
        if "category" in resource:
            quantity = resource.get("valueQuantity", {})
            if not observed_at or quantity.get("system") != "http://unitsofmeasure.org" or quantity.get("code") not in {"kg", "g", "[lb_av]"}:
                notes.append("A body weight observation was omitted because its profile-required time, quantity, or unit was incomplete.")
                continue
        entry, full_url = _entry(resource)
        entries.append(entry)
        included_observations[observation] = (entry, full_url)
        task_observations[generated_by].append((observation, full_url))

    for task, task_resource in tasks.items():
        for report in graph.objects(task, HEALTH.generatesReport):
            if (_ambiguous(graph, report, (HEALTH.reportStatus, HEALTH.reportCodeSystem, HEALTH.reportCode, HEALTH.findingText))
                    or len(set(graph.subjects(HEALTH.generatesReport, report))) != 1):
                notes.append("A clinical report was omitted because its fields or task association were ambiguous.")
                continue
            status = _one(graph, report, HEALTH.reportStatus)
            code_system = _one(graph, report, HEALTH.reportCodeSystem)
            code = _one(graph, report, HEALTH.reportCode)
            record = _one(graph, task, HEALTH.associatedWithRecord)
            if (status is None or str(status) not in FHIR_REPORT_STATUSES
                    or not _coding_system(code_system) or code is None or not valid_code(str(code)) or record not in records):
                notes.append("A clinical report was omitted because its required status or coded type was not recorded.")
                continue
            resource_id = _resource_id("DiagnosticReport", report)
            resource = {
                "resourceType": "DiagnosticReport", "id": resource_id,
                "status": str(status),
                "code": {"coding": [{"system": _coding_system(code_system), "code": str(code)}]},
                "subject": {"reference": patient_full_urls[record]},
            }
            findings = list(graph.objects(report, HEALTH.findingText))
            if len(findings) == 1 and str(findings[0]).strip():
                resource["conclusion"] = str(findings[0])
            result_refs = []
            for observation in graph.objects(report, HEALTH.reportResult):
                if observation in included_observations and _one(graph, observation, HEALTH.observesRecord) == record:
                    result_refs.append({"reference": included_observations[observation][1]})
            if result_refs:
                resource["result"] = result_refs
            entry, full_url = _entry(resource)
            entries.append(entry)
            included_reports[report] = (entry, full_url)
            task_reports[task].append((report, full_url))

    for task, resource in tasks.items():
        outputs = []
        outputs.extend({"type": {"text": "Clinical observation"},
                        "valueReference": {"reference": reference}}
                       for _, reference in task_observations.get(task, []))
        outputs.extend({"type": {"text": "Diagnostic report"},
                        "valueReference": {"reference": reference}}
                       for _, reference in task_reports.get(task, []))
        if outputs:
            resource["output"] = outputs

    if notes:
        outcome = {
            "resourceType": "OperationOutcome",
            "id": _resource_id("OperationOutcome", "incomplete-healthcare-mapping"),
            "issue": [{
                "severity": "warning", "code": "incomplete",
                "diagnostics": "Some clinical resources were omitted because required exchange fields were absent or invalid.",
            }],
        }
        outcome_entry, _ = _entry(outcome)
        entries.append(outcome_entry)

    bundle_id = uuid.uuid4().hex
    bundle = {
        "resourceType": "Bundle", "id": bundle_id, "type": "collection",
        "timestamp": (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(),
    }
    if entries:
        bundle["entry"] = entries
    return bundle


def validate_collection_bundle(bundle):
    """Compatibility entry point for the bounded, network-free export checks."""
    from fhir_validation import validate_collection_bundle as validate
    return validate(bundle)
