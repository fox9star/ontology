"""Trip plans keep unchecked entry requirements and unconfirmed bookings distinct from confirmed ones."""

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
FOLDER = ROOT / 'custom-ontologies/overseas-trip'
TRIP = Namespace('https://example.org/ontology/custom/overseas-trip#')
EX = Namespace('https://example.test/overseas-trip/')
PATTERN = re.compile(r'^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~', re.MULTILINE | re.DOTALL)


class OverseasTripOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema_graph(ROOT, 'custom-ontologies/overseas-trip/schema.ttl')
        cls.shapes = load_shape_graph(ROOT, 'custom-ontologies/overseas-trip/shapes.ttl')
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

    def confirmed_synthetic_graph(self):
        """Construct a test-only ready state; URNs denote imaginary test evidence."""
        graph = self.clone()
        for name in ('reqPassportA', 'reqPassportB', 'reqVisa'):
            graph.set((EX[name], TRIP.checkStatus, Literal('satisfied')))
            graph.add((EX[name], TRIP.checkEvidenceUri, Literal('urn:synthetic:check:' + name, datatype=XSD.anyURI)))
        for name in ('flight', 'lodging', 'rail', 'insurance'):
            graph.set((EX[name], TRIP.bookingStatus, Literal('booked')))
            graph.add((EX[name], TRIP.confirmationEvidenceUri, Literal('urn:synthetic:booking:' + name, datatype=XSD.anyURI)))
        graph.set((EX.plan, TRIP.planStatus, Literal('confirmed')))
        return graph

    def test_schema_exports_and_bilingual_definitions_match(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        self.assertTrue(isomorphic(schema, Graph().parse(FOLDER / 'schema.owl', format='xml')))
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        self.assertEqual(len(terms), 58)
        for term in terms:
            for predicate in (RDFS.label, RDFS.comment):
                self.assertEqual({value.language for value in schema.objects(term, predicate)}, {'ko', 'en'})

    def test_draft_fixture_is_valid_without_fabricated_checks_or_reservations(self):
        self.assert_acceptance(self.clone(), True)
        for predicate in (TRIP.checkEvidenceUri, TRIP.confirmationEvidenceUri):
            self.assertEqual(list(self.fixture.triples((None, predicate, None))), [])
        self.assertEqual(set(self.fixture.objects(None, TRIP.checkStatus)), {Literal('unchecked')})
        self.assertEqual(set(self.fixture.objects(None, TRIP.bookingStatus)), {Literal('planned')})
        self.assertEqual(set(self.fixture.objects(None, TRIP.planStatus)), {Literal('draft')})

    def test_all_nine_questions_match_independently_specified_golden_rows(self):
        answers = json.loads((FOLDER / 'question-answers.json').read_text(encoding='utf-8'))
        self.assertEqual(set(answers), set(self.queries))
        self.assertEqual(len(answers), 9)
        for identifier, query in self.queries.items():
            with self.subTest(question=identifier):
                self.assertEqual(query_answer(self.fixture, query), answers[identifier])

    def test_questions_reference_every_named_trip_term(self):
        schema = Graph().parse(FOLDER / 'schema.ttl', format='turtle')
        terms = set().union(*(set(schema.subjects(RDF.type, kind)) for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)))
        _, references = question_references((FOLDER / 'questions.md').read_text(encoding='utf-8'))
        self.assertEqual(terms - references.keys(), set())

    def test_missing_explicit_endpoint_type_is_not_repaired_by_acceptance(self):
        graph = self.clone()
        graph.remove((EX.flight, RDF.type, TRIP.Booking))
        result = validate_phases(graph, self.schema, self.shapes)
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_confirming_without_checks_or_bookings_fails(self):
        graph = self.clone()
        graph.set((EX.plan, TRIP.planStatus, Literal('confirmed')))
        self.assert_acceptance(graph, False)

    def test_checked_and_booked_states_require_evidence(self):
        for subject, predicate, value in ((EX.reqVisa, TRIP.checkStatus, 'satisfied'),
                                          (EX.reqVisa, TRIP.checkStatus, 'not-required'),
                                          (EX.flight, TRIP.bookingStatus, 'booked')):
            with self.subTest(subject=subject, value=value):
                graph = self.clone()
                graph.set((subject, predicate, Literal(value)))
                self.assert_acceptance(graph, False)

    def test_evidence_cannot_be_attached_to_unchecked_or_planned_records(self):
        graph = self.clone()
        graph.add((EX.reqVisa, TRIP.checkEvidenceUri, Literal('urn:synthetic:check:x', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.flight, TRIP.confirmationEvidenceUri, Literal('urn:synthetic:booking:x', datatype=XSD.anyURI)))
        self.assert_acceptance(graph, False)

    def test_date_and_order_rules_fail(self):
        cases = (
            (EX.plan, TRIP.returnDate, Literal('2027-03-09', datatype=XSD.date)),
            (EX.day2, TRIP.dayNumber, Literal(1)),
            (EX.act02, TRIP.activityOrder, Literal(1)),
            (EX.day3, TRIP.dayDate, Literal('2027-03-20', datatype=XSD.date)),
            (EX.rail, TRIP.bookingEndDate, Literal('2027-03-11', datatype=XSD.date)),
            (EX.flight, TRIP.bookingEndDate, Literal('2027-03-15', datatype=XSD.date)),
        )
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_value_constraints_fail(self):
        cases = (
            (EX.japan, TRIP.countryCode, Literal('jp')),
            (EX.budgetFood, TRIP.currencyCode, Literal('yen')),
            (EX.budgetFood, TRIP.plannedAmount, Literal('-1', datatype=XSD.decimal)),
            (EX.plan, TRIP.travelerCount, Literal(0)),
            (EX.act01, TRIP.plannedDurationMinutes, Literal(0)),
            (EX.act01, TRIP.activityCategory, Literal('shopping')),
        )
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_cross_plan_links_are_rejected(self):
        graph = self.clone()
        other = EX.otherPlan
        graph.add((other, RDF.type, TRIP.TripPlan))
        graph.add((other, RDFS.label, Literal('다른 계획', lang='ko')))
        graph.add((other, TRIP.planStatus, Literal('draft')))
        graph.add((other, TRIP.departureDate, Literal('2027-03-10', datatype=XSD.date)))
        graph.add((other, TRIP.returnDate, Literal('2027-03-14', datatype=XSD.date)))
        graph.add((other, TRIP.travelerCount, Literal(1)))
        graph.add((other, TRIP.hasBudgetItem, EX.budgetFood))
        self.assert_acceptance(graph, False)

    def test_booking_covering_another_plans_activity_fails(self):
        graph = self.clone()
        graph.add((EX.flight, TRIP.coversActivity, EX.strayActivity))
        graph.add((EX.strayActivity, RDF.type, TRIP.Activity))
        graph.add((EX.strayActivity, RDFS.label, Literal('소속 없는 활동', lang='ko')))
        self.assert_acceptance(graph, False)

    def test_confirmed_plan_is_valid_and_blockers_reappear_when_evidence_is_removed(self):
        graph = self.confirmed_synthetic_graph()
        self.assert_acceptance(graph, True)
        self.assertEqual(query_answer(graph, self.queries['TRIP-05'])['rows'], [])
        self.assertEqual(query_answer(graph, self.queries['TRIP-02'])['rows'], [])
        graph.remove((EX.rail, TRIP.confirmationEvidenceUri, None))
        self.assert_acceptance(graph, False)
        rows = query_answer(graph, self.queries['TRIP-05'])['rows']
        self.assertEqual([row[5:] for row in rows], [['booking-unconfirmed', str(EX.rail)]])

    def test_missing_requirement_evidence_changes_requirement_answer(self):
        graph = self.confirmed_synthetic_graph()
        graph.remove((EX.reqVisa, TRIP.checkEvidenceUri, None))
        self.assert_acceptance(graph, False)
        rows = query_answer(graph, self.queries['TRIP-02'])['rows']
        self.assertEqual(rows, [[str(EX.plan), 'JP', str(EX.reqVisa), 'visa', 'satisfied', None, None]])

    def test_flight_segments_must_exist_connect_and_stay_in_the_booking_period(self):
        graph = self.clone()
        graph.remove((EX.flight, TRIP.hasFlightSegment, EX.segOut))
        graph.remove((EX.flight, TRIP.hasFlightSegment, EX.segBack))
        self.assert_acceptance(graph, False)
        cases = (
            (EX.segBack, TRIP.departureAirport, Literal('KIX')),
            (EX.segBack, TRIP.arrivalAirport, Literal('NRT')),
            (EX.segBack, TRIP.segmentOrder, Literal(1)),
            (EX.segBack, TRIP.segmentDepartureDate, Literal('2027-03-09', datatype=XSD.date)),
            (EX.segOut, TRIP.segmentArrivalDate, Literal('2027-03-09', datatype=XSD.date)),
            (EX.segBack, TRIP.segmentArrivalDate, Literal('2027-03-15', datatype=XSD.date)),
            (EX.segOut, TRIP.departureAirport, Literal('icn')),
        )
        for subject, predicate, value in cases:
            with self.subTest(subject=subject, predicate=predicate, value=value):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_segments_and_policies_belong_only_to_matching_booking_kinds(self):
        graph = self.clone()
        graph.add((EX.lodging, TRIP.hasFlightSegment, EX.segOut))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.lodging, TRIP.hasInsurancePolicy, EX.policy))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.insurance, TRIP.hasInsurancePolicy, EX.policy))
        self.assert_acceptance(graph, False)

    def test_traveler_count_roles_and_age_rules_fail(self):
        graph = self.clone()
        graph.set((EX.plan, TRIP.travelerCount, Literal(3)))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.travelerB, TRIP.travelerRole, Literal('primary')))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.travelerA, TRIP.ageGroup, Literal('child')))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.set((EX.travelerA, TRIP.nationalityCode, Literal('korea')))
        self.assert_acceptance(graph, False)

    def test_traveler_specific_requirements_may_repeat_a_kind_but_not_per_traveler(self):
        graph = self.clone()
        graph.add((EX.reqPassportB, TRIP.appliesToTraveler, EX.travelerA))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.remove((EX.reqPassportB, TRIP.appliesToTraveler, None))
        self.assert_acceptance(graph, True)
        graph.add((EX.reqPassportA, TRIP.appliesToTraveler, EX.travelerA))
        self.assert_acceptance(graph, True)

    def test_policy_and_requirement_cannot_reference_another_plans_traveler(self):
        graph = self.clone()
        graph.add((EX.stranger, RDF.type, TRIP.Traveler))
        graph.add((EX.stranger, RDFS.label, Literal('다른 계획 동반자', lang='ko')))
        graph.add((EX.stranger, TRIP.travelerRole, Literal('companion')))
        graph.add((EX.stranger, TRIP.ageGroup, Literal('adult')))
        graph.add((EX.policy, TRIP.coversTraveler, EX.stranger))
        self.assert_acceptance(graph, False)
        graph = self.clone()
        graph.add((EX.stranger, RDF.type, TRIP.Traveler))
        graph.add((EX.stranger, RDFS.label, Literal('다른 계획 동반자', lang='ko')))
        graph.add((EX.stranger, TRIP.travelerRole, Literal('companion')))
        graph.add((EX.stranger, TRIP.ageGroup, Literal('adult')))
        graph.add((EX.reqVisa, TRIP.appliesToTraveler, EX.stranger))
        self.assert_acceptance(graph, False)

    def test_insurance_value_constraints_fail(self):
        cases = (
            (EX.policy, TRIP.coverageKind, Literal('theft')),
            (EX.policy, TRIP.coverageLimitAmount, Literal('-1', datatype=XSD.decimal)),
            (EX.policy, TRIP.coverageLimitCurrency, Literal('won')),
        )
        for subject, predicate, value in cases:
            with self.subTest(predicate=predicate):
                graph = self.clone()
                graph.set((subject, predicate, value))
                self.assert_acceptance(graph, False)

    def test_insurance_gap_query_follows_coverage_and_cancellation(self):
        graph = self.clone()
        self.assertEqual([row[1] for row in query_answer(graph, self.queries['TRIP-09'])['rows']], [str(EX.travelerB)])
        graph.add((EX.policy, TRIP.coversTraveler, EX.travelerB))
        self.assert_acceptance(graph, True)
        self.assertEqual(query_answer(graph, self.queries['TRIP-09'])['rows'], [])
        graph.set((EX.insurance, TRIP.bookingStatus, Literal('cancelled')))
        self.assert_acceptance(graph, True)
        self.assertEqual([row[1] for row in query_answer(graph, self.queries['TRIP-09'])['rows']],
                         [str(EX.travelerA), str(EX.travelerB)])
        graph = self.clone()
        graph.set((EX.policy, TRIP.coverageKind, Literal('baggage')))
        self.assertEqual(len(query_answer(graph, self.queries['TRIP-09'])['rows']), 2)

    def test_missing_itinerary_link_changes_daily_answer(self):
        graph = self.clone()
        graph.remove((EX.day3, TRIP.hasActivity, EX.act06))
        answer = query_answer(graph, self.queries['TRIP-01'])
        self.assertEqual(len(answer['rows']), 5)
        self.assert_acceptance(graph, False)


if __name__ == '__main__':
    unittest.main()
