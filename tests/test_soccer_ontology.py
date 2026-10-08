"""Soccer results stay backed by a report, goal events and a valid lineup."""

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
FOLDER = ROOT / 'custom-ontologies/soccer'
SC = Namespace('https://example.org/ontology/custom/soccer#')
EX = Namespace('https://example.test/soccer/')
PATTERN = re.compile(r'^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~', re.MULTILINE | re.DOTALL)


class SoccerOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema_graph(ROOT, 'custom-ontologies/soccer/schema.ttl')
        cls.shapes = load_shape_graph(ROOT, 'custom-ontologies/soccer/shapes.ttl')
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

    def add_appearance(self, graph, match, name, club, player, role, position, shirt, minute_in=None):
        node = EX[name]
        graph.add((node, RDF.type, SC.Appearance))
        graph.add((node, RDFS.label, Literal(name, lang='ko')))
        graph.add((node, SC.forPlayer, player))
        graph.add((node, SC.forClub, club))
        graph.add((node, SC.lineupRole, Literal(role)))
        graph.add((node, SC.position, Literal(position)))
        graph.add((node, SC.shirtNumber, Literal(shirt)))
        if minute_in:
            graph.add((node, SC.minuteIn, Literal(minute_in)))
        graph.add((match, SC.hasAppearance, node))
        return node

    def add_player(self, graph, name):
        graph.add((EX[name], RDF.type, SC.Player))
        graph.add((EX[name], RDFS.label, Literal(name, lang='ko')))
        return EX[name]

    def test_schema_exports_and_bilingual_definitions_match(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        self.assertTrue(isomorphic(schema, Graph().parse(FOLDER / 'schema.owl', format='xml')))
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        self.assertEqual(len(terms), 30)
        for term in terms:
            for predicate in (RDFS.label, RDFS.comment):
                self.assertEqual({value.language for value in schema.objects(term, predicate)}, {'ko', 'en'})

    def test_example_and_fixture_describe_the_same_graph_and_are_valid(self):
        self.assert_acceptance(self.clone(), True)
        example = Graph().parse(FOLDER / 'example.ttl', format='turtle')
        self.assertEqual(len(example), len(self.fixture))
        self.assert_acceptance(example, True)

    def test_all_ten_questions_match_independently_specified_golden_rows(self):
        answers = json.loads((FOLDER / 'question-answers.json').read_text(encoding='utf-8'))
        self.assertEqual(set(answers), set(self.queries))
        self.assertEqual(len(answers), 10)
        for identifier, query in self.queries.items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(self.fixture, query), answers[identifier])

    def test_questions_reference_every_named_soccer_term(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        _, references = question_references((FOLDER / 'questions.md').read_text(encoding='utf-8'))
        self.assertEqual(terms - references.keys(), set())

    def test_missing_explicit_endpoint_type_is_not_repaired_by_acceptance(self):
        graph = self.clone()
        graph.remove((EX.clubA, RDF.type, SC.Club))
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_match_status_decides_which_result_facts_are_allowed(self):
        for subject, predicate in ((EX.match1, SC.matchReportUri), (EX.match1, SC.homeGoals), (EX.match1, SC.awayGoals)):
            with self.subTest(missing=predicate):
                graph = self.clone()
                graph.remove((subject, predicate, None))
                self.assert_acceptance(graph, False)
        for subject, predicate, value in (
            (EX.match3, SC.homeGoals, Literal(0)),
            (EX.match3, SC.matchReportUri, Literal('urn:synthetic:report:x', datatype=XSD.anyURI)),
            (EX.match3, SC.hasEvent, EX.match1ev1),
            (EX.match4, SC.homeGoals, Literal(0)),
        ):
            with self.subTest(added=predicate, match=subject):
                graph = self.clone()
                graph.add((subject, predicate, value))
                self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.match4, SC.hasAppearance, EX.match1A01))
        self.assert_acceptance(graph, False)
        self.assert_each_fails(((EX.match1, SC.matchStatus, Literal('abandoned')), (EX.match1, SC.awayClub, EX.clubA)))

    def test_finished_match_needs_eleven_starters_and_one_starting_goalkeeper(self):
        graph = self.clone()
        graph.set((EX.match1A11, SC.lineupRole, Literal('substitute')))
        graph.add((EX.match1A11, SC.minuteIn, Literal(80)))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        player = self.add_player(graph, 'playerA99')
        self.add_appearance(graph, EX.match1, 'extraStarter', EX.clubA, player, 'starter', 'forward', 99)
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.match1A02, SC.position, Literal('goalkeeper')))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.match1A01, SC.position, Literal('defender')))
        self.assert_acceptance(graph, False)

    def test_substitutions_cannot_exceed_the_competition_limit(self):
        graph = self.clone()
        for index in range(3):  # the cup allows three; Club B already used one in match2
            player = self.add_player(graph, f'playerBx{index}')
            self.add_appearance(graph, EX.match2, f'extraSub{index}', EX.clubB, player, 'substitute', 'forward', 90 + index, 85)
        self.assert_acceptance(graph, False)
        graph = self.clone()
        for index in range(2):  # one used plus two is exactly the limit of three
            player = self.add_player(graph, f'playerBx{index}')
            self.add_appearance(graph, EX.match2, f'extraSub{index}', EX.clubB, player, 'substitute', 'forward', 90 + index, 85)
        self.assert_acceptance(graph, True)

    def test_recorded_score_must_equal_goal_events_with_own_goals_credited_to_the_opponent(self):
        self.assert_each_fails(((EX.match1, SC.homeGoals, Literal(3)), (EX.match1, SC.awayGoals, Literal(0))))
        graph = self.clone()
        graph.set((EX.match2ev7, SC.eventType, Literal('goal')))  # Club C player scoring for Club C, not Club B
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.match1, SC.hasEvent, EX.match1ev4))
        self.assert_acceptance(graph, False)
        self.assertEqual([row[1] for row in query_answer(graph, self.queries['SOC-10'])['rows']], [str(EX.clubA)])

    def test_appearances_follow_club_player_shirt_and_minute_rules(self):
        self.assert_each_fails((
            (EX.match1A02, SC.forClub, EX.clubC),
            (EX.match1A02, SC.shirtNumber, Literal(3)),
            (EX.match1A12, SC.minuteOut, Literal(60)),
            (EX.match1A02, SC.position, Literal('striker')),
            (EX.match1A02, SC.shirtNumber, Literal(100)),
            (EX.match1A02, SC.lineupRole, Literal('captain')),
        ))
        graph = self.clone()
        graph.remove((EX.match1A12, SC.minuteIn, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.match1A02, SC.minuteIn, Literal(10)))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.dupPlayer, RDF.type, SC.Appearance))
        graph.add((EX.dupPlayer, RDFS.label, Literal('중복 출전', lang='ko')))
        graph.add((EX.dupPlayer, SC.forPlayer, EX.playerA10))
        graph.add((EX.dupPlayer, SC.forClub, EX.clubA))
        graph.add((EX.dupPlayer, SC.lineupRole, Literal('unused-substitute')))
        graph.add((EX.dupPlayer, SC.position, Literal('forward')))
        graph.add((EX.dupPlayer, SC.shirtNumber, Literal(77)))
        graph.add((EX.match1, SC.hasAppearance, EX.dupPlayer))
        self.assert_acceptance(graph, False)

    def test_event_rules_fail(self):
        self.assert_each_fails((
            (EX.match1ev1, SC.eventType, Literal('foul')),
            (EX.match1ev1, SC.eventMinute, Literal(0)),
            (EX.match1ev1, SC.eventMinute, Literal(131)),
            (EX.match1ev1, SC.byPlayer, EX.playerC01),  # did not play in match1
        ))
        graph = self.clone()
        graph.add((EX.lateCard, RDF.type, SC.MatchEvent))
        graph.add((EX.lateCard, RDFS.label, Literal('퇴장 뒤 경고', lang='ko')))
        graph.add((EX.lateCard, SC.eventType, Literal('yellow-card')))
        graph.add((EX.lateCard, SC.eventMinute, Literal(70)))
        graph.add((EX.lateCard, SC.byPlayer, EX.playerC07))
        graph.add((EX.match2, SC.hasEvent, EX.lateCard))
        self.assert_acceptance(graph, False)

    def test_competition_and_match_value_constraints_fail(self):
        self.assert_each_fails((
            (EX.league2026, SC.season, Literal('26')),
            (EX.league2026, SC.competitionType, Literal('friendly')),
            (EX.league2026, SC.substitutionLimit, Literal(0)),
            (EX.league2026, SC.substitutionLimit, Literal(12)),
            (EX.match1, SC.matchday, Literal(0)),
            (EX.match1, SC.homeGoals, Literal(-1)),
        ))

    def test_results_and_lineups_change_the_answers(self):
        graph = self.clone()
        graph.set((EX.match3, SC.matchStatus, Literal('postponed')))
        self.assertEqual([row[1] for row in query_answer(graph, self.queries['SOC-09'])['rows']], ['postponed', 'postponed'])
        graph = self.clone()
        graph.remove((EX.match1A12, SC.lineupRole, None))
        graph.add((EX.match1A12, SC.lineupRole, Literal('unused-substitute')))
        self.assertEqual(len(query_answer(graph, self.queries['SOC-06'])['rows']), 3)


if __name__ == '__main__':
    unittest.main()
