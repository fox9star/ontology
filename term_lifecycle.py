"""Check term retirement and compare reviewed ontology compatibility snapshots."""

import argparse
import hashlib
import json
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

from namespace_policy import ROOT, SEMVER, check_namespaces, declared_terms, is_absolute_iri, read_schema_bundle

POLICY_FILE = "term_lifecycle_policy.json"
SNAPSHOT_VERSION = 1
ANNOTATIONS = {
    RDFS.label, RDFS.comment, RDFS.seeAlso, RDFS.isDefinedBy, OWL.deprecated, DCTERMS.isReplacedBy,
    SKOS.prefLabel, SKOS.altLabel, SKOS.hiddenLabel, SKOS.definition, SKOS.note, SKOS.scopeNote,
    SKOS.example, SKOS.editorialNote, SKOS.historyNote, SKOS.changeNote,
}
SYMMETRIC_RELATIONS = {OWL.disjointWith, OWL.equivalentClass, OWL.equivalentProperty, OWL.inverseOf, OWL.propertyDisjointWith}


def _role(roles):
    specific = roles - {"property"}
    return sorted(specific or roles)[0] if len(specific or roles) == 1 else None


def _load_policy(root):
    path = Path(root) / POLICY_FILE
    if not path.is_file():
        return {"retired_terms": {}, "external_replacements": [], "equivalence_justifications": []}
    policy = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError("Lifecycle policy must be an object")
    return policy


def check_lifecycle(root=ROOT, policy=None):
    """Validate replacement targets and explicit retirement/equivalence decisions."""
    root = Path(root)
    errors = list(check_namespaces(root))
    graphs = read_schema_bundle(root)
    graph = Graph()
    terms = {}
    for module in graphs.values():
        graph += module
        for term, roles in declared_terms(module).items():
            terms.setdefault(term, set()).update(roles)
    policy = _load_policy(root) if policy is None else policy
    retired = policy.get("retired_terms", {})
    external = policy.get("external_replacements", [])
    justifications = policy.get("equivalence_justifications", [])
    if not isinstance(retired, dict) or not isinstance(external, list) or not isinstance(justifications, list):
        return errors + ["Lifecycle policy requires retired_terms object and external_replacements/equivalence_justifications lists"]

    deprecated = set()
    for term in set(graph.subjects(OWL.deprecated, None)):
        values = list(graph.objects(term, OWL.deprecated))
        if term not in terms:
            errors.append(f"Undeclared term carries owl:deprecated: {term}")
        if len(values) != 1 or not isinstance(values[0], Literal) or values[0].datatype != XSD.boolean or values[0].toPython() not in (True, False):
            errors.append(f"{term}: owl:deprecated must have one xsd:boolean value")
        elif values[0].toPython() is True:
            deprecated.add(term)

    external_map = {}
    for entry in external:
        if not isinstance(entry, dict):
            errors.append("External replacement must be an object")
            continue
        if not all(isinstance(entry.get(field), str) and entry[field].strip() for field in ("source", "target", "role", "reason")):
            errors.append("External replacement requires non-empty source, target, role and reason strings")
            continue
        source, target = URIRef(entry.get("source", "")), URIRef(entry.get("target", ""))
        if source in external_map:
            errors.append(f"Duplicate external replacement policy for {source}")
        if not is_absolute_iri(source) or not is_absolute_iri(target) or not str(entry.get("reason", "")).strip():
            errors.append(f"Invalid external replacement policy for {source}")
        if source not in terms or entry.get("role") != _role(terms.get(source, set())):
            errors.append(f"External replacement policy has unknown source or mismatched role: {source}")
        if target in terms:
            errors.append(f"External replacement policy target is local: {target}")
        external_map[source] = entry

    replacements = {}
    for source in set(graph.subjects(DCTERMS.isReplacedBy, None)):
        targets = list(graph.objects(source, DCTERMS.isReplacedBy))
        if source not in terms:
            errors.append(f"Undeclared replacement source: {source}")
        if source not in deprecated:
            errors.append(f"{source}: a replacement requires owl:deprecated true")
        if len(targets) != 1:
            errors.append(f"{source}: expected exactly one dcterms:isReplacedBy target")
            continue
        target = targets[0]
        if not is_absolute_iri(target):
            errors.append(f"{source}: replacement target must be an absolute IRI")
            continue
        replacements[source] = target
        if source == target:
            errors.append(f"{source}: term cannot replace itself")
        if target in terms:
            if _role(terms.get(source, set())) != _role(terms[target]):
                errors.append(f"{source}: replacement {target} has a different term role")
            if target in deprecated:
                errors.append(f"{source}: replacement target {target} is deprecated")
        else:
            approved = external_map.get(source)
            if not approved or approved.get("target") != str(target):
                errors.append(f"{source}: replacement {target} is neither declared locally nor explicitly approved externally")
    for source, target in replacements.items():
        if target in replacements:
            errors.append(f"Replacement chain is forbidden: {source} -> {target} -> {replacements[target]}")
        visited = {source}
        cursor = target
        while cursor in replacements:
            if cursor in visited:
                errors.append(f"Replacement cycle starts at {source}")
                break
            visited.add(cursor)
            cursor = replacements[cursor]
    for term in deprecated - replacements.keys():
        if not isinstance(retired.get(str(term)), str) or not retired[str(term)].strip():
            errors.append(f"{term}: retirement without replacement requires a reason in {POLICY_FILE}")
    for source in retired:
        if URIRef(source) not in deprecated or URIRef(source) in replacements:
            errors.append(f"Stale retirement policy: {source}")
    for source, entry in external_map.items():
        if str(replacements.get(source, "")) != entry.get("target"):
            errors.append(f"Stale external replacement policy: {source}")

    equivalences = set()
    for predicate in (OWL.equivalentClass, OWL.equivalentProperty):
        for source, target in graph.subject_objects(predicate):
            equivalences.add((str(source), str(predicate), str(target)))
    approved_equivalences = set()
    for entry in justifications:
        if not isinstance(entry, dict):
            errors.append("Equivalence justification must be an object")
            continue
        if not all(isinstance(entry.get(field), str) and entry[field].strip() for field in ("source", "predicate", "target", "reason")):
            errors.append("Equivalence justification requires non-empty source, predicate, target and reason strings")
            continue
        key = tuple(entry.get(field, "") for field in ("source", "predicate", "target"))
        if key in approved_equivalences:
            errors.append(f"Duplicate equivalence justification: {key}")
        if not str(entry.get("reason", "")).strip() or key[1] not in map(str, (OWL.equivalentClass, OWL.equivalentProperty)):
            errors.append(f"Invalid equivalence justification: {key}")
        approved_equivalences.add(key)
    for assertion in equivalences - approved_equivalences:
        errors.append(f"Equivalence requires a reviewed semantic justification in {POLICY_FILE}: {assertion}")
    for assertion in approved_equivalences - equivalences:
        errors.append(f"Stale equivalence justification: {assertion}")
    return errors


def _term_semantics(graph, term):
    """Canonicalize a term's axioms including anonymous restrictions and lists."""
    result = Graph()
    queue, visited = [term], set()
    for predicate in SYMMETRIC_RELATIONS:
        for source in graph.subjects(predicate, term):
            result.add((source, predicate, term))
            if isinstance(source, BNode):
                queue.append(source)
    # Include multi-class/property disjointness groups affecting this term.
    for group_type in (OWL.AllDisjointClasses, OWL.AllDisjointProperties):
        for group in graph.subjects(RDF.type, group_type):
            for head in graph.objects(group, OWL.members):
                if term in set(graph.items(head)):
                    queue.append(group)
    while queue:
        subject = queue.pop()
        if subject in visited:
            continue
        visited.add(subject)
        for predicate, obj in graph.predicate_objects(subject):
            if predicate in ANNOTATIONS:
                continue
            result.add((subject, predicate, obj))
            if isinstance(obj, BNode):
                queue.append(obj)
    canonical = to_canonical_graph(result)
    triples = sorted(f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in canonical)
    return hashlib.sha256("\n".join(triples).encode("utf-8")).hexdigest()


def create_snapshot(root=ROOT):
    """Capture a schema-only baseline; annotations and SHACL are separate gates."""
    errors = check_lifecycle(root)
    if errors:
        raise ValueError("Cannot snapshot invalid schema bundle: " + "; ".join(errors))
    modules = {}
    for filename, graph in read_schema_bundle(root).items():
        ontology = next(graph.subjects(RDF.type, OWL.Ontology))
        modules[filename] = {
            "ontology": str(ontology),
            "version": str(next(graph.objects(ontology, OWL.versionInfo))),
            "imports": sorted(map(str, graph.objects(ontology, OWL.imports))),
            "terms": {
                str(term): {"role": _role(roles), "semantic_hash": _term_semantics(graph, term)}
                for term, roles in sorted(declared_terms(graph).items(), key=lambda item: str(item[0]))
            },
        }
    return {"snapshot_version": SNAPSHOT_VERSION, "scope": "canonical-schema-axioms", "modules": modules}


def _version_parts(version):
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError(f"Invalid semantic version in compatibility snapshot: {version!r}")
    return tuple(map(int, version.split("+")[0].split("-")[0].split(".")))


def _version_key(version):
    numbers = _version_parts(version)
    plain = version.split("+", 1)[0]
    if "-" not in plain:
        return numbers, 1, ()
    prerelease = tuple((0, int(part)) if part.isdigit() else (1, part) for part in plain.split("-", 1)[1].split("."))
    return numbers, 0, prerelease


def compare_snapshots(previous, current):
    """Require a module major bump for removed terms or changed asserted semantics."""
    if previous.get("snapshot_version") != SNAPSHOT_VERSION or current.get("snapshot_version") != SNAPSHOT_VERSION:
        raise ValueError("Unsupported compatibility snapshot version")
    errors, modules = [], []
    old_modules, new_modules = previous["modules"], current["modules"]
    for filename, old in sorted(old_modules.items()):
        if filename not in new_modules:
            errors.append(f"{filename}: previous module is removed; preserve its declaration and version the retirement")
            modules.append({"file": filename, "removed_module": True, "breaking": True})
            continue
        new = new_modules[filename]
        old_terms, new_terms = old["terms"], new["terms"]
        removed = sorted(set(old_terms) - set(new_terms))
        added = sorted(set(new_terms) - set(old_terms))
        changed = sorted(term for term in set(old_terms) & set(new_terms) if old_terms[term] != new_terms[term])
        metadata_changed = old["ontology"] != new["ontology"] or old["imports"] != new["imports"]
        breaking = bool(removed or changed or metadata_changed)
        old_version, new_version = _version_parts(old["version"]), _version_parts(new["version"])
        if _version_key(new["version"]) < _version_key(old["version"]):
            errors.append(f"{filename}: version cannot decrease from {old['version']} to {new['version']}")
        if breaking and new_version[0] <= old_version[0]:
            errors.append(f"{filename}: removed/changed semantics require a major version greater than {old_version[0]} (current {new['version']})")
        if added and not breaking and _version_key(new["version"]) <= _version_key(old["version"]):
            errors.append(f"{filename}: added terms require a version increase from {old['version']}")
        modules.append({"file": filename, "previous_version": old["version"], "current_version": new["version"], "removed": removed, "added": added, "changed": changed, "ontology_or_imports_changed": metadata_changed, "breaking": breaking})
    for filename in sorted(set(new_modules) - set(old_modules)):
        modules.append({"file": filename, "added_module": True, "breaking": False})
    return {"compatible": not errors, "modules": modules, "errors": errors}


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("check", help="Check retirement, replacement and equivalence policy")
    snapshot_parser = commands.add_parser("snapshot", help="Create a reviewed baseline; never rewrite it automatically in CI")
    snapshot_parser.add_argument("--output", type=Path, required=True)
    compare_parser = commands.add_parser("compare", help="Compare current schemas with a previous reviewed baseline")
    compare_parser.add_argument("--previous", type=Path, required=True)
    compare_parser.add_argument("--json", type=Path)
    options = parser.parse_args(argv)
    try:
        if options.command == "snapshot":
            snapshot = create_snapshot(options.root)
            _write_json(options.output, snapshot)
            print(f"Saved {len(snapshot['modules'])} module compatibility baseline to {options.output}.")
            return 0
        if options.command == "compare":
            previous = json.loads(options.previous.read_text(encoding="utf-8"))
            report = compare_snapshots(previous, create_snapshot(options.root))
            if options.json:
                _write_json(options.json, report)
            for module in report["modules"]:
                if module.get("breaking") or module.get("added"):
                    print(json.dumps(module, ensure_ascii=False, sort_keys=True))
            errors = report["errors"]
        else:
            errors = check_lifecycle(options.root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print("OK: ontology compatibility policy passed." if options.command == "compare" else "OK: term retirement, replacement and equivalence policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
