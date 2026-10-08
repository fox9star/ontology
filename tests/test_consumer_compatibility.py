"""Detect contract mutations while allowing additive endpoints and questions."""

import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from flask import jsonify
from rdflib import BNode, Dataset, Graph, Literal, RDF, SH, URIRef

import app
import consumer_compatibility as compatibility
from ontology_loader import load_schema_graph, load_shape_graph
from validation_pipeline import validate_phases


class ConsumerCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = compatibility.build_snapshot()
        cls.baseline = json.loads(compatibility.BASELINE.read_text(encoding="utf-8"))

    def changed(self):
        return copy.deepcopy(self.current)

    def assert_drift(self, changed, text):
        result = compatibility.compare_snapshots(self.baseline, changed)
        self.assertFalse(result["compatible"], result)
        self.assertEqual(result["status"], "major-review-required")
        self.assertTrue(any(text in issue for issue in result["issues"]), result)

    def test_current_contracts_match_frozen_reviewed_baseline(self):
        result = compatibility.compare_snapshots(self.baseline, self.current)
        self.assertTrue(result["compatible"], result)
        self.assertEqual(set(self.current["shacl"]), set(app.ONTOLOGIES) | {"evidence"})
        self.assertEqual(len(self.current["acceptance_cases"]), 2 * len(self.current['shacl']))
        for case, outcome in self.current["acceptance_cases"].items():
            self.assertEqual(outcome["raw_conforms"], case.endswith("-accept"))
            self.assertEqual(outcome["inferred_conforms"], case.endswith("-accept"))

    def test_blank_node_relabeling_and_serialization_order_are_semantically_stable(self):
        first = Graph().parse(data="""
          @prefix sh: <http://www.w3.org/ns/shacl#> .
          @prefix ex: <https://example.test/> .
          ex:Shape a sh:NodeShape ; sh:targetClass ex:Image ;
              sh:property [ sh:path ex:width ; sh:minCount 1 ; sh:maxCount 1 ] .
        """, format="turtle")
        second = Graph().parse(data=first.serialize(format="turtle"), format="turtle")
        old = compatibility.semantic_shape_snapshot(first)
        new = compatibility.semantic_shape_snapshot(second)
        self.assertEqual(old, new)
        renamed = Graph()
        mapping = {node: BNode() for node in set(first.all_nodes()) if isinstance(node, BNode)}
        for subject, predicate, obj in reversed(list(first)):
            renamed.add((mapping.get(subject, subject), predicate, mapping.get(obj, obj)))
        self.assertEqual(old, compatibility.semantic_shape_snapshot(renamed))

    def test_presentation_message_change_does_not_change_constraint_semantics(self):
        shape = Graph().parse(data="""
          @prefix sh: <http://www.w3.org/ns/shacl#> .
          @prefix ex: <https://example.test/> .
          ex:Shape a sh:NodeShape ; sh:targetClass ex:Image ; sh:message "old explanation" .
        """, format="turtle")
        original = compatibility.semantic_shape_snapshot(shape)
        shape.set((URIRef("https://example.test/Shape"), SH.message, Literal("new explanation")))
        self.assertEqual(original, compatibility.semantic_shape_snapshot(shape))

    def test_shape_tightening_rejects_a_previously_accepted_frozen_instance(self):
        shapes = load_shape_graph(compatibility.ROOT, "mv-shapes.ttl")
        width = URIRef("https://example.org/mv#width")
        for constraint in shapes.subjects(SH.path, width):
            shapes.set((constraint, SH.minCount, Literal(2)))
        cases = Dataset().parse(compatibility.ROOT / compatibility.CASES, format="trig")
        result = validate_phases(cases.graph(URIRef(compatibility.CASE_NS + "mv-accept")),
                                 load_schema_graph(compatibility.ROOT, "mv-schema.ttl"), shapes)
        self.assertFalse(result["raw_conforms"])
        changed = self.changed()
        changed["shacl"]["mv"] = compatibility.semantic_shape_snapshot(shapes)
        self.assert_drift(changed, "SHACL semantic contract changed")

    def test_cardinality_enum_and_target_changes_detect_real_acceptance_drift(self):
        cases = Dataset().parse(compatibility.ROOT / compatibility.CASES, format="trig")
        schema = load_schema_graph(compatibility.ROOT, "mv-schema.ttl")
        for mutation in ("max-count", "enum", "target-class"):
            with self.subTest(mutation=mutation):
                shapes = load_shape_graph(compatibility.ROOT, "mv-shapes.ttl")
                expected = False
                case = "mv-accept"
                if mutation == "target-class":
                    # Removing the image target admits a formerly rejected image.
                    shapes.set((URIRef("https://example.org/mv#ImageAssetShape"),
                                SH.targetClass, URIRef("https://example.test/UnrelatedClass")))
                    case, expected = "mv-reject", True
                else:
                    for constraint in list(shapes.subjects(SH.path, URIRef("https://example.org/mv#width"))):
                        if mutation == "max-count":
                            shapes.set((constraint, SH.maxCount, Literal(0)))
                        else:
                            values = BNode()
                            shapes.add((constraint, SH["in"], values))
                            shapes.add((values, RDF.first, Literal(640)))
                            shapes.add((values, RDF.rest, RDF.nil))
                result = validate_phases(cases.graph(URIRef(compatibility.CASE_NS + case)), schema, shapes)
                self.assertEqual(result["raw_conforms"], expected)
                self.assertEqual(result["inferred_conforms"], expected)
                changed = self.changed()
                changed["shacl"]["mv"] = compatibility.semantic_shape_snapshot(shapes)
                self.assert_drift(changed, "SHACL semantic contract changed")

    def test_acceptance_or_rejection_change_requires_review(self):
        for case, field in [("academic-accept", "raw_conforms"), ("evidence-reject", "inferred_conforms")]:
            changed = self.changed()
            changed["acceptance_cases"][case][field] = not changed["acceptance_cases"][case][field]
            self.assert_drift(changed, "acceptance changed")

    def test_frozen_input_mutation_requires_review(self):
        changed = self.changed()
        changed["acceptance_fixture_sha256"] = "0" * 64
        self.assert_drift(changed, "fixture changed")

    def test_openapi_removal_and_response_declaration_change_require_review(self):
        operation = "GET /api/v1/domains"
        changed = self.changed()
        changed["openapi"]["operations"].pop(operation)
        self.assert_drift(changed, "operation removed")
        changed = self.changed()
        changed["openapi"]["operations"][operation]["responses"].pop("200")
        self.assert_drift(changed, "response declaration changed")

    def test_added_operations_and_questions_are_allowed_without_rewriting_baseline(self):
        changed = self.changed()
        changed["openapi"]["operations"]["GET /api/v1/new-read"] = {"responses": {"200": {}}}
        changed["competency_questions"]["NEW-01"] = {"variables": ["answer"], "golden_answer": {"variables": ["answer"], "rows": [["1"]]}, "query_sha256": "new", "input_sha256": {}}
        result = compatibility.compare_snapshots(self.baseline, changed)
        self.assertTrue(result["compatible"], result)
        already_added = compatibility.compare_snapshots(self.baseline, self.current)['allowed_additions']
        self.assertEqual(set(result['allowed_additions']) - set(already_added), {
            'OpenAPI operation added: GET /api/v1/new-read', 'Competency question added: NEW-01'})

    def test_actual_read_only_http_response_field_removal_is_detected(self):
        with patch.dict(app.app.view_functions, {"api_v1_domains": lambda: jsonify({"domains": list(app.ONTOLOGIES)})}):
            response = app.app.test_client().get("/api/v1/domains")
        changed = self.changed()
        changed["http_responses"]["GET /api/v1/domains"]["json"] = compatibility.response_shape(response.get_json())
        self.assert_drift(changed, "response field removed")

    def test_actual_read_only_http_response_field_type_change_is_detected(self):
        with patch.dict(app.app.view_functions, {"api_v1_auth_identity": lambda: jsonify({"authenticated": "yes", "identity": "local", "role": "owner"})}):
            response = app.app.test_client().get("/api/v1/auth/identity")
        changed = self.changed()
        changed["http_responses"]["GET /api/v1/auth/identity"]["json"] = compatibility.response_shape(response.get_json())
        self.assert_drift(changed, "response type changed")

    def test_new_response_field_is_additive(self):
        changed = self.changed()
        shape = changed["http_responses"]["GET /api/v1/domains"]["json"]
        shape["properties"]["extra"] = {"type": "string"}
        self.assertTrue(compatibility.compare_snapshots(self.baseline, changed)["compatible"])

    def test_question_variables_answers_query_and_fixture_drift_require_review(self):
        for field, replacement in [("variables", ["renamed"]),
                                   ("golden_answer", {"variables": ["shotName"], "rows": []}),
                                   ("query_sha256", "0" * 64),
                                   ("input_sha256", {"fixture.ttl": "0" * 64})]:
            with self.subTest(field=field):
                changed = self.changed()
                changed["competency_questions"]["MV-01"][field] = replacement
                self.assert_drift(changed, "golden/input contract changed")

    def test_question_removal_requires_review(self):
        changed = self.changed()
        changed["competency_questions"].pop("EV-01")
        self.assert_drift(changed, "question removed")

    def test_shapes_and_http_snapshots_contain_no_response_values_or_patient_data(self):
        payload = json.dumps(self.current)
        self.assertNotIn("PATIENT-9081", payload)
        self.assertNotIn("Patient_P9081", payload)
        self.assertNotIn("healthcare-example.ttl", payload)
        self.assertEqual(compatibility.response_shape({"identity": "PRIVATE-SENTINEL"}),
                         {"type": "object", "properties": {"identity": {"type": "string"}}})

    def test_missing_baseline_fails_without_automatically_creating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "absent.json"
            report = Path(directory) / "report.json"
            with patch("consumer_compatibility.build_snapshot", return_value=self.current), redirect_stdout(io.StringIO()):
                exit_code = compatibility.main(["--baseline", str(baseline), "--report", str(report)])
            self.assertNotEqual(exit_code, 0)
            self.assertFalse(baseline.exists())
            self.assertEqual(json.loads(report.read_text())["status"], "blocked")

    def test_collection_error_fails_closed_without_exposing_source_values(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline.json"
            baseline.write_text("reviewed baseline sentinel", encoding="utf-8")
            report = Path(directory) / "report.json"
            output = io.StringIO()
            with patch("consumer_compatibility.build_snapshot", side_effect=ValueError("PRIVATE-SOURCE-SENTINEL")), redirect_stdout(output):
                exit_code = compatibility.main(["--baseline", str(baseline), "--report", str(report)])
            self.assertNotEqual(exit_code, 0)
            self.assertEqual(baseline.read_text(encoding="utf-8"), "reviewed baseline sentinel")
            payload = report.read_text(encoding="utf-8")
            self.assertEqual(json.loads(payload)["status"], "blocked")
            self.assertNotIn("PRIVATE-SOURCE-SENTINEL", payload + output.getvalue())


if __name__ == "__main__":
    unittest.main()
