"""Conservative consumer contract gate for SHACL, selected HTTP APIs and CQs.

Baselines are written only by an explicit --write-baseline command. Shape and
fixture changes require review; added operations/questions are allowed when
previous contracts remain intact. Schema axioms have a separate existing gate.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re

from rdflib import Dataset, Graph, URIRef
from rdflib.compare import to_canonical_graph
from rdflib.namespace import RDFS, SH
from rdflib.plugins.sparql.algebra import translateQuery
from rdflib.plugins.sparql.parser import parseQuery

from ontology_loader import load_schema_graph, load_shape_graph
from validation_pipeline import validate_phases
from ontology_registry import read_registry

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "consumer-compatibility-baseline.json"
CASES = "tests/fixtures/consumer_compatibility_cases.trig"
CASE_NS = "https://example.test/consumer/"
QUESTIONS = re.compile(r"^###\s+(?P<title>.+?)\n(?:.*?\n)?~~~sparql\n(?P<query>.*?)\n~~~", re.MULTILINE | re.DOTALL)
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
SAFE_HTTP_PATHS = ("/api/v1/domains", "/api/v1/auth/identity")
DOMAIN_BY_CODE = {"MV": "mv", "E2E": "e2e", "DEV": "devops", "AG": "agent", "EC": "ecommerce", "AC": "academic"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def semantic_shape_snapshot(graph):
    """Ignore presentation annotations and canonicalize anonymous RDF nodes."""
    semantics = Graph()
    annotations = {SH.message, SH.name, SH.description, SH.order, RDFS.label, RDFS.comment}
    for subject, predicate, obj in graph:
        if predicate not in annotations:
            semantics.add((subject, predicate, obj))
    canonical = to_canonical_graph(semantics)
    triples = sorted(f"{subject.n3()} {predicate.n3()} {obj.n3()} ." for subject, predicate, obj in canonical)
    return {"sha256": hashlib.sha256("\n".join(triples).encode("utf-8")).hexdigest(), "triples": triples}


def response_shape(value):
    """Save JSON keys and types, never response values or patient data."""
    if isinstance(value, dict):
        return {"type": "object", "properties": {key: response_shape(child) for key, child in sorted(value.items())}}
    if isinstance(value, list):
        shapes = {json.dumps(response_shape(item), sort_keys=True) for item in value}
        return {"type": "array", "items": [json.loads(item) for item in sorted(shapes)]}
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    raise ValueError("Unsupported response value type")


def _contract_json(value):
    """Strip prose/examples, preserving declared constraints and response codes."""
    if isinstance(value, dict):
        return {key: _contract_json(child) for key, child in sorted(value.items())
                if key not in {"description", "summary", "example", "examples", "externalDocs", "tags"}}
    if isinstance(value, list):
        return [_contract_json(item) for item in value]
    return value


def openapi_snapshot(spec):
    operations = {}
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            contract = {key: operation[key] for key in ("operationId", "parameters", "requestBody", "responses", "security", "deprecated") if key in operation}
            if path_item.get("parameters"):
                contract["pathParameters"] = path_item["parameters"]
            if "security" not in contract and "security" in spec:
                contract["security"] = spec["security"]
            operations[method.upper() + " " + path] = _contract_json(contract)
    return {"operations": operations, "components": _contract_json(spec.get("components", {}))}


def _query_map(root):
    result = {}
    files = {"COMPETENCY_QUESTIONS.md", "EVIDENCE_QUESTIONS.md"}
    files.update(module['questions'] for module in read_registry(root)['modules'] if module.get('questions'))
    for filename in sorted(files):
        path = root / filename
        if not path.exists():
            continue
        for match in QUESTIONS.finditer(path.read_text(encoding="utf-8")):
            identifier = match.group("title").split(".", 1)[0]
            if identifier in result:
                raise ValueError("Duplicate question identifier")
            result[identifier] = match.group("query")
    return result


def question_snapshot(root=ROOT, configs=None):
    root = Path(root)
    if configs is None:
        import app
        configs = app.ONTOLOGIES
    golden = {}
    for name in ("competency_answers.json", "business_answers.json"):
        path = root / "tests/fixtures" / name
        if path.is_file():
            golden.update(json.loads(path.read_text(encoding="utf-8")))
    # BMV answers are independently calculated from a deterministic design.
    from benchmark_workload import expected_answers, generate_workload, query_answer
    benchmark, metadata = generate_workload(1000)
    golden.update(expected_answers(metadata))
    queries = _query_map(root)
    supplemental = {}
    for module in read_registry(root)['modules']:
        if not module.get('question_answers'):
            continue
        answers = json.loads((root / module['question_answers']).read_text(encoding='utf-8'))
        fixture = Graph().parse(root / module['questions_fixture'], format='turtle')
        fixture += load_schema_graph(root, module['schema'])
        for identifier, answer in answers.items():
            if identifier in golden or identifier in supplemental:
                raise ValueError('Supplemental question IDs must be unique')
            supplemental[identifier] = (answer, fixture, module)
    snapshot = {}
    for identifier, query in queries.items():
        algebra = translateQuery(parseQuery(query)).algebra
        variables = [str(value) for value in algebra.get("PV", [])]
        if identifier in supplemental:
            answer, fixture, module = supplemental[identifier]
            if query_answer(fixture, query) != answer:
                raise ValueError('Supplemental question differs from its frozen expected answer')
            inputs = [module['questions_fixture'], module['question_answers']]
        elif identifier.startswith("EV-"):
            evidence = Graph().parse(root / "evidence-example.ttl", format="turtle")
            evidence += load_schema_graph(root, "evidence-schema.ttl")
            answer = query_answer(evidence, query)
            inputs = ["evidence-example.ttl"]
        else:
            if identifier not in golden:
                raise ValueError("A competency question lacks a reviewed answer contract")
            answer = golden[identifier]
            if identifier.startswith("SYN-"):
                inputs = ["tests/fixtures/competency_synthetic.trig"]
            elif identifier.startswith("BUS-"):
                inputs = ["tests/fixtures/business_scenarios.trig"]
            elif identifier.startswith("BMV-"):
                inputs = ["benchmark_workload.py"]
                if query_answer(benchmark, query) != answer:
                    raise ValueError("Benchmark question disagrees with independent expected answer")
            elif identifier.startswith("HC-"):
                # These questions use a tiny constructed aggregate-only graph,
                # never healthcare-example.ttl or a selected patient dataset.
                inputs = ["tests/test_competency_questions.py"]
            else:
                domain = DOMAIN_BY_CODE[identifier.split("-", 1)[0]]
                inputs = [configs[domain]["example"]]
        if variables != answer["variables"]:
            raise ValueError("Query output variables disagree with the answer contract")
        snapshot[identifier] = {"variables": variables, "golden_answer": answer,
                                "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                                "input_sha256": {name: digest(root / name) for name in inputs}}
    return snapshot


def build_snapshot(root=ROOT):
    root = Path(root).resolve()
    import app
    from openapi_spec import OPENAPI_SPEC
    profiles = dict(app.ONTOLOGIES)
    profiles["evidence"] = {"schema": "evidence-schema.ttl", "shapes": "evidence-shapes.ttl"}
    cases = Dataset(default_union=False).parse(root / CASES, format="trig")
    supplemental_cases = {}
    for module in read_registry(root)['modules']:
        if module.get('compatibility_cases'):
            cases.parse(root / module['compatibility_cases'], format='trig')
            supplemental_cases[module['schema']] = digest(root / module['compatibility_cases'])
    shape_contracts, acceptance = {}, {}
    for key, config in profiles.items():
        schema = load_schema_graph(root, config["schema"])
        shapes = load_shape_graph(root, config["shapes"])
        shape_contracts[key] = semantic_shape_snapshot(shapes)
        for outcome in ("accept", "reject"):
            case = key + "-" + outcome
            graph = cases.graph(URIRef(CASE_NS + case))
            if not len(graph):
                raise ValueError("A profile lacks a frozen synthetic compatibility case")
            phased = validate_phases(graph, schema, shapes)
            acceptance[case] = {"profile": key, "raw_conforms": phased["raw_conforms"],
                                "inferred_conforms": phased["inferred_conforms"]}
            if config['schema'] in supplemental_cases:
                acceptance[case]['fixture_sha256'] = supplemental_cases[config['schema']]
            if phased["conforms"] != (outcome == "accept"):
                raise ValueError("A frozen synthetic compatibility case changed acceptance")
    http = {}
    with app.app.test_client() as client:
        for path in SAFE_HTTP_PATHS:
            response = client.get(path, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
            if response.status_code != 200 or not response.is_json:
                raise ValueError("A selected read-only HTTP response failed")
            http["GET " + path] = {"status": response.status_code, "mimetype": response.mimetype,
                                  "json": response_shape(response.get_json())}
    return {"format_version": 1, "scope": "bounded-consumer-compatibility",
            "shacl": shape_contracts, "acceptance_cases": acceptance,
            "acceptance_fixture_sha256": digest(root / CASES),
            "openapi": openapi_snapshot(OPENAPI_SPEC), "http_responses": http,
            "competency_questions": question_snapshot(root, profiles),
            "limits": ["Separate schema-axiom compatibility gate still required.",
                       "HTTP coverage includes two read-only endpoint key/type contracts, not all API behavior.",
                       "Frozen acceptance cases are constructed examples, not exhaustive contract equivalence.",
                       "FHIR/clinical/partner-profile compatibility is not asserted."]}


def _shape_issues(old, new, path):
    if old.get("type") != new.get("type"):
        return [path + ": JSON response type changed"]
    issues = []
    if old["type"] == "object":
        for key, contract in old["properties"].items():
            if key not in new.get("properties", {}):
                issues.append(path + "." + key + ": JSON response field removed")
            else:
                issues.extend(_shape_issues(contract, new["properties"][key], path + "." + key))
    elif old["type"] == "array":
        for index, contract in enumerate(old["items"]):
            candidates = [candidate for candidate in new.get("items", []) if not _shape_issues(contract, candidate, path + "[]")]
            if not candidates:
                issues.append(path + "[]: previously observed array item contract changed")
    return issues


def compare_snapshots(baseline, current):
    issues, additions = [], []
    if baseline.get("format_version") != current.get("format_version"):
        issues.append("Unsupported consumer baseline format change")
    for profile, contract in baseline.get("shacl", {}).items():
        if current.get("shacl", {}).get(profile) != contract:
            issues.append("SHACL semantic contract changed or was removed: " + profile)
    for name, expected in baseline.get("acceptance_cases", {}).items():
        if current.get("acceptance_cases", {}).get(name) != expected:
            issues.append("Frozen synthetic raw/inferred acceptance changed: " + name)
    if current.get("acceptance_fixture_sha256") != baseline.get("acceptance_fixture_sha256"):
        issues.append("Frozen synthetic acceptance fixture changed")
    old_ops = baseline.get("openapi", {}).get("operations", {})
    new_ops = current.get("openapi", {}).get("operations", {})
    for operation, contract in old_ops.items():
        if operation not in new_ops:
            issues.append("OpenAPI operation removed: " + operation)
        elif contract != new_ops[operation]:
            issues.append("OpenAPI operation/response declaration changed: " + operation)
    for operation in new_ops.keys() - old_ops.keys():
        additions.append("OpenAPI operation added: " + operation)
    if baseline.get("openapi", {}).get("components", {}) != current.get("openapi", {}).get("components", {}):
        issues.append("OpenAPI reusable component contracts changed")
    for endpoint, expected in baseline.get("http_responses", {}).items():
        actual = current.get("http_responses", {}).get(endpoint)
        if actual is None:
            issues.append("Selected HTTP response contract removed: " + endpoint)
        elif (expected["status"], expected["mimetype"]) != (actual["status"], actual["mimetype"]):
            issues.append("Selected HTTP response status or media type changed: " + endpoint)
        else:
            issues.extend(_shape_issues(expected["json"], actual["json"], endpoint))
    old_questions = baseline.get("competency_questions", {})
    new_questions = current.get("competency_questions", {})
    for identifier, contract in old_questions.items():
        if identifier not in new_questions:
            issues.append("Competency question removed: " + identifier)
        elif contract != new_questions[identifier]:
            issues.append("Competency question query/variables/golden/input contract changed: " + identifier)
    for identifier in new_questions.keys() - old_questions.keys():
        additions.append("Competency question added: " + identifier)
    return {"status": "major-review-required" if issues else "compatible",
            "compatible": not issues, "issues": issues, "allowed_additions": sorted(additions),
            "scope": "bounded-consumer-compatibility", "limits": current.get("limits", [])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/consumer-compatibility.json")
    parser.add_argument("--write-baseline", action="store_true", help="Explicitly record a reviewed baseline; never automatic.")
    args = parser.parse_args(argv)
    try:
        current = build_snapshot()
        if args.write_baseline:
            args.baseline.parent.mkdir(parents=True, exist_ok=True)
            args.baseline.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": "baseline-written", "profiles": len(current["shacl"]), "questions": len(current["competency_questions"])}))
            return 0
        if not args.baseline.is_file():
            report = {"status": "blocked", "compatible": False, "issues": ["Consumer baseline is absent; explicit reviewed initialization is required."]}
        else:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            report = compare_snapshots(baseline, current)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        report = {"status": "blocked", "compatible": False,
                  "issues": ["Consumer contract collection failed: " + type(exc).__name__]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "compatible": report["compatible"], "issue_count": len(report.get("issues", []))}))
    return 0 if report["compatible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
