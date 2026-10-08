"""Execute the documented competency questions against fixed profile fixtures."""

import json
import re
import sys
import unittest
from pathlib import Path

from rdflib import Dataset, Graph, Literal, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as studio
import healthcare_privacy
import owl_reasoner
import pyshacl
from benchmark_workload import catalog_queries, expected_answers, generate_workload, query_answer
from ontology_loader import load_schema_graph, load_shape_graph


QUESTION_PATTERN = re.compile(
    r"^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~",
    re.MULTILINE | re.DOTALL,
)
DOMAIN_BY_CODE = {
    "MV": "mv", "E2E": "e2e", "DEV": "devops", "AG": "agent",
    "EC": "ecommerce", "HC": "healthcare", "AC": "academic",
}
HEALTH = Namespace("http://example.org/ontology/healthcare#")
EX = Namespace("https://example.test/competency/")
MV = Namespace("https://example.org/mv#")
PROV = Namespace("http://www.w3.org/ns/prov#")
BUSINESS = Namespace("https://example.test/business/")
DEV = Namespace("http://example.org/ontology/devops#")
AG = Namespace("https://example.org/agent#")


def _business_dataset():
    dataset = Dataset(default_union=False)
    dataset.parse(ROOT / "tests" / "fixtures" / "business_scenarios.trig", format="trig")
    return dataset


def _synthetic_healthcare_graph():
    """Provide synthetic-only records to exercise the privacy-safe HC queries."""
    graph = Graph()
    record = HEALTH.SyntheticQuestionFixture
    graph.add((record, RDF.type, HEALTH.PatientRecord))
    graph.add((record, HEALTH.dataClassification, HEALTH.Synthetic))
    for local_id, status in (("PendingFixture", "PENDING"), ("CompletedFixture", "COMPLETED")):
        task = HEALTH[local_id]
        graph.add((task, RDF.type, HEALTH.DiagnosticTask))
        graph.add((task, HEALTH.associatedWithRecord, record))
        graph.add((task, HEALTH.diagnosticStatus, Literal(status)))
    return healthcare_privacy.redact_graph(graph)


def _query_rows(graph, query):
    result = graph.query(query)
    variables = [str(variable) for variable in (result.vars or [])]
    rows = [[None if row[variable] is None else str(row[variable]) for variable in variables]
            for row in result]
    return variables, rows


def _synthetic_query_graph(question_id, inference=True):
    dataset = Dataset(default_union=False)
    dataset.parse(ROOT / "tests" / "fixtures" / "competency_synthetic.trig", format="trig")
    if question_id in {"SYN-05", "SYN-06", "SYN-10"}:
        return dataset
    graph = dataset.default_graph
    if inference and question_id in {"SYN-07", "SYN-08"}:
        graph += load_schema_graph(ROOT, "mv-schema.ttl")
        result = owl_reasoner.run_owl_deductive_closure(graph)
        if not result["consistent"]:
            raise AssertionError(result["semantic_violations"])
    return graph


def _questions():
    source = (ROOT / "COMPETENCY_QUESTIONS.md").read_text(encoding="utf-8")
    return {match.group("title").split(".", 1)[0]: match.group("query")
            for match in QUESTION_PATTERN.finditer(source)}


class CompetencyQuestionTests(unittest.TestCase):
    def test_documented_questions_match_golden_answers(self):
        questions = _questions()
        self.assertEqual(len(questions), 37, "Update the golden set when competency questions change.")

        expected_path = ROOT / "tests" / "fixtures" / "competency_answers.json"
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        observed = {}
        for question_id, query in questions.items():
            code = question_id.split("-", 1)[0]
            if code in {"BUS", "BMV"}:
                continue
            if code == "SYN":
                graph = _synthetic_query_graph(question_id)
            else:
                domain = DOMAIN_BY_CODE[code]
                graph = (_synthetic_healthcare_graph() if domain == "healthcare"
                         else studio._load_response_graph(domain, None, False))
            variables, rows = _query_rows(graph, query)
            observed[question_id] = {"variables": variables, "rows": rows}

        self.assertEqual(set(observed), set(expected))
        for question_id, answer in expected.items():
            with self.subTest(question=question_id):
                self.assertEqual(observed[question_id], answer)

    def test_inference_questions_require_schema_expansion(self):
        for question_id in ("SYN-07", "SYN-08"):
            with self.subTest(question=question_id):
                query = _questions()[question_id]
                self.assertEqual(_query_rows(_synthetic_query_graph(question_id, inference=False), query)[1], [])
                self.assertEqual(len(_query_rows(_synthetic_query_graph(question_id), query)[1]), 1)

    def test_empty_lineage_case_becomes_visible_when_provenance_is_recorded(self):
        graph = _synthetic_query_graph("SYN-09")
        query = _questions()["SYN-09"]
        self.assertEqual(_query_rows(graph, query)[1], [])
        graph.add((EX.unverifiedAsset, PROV.wasDerivedFrom, EX.syntheticNewSource))
        self.assertEqual(_query_rows(graph, query)[1], [[str(EX.syntheticNewSource)]])

    def test_cross_project_link_diagnostic_detects_a_leaked_reference(self):
        dataset = _synthetic_query_graph("SYN-10")
        query = _questions()["SYN-10"]
        self.assertEqual(_query_rows(dataset, query)[1], [])
        dataset.graph(EX.alpha).add((EX.alphaProject, MV.hasImage, EX.betaAsset))
        self.assertEqual(_query_rows(dataset, query)[1], [[str(EX.betaAsset)]])

    def test_unselected_project_cannot_change_scoped_query(self):
        dataset = _synthetic_query_graph("SYN-05")
        query = _questions()["SYN-05"]
        before = _query_rows(dataset, query)
        dataset.graph(EX.beta).add((EX.betaProject, MV.hasImage, EX.betaNewAsset))
        dataset.graph(EX.beta).add((EX.betaNewAsset,
                                   Namespace("http://purl.org/dc/terms/").identifier,
                                   Literal("SHARED-001")))
        self.assertEqual(_query_rows(dataset, query), before)
        self.assertEqual(before[1], [[str(EX.alphaAsset), "SHARED-001"]])

    def test_private_healthcare_example_never_enters_golden_answers(self):
        serialized = json.dumps(
            json.loads((ROOT / "tests" / "fixtures" / "competency_answers.json").read_text(encoding="utf-8"))
        )
        self.assertNotIn("PATIENT-9081", serialized)
        self.assertNotIn("Patient_P9081", serialized)

    def test_business_questions_match_reviewed_golden_answers(self):
        expected = json.loads((ROOT / "tests" / "fixtures" / "business_answers.json").read_text(encoding="utf-8"))
        dataset = _business_dataset()
        questions = {key: value for key, value in _questions().items() if key.startswith("BUS-")}
        self.assertEqual(set(expected), set(questions))
        for identifier, query in questions.items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(dataset, query), expected[identifier])

    def test_business_normal_is_valid_and_bad_variants_fail_validation(self):
        schema, shapes = Graph(), Graph()
        for domain in ("devops", "agent", "mv"):
            schema += load_schema_graph(ROOT, f"{domain}-schema.ttl")
            shapes += load_shape_graph(ROOT, f"{domain}-shapes.ttl")
        dataset = _business_dataset()
        for case, expected in (("normal", True), ("missing", False), ("conflict", False)):
            with self.subTest(case=case):
                conforms, _, details = pyshacl.validate(dataset.graph(BUSINESS[case]), shacl_graph=shapes,
                                                        ont_graph=schema, inference="none", advanced=True)
                self.assertEqual(conforms, expected, details)

    def test_one_edge_mutations_break_success_and_raise_diagnostics(self):
        # Removing one recorded edge must affect the answer and its diagnosis.
        mutations = (
            ("BUS-01", "BUS-02", (BUSINESS.deploy, DEV.deploysArtifact, BUSINESS.package)),
            ("BUS-03", "BUS-04", (BUSINESS.review, AG.hasDecision, BUSINESS.accepted)),
            ("BUS-05", "BUS-06", (BUSINESS.video, MV.usesAudio, BUSINESS.audio)),
        )
        for success_id, diagnostic_id, edge in mutations:
            with self.subTest(question=success_id):
                source = _business_dataset().graph(BUSINESS.normal)
                dataset = Dataset(default_union=False)
                graph = dataset.graph(BUSINESS.normal)
                graph += source
                success_before = query_answer(dataset, _questions()[success_id])
                diagnostic_before = query_answer(dataset, _questions()[diagnostic_id])
                self.assertEqual(len(success_before["rows"]), 1)
                self.assertEqual(diagnostic_before["rows"], [])
                graph.remove(edge)
                self.assertEqual(query_answer(dataset, _questions()[success_id])["rows"], [])
                self.assertNotEqual(query_answer(dataset, _questions()[diagnostic_id]), diagnostic_before)

    def test_wrong_review_and_deployed_artifact_do_not_satisfy_success_chain(self):
        for identifier, diagnostic, edge, replacement in (
            ("BUS-01", "BUS-02", (BUSINESS.deploy, DEV.deploysArtifact, BUSINESS.package), BUSINESS.unbuiltPackage),
            ("BUS-03", "BUS-04", (BUSINESS.accepted, AG.decisionAbout, BUSINESS.document), BUSINESS.unrelatedDocument),
            ("BUS-03", "BUS-04", (BUSINESS.handoff, AG.toAgent, BUSINESS.reviewer), BUSINESS.author),
        ):
            with self.subTest(question=identifier):
                dataset = Dataset(default_union=False)
                graph = dataset.graph(BUSINESS.normal)
                graph += _business_dataset().graph(BUSINESS.normal)
                graph.remove(edge)
                graph.add((edge[0], edge[1], replacement))
                self.assertEqual(query_answer(dataset, _questions()[identifier])["rows"], [])
                self.assertEqual(len(query_answer(dataset, _questions()[diagnostic])["rows"]), 1)

    def test_catalog_workload_answers_are_independently_calculated(self):
        graph, metadata = generate_workload(1000)
        for identifier, query in catalog_queries().items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(graph, query), expected_answers(metadata)[identifier])

    def test_lost_generation_link_preserves_uncertainty_and_changes_answer(self):
        dataset = Dataset(default_union=False)
        graph = dataset.graph(BUSINESS.normal)
        graph += _business_dataset().graph(BUSINESS.normal)
        before = query_answer(dataset, _questions()["BUS-05"])
        graph.remove((BUSINESS.image, PROV.wasGeneratedBy, BUSINESS.generation))
        after = query_answer(dataset, _questions()["BUS-05"])
        self.assertEqual(len(after["rows"]), 1)
        self.assertNotEqual(before, after)
        self.assertEqual(after["rows"][0][-1], "generation-metadata-not-recorded")
        self.assertEqual(query_answer(dataset, _questions()["BUS-06"])["rows"][0][-1],
                         "generation-evidence-not-recorded")


if __name__ == "__main__":
    unittest.main()
