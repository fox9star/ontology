"""Operational production plans, explicit evidence and meaningful counterexamples."""

import json
from pathlib import Path
import re
import unittest

from rdflib import Graph, Literal, Namespace, RDF, RDFS
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, XSD

from benchmark_workload import query_answer
from ontology_loader import load_schema_graph, load_shape_graph
from ontology_quality import question_references
from validation_pipeline import validate_phases

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'custom-ontologies/ai-film'
FILM = Namespace('https://example.org/ontology/custom/ai-film#')
EX = Namespace('https://example.test/ai-film/')
PATTERN = re.compile(r'^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~', re.MULTILINE | re.DOTALL)


class AIFilmOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema_graph(ROOT, 'custom-ontologies/ai-film/schema.ttl')
        cls.shapes = load_shape_graph(ROOT, 'custom-ontologies/ai-film/shapes.ttl')
        cls.fixture = Graph().parse(FOLDER / 'question-fixture.ttl', format='turtle')
        cls.queries = {match.group('title').split('.', 1)[0]: match.group('query')
                       for match in PATTERN.finditer((FOLDER / 'questions.md').read_text(encoding='utf-8'))}

    def clone(self):
        return Graph() + self.fixture

    def assert_acceptance(self, graph, expected):
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertEqual(result['raw_conforms'], expected, result['raw_report_text'])
        self.assertEqual(result['inferred_conforms'], expected, result['inferred_report_text'])
        return result

    def approved_synthetic_graph(self):
        """Construct a test-only ready state; URNs denote imaginary test evidence."""
        graph = self.clone()
        for number in ('01', '02'):
            task, asset = EX['task' + number], EX['asset' + number]
            graph.set((task, FILM.taskStatus, Literal('completed')))
            graph.add((task, FILM.generationEvidenceUri, Literal('urn:synthetic:run:' + number, datatype=XSD.anyURI)))
            graph.set((asset, FILM.assetStatus, Literal('available')))
            graph.add((asset, FILM.assetUri, Literal('urn:synthetic:asset:' + number, datatype=XSD.anyURI)))
            graph.add((asset, FILM.sourceEvidenceUri, Literal('urn:synthetic:source:' + number, datatype=XSD.anyURI)))
            for kind in ('rights', 'quality'):
                review = EX[kind + number]
                graph.set((review, FILM.decision, Literal('approved')))
                graph.add((review, FILM.reviewEvidenceUri, Literal('urn:synthetic:review:' + kind + number, datatype=XSD.anyURI)))
        graph.set((EX.edit01, FILM.editStatus, Literal('approved')))
        return graph

    def test_schema_exports_and_bilingual_definitions_match(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        self.assertTrue(isomorphic(schema, Graph().parse(FOLDER / 'schema.owl', format='xml')))
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        self.assertEqual(len(terms), 34)
        for term in terms:
            for predicate in (RDFS.label, RDFS.comment):
                self.assertEqual({value.language for value in schema.objects(term, predicate)}, {'ko', 'en'})

    def test_planned_fixture_is_valid_without_fabricated_execution_or_rights(self):
        self.assert_acceptance(self.clone(), True)
        for predicate in (FILM.modelIdentifier, FILM.generationEvidenceUri, FILM.assetUri,
                          FILM.sourceEvidenceUri, FILM.reviewEvidenceUri):
            self.assertEqual(list(self.fixture.triples((None, predicate, None))), [])
        self.assertEqual(set(self.fixture.objects(None, FILM.decision)), {Literal('pending')})
        self.assertEqual(set(self.fixture.objects(None, FILM.taskStatus)), {Literal('planned')})

    def test_all_five_questions_match_independently_specified_golden_rows(self):
        answers = json.loads((FOLDER / 'question-answers.json').read_text(encoding='utf-8'))
        self.assertEqual(set(answers), set(self.queries))
        self.assertEqual(len(answers), 5)
        for identifier, query in self.queries.items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(self.fixture, query), answers[identifier])

    def test_questions_reference_every_named_film_term(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        _, references = question_references((FOLDER / 'questions.md').read_text(encoding='utf-8'))
        self.assertEqual(terms - references.keys(), set())

    def test_missing_explicit_endpoint_type_is_not_repaired_by_acceptance(self):
        graph = self.clone()
        graph.remove((EX.asset01, RDF.type, FILM.MediaAsset))
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_missing_required_prompt_and_conflicting_task_states_fail(self):
        graph = self.clone()
        graph.remove((EX.task01, FILM.promptText, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.task01, FILM.taskStatus, Literal('running')))
        self.assert_acceptance(graph, False)

    def test_duplicate_shot_order_and_nonpositive_duration_fail(self):
        graph = self.clone()
        graph.set((EX.shot02, FILM.shotOrder, Literal(1)))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.shot01, FILM.targetDurationSeconds, Literal('0', datatype=XSD.decimal)))
        self.assert_acceptance(graph, False)

    def test_model_unknown_cannot_be_silently_replaced_by_guessed_identifier(self):
        graph = self.clone()
        graph.add((EX.task01, FILM.modelIdentifier, Literal('guessed-model')))
        self.assert_acceptance(graph, False)
        graph.set((EX.task01, FILM.modelKnowledgeStatus, Literal('recorded')))
        self.assert_acceptance(graph, True)
        graph.remove((EX.task01, FILM.modelIdentifier, None))
        self.assert_acceptance(graph, False)

    def test_completion_and_approval_without_evidence_fail(self):
        for subject, predicate, value in ((EX.task01, FILM.taskStatus, 'completed'),
                                          (EX.asset01, FILM.assetStatus, 'available'),
                                          (EX.rights01, FILM.decision, 'approved'),
                                          (EX.edit01, FILM.editStatus, 'approved')):
            with self.subTest(subject=subject):
                graph = self.clone()
                graph.set((subject, predicate, Literal(value)))
                self.assert_acceptance(graph, False)

    def test_ready_edit_query_requires_every_asset_and_approval_evidence(self):
        graph = self.approved_synthetic_graph()
        self.assert_acceptance(graph, True)
        self.assertEqual(query_answer(graph, self.queries['AIF-05'])['rows'],
                         [[str(EX.project), str(EX.edit01), 'draft-01', '2']])
        self.assertEqual(query_answer(graph, self.queries['AIF-04'])['rows'], [])
        graph.remove((EX.rights02, FILM.reviewEvidenceUri, None))
        self.assert_acceptance(graph, False)
        self.assertEqual(query_answer(graph, self.queries['AIF-05'])['rows'], [])
        self.assertEqual(query_answer(graph, self.queries['AIF-04'])['rows'],
                         [[str(EX.edit01), 'draft-01', str(EX.asset02), 'rights-review-incomplete']])

    def test_missing_generation_link_changes_work_queue_answer(self):
        graph = self.clone()
        graph.remove((EX.shot02, FILM.hasGenerationTask, EX.task02))
        answer = query_answer(graph, self.queries['AIF-01'])
        self.assertEqual(len(answer['rows']), 1)
        self.assertEqual(answer['rows'][0][3], str(EX.shot01))
        self.assert_acceptance(graph, False)


if __name__ == '__main__':
    unittest.main()
