"""Semantic counterexamples and open-world controls for the reasoning preview."""

import unittest

from rdflib import BNode, Graph, Literal, Namespace, OWL, RDF, XSD
from rdflib.collection import Collection

import owl_reasoner

EX = Namespace("https://example.test/semantic/")


class SemanticConsistencyTests(unittest.TestCase):
    def expanded(self, graph):
        return owl_reasoner.run_owl_deductive_closure(graph)

    def kinds(self, graph):
        return {item["kind"] for item in self.expanded(graph)["semantic_violations"]}

    def functional_graph(self, inverse=False):
        graph = Graph()
        graph.add((EX.p, RDF.type, OWL.InverseFunctionalProperty if inverse else OWL.FunctionalProperty))
        graph.add((EX.a, EX.p, EX.key if inverse else EX.b))
        graph.add((EX.b if inverse else EX.a, EX.p, EX.key if inverse else EX.c))
        return graph

    def test_functional_object_property_does_not_assume_unique_names(self):
        graph = self.functional_graph()
        self.assertTrue(self.expanded(graph)["consistent"])
        self.assertIn((EX.b, OWL.sameAs, EX.c), graph)

    def test_inverse_functional_property_merges_names_without_conflict(self):
        graph = self.functional_graph(inverse=True)
        self.assertTrue(self.expanded(graph)["consistent"])
        self.assertIn((EX.a, OWL.sameAs, EX.b), graph)

    def test_functional_property_conflicts_with_explicit_inequality(self):
        graph = self.functional_graph()
        graph.add((EX.b, OWL.differentFrom, EX.c))
        self.assertIn("identity_conflict", self.kinds(graph))

    def test_inverse_functional_property_conflicts_with_all_different(self):
        graph = self.functional_graph(inverse=True)
        head = BNode()
        Collection(graph, head, [EX.a, EX.b])
        graph.add((EX.distinct, RDF.type, OWL.AllDifferent))
        graph.add((EX.distinct, OWL.distinctMembers, head))
        self.assertIn("identity_conflict", self.kinds(graph))

    def test_identity_conflict_detects_transitive_same_as_path(self):
        graph = Graph()
        graph.add((EX.a, OWL.sameAs, EX.b))
        graph.add((EX.b, OWL.sameAs, EX.c))
        graph.add((EX.a, OWL.differentFrom, EX.c))
        self.assertIn("identity_conflict", self.kinds(graph))

    def test_unequal_functional_literal_values_are_inconsistent(self):
        graph = Graph()
        graph.add((EX.p, RDF.type, OWL.FunctionalProperty))
        graph.add((EX.a, EX.p, Literal("1", datatype=XSD.integer)))
        graph.add((EX.a, EX.p, Literal("2", datatype=XSD.integer)))
        self.assertIn("functional_literal_conflict", self.kinds(graph))

    def test_equal_numeric_values_with_different_datatypes_are_consistent(self):
        graph = Graph()
        graph.add((EX.p, RDF.type, OWL.FunctionalProperty))
        graph.add((EX.a, EX.p, Literal("1", datatype=XSD.integer, normalize=False)))
        graph.add((EX.a, EX.p, Literal("1.0", datatype=XSD.decimal, normalize=False)))
        self.assertTrue(self.expanded(graph)["consistent"])

    def test_disjoint_properties_require_overlapping_subject_and_object(self):
        graph = Graph()
        graph.add((EX.p, OWL.propertyDisjointWith, EX.q))
        graph.add((EX.a, EX.p, EX.b))
        graph.add((EX.a, EX.q, EX.c))
        self.assertTrue(self.expanded(graph)["consistent"])
        graph.add((EX.b, OWL.sameAs, EX.c))
        self.assertIn("disjoint_properties", self.kinds(graph))

    def test_all_disjoint_properties_detects_shared_value(self):
        graph = Graph()
        head = BNode()
        Collection(graph, head, [EX.p, EX.q])
        graph.add((EX.distinct, RDF.type, OWL.AllDisjointProperties))
        graph.add((EX.distinct, OWL.members, head))
        graph.add((EX.a, EX.p, EX.b))
        graph.add((EX.a, EX.q, EX.b))
        self.assertIn("disjoint_properties", self.kinds(graph))

    def test_irreflexive_relation_respects_same_as(self):
        graph = Graph()
        graph.add((EX.p, RDF.type, OWL.IrreflexiveProperty))
        graph.add((EX.a, EX.p, EX.b))
        self.assertTrue(self.expanded(graph)["consistent"])
        graph.add((EX.a, OWL.sameAs, EX.b))
        self.assertIn("irreflexive_property", self.kinds(graph))

    def test_asymmetric_relation_allows_one_direction_only(self):
        graph = Graph()
        graph.add((EX.p, RDF.type, OWL.AsymmetricProperty))
        graph.add((EX.a, EX.p, EX.b))
        self.assertTrue(self.expanded(graph)["consistent"])
        graph.add((EX.b, EX.p, EX.a))
        self.assertIn("asymmetric_property", self.kinds(graph))

    def negative_graph(self, target, value=False):
        graph = Graph()
        graph.add((EX.negation, RDF.type, OWL.NegativePropertyAssertion))
        graph.add((EX.negation, OWL.sourceIndividual, EX.a))
        graph.add((EX.negation, OWL.assertionProperty, EX.p))
        graph.add((EX.negation, OWL.targetValue if value else OWL.targetIndividual, target))
        return graph

    def test_negative_object_assertion_is_not_a_missing_fact_check(self):
        graph = self.negative_graph(EX.b)
        self.assertTrue(self.expanded(graph)["consistent"])
        graph.add((EX.a, EX.p, EX.b))
        self.assertIn("negative_property_assertion", self.kinds(graph))

    def test_negative_data_assertion_uses_value_not_lexical_equality(self):
        graph = self.negative_graph(Literal("1", datatype=XSD.integer), value=True)
        graph.add((EX.a, EX.p, Literal("1.0", datatype=XSD.decimal, normalize=False)))
        self.assertIn("negative_property_assertion", self.kinds(graph))

    def test_invalid_datatype_lexical_forms_and_integer_bounds(self):
        for lexical, datatype in (("oops", XSD.integer), ("256", XSD.unsignedByte),
                                  ("-1", XSD.nonNegativeInteger), ("maybe", XSD.boolean),
                                  ("1e2", XSD.decimal), ("infinity", XSD.double),
                                  ("\u00a01\u00a0", XSD.integer),
                                  ("2026-99-01", XSD.date)):
            with self.subTest(lexical=lexical, datatype=datatype):
                graph = Graph()
                graph.add((EX.a, EX.p, Literal(lexical, datatype=datatype, normalize=False)))
                self.assertIn("invalid_literal", self.kinds(graph))

    def test_valid_datatype_lexical_variants_are_accepted(self):
        graph = Graph()
        for lexical, datatype in (("+001", XSD.integer), (" 1 ", XSD.boolean),
                                  (".5", XSD.decimal), ("INF", XSD.double),
                                  ("2026-10-05T00:00:00Z", XSD.dateTime)):
            graph.add((EX.a, EX.p, Literal(lexical, datatype=datatype, normalize=False)))
        self.assertTrue(self.expanded(graph)["consistent"])

    def test_negative_assertion_detects_an_inferred_subproperty_fact(self):
        graph = self.negative_graph(EX.b)
        graph.add((EX.q, Namespace("http://www.w3.org/2000/01/rdf-schema#").subPropertyOf, EX.p))
        graph.add((EX.a, EX.q, EX.b))
        self.assertIn("negative_property_assertion", self.kinds(graph))

    def test_custom_datatype_is_not_reported_as_invalid(self):
        graph = Graph()
        graph.add((EX.a, EX.p, Literal("unknown syntax", datatype=EX.custom)))
        self.assertTrue(self.expanded(graph)["consistent"])

    def test_custom_datatypes_do_not_imply_known_unequal_values(self):
        graph = Graph()
        graph.add((EX.p, RDF.type, OWL.FunctionalProperty))
        graph.add((EX.a, EX.p, Literal("one", datatype=EX.custom)))
        graph.add((EX.a, EX.p, Literal("1", datatype=EX.otherCustom)))
        self.assertTrue(self.expanded(graph)["consistent"])

    def test_boolean_lexical_variants_compare_by_value(self):
        graph = Graph()
        graph.add((EX.p, RDF.type, OWL.FunctionalProperty))
        graph.add((EX.a, EX.p, Literal("1", datatype=XSD.boolean, normalize=False)))
        graph.add((EX.a, EX.p, Literal("true", datatype=XSD.boolean, normalize=False)))
        self.assertTrue(self.expanded(graph)["consistent"])


if __name__ == "__main__":
    unittest.main()
