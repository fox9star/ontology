"""World War I records stay consistent in time and never claim a source check that has no source."""

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
FOLDER = ROOT / 'custom-ontologies/ww1'
WW1 = Namespace('https://example.org/ontology/custom/ww1#')
EX = Namespace('https://example.test/ww1/')
PATTERN = re.compile(r'^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~', re.MULTILINE | re.DOTALL)


def date(value):
    return Literal(value, datatype=XSD.date)


class WorldWarOneOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema_graph(ROOT, 'custom-ontologies/ww1/schema.ttl')
        cls.shapes = load_shape_graph(ROOT, 'custom-ontologies/ww1/shapes.ttl')
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

    def source_checked_graph(self):
        """Test-only state: URNs denote an imaginary source, not a real citation."""
        graph = self.clone()
        graph.add((EX.sourceA, RDF.type, WW1.SourceReference))
        graph.add((EX.sourceA, RDFS.label, Literal('합성 출처 A', lang='ko')))
        graph.add((EX.sourceA, WW1.citationText, Literal('Synthetic test citation A')))
        graph.add((EX.sourceA, WW1.sourceUri, Literal('urn:synthetic:source:a', datatype=XSD.anyURI)))
        graph.set((EX.verdun, WW1.verificationStatus, Literal('source-checked')))
        graph.add((EX.verdun, WW1.supportedBy, EX.sourceA))
        return graph

    def test_schema_exports_and_bilingual_definitions_match(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        self.assertTrue(isomorphic(schema, Graph().parse(FOLDER / 'schema.owl', format='xml')))
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        self.assertEqual(len(terms), 45)
        for term in terms:
            for predicate in (RDFS.label, RDFS.comment):
                self.assertEqual({value.language for value in schema.objects(term, predicate)}, {'ko', 'en'})

    def test_example_and_fixture_describe_the_same_graph_and_are_valid_but_unverified(self):
        self.assert_acceptance(self.clone(), True)
        example = Graph().parse(FOLDER / 'example.ttl', format='turtle')
        self.assert_acceptance(example, True)
        self.assertEqual(len(example), len(self.fixture))
        for graph in (example, self.fixture):
            self.assertEqual(set(graph.objects(None, WW1.verificationStatus)), {Literal('unverified')})
            self.assertEqual(list(graph.triples((None, WW1.supportedBy, None))), [])
            self.assertEqual(list(graph.subjects(RDF.type, WW1.SourceReference)), [])

    def test_all_twelve_questions_match_independently_specified_golden_rows(self):
        answers = json.loads((FOLDER / 'question-answers.json').read_text(encoding='utf-8'))
        self.assertEqual(set(answers), set(self.queries))
        self.assertEqual(len(answers), 12)
        for identifier, query in self.queries.items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(self.fixture, query), answers[identifier])

    def test_questions_reference_every_named_ww1_term(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        _, references = question_references((FOLDER / 'questions.md').read_text(encoding='utf-8'))
        self.assertEqual(terms - references.keys(), set())

    def test_missing_explicit_endpoint_type_is_not_repaired_by_acceptance(self):
        graph = self.clone()
        graph.remove((EX.declUSGer, RDF.type, WW1.Event))
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_participation_dates_must_follow_their_events_and_agreements(self):
        cases = (
            (EX.partGermany, WW1.entryDate, date('1914-08-02')),
            (EX.partRussia, WW1.exitDate, date('1918-03-04')),
            (EX.partFrance, WW1.entryDate, date('1914-07-01')),
            (EX.partGermany, WW1.exitDate, date('1918-11-12')),
        )
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate, value=value):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_exit_needs_an_agreement_to_which_the_state_is_a_party(self):
        graph = self.clone()
        graph.remove((EX.partRussia, WW1.endedByAgreement, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.partRussia, WW1.exitDate, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.compiegne, WW1.hasParty, EX.germany))  # Germany stays a party to Versailles
        self.assert_acceptance(graph, False)

    def test_entry_event_must_involve_the_state_and_be_a_start_of_war_action(self):
        graph = self.clone()
        graph.set((EX.partBelgium, WW1.enteredVia, EX.declUKGer))  # same date, but Belgium is not involved
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.partUsa, WW1.enteredVia, EX.verdun))
        self.assert_acceptance(graph, False)

    def test_a_state_has_one_participation_per_war(self):
        graph = self.clone()
        graph.add((EX.again, RDF.type, WW1.Participation))
        graph.add((EX.again, RDFS.label, Literal('중복 참전', lang='ko')))
        graph.add((EX.again, WW1.participant, EX.france))
        graph.add((EX.again, WW1.inConflict, EX.wwi))
        graph.add((EX.again, WW1.onSide, EX.alliedPowers))
        graph.add((EX.again, WW1.entryDate, date('1914-08-03')))
        graph.add((EX.again, WW1.enteredVia, EX.declGerFrance))
        graph.add((EX.again, WW1.verificationStatus, Literal('unverified')))
        self.assert_acceptance(graph, False)

    def test_battle_belligerents_must_be_two_sided_and_active(self):
        graph = self.clone()
        graph.remove((EX.verdun, WW1.hasBelligerent, EX.partGermany))
        self.assert_acceptance(graph, False)
        for battle, participation in ((EX.tannenberg, EX.partUsa), (EX.springOffensive, EX.partRussia), (EX.marne, EX.partItaly)):
            with self.subTest(battle=battle, participation=participation):
                graph = self.clone()
                graph.add((battle, WW1.hasBelligerent, participation))
                self.assert_acceptance(graph, False)

    def test_battle_commanders_must_have_served_a_belligerent_and_been_alive(self):
        graph = self.clone()
        graph.add((EX.verdun, WW1.hadCommander, EX.haig))  # served the UK, absent from Verdun
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.samsonov, WW1.servedState, EX.germany))  # isolates the lifespan rule
        graph.add((EX.hundredDays, WW1.hadCommander, EX.samsonov))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.foch, WW1.birthYear, Literal(1928)))  # born after the Somme but before his death year
        self.assert_acceptance(graph, False)

    def test_event_kind_decides_the_allowed_properties(self):
        cases = (
            (EX.declUSGer, WW1.inTheatre, EX.theatreWestern),
            (EX.sarajevo, WW1.initiatedBy, EX.austriaHungary),
            (EX.verdun, WW1.initiatedBy, EX.germany),
            (EX.verdun, WW1.outcome, Literal('draw')),
            (EX.declUSGer, WW1.directedAgainst, EX.usa),
        )
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate):
                graph = self.clone()
                graph.add((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_event_and_conflict_date_rules_fail(self):
        cases = (
            (EX.hundredDays, WW1.endDate, date('1918-11-12')),
            (EX.marne, WW1.startDate, date('1914-09-13')),
            (EX.declUKGer, WW1.endDate, date('1914-08-05')),
            (EX.wwi, WW1.conflictEndDate, date('1914-01-01')),
            (EX.versailles, WW1.inForceDate, date('1919-06-01')),
        )
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_value_constraints_fail(self):
        cases = (
            (EX.uk, WW1.governmentForm, Literal('monarchy')),
            (EX.compiegne, WW1.agreementKind, Literal('truce')),
            (EX.haig, WW1.birthYear, Literal('1861')),
        )
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.compiegne, WW1.inForceDate, date('1918-11-12')))  # only a peace treaty has a force date
        self.assert_acceptance(graph, False)

    def test_source_checked_state_requires_a_source_and_unverified_must_not_cite_one(self):
        graph = self.clone()
        graph.set((EX.verdun, WW1.verificationStatus, Literal('source-checked')))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.sourceA, RDF.type, WW1.SourceReference))
        graph.add((EX.sourceA, RDFS.label, Literal('합성 출처 A', lang='ko')))
        graph.add((EX.sourceA, WW1.citationText, Literal('Synthetic test citation A')))
        graph.add((EX.verdun, WW1.supportedBy, EX.sourceA))
        self.assert_acceptance(graph, False)

    def test_source_checked_record_is_valid_and_changes_the_verification_answers(self):
        graph = self.source_checked_graph()
        self.assert_acceptance(graph, True)
        self.assertEqual(query_answer(graph, self.queries['WW1-11'])['rows'], [['source-checked', '1'], ['unverified', '40']])
        self.assertEqual(query_answer(graph, self.queries['WW1-12'])['rows'],
                         [[str(EX.verdun), str(EX.sourceA), 'Synthetic test citation A', 'urn:synthetic:source:a']])
        graph.remove((EX.verdun, WW1.supportedBy, None))
        self.assert_acceptance(graph, False)
        self.assertEqual(query_answer(graph, self.queries['WW1-12'])['rows'], [])

    def test_source_references_need_a_citation_and_a_supported_claim(self):
        graph = self.source_checked_graph()
        graph.remove((EX.sourceA, WW1.citationText, None))
        self.assert_acceptance(graph, False)
        graph = self.source_checked_graph()
        graph.set((EX.sourceA, WW1.sourceUri, Literal('ftp://example.test/a', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.orphan, RDF.type, WW1.SourceReference))
        graph.add((EX.orphan, RDFS.label, Literal('주장 없는 출처', lang='ko')))
        graph.add((EX.orphan, WW1.citationText, Literal('Synthetic orphan citation')))
        self.assert_acceptance(graph, False)

    def test_removing_links_changes_coverage_answers(self):
        graph = self.clone()
        graph.remove((EX.partBulgaria, RDF.type, None))  # an untyped record is not a participation
        self.assertEqual([row[0] for row in query_answer(graph, self.queries['WW1-10'])['rows']], [str(EX.japan), str(EX.serbia)])
        graph = self.clone()
        graph.remove((EX.salonica, WW1.hasParty, EX.bulgaria))
        self.assertEqual(query_answer(graph, self.queries['WW1-09'])['rows'][1][3], '3')
        graph = self.clone()
        graph.add((EX.verdun, WW1.hasBelligerent, EX.partSerbia))
        self.assertEqual([row[0] for row in query_answer(graph, self.queries['WW1-10'])['rows']], [str(EX.bulgaria), str(EX.japan)])


if __name__ == '__main__':
    unittest.main()
