"""Read-only schema, SHACL, CQ and instance coverage report with regression gates.

Instance output contains counts only, never patient identifiers, labels, values
or raw SHACL messages. An absent provenance edge is a gap, not inferred evidence.
"""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.exceptions import ParserError
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SH, XSD
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.paths import Path as RDFPath
import pyshacl

from namespace_policy import SCHEMA_FILES
from ontology_loader import load_schema_graph, load_shape_graph
from ontology_registry import read_registry
from validation_pipeline import validate_phases, public_summary

ROOT = Path(__file__).resolve().parent
TERM_TYPES = (OWL.Class, RDFS.Class, OWL.ObjectProperty, OWL.DatatypeProperty)
PROV = "http://www.w3.org/ns/prov#"
CORE = "https://example.org/ontology/core#"
HEALTH = "http://example.org/ontology/healthcare#"
QUESTION_PATTERN = re.compile(
    r"^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~",
    re.MULTILINE | re.DOTALL,
)


def _ancestors(graph, node, predicate=RDFS.subClassOf):
    found, pending = {node}, [node]
    while pending:
        for parent in graph.objects(pending.pop(), predicate):
            if isinstance(parent, URIRef) and parent not in found:
                found.add(parent)
                pending.append(parent)
    return found


def _uris(value, seen=None):
    """Read expanded IRIs from SPARQL algebra, not prefix/substring guesses."""
    seen = set() if seen is None else seen
    if isinstance(value, URIRef):
        return {value}
    if isinstance(value, (str, Literal)) or id(value) in seen:
        return set()
    seen.add(id(value))
    children = value.values() if isinstance(value, dict) else vars(value).values() if isinstance(value, RDFPath) else value if isinstance(value, (list, tuple, set)) else ()
    return set().union(*(_uris(child, seen) for child in children)) if children else set()


def question_references(source):
    references = defaultdict(set)
    questions = []
    for match in QUESTION_PATTERN.finditer(source):
        identifier = match.group("title").split(".", 1)[0]
        if identifier in questions:
            raise ValueError(f"Duplicate competency question ID: {identifier}")
        questions.append(identifier)
        algebra = translateQuery(parseQuery(match.group("query"))).algebra
        for iri in _uris(algebra):
            references[iri].add(identifier)
    return questions, references


def _path_terms(graph, node, visited=None):
    visited = set() if visited is None else visited
    if isinstance(node, URIRef):
        return {node}
    if node in visited:
        return set()
    visited.add(node)
    terms = set()
    for predicate in (RDF.first, RDF.rest, SH.inversePath, SH.alternativePath,
                      SH.zeroOrMorePath, SH.oneOrMorePath, SH.zeroOrOnePath):
        for value in graph.objects(node, predicate):
            if value != RDF.nil:
                terms.update(_path_terms(graph, value, visited))
    return terms


def _shape_indexes(shapes):
    targets, paths = defaultdict(set), defaultdict(set)
    constraint_predicates = {
        SH["class"], SH.datatype, SH.nodeKind, SH.minCount, SH.maxCount,
        SH.minLength, SH.maxLength, SH.minInclusive, SH.maxInclusive,
        SH.minExclusive, SH.maxExclusive, SH.pattern, SH["in"], SH.hasValue,
        SH.equals, SH.disjoint, SH.lessThan, SH.lessThanOrEquals, SH.closed,
        SH.qualifiedMinCount, SH.qualifiedMaxCount, SH.sparql,
        SH.uniqueLang, SH.languageIn,
    }
    roots = {root for predicate in (SH.targetClass, SH.targetNode, SH.targetSubjectsOf, SH.targetObjectsOf, SH.target)
             for root in shapes.subjects(predicate, None)}
    for root in roots:
        seen, pending, active_constraints = set(), [root], []
        while pending:
            node = pending.pop()
            if node in seen or shapes.value(node, SH.deactivated) == Literal(True):
                continue
            seen.add(node)
            if any(list(shapes.objects(node, p)) for p in constraint_predicates):
                active_constraints.append(node)
            for predicate in (SH.property, SH.node, SH.qualifiedValueShape, SH["not"]):
                pending.extend(shapes.objects(node, predicate))
            for predicate in (SH["or"], SH["and"], SH.xone):
                for head in shapes.objects(node, predicate):
                    pending.extend(shapes.items(head))
        if active_constraints:
            for target in shapes.objects(root, SH.targetClass):
                targets[target].add(str(root))
            for constraint in active_constraints:
                for path in shapes.objects(constraint, SH.path):
                    for iri in _path_terms(shapes, path):
                        paths[iri].add(str(root))
    return targets, paths


def _expression(graph, value, visited=None):
    """Stable names for anonymous OWL expressions in generated reports."""
    if not isinstance(value, BNode):
        return str(value)
    visited = set() if visited is None else visited
    if value in visited:
        return "anonymous-cycle"
    visited.add(value)
    for predicate, name in ((OWL.unionOf, "union"), (OWL.intersectionOf, "intersection"), (OWL.oneOf, "oneOf")):
        head = graph.value(value, predicate)
        if head is not None:
            return name + "(" + ", ".join(sorted(_expression(graph, item, visited.copy()) for item in graph.items(head))) + ")"
    return "anonymous-expression"


def _instance_summary(data, schema, shapes, namespaces, validate=True):
    declared = set(schema.subjects())
    classes = {s for kind in (OWL.Class, RDFS.Class) for s in schema.subjects(RDF.type, kind)}
    properties = {s for kind in (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty)
                  for s in schema.subjects(RDF.type, kind)}
    targets, _ = _shape_indexes(shapes)
    typed = {subject for subject, kind in data.subject_objects(RDF.type)
             if subject not in declared and kind not in TERM_TYPES + (OWL.Ontology, SH.NodeShape)}
    is_local = lambda value: isinstance(value, URIRef) and any(str(value).startswith(ns) for ns in namespaces)
    unknown_classes = {kind for _, kind in data.subject_objects(RDF.type) if is_local(kind) and kind not in classes and kind not in declared}
    unknown_properties = {p for p in data.predicates() if is_local(p) and p not in properties}
    subjects = set(data.subjects())
    dangling = {o for _, p, o in data if p != RDF.type and is_local(o) and o not in subjects and o not in declared}
    uncovered = set()
    artifacts = set()
    for subject in typed:
        kinds = set(data.objects(subject, RDF.type))
        ancestors = set().union(*(_ancestors(schema, kind) for kind in kinds))
        if not ancestors.intersection(targets):
            uncovered.add(subject)
        if URIRef(CORE + "Artifact") in ancestors or URIRef("https://example.org/mv#MediaAsset") in ancestors or URIRef(PROV + "Entity") in kinds:
            artifacts.add(subject)
    provenance_fields = (URIRef(PROV + "wasDerivedFrom"), URIRef(PROV + "wasGeneratedBy"),
                         URIRef(PROV + "hadPrimarySource"), DCTERMS.source)
    linked = {s for s in artifacts if any(list(data.objects(s, p)) for p in provenance_fields)}
    identifiers = defaultdict(set)
    for subject, value in data.subject_objects(DCTERMS.identifier):
        if isinstance(value, Literal):
            identifiers[value].add(subject)
    enum_paths = defaultdict(set)
    for constraint, list_head in shapes.subject_objects(SH["in"]):
        path = shapes.value(constraint, SH.path)
        if isinstance(path, URIRef):
            enum_paths[path].update(shapes.items(list_head))
    unmapped = sum(1 for _, p, value in data if p in enum_paths and value not in enum_paths[p])
    records = set(data.subjects(RDF.type, URIRef(HEALTH + "PatientRecord")))
    classification = URIRef(HEALTH + "dataClassification")
    counts = Counter(value for record in records for value in data.objects(record, classification))
    known_classifications = {"Synthetic", "Pseudonymized", "Sensitive", "Unverified"}
    # Only fixed, known classification names escape into the report.
    privacy_counts = {name: counts[URIRef(HEALTH + name)] for name in sorted(known_classifications)}
    privacy_counts["missing"] = sum(not list(data.objects(record, classification)) for record in records)
    privacy_counts["unknown"] = sum(n for value, n in counts.items() if value not in {URIRef(HEALTH + name) for name in known_classifications})
    result = {
        "triples": len(data), "typed_subjects": len(typed),
        "subjects_without_class_shape": len(uncovered),
        "unknown_local_classes": len(unknown_classes), "unknown_local_properties": len(unknown_properties),
        "unresolved_local_references": len(dangling), "unmapped_enum_values": unmapped,
        "duplicate_identifier_groups": sum(len(values) > 1 for values in identifiers.values()),
        "artifact_candidates": len(artifacts), "artifacts_with_provenance_link": len(linked),
        "artifacts_without_provenance_link": len(artifacts - linked),
        "healthcare_classification_counts": privacy_counts,
        "shacl_conforms": None, "shacl_results": None,
    }
    if validate:
        phases = validate_phases(data, schema, shapes)
        result["validation_phases"] = public_summary(phases)
        result["shacl_conforms"] = phases["conforms"]
        result["shacl_results"] = phases["raw_results"] + phases["inferred_results"]
    return result


def build_report(root=ROOT, configs=None, validate_instances=True, include_projects=False, policy=None):
    root = Path(root)
    if configs is None:
        from app import ONTOLOGIES
        configs = ONTOLOGIES
    if policy is None:
        policy = json.loads((root / "ontology-quality-policy.json").read_text(encoding="utf-8"))
    schema, shapes = Graph(), Graph()
    owners = defaultdict(set)
    modules = []
    for filename in SCHEMA_FILES:
        graph = Graph().parse(root / filename, format="turtle")
        schema += graph
        ontologies = sorted(graph.subjects(RDF.type, OWL.Ontology), key=str)
        ontology = ontologies[0] if len(ontologies) == 1 else None
        modules.append({"file": filename, "ontology": str(ontology) if ontology else None,
                        "version": str(graph.value(ontology, OWL.versionInfo)) if ontology and graph.value(ontology, OWL.versionInfo) is not None else None,
                        "imports": sorted(str(value) for value in graph.objects(ontology, OWL.imports)) if ontology else []})
        for kind in TERM_TYPES:
            for term in graph.subjects(RDF.type, kind):
                if isinstance(term, URIRef):
                    owners[term].add(filename)
    registry = read_registry(root)
    configs = dict(configs)
    for module in registry['modules']:
        if module.get('example') and module.get('shapes') and not any(cfg['example'] == module['example'] for cfg in configs.values()):
            name = module.get('id') or Path(module['schema']).stem.removesuffix('-schema')
            configs.setdefault(name, {'schema': module['schema'], 'shapes': module['shapes'][0], 'example': module['example']})
    registered_shapes = {filename for module in registry['modules'] for filename in module.get('shapes', [])}
    for filename in sorted({cfg["shapes"] for cfg in configs.values()} | {"core-shapes.ttl", "property-contract-shapes.ttl"} | registered_shapes):
        shapes += Graph().parse(root / filename, format="turtle")
    questions, references = question_references((root / "COMPETENCY_QUESTIONS.md").read_text(encoding="utf-8"))
    for filename in sorted({module['questions'] for module in registry['modules'] if module.get('questions')}):
        added, links = question_references((root / filename).read_text(encoding='utf-8'))
        if set(added) & set(questions):
            raise ValueError('Supplemental competency question IDs must be unique')
        questions.extend(added)
        for term, identifiers in links.items():
            references[term].update(identifiers)
    targets, paths = _shape_indexes(shapes)
    namespaces = sorted({str(term).rsplit("#", 1)[0] + "#" if "#" in str(term)
                         else str(term).rsplit("/", 1)[0] + "/" for term in owners})
    exceptions = policy.get("exceptions", {})
    backlog = policy.get("cq_backlog", {})
    errors, rows = [], []
    for iri, reasons in exceptions.items():
        if URIRef(iri) not in owners:
            errors.append(f"Stale exception for undeclared term: {iri}")
        if not isinstance(reasons, dict) or any(not isinstance(reason, str) or not reason.strip() for reason in reasons.values()):
            errors.append(f"Exception requires a written reason: {iri}")
        elif set(reasons) - {"domain", "class_shape"}:
            errors.append(f"Unsupported quality exception: {iri}")
    for iri, reason in backlog.items():
        if URIRef(iri) not in owners or not isinstance(reason, str) or not reason.strip():
            errors.append(f"CQ backlog requires a declared term and reason: {iri}")
        elif references[URIRef(iri)]:
            errors.append(f"CQ backlog must be removed after coverage is added: {iri}")
    for term in sorted(owners, key=str):
        kinds = set(schema.objects(term, RDF.type))
        is_class = bool(kinds.intersection((OWL.Class, RDFS.Class)))
        applicable = set().union(*(targets[ancestor] for ancestor in _ancestors(schema, term))) if is_class else paths[term]
        domain, ranges = list(schema.objects(term, RDFS.domain)), list(schema.objects(term, RDFS.range))
        reasons = exceptions.get(str(term), {})
        gaps = []
        if "domain" in reasons and (is_class or domain):
            errors.append(f"Stale domain exception: {term}")
        if "class_shape" in reasons and (not is_class or applicable):
            errors.append(f"Stale class shape exception: {term}")
        if not is_class:
            if not domain:
                gaps.append("domain")
                if "domain" not in reasons:
                    errors.append(f"Property has no domain or documented exception: {term}")
            if not ranges:
                gaps.append("range")
                errors.append(f"Property has no range: {term}")
            if any(isinstance(value, Literal) for value in domain + ranges):
                errors.append(f"Property domain/range cannot be a literal: {term}")
            if OWL.ObjectProperty in kinds and any(str(value).startswith(str(XSD)) for value in ranges):
                errors.append(f"Object property has a datatype range: {term}")
            if not applicable:
                gaps.append("property_shape")
                errors.append(f"Property is absent from SHACL paths: {term}")
        elif not applicable:
            gaps.append("class_shape")
            if "class_shape" not in reasons:
                errors.append(f"Class has no applicable SHACL class target or documented exception: {term}")
        if not references[term]:
            gaps.append("cq")
            if str(term) not in backlog:
                errors.append(f"New competency question coverage gap: {term}")
        labels = {language: bool([value for value in schema.objects(term, RDFS.label) if getattr(value, "language", None) == language]) for language in ("ko", "en")}
        definitions = {language: bool([value for value in schema.objects(term, RDFS.comment) if getattr(value, "language", None) == language]) for language in ("ko", "en")}
        rows.append({"iri": str(term), "kind": "class" if is_class else "property", "sources": sorted(owners[term]),
                     "domain": sorted(_expression(schema, value) for value in domain),
                     "range": sorted(_expression(schema, value) for value in ranges),
                     "labels": labels, "definitions": definitions,
                     "shapes": sorted(applicable), "questions": sorted(references[term]),
                     "instance_uses": 0, "gaps": gaps, "exceptions": reasons,
                     "cq_backlog_reason": backlog.get(str(term)) if not references[term] else None})
    for predicate in (SH.targetClass, SH["class"]):
        for target in shapes.objects(None, predicate):
            if any(str(target).startswith(ns) for ns in namespaces) and not set(schema.objects(target, RDF.type)).intersection((OWL.Class, RDFS.Class)):
                errors.append(f"SHACL references an undeclared local class: {target}")
    all_path_terms = set().union(*(_path_terms(shapes, path) for path in shapes.objects(None, SH.path)))
    all_path_terms.update(shapes.objects(None, SH.targetSubjectsOf))
    all_path_terms.update(shapes.objects(None, SH.targetObjectsOf))
    for path in all_path_terms:
        if any(str(path).startswith(ns) for ns in namespaces) and not set(schema.objects(path, RDF.type)).intersection((OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty, RDF.Property)):
            errors.append(f"SHACL uses an undeclared local property: {path}")
    profiles = {}
    for name, cfg in sorted(configs.items()):
        domain_schema = load_schema_graph(root, cfg["schema"])
        domain_shapes = load_shape_graph(root, cfg["shapes"])
        data = Graph().parse(root / cfg["example"], format="turtle")
        profiles[name] = _instance_summary(data, domain_schema, domain_shapes, namespaces, validate_instances)
        module = next(item for item in modules if item["file"] == cfg["schema"])
        profiles[name]["schema_version"] = module["version"]
        if "version" in cfg and cfg["version"] != module["version"]:
            errors.append(f"Application profile version differs from its canonical schema: {name}")
        for row in rows:
            term = URIRef(row["iri"])
            row["instance_uses"] += len(set(data.subjects(RDF.type, term))) if row["kind"] == "class" else len(list(data.triples((None, term, None))))
        if profiles[name]["shacl_conforms"] is False:
            errors.append(f"Bundled profile does not conform to SHACL: {name}")
        if profiles[name]["unknown_local_classes"] or profiles[name]["unknown_local_properties"]:
            errors.append(f"Bundled profile uses undeclared local schema terms: {name}")
    projects = []
    if include_projects:
        project_root = (root / "projects").resolve()
        for path in sorted(project_root.glob("*/data.ttl")):
            if not path.resolve().is_relative_to(project_root) or path.parent.is_symlink():
                raise ValueError("Project data path escapes the project directory")
            metadata = json.loads((path.parent / "project.json").read_text(encoding="utf-8"))
            config = configs[metadata.get("ontology", "mv")]
            data = Graph().parse(path, format="turtle")
            project_schema = load_schema_graph(root, config["schema"])
            project_shapes = load_shape_graph(root, config["shapes"])
            # Ordinal only: no project names or instance identifiers in shared reports.
            stats = _instance_summary(data, project_schema, project_shapes, namespaces, validate_instances)
            if (path.parent / 'manifest.json').exists() and validate_instances:
                try:
                    for filename in ('evidence.ttl', 'evidence.json', 'manifest.json', 'project.json'):
                        evidence_path = path.parent / filename
                        if evidence_path.is_symlink() or not evidence_path.resolve().is_relative_to(path.parent.resolve()):
                            raise ValueError('Evidence path escapes its project')
                    from evidence import check_project
                    stats['provenance_evidence'] = check_project(path.parent)
                except (OSError, ValueError, TypeError, KeyError, SyntaxError, ParserError):
                    # Do not expose paths, parse errors, or clinical values.
                    stats['provenance_evidence'] = {'conforms': False, 'reason': 'Saved evidence is missing, unreadable, or invalid'}
                if not stats['provenance_evidence']['conforms']:
                    errors.append(f'Included project evidence does not conform: graph {len(projects) + 1}')
            projects.append(stats)
            if stats["shacl_conforms"] is False:
                errors.append(f"Included project graph does not conform to SHACL: graph {len(projects)}")
            if stats["unknown_local_classes"] or stats["unknown_local_properties"]:
                errors.append(f"Included project graph uses undeclared local schema terms: graph {len(projects)}")
    summary = {"terms": len(rows), "classes": sum(row["kind"] == "class" for row in rows),
               "properties": sum(row["kind"] == "property" for row in rows), "questions": len(questions),
               "terms_with_shapes": sum(bool(row["shapes"]) for row in rows),
               "terms_referenced_by_questions": sum(bool(row["questions"]) for row in rows),
               "terms_used_by_bundled_instances": sum(bool(row["instance_uses"]) for row in rows),
               "cq_backlog_terms": sum(not row["questions"] for row in rows),
               "structural_exceptions": sum(bool(row["exceptions"]) for row in rows),
               "profile_count": len(profiles), "project_count": len(projects)}
    return {"format_version": 1, "valid": not errors, "summary": summary,
            "errors": sorted(set(errors)), "modules": modules, "terms": rows, "profiles": profiles, "projects": projects,
            "limits": ["CQ coverage means a term is referenced by parsed query algebra; golden-answer tests verify behavior separately.",
                       "Instance use counts are explicit facts in bundled examples, without inferred duplicates.",
                       "Provenance links do not verify original model, prompt, source contents or generation quality.",
                       "Only counts are exported for instances; reports omit patient identities and SHACL value messages.",
                       "CQ backlog is remaining work, not completed test coverage."]}


def render_markdown(report):
    summary = report["summary"]
    lines = ["# 온톨로지 품질 현황", "", "이 보고서는 읽기 전용 점검 결과입니다. 인스턴스 정보는 집계 수치만 포함합니다.", "",
             "| 지표 | 수치 |", "|---|---:|"]
    lines.extend(f"| {key} | {value} |" for key, value in summary.items())
    lines.extend(["", "## 정본 모듈 버전", "", "| 파일 | 버전 | Ontology IRI |", "|---|---|---|"])
    for module in report["modules"]:
        lines.append(f"| {module['file']} | {module['version']} | {module['ontology']} |")
    lines.extend(["", "## 품질 게이트", "", "통과" if report["valid"] else "실패"])
    lines.extend(f"- {error}" for error in report["errors"])
    lines.extend(["", "## 인스턴스 집계", "", "| 프로파일 | 개체 | SHACL | 미선언 속성/유형 | 출처 관계 없는 자산 | 해결되지 않은 로컬 참조 |", "|---|---:|---|---:|---:|---:|"])
    for name, stats in report["profiles"].items():
        lines.append(f"| {name} | {stats['typed_subjects']} | {stats['shacl_conforms']} | {stats['unknown_local_properties'] + stats['unknown_local_classes']} | {stats['artifacts_without_provenance_link']} | {stats['unresolved_local_references']} |")
    lines.extend(["", "## 용어 연결표", "", "SHACL은 상위 클래스 target에서 상속된 제약을 포함합니다. CQ 없음은 미완료 항목입니다.", "",
                  "| 용어 | 종류 | SHACL 수 | CQ | 예제 사용 수 | 남은 공백 |", "|---|---|---:|---|---:|---|"])
    for row in report["terms"]:
        lines.append(f"| {row['iri']} | {row['kind']} | {len(row['shapes'])} | {', '.join(row['questions']) or '미포함'} | {row['instance_uses']} | {', '.join(row['gaps']) or '없음'} |")
    lines.extend(["", "## 구조 예외와 CQ 미포함 사유", ""])
    for row in report["terms"]:
        for kind, reason in row["exceptions"].items():
            lines.append(f"- `{row['iri']}` ({kind}): {reason}")
        if row["cq_backlog_reason"]:
            lines.append(f"- `{row['iri']}` (CQ 미포함): {row['cq_backlog_reason']}")
    lines.extend(["", "## 해석 범위", ""] + [f"- {limit}" for limit in report["limits"]])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=ROOT / ".runtime" / "ontology-quality.json")
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--include-projects", action="store_true", help="Inspect each registered graph separately, exporting aggregate counts only")
    parser.add_argument("--no-instance-validation", action="store_true", help="Report coverage only; shacl_conforms stays null")
    options = parser.parse_args(argv)
    report = build_report(validate_instances=not options.no_instance_validation, include_projects=options.include_projects)
    options.json.parent.mkdir(parents=True, exist_ok=True)
    options.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if options.markdown:
        options.markdown.parent.mkdir(parents=True, exist_ok=True)
        options.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"valid": report["valid"], **report["summary"]}, ensure_ascii=False))
    for error in report["errors"]:
        print(f"FAIL: {error}")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
