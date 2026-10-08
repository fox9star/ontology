"""Counterexamples where RDFS would otherwise conceal absent source types."""

import unittest
from rdflib import BNode, Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD
from validation_pipeline import validate_phases, public_summary

N = Namespace('https://example.test/explicit#')


class ValidationPhaseTests(unittest.TestCase):
    def setUp(self):
        self.schema = Graph()
        for kind in (N.Project, N.Asset, N.Image, N.Other):
            self.schema.add((kind, RDF.type, OWL.Class))
        self.schema.add((N.Image, RDFS.subClassOf, N.Asset))
        self.schema.add((N.hasAsset, RDFS.domain, N.Project))
        self.schema.add((N.hasAsset, RDFS.range, N.Asset))
        self.schema.add((N.hasAsset, RDF.type, OWL.ObjectProperty))
        self.shapes = Graph()
        self.shapes.add((N.Shape, SH.targetSubjectsOf, N.hasAsset))
        self.shapes.add((N.Shape, SH.property, N.LinkShape))
        self.shapes.add((N.LinkShape, SH.path, N.hasAsset))
        self.shapes.add((N.LinkShape, SH['class'], N.Asset))
        self.data = Graph()
        self.data.add((N.project, RDF.type, N.Project))
        self.data.add((N.project, N.hasAsset, N.image))
        self.data.add((N.image, RDF.type, N.Image))

    def run_validation(self):
        return validate_phases(self.data, self.schema, self.shapes)

    def test_asserted_subclass_is_valid_without_redundant_base_type(self):
        result = self.run_validation()
        self.assertTrue(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertGreater(result['inferred_type_count'], 0)

    def test_missing_object_type_is_not_repaired_for_acceptance(self):
        self.data.remove((N.image, RDF.type, None))
        result = self.run_validation()
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])
        self.assertFalse(result['conforms'])

    def test_missing_subject_type_cannot_evade_class_targets(self):
        self.data.remove((N.project, RDF.type, None))
        result = self.run_validation()
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])

    def test_wrong_type_is_not_repaired_by_range_inference(self):
        self.data.remove((N.image, RDF.type, None))
        self.data.add((N.image, RDF.type, N.Other))
        result = self.run_validation()
        self.assertFalse(result['raw_conforms'])
        self.assertTrue(result['inferred_conforms'])

    def test_asserted_dictionary_instance_is_a_valid_reference(self):
        self.data.remove((N.image, RDF.type, None))
        self.schema.add((N.image, RDF.type, N.Image))
        self.assertTrue(self.run_validation()['conforms'])

    def test_raw_union_domain_accepts_recorded_member_and_rejects_missing_type(self):
        union, head, rest = BNode(), BNode(), BNode()
        self.schema.remove((N.hasAsset, RDFS.domain, None))
        self.schema.add((N.hasAsset, RDFS.domain, union))
        self.schema.add((union, OWL.unionOf, head))
        self.schema.add((head, RDF.first, N.Project))
        self.schema.add((head, RDF.rest, rest))
        self.schema.add((rest, RDF.first, N.Other))
        self.schema.add((rest, RDF.rest, RDF.nil))
        self.assertTrue(self.run_validation()['raw_conforms'])
        self.data.remove((N.project, RDF.type, None))
        self.assertFalse(self.run_validation()['raw_conforms'])

    def test_both_phases_leave_all_caller_graphs_unchanged(self):
        previous = tuple(set(g) for g in (self.data, self.schema, self.shapes))
        self.run_validation()
        self.assertEqual(previous, tuple(set(g) for g in (self.data, self.schema, self.shapes)))

    def test_named_union_accepts_explicit_member_or_union_type(self):
        head, rest = BNode(), BNode()
        self.schema.add((N.Union, RDF.type, OWL.Class))
        self.schema.add((N.Union, OWL.unionOf, head))
        self.schema.add((head, RDF.first, N.Project))
        self.schema.add((head, RDF.rest, rest))
        self.schema.add((rest, RDF.first, N.Other))
        self.schema.add((rest, RDF.rest, RDF.nil))
        self.schema.set((N.hasAsset, RDFS.domain, N.Union))
        self.assertTrue(self.run_validation()['raw_conforms'])
        self.data.set((N.project, RDF.type, N.Union))
        self.assertTrue(self.run_validation()['raw_conforms'])
        self.data.remove((N.project, RDF.type, None))
        self.assertFalse(self.run_validation()['raw_conforms'])

    def test_public_summary_has_no_identifier_or_raw_value(self):
        self.data.remove((N.image, RDF.type, None))
        result = self.run_validation()
        import json
        encoded = json.dumps(public_summary(result))
        self.assertNotIn(str(N.image), encoded)
        self.assertNotIn('report_text', encoded)
        self.assertGreater(result['raw_results'], 0)


if __name__ == '__main__':
    unittest.main()
