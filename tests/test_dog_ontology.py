"""Dog records keep scheduled doses and unregistered dogs distinct from completed, evidenced ones."""

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
FOLDER = ROOT / 'custom-ontologies/dog'
DOG = Namespace('https://example.org/ontology/custom/dog#')
EX = Namespace('https://example.test/dog/')
PATTERN = re.compile(r'^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~', re.MULTILINE | re.DOTALL)


def date(value):
    return Literal(value, datatype=XSD.date)


class DogOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema_graph(ROOT, 'custom-ontologies/dog/schema.ttl')
        cls.shapes = load_shape_graph(ROOT, 'custom-ontologies/dog/shapes.ttl')
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

    def test_schema_exports_and_bilingual_definitions_match(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        self.assertTrue(isomorphic(schema, Graph().parse(FOLDER / 'schema.owl', format='xml')))
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        self.assertEqual(len(terms), 31)
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

    def test_questions_reference_every_named_dog_term(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        _, references = question_references((FOLDER / 'questions.md').read_text(encoding='utf-8'))
        self.assertEqual(terms - references.keys(), set())

    def test_missing_explicit_endpoint_type_is_not_repaired_by_acceptance(self):
        graph = self.clone()
        graph.remove((EX.guardianA, RDF.type, DOG.Guardian))
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_registration_requires_number_and_evidence_and_unregistered_has_neither(self):
        graph = self.clone()
        graph.remove((EX.kongi, DOG.microchipNumber, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.kongi, DOG.registrationEvidenceUri, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.bori, DOG.microchipNumber, Literal('999000000000002')))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.bori, DOG.registrationEvidenceUri, Literal('urn:synthetic:registration:x', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, False)
        self.assert_each_fails(((EX.kongi, DOG.microchipNumber, Literal('12345')),
                                (EX.kongi, DOG.microchipStatus, Literal('pending'))))

    def test_administered_vaccination_requires_date_certificate_and_clinic(self):
        for predicate in (DOG.administeredDate, DOG.certificateUri, DOG.administeredAt):
            with self.subTest(missing=predicate):
                graph = self.clone()
                graph.remove((EX.kongiRabies, predicate, None))
                self.assert_acceptance(graph, False)

    def test_scheduled_vaccination_cannot_carry_completion_facts_and_needs_a_due_date(self):
        graph = self.clone()
        graph.add((EX.nuriRabies, DOG.administeredDate, date('2026-10-01')))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.nuriRabies, DOG.certificateUri, Literal('urn:synthetic:certificate:x', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.nuriRabies, DOG.nextDueDate, None))
        self.assert_acceptance(graph, False)

    def test_date_rules_fail(self):
        self.assert_each_fails((
            (EX.kongiRabies, DOG.nextDueDate, date('2025-01-01')),
            (EX.kongiRabies, DOG.administeredDate, date('2020-01-01')),
            (EX.boriVisit1, DOG.visitDate, date('2022-01-01')),
            (EX.boriWeight1, DOG.measuredDate, date('2022-01-01')),
            (EX.boriWeight2, DOG.measuredDate, date('2026-07-01')),
        ))

    def test_birth_date_certainty_matches_the_presence_of_a_date(self):
        graph = self.clone()
        graph.remove((EX.bori, DOG.birthDate, None))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.dalgi, DOG.birthDate, date('2022-01-01')))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.dalgi, DOG.birthDateKnowledge, Literal('estimated')))
        self.assert_acceptance(graph, False)

    def test_value_constraints_fail(self):
        self.assert_each_fails((
            (EX.boriWeight1, DOG.weightKg, Literal('-1', datatype=XSD.decimal)),
            (EX.boriWeight1, DOG.weightKg, Literal('500', datatype=XSD.decimal)),
            (EX.bori, DOG.sex, Literal('unknown')),
            (EX.boriVisit2, DOG.visitReason, Literal('grooming')),
            (EX.jindo, DOG.typicalSizeClass, Literal('huge')),
            (EX.nuri, DOG.neuterStatus, Literal('maybe')),
            (EX.kongiRabies, DOG.vaccineKind, Literal('flu')),
        ))

    def test_required_links_and_single_ownership(self):
        for subject, predicate in ((EX.nuri, DOG.hasGuardian), (EX.nuri, DOG.hasBreed), (EX.boriVisit1, DOG.visitedClinic)):
            with self.subTest(missing=predicate):
                graph = self.clone()
                graph.remove((subject, predicate, None))
                self.assert_acceptance(graph, False)
        for predicate, record in ((DOG.hasVaccination, EX.kongiRabies), (DOG.hasVisit, EX.kongiVisit1), (DOG.hasWeightRecord, EX.kongiWeight1)):
            with self.subTest(shared=predicate):
                graph = self.clone()
                graph.add((EX.bori, predicate, record))
                self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.kongi, RDFS.label, None))
        self.assert_acceptance(graph, False)

    def test_completing_a_scheduled_dose_with_evidence_is_valid_and_changes_the_answers(self):
        graph = self.clone()
        graph.set((EX.nuriRabies, DOG.vaccinationStatus, Literal('administered')))
        graph.add((EX.nuriRabies, DOG.administeredDate, date('2026-10-02')))
        graph.add((EX.nuriRabies, DOG.administeredAt, EX.clinicB))
        graph.add((EX.nuriRabies, DOG.certificateUri, Literal('urn:synthetic:certificate:nuri-rabies', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, True)
        rows = query_answer(graph, self.queries['DOG-03'])['rows']
        self.assertEqual([(row[0], row[5]) for row in rows], [(str(EX.bori), 'current'), (str(EX.kongi), 'overdue'), (str(EX.nuri), 'current')])
        self.assertEqual([row[1] for row in query_answer(graph, self.queries['DOG-06'])['rows']], ['2', '2'])
        self.assertEqual(len(query_answer(graph, self.queries['DOG-05'])['rows']), 1)

    def test_removing_links_changes_the_coverage_answers(self):
        graph = self.clone()
        graph.remove((EX.boriRabies, DOG.vaccineKind, None))
        self.assertEqual([row[0] for row in query_answer(graph, self.queries['DOG-04'])['rows']], [str(EX.bori), str(EX.dalgi)])
        graph = self.clone()
        graph.remove((EX.kongi, DOG.hasGuardian, EX.guardianA))
        self.assertEqual(query_answer(graph, self.queries['DOG-02'])['rows'][0], [str(EX.guardianB), '2'])


if __name__ == '__main__':
    unittest.main()
