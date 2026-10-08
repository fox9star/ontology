"""Swimming results stay evidenced, course-aware and internally consistent."""

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
FOLDER = ROOT / 'custom-ontologies/swimming'
SW = Namespace('https://example.org/ontology/custom/swimming#')
EX = Namespace('https://example.test/swimming/')
PATTERN = re.compile(r'^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~', re.MULTILINE | re.DOTALL)


def decimal(value):
    return Literal(value, datatype=XSD.decimal)


class SwimmingOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema_graph(ROOT, 'custom-ontologies/swimming/schema.ttl')
        cls.shapes = load_shape_graph(ROOT, 'custom-ontologies/swimming/shapes.ttl')
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

    def assert_each_fails(self, cases):
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate, value=value):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def assert_removal_fails(self, cases):
        for subject, predicate in cases:
            with self.subTest(subject=subject, removed=predicate):
                graph = self.clone()
                graph.remove((subject, predicate, None))
                self.assert_acceptance(graph, False)

    def test_schema_exports_and_bilingual_definitions_match(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        self.assertTrue(isomorphic(schema, Graph().parse(FOLDER / 'schema.owl', format='xml')))
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        self.assertEqual(len(terms), 29)
        for term in terms:
            for predicate in (RDFS.label, RDFS.comment):
                self.assertEqual({value.language for value in schema.objects(term, predicate)}, {'ko', 'en'})

    def test_example_and_fixture_describe_the_same_graph_and_are_valid(self):
        self.assert_acceptance(self.clone(), True)
        example = Graph().parse(FOLDER / 'example.ttl', format='turtle')
        self.assert_acceptance(example, True)
        self.assertEqual(len(example), len(self.fixture))

    def test_all_ten_questions_match_independently_specified_golden_rows(self):
        answers = json.loads((FOLDER / 'question-answers.json').read_text(encoding='utf-8'))
        self.assertEqual(set(answers), set(self.queries))
        self.assertEqual(len(answers), 10)
        for identifier, query in self.queries.items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(self.fixture, query), answers[identifier])

    def test_questions_reference_every_named_swimming_term(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        _, references = question_references((FOLDER / 'questions.md').read_text(encoding='utf-8'))
        self.assertEqual(terms - references.keys(), set())

    def test_missing_explicit_endpoint_type_is_not_repaired_by_acceptance(self):
        graph = self.clone()
        graph.remove((EX.clubA, RDF.type, SW.Club))
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_official_results_need_a_time_and_timing_evidence(self):
        self.assert_removal_fails(((EX.entryB2, SW.finalTimeSeconds), (EX.entryB2, SW.timingEvidenceUri)))
        self.assert_each_fails((
            (EX.entryB2, SW.finalTimeSeconds, decimal('0')),
            (EX.entryB2, SW.timingEvidenceUri, Literal('ftp://example.test/x', datatype=XSD.anyURI)),
            (EX.entryB2, SW.entryStatus, Literal('won')),
            (EX.entryB2, SW.placeRank, Literal(0)),
        ))

    def test_disqualification_needs_reason_and_evidence_and_has_no_time_or_rank(self):
        self.assert_removal_fails(((EX.entryD2, SW.disqualificationReason), (EX.entryD2, SW.timingEvidenceUri)))
        for predicate, value in ((SW.finalTimeSeconds, decimal('60.00')), (SW.placeRank, Literal(2))):
            with self.subTest(added=predicate):
                graph = self.clone()
                graph.add((EX.entryD2, predicate, value))
                self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.entryB2, SW.disqualificationReason, Literal('other')))
        self.assert_acceptance(graph, False)

    def test_unfinished_states_cannot_carry_result_facts(self):
        for entry, predicate, value in (
            (EX.entryA3, SW.finalTimeSeconds, decimal('70.00')),
            (EX.entryA3, SW.timingEvidenceUri, Literal('urn:synthetic:x', datatype=XSD.anyURI)),
            (EX.entryA7, SW.finalTimeSeconds, decimal('126.00')),
            (EX.entryA7, SW.placeRank, Literal(1)),
            (EX.entryA7, SW.hasSplit, EX.splitA1a),
        ):
            with self.subTest(entry=entry, predicate=predicate):
                graph = self.clone()
                graph.add((entry, predicate, value))
                self.assert_acceptance(graph, False)
        self.assert_each_fails(((EX.entryA7, SW.seedTimeSeconds, decimal('-1')),))

    def test_entries_must_match_category_and_be_unique_per_event(self):
        self.assert_each_fails(((EX.entryB2, SW.forSwimmer, EX.swimmerA),))
        graph = self.clone()
        graph.add((EX.dup, RDF.type, SW.Entry))
        graph.add((EX.dup, RDFS.label, Literal('중복 출전', lang='ko')))
        graph.add((EX.dup, SW.forSwimmer, EX.swimmerC))
        graph.add((EX.dup, SW.inEvent, EX.event1))
        graph.add((EX.dup, SW.entryStatus, Literal('did-not-start')))
        self.assert_acceptance(graph, False)

    def test_a_faster_time_cannot_rank_lower(self):
        graph = self.clone()
        graph.set((EX.entryA1, SW.placeRank, Literal(1)))
        graph.set((EX.entryC1, SW.placeRank, Literal(2)))
        self.assert_acceptance(graph, False)

    def test_splits_follow_pool_length_distance_and_time_order(self):
        self.assert_each_fails((
            (EX.splitA1b, SW.splitDistanceMeters, Literal(125)),
            (EX.splitA1a, SW.splitDistanceMeters, Literal(40)),
            (EX.splitA5a, SW.splitDistanceMeters, Literal(25)),  # 25 m is not a split length in a 50 m pool
            (EX.splitA1a, SW.splitTimeSeconds, decimal('60.00')),
            (EX.splitA1b, SW.splitTimeSeconds, decimal('58.50')),
            (EX.splitA1a, SW.splitDistanceMeters, Literal(100)),
        ))
        graph = self.clone()
        graph.add((EX.entryC1, SW.hasSplit, EX.splitA1a))
        self.assert_acceptance(graph, False)

    def test_stroke_distance_and_course_combinations_are_restricted(self):
        self.assert_each_fails((
            (EX.event4, SW.distanceMeters, Literal(400)),
            (EX.event3, SW.distanceMeters, Literal(800)),
            (EX.event1, SW.distanceMeters, Literal(75)),
            (EX.event4, SW.stroke, Literal('dolphin')),
            (EX.meet1, SW.heldAt, EX.pool50),  # the 100 m medley exists only in a 25 m pool
        ))

    def test_pool_meet_and_swimmer_value_constraints_fail(self):
        self.assert_each_fails((
            (EX.pool25, SW.poolLengthMeters, Literal(33)),
            (EX.pool25, SW.laneCount, Literal(0)),
            (EX.meet1, SW.endDate, Literal('2026-03-01', datatype=XSD.date)),
            (EX.swimmerA, SW.competitionCategory, Literal('mixed')),
        ))
        self.assert_removal_fails(((EX.meet1, SW.heldAt), (EX.swimmerA, RDFS.label)))
        for subject, predicate, value in ((EX.meet2, SW.hasEvent, EX.event1), (EX.swimmerA, SW.memberOf, EX.clubB)):
            with self.subTest(extra=predicate):
                graph = self.clone()
                graph.add((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_course_length_keeps_personal_bests_apart_and_new_results_change_answers(self):
        rows = query_answer(self.fixture, self.queries['SWIM-04'])['rows']
        self.assertEqual([row[3:5] for row in rows if row[0] == str(EX.swimmerA)], [['25', '58.42'], ['50', '57.95']])
        graph = self.clone()
        graph.set((EX.entryA7, SW.entryStatus, Literal('official')))
        graph.remove((EX.entryA7, SW.seedTimeSeconds, None))
        graph.add((EX.entryA7, SW.finalTimeSeconds, decimal('125.10')))
        graph.add((EX.entryA7, SW.timingEvidenceUri, Literal('urn:synthetic:results:entryA7', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, True)
        self.assertEqual(len(query_answer(graph, self.queries['SWIM-04'])['rows']), 11)
        self.assertEqual([row[1] for row in query_answer(graph, self.queries['SWIM-06'])['rows']], [str(EX.swimmerC)])

    def test_removing_links_changes_the_coverage_answers(self):
        graph = self.clone()
        graph.remove((EX.swimmerA, SW.memberOf, None))
        rows = query_answer(graph, self.queries['SWIM-08'])['rows']
        self.assertEqual([row[2] for row in rows], [None, str(EX.clubA), str(EX.clubB), None])
        graph = self.clone()
        graph.remove((EX.entryC3, SW.placeRank, None))
        self.assertEqual([row[1] for row in query_answer(graph, self.queries['SWIM-10'])['rows']], ['3', '2'])


if __name__ == '__main__':
    unittest.main()
