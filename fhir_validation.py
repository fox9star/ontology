"""Bounded local checks for this application's closed FHIR R5 export.

This is deliberately not a FHIR schema or terminology validator. It rejects
malformed export values and recursively resolves references without fetching
anything from a network. Use the official validator for R5 conformance.
"""

from datetime import datetime
import math
import re
from urllib.parse import urlsplit
import uuid

ID_PATTERN = re.compile(r"[A-Za-z0-9\-.]{1,64}\Z")
CODE_PATTERN = re.compile(r"[^\s]+(?: [^\s]+)*\Z")
RESOURCE_TYPES = {"Patient", "Task", "Observation", "DiagnosticReport", "OperationOutcome"}
TASK_STATUSES = {"draft", "requested", "received", "accepted", "rejected", "ready", "cancelled", "in-progress", "on-hold", "failed", "completed", "entered-in-error"}
TASK_INTENTS = {"unknown", "proposal", "plan", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"}
OBSERVATION_STATUSES = {"registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"}
REPORT_STATUSES = {"registered", "partial", "preliminary", "modified", "final", "amended", "corrected", "appended", "cancelled", "entered-in-error", "unknown"}


def valid_code(value):
    return isinstance(value, str) and bool(CODE_PATTERN.fullmatch(value))


def _one_of(value, values):
    return isinstance(value, str) and value in values


def absolute_uri(value):
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        return False
    try:
        parts = urlsplit(value)
        return bool(parts.scheme and (parts.netloc if parts.scheme in {"http", "https"} else parts.path))
    except ValueError:
        return False


def parse_instant(value):
    """Parse the full timestamp subset produced by the exporter, including zone."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def validate_collection_bundle(bundle, *, allow_external_references=False):
    """Validate supported export values and every nested Reference.reference.

    The default policy is a closed collection. Absolute references are accepted
    only if they match an entry fullUrl; callers can explicitly permit external
    references, which are then reported as unverified warnings. Contained IDs
    resolve only inside their owning entry, never across entries.
    """
    errors, warnings = [], []
    if not isinstance(bundle, dict):
        return {"valid": False, "errors": ["Expected a Bundle JSON object."], "warnings": [], "entries": 0, "scope": "local-export-contract"}
    if bundle.get("resourceType") != "Bundle" or bundle.get("type") != "collection":
        errors.append("Expected an R5 Bundle with type=collection.")
    if not isinstance(bundle.get("id"), str) or not ID_PATTERN.fullmatch(bundle["id"]):
        errors.append("Bundle.id is missing or invalid.")
    if parse_instant(bundle.get("timestamp")) is None:
        errors.append("Bundle.timestamp requires a valid timestamp with a timezone.")
    entries = bundle.get("entry", [])
    if not isinstance(entries, list):
        errors.append("Bundle.entry must be an array.")
        entries = []
    full_urls, identities, resources = {}, {}, []
    for index, entry in enumerate(entries):
        path = f"entry[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{path} must be an object.")
            continue
        full_url, resource = entry.get("fullUrl"), entry.get("resource")
        if not absolute_uri(full_url) or "/_history/" in str(full_url):
            errors.append(f"{path}.fullUrl must be an absolute, non-versioned URI.")
        elif full_url in full_urls:
            errors.append(f"{path} has a duplicate fullUrl.")
        else:
            full_urls[full_url] = resource
        if isinstance(full_url, str) and full_url.startswith("urn:uuid:"):
            try:
                uuid.UUID(full_url[9:])
            except ValueError:
                errors.append(f"{path}.fullUrl has an invalid UUID.")
        if not isinstance(resource, dict):
            errors.append(f"{path} has no identified resource.")
            continue
        kind, resource_id = resource.get("resourceType"), resource.get("id")
        if not _one_of(kind, RESOURCE_TYPES):
            errors.append(f"{path} has an unsupported resourceType.")
        if not isinstance(resource_id, str) or not ID_PATTERN.fullmatch(resource_id):
            errors.append(f"{path}.resource.id is missing or invalid.")
        else:
            identity = f"{kind}/{resource_id}"
            if identity in identities:
                errors.append(f"{path} has a duplicate resource identity.")
            identities[identity] = resource
        if isinstance(full_url, str) and full_url.startswith(("http://", "https://")) and resource_id:
            tail = full_url.rstrip("/").split("/")[-2:]
            if len(tail) == 2 and tail[0] in RESOURCE_TYPES and tail != [kind, resource_id]:
                errors.append(f"{path}.fullUrl disagrees with resource identity.")
        resources.append((path + ".resource", resource))

    def coding(value, path):
        if not isinstance(value, dict) or not valid_code(value.get("code")) or not absolute_uri(value.get("system")):
            errors.append(f"{path} requires a code and an absolute code system URI.")
        elif "display" in value and (not isinstance(value["display"], str) or not value["display"].strip()):
            errors.append(f"{path}.display must be a nonempty string.")

    def concept(value, path):
        if not isinstance(value, dict) or not isinstance(value.get("coding"), list) or not value["coding"]:
            errors.append(f"{path} requires a nonempty coding array.")

    def walk(value, path, contained):
        if isinstance(value, dict):
            if not value:
                errors.append(f"{path} must not be an empty JSON object.")
            for key, child in value.items():
                child_path = path + "." + key
                if key == "reference":
                    target = None
                    if not isinstance(child, str) or not child or any(c.isspace() for c in child):
                        errors.append(f"{child_path} requires a nonempty reference string.")
                    elif child.startswith("#"):
                        target = contained.get(child[1:])
                        if target is None:
                            errors.append(f"{child_path} has an unresolved contained reference.")
                    elif child in full_urls:
                        target = full_urls[child]
                    elif child in identities:
                        target = identities[child]
                    elif absolute_uri(child) and not child.startswith("urn:") and allow_external_references:
                        warnings.append(f"{child_path} has an unverified external reference.")
                    else:
                        errors.append(f"{child_path} has an unresolved Bundle reference.")
                    declared_type = value.get("type")
                    if target is not None and declared_type and isinstance(target, dict) and str(declared_type).split("/")[-1] != target.get("resourceType"):
                        errors.append(f"{child_path} target disagrees with Reference.type.")
                if key == "coding":
                    if not isinstance(child, list) or not child:
                        errors.append(f"{child_path} must be a nonempty coding array.")
                    else:
                        for index, item in enumerate(child):
                            coding(item, f"{child_path}[{index}]")
                if key in {"effectiveDateTime", "timestamp", "issued"} and parse_instant(child) is None:
                    errors.append(f"{child_path} requires a valid timestamp with a timezone.")
                if key == "valueQuantity":
                    if not isinstance(child, dict):
                        errors.append(f"{child_path} must be a Quantity object.")
                    else:
                        number = child.get("value")
                        if isinstance(number, bool) or not isinstance(number, (int, float)) or (isinstance(number, float) and not math.isfinite(number)):
                            errors.append(f"{child_path}.value must be a finite JSON number.")
                        if not absolute_uri(child.get("system")) or not valid_code(child.get("code")):
                            errors.append(f"{child_path} requires a coded unit and system.")
                        if not isinstance(child.get("unit"), str) or not child["unit"].strip():
                            errors.append(f"{child_path}.unit must be a nonempty string.")
                        if child.get("system") == "http://unitsofmeasure.org" and child.get("unit") != child.get("code"):
                            warnings.append(f"{child_path} UCUM display differs from the code; terminology validation is required.")
                if key == "valueString" and (not isinstance(child, str) or not child.strip()):
                    errors.append(f"{child_path} must be a nonempty string.")
                if key in {"valueBoolean", "active", "userSelected"} and not isinstance(child, bool):
                    errors.append(f"{child_path} must be a JSON boolean.")
                walk(child, child_path, contained)
        elif isinstance(value, list):
            if not value:
                errors.append(f"{path} must not be an empty JSON array.")
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]", contained)
        elif value is None:
            errors.append(f"{path} must not be JSON null.")
        elif isinstance(value, str) and not value.strip():
            errors.append(f"{path} must not be an empty string.")
        elif isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path} must be a finite JSON number.")

    for path, resource in resources:
        contained_items = resource.get("contained", [])
        contained = {}
        if not isinstance(contained_items, list):
            errors.append(f"{path}.contained must be an array.")
            contained_items = []
        for item in contained_items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not ID_PATTERN.fullmatch(item["id"]):
                errors.append(f"{path}.contained has an invalid resource identity.")
            elif item["id"] in contained:
                errors.append(f"{path}.contained has a duplicate id.")
            else:
                contained[item["id"]] = item
        kind = resource.get("resourceType")
        subject_field = "for" if kind == "Task" else "subject" if _one_of(kind, {"Observation", "DiagnosticReport"}) else None
        if subject_field:
            reference_object = resource.get(subject_field)
            reference = reference_object.get("reference") if isinstance(reference_object, dict) else None
            target = full_urls.get(reference) or identities.get(reference) if isinstance(reference, str) else None
            if isinstance(reference, str) and reference.startswith("#"):
                target = contained.get(reference[1:])
            if not isinstance(reference_object, dict) or not isinstance(reference, str):
                errors.append(f"{path}.{subject_field} requires a subject reference for this export.")
            elif target is not None and isinstance(target, dict) and target.get("resourceType") != "Patient":
                errors.append(f"{path}.{subject_field} requires a Patient reference for this export.")
        if kind == "DiagnosticReport" and "result" in resource:
            if not isinstance(resource["result"], list):
                errors.append(f"{path}.result must be an array of references.")
            else:
                for index, item in enumerate(resource["result"]):
                    reference = item.get("reference") if isinstance(item, dict) else None
                    target = full_urls.get(reference) or identities.get(reference) if isinstance(reference, str) else None
                    if not isinstance(reference, str):
                        errors.append(f"{path}.result[{index}] requires a reference.")
                    elif target is not None and isinstance(target, dict):
                        if target.get("resourceType") != "Observation":
                            errors.append(f"{path}.result[{index}] requires an Observation reference.")
                        elif target.get("subject") != resource.get("subject"):
                            # Resolve equivalent relative/fullUrl forms before
                            # comparing identity, rather than comparing text.
                            def subject_target(value):
                                ref = value.get("reference") if isinstance(value, dict) else None
                                return full_urls.get(ref) or identities.get(ref) if isinstance(ref, str) else None
                            if subject_target(target.get("subject")) is not subject_target(resource.get("subject")):
                                errors.append(f"{path}.result[{index}] belongs to a different subject.")
        if kind == "Task":
            if not _one_of(resource.get("status"), TASK_STATUSES) or not _one_of(resource.get("intent"), TASK_INTENTS):
                errors.append(f"{path} Task is missing a valid status or intent.")
            if "executionPeriod" in resource:
                period = resource["executionPeriod"]
                start = parse_instant(period.get("start")) if isinstance(period, dict) else None
                end = parse_instant(period.get("end")) if isinstance(period, dict) else None
                if start is None or end is None or start > end:
                    errors.append(f"{path}.executionPeriod requires ordered timezone-aware start and end times.")
        if _one_of(kind, {"Observation", "DiagnosticReport"}):
            statuses = OBSERVATION_STATUSES if kind == "Observation" else REPORT_STATUSES
            if not _one_of(resource.get("status"), statuses):
                errors.append(f"{path} is missing a valid status.")
            concept(resource.get("code"), path + ".code")
        if kind == "Observation":
            value_keys = [key for key in resource if key.startswith("value")]
            if len(value_keys) != 1 or value_keys[0] not in {"valueQuantity", "valueString"}:
                errors.append(f"{path} requires exactly one supported observation value.")
            codings = resource.get("code", {}).get("coding", []) if isinstance(resource.get("code"), dict) else []
            if isinstance(codings, list) and any(isinstance(item, dict) and item.get("system") == "http://loinc.org" and item.get("code") == "29463-7" for item in codings):
                category = resource.get("category", [])
                categories = [item for concept_value in category if isinstance(concept_value, dict) and isinstance(concept_value.get("coding"), list) for item in concept_value["coding"]] if isinstance(category, list) else []
                quantity = resource.get("valueQuantity")
                if not any(isinstance(item, dict) and item.get("system") == "http://terminology.hl7.org/CodeSystem/observation-category" and item.get("code") == "vital-signs" for item in categories):
                    errors.append(f"{path} body weight profile requires the vital-signs category.")
                if parse_instant(resource.get("effectiveDateTime")) is None or not isinstance(quantity, dict) or quantity.get("system") != "http://unitsofmeasure.org" or not _one_of(quantity.get("code"), {"kg", "g", "[lb_av]"}):
                    errors.append(f"{path} body weight profile requires an effective time and a supported UCUM quantity.")
        if kind == "OperationOutcome":
            issues = resource.get("issue")
            if not isinstance(issues, list) or not issues:
                errors.append(f"{path} requires a nonempty issue array.")
            else:
                for index, issue in enumerate(issues):
                    if not isinstance(issue, dict) or not _one_of(issue.get("severity"), {"fatal", "error", "warning", "information", "success"}) or not valid_code(issue.get("code")):
                        errors.append(f"{path}.issue[{index}] requires a valid severity and issue code.")
        walk(resource, path, contained)
    return {"valid": not errors, "errors": errors, "warnings": warnings, "entries": len(resources), "scope": "local-export-contract", "terminology_validated": False}
