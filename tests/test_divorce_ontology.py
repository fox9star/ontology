"""Divorce case records keep dates ordered, require evidence to finalize and divide property to exactly 100."""

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
FOLDER = ROOT / 'custom-ontologies/divorce'
DIV = Namespace('https://example.org/ontology/custom/divorce#')
EX = Namespace('https://example.test/divorce/')
PATTERN = re.compile(r'^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~', re.MULTILINE | re.DOTALL)


def date(value):
    return Literal(value, datatype=XSD.date)


def decimal(value):
    return Literal(value, datatype=XSD.decimal)


class DivorceOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema_graph(ROOT, 'custom-ontologies/divorce/schema.ttl')
        cls.shapes = load_shape_graph(ROOT, 'custom-ontologies/divorce/shapes.ttl')
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

    def assert_addition_fails(self, cases):
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, added=predicate):
                graph = self.clone()
                graph.add((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_schema_exports_and_bilingual_definitions_match(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        self.assertTrue(isomorphic(schema, Graph().parse(FOLDER / 'schema.owl', format='xml')))
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        self.assertEqual(len(terms), 37)
        for term in terms:
            for predicate in (RDFS.label, RDFS.comment):
                self.assertEqual({value.language for value in schema.objects(term, predicate)}, {'ko', 'en'})

    def test_example_and_fixture_describe_the_same_graph_and_are_valid(self):
        self.assert_acceptance(self.clone(), True)
        example = Graph().parse(FOLDER / 'example.ttl', format='turtle')
        self.assertEqual(len(example), len(self.fixture))
        self.assert_acceptance(example, True)

    def test_all_twelve_questions_match_independently_specified_golden_rows(self):
        answers = json.loads((FOLDER / 'question-answers.json').read_text(encoding='utf-8'))
        self.assertEqual(set(answers), set(self.queries))
        self.assertEqual(len(answers), 12)
        for identifier, query in self.queries.items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(self.fixture, query), answers[identifier])

    def test_questions_reference_every_named_divorce_term(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        _, references = question_references((FOLDER / 'questions.md').read_text(encoding='utf-8'))
        self.assertEqual(terms - references.keys(), set())

    def test_missing_explicit_endpoint_type_is_not_repaired_by_acceptance(self):
        graph = self.clone()
        graph.remove((EX.partyA1, RDF.type, DIV.Party))
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_stage_decides_which_dates_and_evidence_are_required_or_forbidden(self):
        self.assert_removal_fails(((EX.case1, DIV.decreeEvidenceUri), (EX.case1, DIV.effectiveDate), (EX.case1, DIV.filedDate),
                                   (EX.case4, DIV.withdrawalDate), (EX.case2, DIV.filedDate)))
        self.assert_addition_fails((
            (EX.case2, DIV.effectiveDate, date('2026-10-02')),
            (EX.case2, DIV.decreeEvidenceUri, Literal('urn:synthetic:x', datatype=XSD.anyURI)),
            (EX.case2, DIV.withdrawalDate, date('2026-09-10')),
            (EX.case1, DIV.withdrawalDate, date('2026-04-20')),
            (EX.case4, DIV.effectiveDate, date('2026-03-02')),
        ))
        graph = self.clone()
        graph.set((EX.case2, DIV.caseStatus, Literal('preparing')))  # a preparing case has not been filed yet
        self.assert_acceptance(graph, False)
        self.assert_each_fails(((EX.case1, DIV.caseStatus, Literal('closed')), (EX.case1, DIV.caseType, Literal('arbitration'))))

    def test_court_set_dates_must_stay_in_order(self):
        self.assert_each_fails((
            (EX.case1, DIV.reflectionEndDate, date('2025-12-31')),   # before filing
            (EX.case1, DIV.confirmationDate, date('2026-04-01')),    # before the reflection end
            (EX.case1, DIV.effectiveDate, date('2026-04-12')),       # before the confirmation
            (EX.case5, DIV.effectiveDate, date('2026-01-01')),       # before filing
            (EX.case4, DIV.withdrawalDate, date('2026-01-15')),      # before filing
        ))

    def test_consensual_and_judicial_cases_need_matching_procedure_facts(self):
        self.assert_removal_fails(((EX.case2, DIV.reflectionEndDate), (EX.case1, DIV.confirmationDate)))
        self.assert_addition_fails((
            (EX.case3, DIV.reflectionEndDate, date('2026-07-15')),
            (EX.case5, DIV.confirmationDate, date('2026-06-01')),
        ))

    def test_party_roles_follow_the_case_type_and_each_case_has_two_parties(self):
        self.assert_each_fails((
            (EX.partyA1, DIV.partyRole, Literal('petitioner')),
            (EX.partyA3, DIV.partyRole, Literal('joint-petitioner')),
            (EX.partyB3, DIV.partyRole, Literal('petitioner')),  # two petitioners
            (EX.partyB5, DIV.partyRole, Literal('plaintiff')),
        ))
        graph = self.clone()
        graph.set((EX.partyA3, DIV.partyRole, Literal('respondent')))  # no petitioner at all
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.case5, DIV.hasParty, EX.partyB5))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.case2, DIV.hasParty, EX.partyA1))  # a party belongs to one case only
        self.assert_acceptance(graph, False)

    def test_finalizing_requires_custody_for_every_minor_child(self):
        graph = self.clone()
        graph.remove((EX.case1, DIV.hasCustodyArrangement, EX.custody1))
        graph.remove((EX.custody1, RDF.type, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.case3, DIV.caseStatus, Literal('finalized')))
        graph.add((EX.case3, DIV.effectiveDate, date('2026-09-30')))
        graph.add((EX.case3, DIV.decreeEvidenceUri, Literal('urn:synthetic:judgment:case3', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, False)  # the minor child has no custody arrangement yet
        graph.add((EX.custody3, RDF.type, DIV.CustodyArrangement))
        graph.add((EX.custody3, RDFS.label, Literal('자녀 3-가 양육 결정', lang='ko')))
        graph.add((EX.custody3, DIV.custodyOfChild, EX.child3a))
        graph.add((EX.custody3, DIV.custodian, EX.partyB3))
        graph.add((EX.custody3, DIV.authorityHolding, Literal('sole')))
        graph.add((EX.case3, DIV.hasCustodyArrangement, EX.custody3))
        self.assert_acceptance(graph, True)
        graph.remove((EX.custody3, DIV.custodian, EX.partyB3))
        graph.add((EX.custody3, DIV.custodian, EX.partyA2))  # a party of another case
        self.assert_acceptance(graph, False)

    def test_custody_arrangements_are_limited_to_minor_children_of_the_case_and_unique(self):
        graph = self.clone()
        graph.add((EX.custodyAdult, RDF.type, DIV.CustodyArrangement))
        graph.add((EX.custodyAdult, RDFS.label, Literal('성인 자녀 양육 결정', lang='ko')))
        graph.add((EX.custodyAdult, DIV.custodyOfChild, EX.child3b))
        graph.add((EX.custodyAdult, DIV.custodian, EX.partyA3))
        graph.add((EX.custodyAdult, DIV.authorityHolding, Literal('sole')))
        graph.add((EX.case3, DIV.hasCustodyArrangement, EX.custodyAdult))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.custodyDup, RDF.type, DIV.CustodyArrangement))
        graph.add((EX.custodyDup, RDFS.label, Literal('중복 양육 결정', lang='ko')))
        graph.add((EX.custodyDup, DIV.custodyOfChild, EX.child1))
        graph.add((EX.custodyDup, DIV.custodian, EX.partyB1))
        graph.add((EX.custodyDup, DIV.authorityHolding, Literal('sole')))
        graph.add((EX.case1, DIV.hasCustodyArrangement, EX.custodyDup))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.custody1, DIV.custodyOfChild, EX.child3a))  # a child of another case
        self.assert_acceptance(graph, False)
        self.assert_each_fails(((EX.custody1, DIV.authorityHolding, Literal('shared')),))

    def test_child_support_follows_party_child_custodian_and_value_rules(self):
        self.assert_each_fails((
            (EX.support1, DIV.payer, EX.partyA1),             # payer equals payee
            (EX.custody1, DIV.custodian, EX.partyB1),         # the payee is no longer the custodian
            (EX.support1, DIV.payer, EX.partyA2),             # a party of another case
            (EX.support1, DIV.supportForChild, EX.child3a),   # a child of another case
            (EX.support1, DIV.monthlyAmount, decimal('0')),
            (EX.support1, DIV.currencyCode, Literal('krw')),
            (EX.support1, DIV.paymentDay, Literal(32)),
        ))
        graph = self.clone()
        graph.add((EX.supportAdult, RDF.type, DIV.SupportObligation))
        graph.add((EX.supportAdult, RDFS.label, Literal('성인 자녀 양육비', lang='ko')))
        graph.add((EX.supportAdult, DIV.supportForChild, EX.child3b))
        graph.add((EX.supportAdult, DIV.payer, EX.partyB3))
        graph.add((EX.supportAdult, DIV.payee, EX.partyA3))
        graph.add((EX.supportAdult, DIV.monthlyAmount, decimal('100000')))
        graph.add((EX.supportAdult, DIV.currencyCode, Literal('KRW')))
        graph.add((EX.supportAdult, DIV.paymentDay, Literal(10)))
        graph.add((EX.case3, DIV.hasSupportObligation, EX.supportAdult))
        self.assert_acceptance(graph, False)

    def test_finalized_property_shares_must_total_one_hundred(self):
        self.assert_each_fails((
            (EX.alloc1a, DIV.sharePercent, decimal('40')),
            (EX.alloc4b, DIV.sharePercent, decimal('35')),
            (EX.alloc1a, DIV.sharePercent, decimal('0')),
            (EX.alloc1a, DIV.sharePercent, decimal('101')),
            (EX.alloc1a, DIV.allocatedTo, EX.partyA2),
            (EX.asset1, DIV.assetType, Literal('jewel')),
            (EX.asset1, DIV.valueCurrency, Literal('won')),
        ))
        graph = self.clone()
        graph.remove((EX.asset4, DIV.hasAllocation, EX.alloc4b))
        graph.remove((EX.alloc4b, RDF.type, None))
        self.assert_acceptance(graph, False)
        self.assertEqual([row[0] for row in query_answer(graph, self.queries['DIV-10'])['rows']], [str(EX.asset4)])
        graph = self.clone()
        graph.set((EX.alloc1b, DIV.allocatedTo, EX.partyA1))  # two shares to the same party
        self.assert_acceptance(graph, False)

    def test_unfinished_cases_may_hold_partial_property_shares(self):
        graph = self.clone()
        graph.add((EX.asset5, RDF.type, DIV.Asset))
        graph.add((EX.asset5, RDFS.label, Literal('가상 차량', lang='ko')))
        graph.add((EX.asset5, DIV.assetType, Literal('vehicle')))
        graph.add((EX.asset5, DIV.estimatedValue, decimal('20000000')))
        graph.add((EX.asset5, DIV.valueCurrency, Literal('KRW')))
        graph.add((EX.asset5, DIV.hasAllocation, EX.alloc5a))
        graph.add((EX.alloc5a, RDF.type, DIV.AssetAllocation))
        graph.add((EX.alloc5a, RDFS.label, Literal('차량 3-가 몫', lang='ko')))
        graph.add((EX.alloc5a, DIV.allocatedTo, EX.partyA3))
        graph.add((EX.alloc5a, DIV.sharePercent, decimal('30')))
        graph.add((EX.case3, DIV.hasAsset, EX.asset5))
        self.assert_acceptance(graph, True)
        self.assertEqual(query_answer(graph, self.queries['DIV-10'])['rows'], [])  # case 3 is not finalized

    def test_value_constraints_fail(self):
        self.assert_each_fails(((EX.child1, DIV.minorAtFiling, Literal('yes')),))
        self.assert_removal_fails(((EX.child1, DIV.minorAtFiling), (EX.case1, RDFS.label), (EX.partyA1, DIV.partyRole)))

    def test_new_facts_change_the_procedure_answers(self):
        graph = self.clone()
        graph.add((EX.case2, DIV.confirmationDate, date('2026-10-02')))
        self.assert_acceptance(graph, True)
        self.assertEqual(query_answer(graph, self.queries['DIV-03'])['rows'], [])
        graph = self.clone()
        graph.set((EX.case2, DIV.reflectionEndDate, date('2026-10-20')))  # the period has not ended on 2026-10-05
        self.assert_acceptance(graph, True)
        self.assertEqual(query_answer(graph, self.queries['DIV-03'])['rows'], [])


if __name__ == '__main__':
    unittest.main()
