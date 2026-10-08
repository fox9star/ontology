"""Measure and enforce Korean and English documentation for named schema terms."""

import argparse
import json
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS
from namespace_policy import is_absolute_iri
from ontology_registry import read_registry


ROOT = Path(__file__).resolve().parent
SCHEMA_FILES = tuple(module["schema"] for module in read_registry(ROOT)["modules"]
                     if module.get("documentation", True))
TERM_TYPES = (OWL.Class, RDFS.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty, RDF.Property)
LANGUAGES = ("ko", "en")
EXCEPTIONS_FILE = "ontology_documentation_exceptions.json"


def documentation_report(root=ROOT, exceptions=None):
    """Return measured coverage; explicit, narrow exceptions never inflate it."""
    root = Path(root)
    errors = []
    entries = []
    if exceptions is None:
        path = root / EXCEPTIONS_FILE
        exceptions = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    exemption_map = {}
    for exception in exceptions:
        if not isinstance(exception, dict):
            errors.append("Documentation exception must be an object")
            continue
        key = tuple(exception.get(field) for field in ("file", "term", "field", "language"))
        if key[0] not in SCHEMA_FILES or not isinstance(key[1], str) or not is_absolute_iri(URIRef(key[1])) or key[2] not in ("label", "definition") or key[3] not in LANGUAGES or not isinstance(exception.get("reason"), str) or not exception["reason"].strip():
            errors.append(f"Invalid documentation exception: {key}")
            continue
        if key in exemption_map:
            errors.append(f"Duplicate documentation exception: {key}")
        exemption_map[key] = exception["reason"]
    used_exemptions = set()
    covered = {language: {"label": 0, "definition": 0} for language in LANGUAGES}
    for filename in SCHEMA_FILES:
        graph = Graph().parse(root / filename, format="turtle")
        terms = {
            subject
            for term_type in TERM_TYPES
            for subject in graph.subjects(RDF.type, term_type)
            if isinstance(subject, URIRef)
        }
        for term in sorted(terms, key=str):
            entry = {"file": filename, "term": str(term), "coverage": {}, "exceptions": []}
            for language in LANGUAGES:
                entry["coverage"][language] = {}
                for field, predicate in (("label", RDFS.label), ("definition", RDFS.comment)):
                    minimum = 1 if field == "label" else (6 if language == "ko" else 12)
                    exists = any(getattr(value, "language", None) == language and len(str(value).strip()) >= minimum for value in graph.objects(term, predicate))
                    entry["coverage"][language][field] = exists
                    covered[language][field] += int(exists)
                    key = (filename, str(term), field, language)
                    if not exists:
                        if key in exemption_map:
                            used_exemptions.add(key)
                            entry["exceptions"].append({"field": field, "language": language, "reason": exemption_map[key]})
                        else:
                            errors.append(f"{filename}: {term} has no {field} in {language} (rdfs:{'label' if field == 'label' else 'comment'}@{language})")
            entries.append(entry)
    for unused in sorted(set(exemption_map) - used_exemptions):
        errors.append(f"Stale or unknown documentation exception: {unused}")
    return {"total": len(entries), "covered": covered, "exception_count": len(used_exemptions), "terms": entries, "errors": errors}


def check_documentation(root=ROOT):
    """Compatibility API returning the term count and bilingual gate failures."""
    report = documentation_report(root)
    return report["total"], report["errors"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", type=Path, help="Save measured coverage and exceptions as UTF-8 JSON")
    options = parser.parse_args(argv)
    report = documentation_report(options.root)
    total, errors = report["total"], report["errors"]
    if options.json:
        options.json.parent.mkdir(parents=True, exist_ok=True)
        options.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for language in LANGUAGES:
        counts = report["covered"][language]
        print(f"{language}: labels {counts['label']}/{total}, definitions {counts['definition']}/{total}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: bilingual documentation gate passed for {total} terms ({report['exception_count']} explicit exceptions).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
