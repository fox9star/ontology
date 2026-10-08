"""Exercise persisted scene edits and scoped snapshots using only temporary data."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
from pathlib import Path
import shutil
import threading
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.compare import isomorphic
from rdflib.namespace import OWL

import app as studio
import graph_versioning
from test_codex_jobs import CodexJobTestCase


class TestAppMutations(CodexJobTestCase):
    def setUp(self):
        super().setUp()
        shutil.copyfile(Path(studio.__file__).resolve().parent / "mv-schema.ttl", self.data_dir / "mv-schema.ttl")
        snapshots = patch.object(graph_versioning, "SNAPSHOT_DIR", str(self.directory / "snapshots"))
        snapshots.start()
        self.addCleanup(snapshots.stop)
        self.namespace = Namespace(studio.ONTOLOGIES["mv"]["prefix"])

    def post_shot(self, payload=None, **kwargs):
        return self.client.post("/api/add-shot", json={} if payload is None else payload, **kwargs)

    def snapshot(self, project=None):
        payload = {"ont": "mv", "description": "Isolated API snapshot"}
        if project:
            payload["project"] = project
        response = self.client.post("/api/v1/snapshots/create", json=payload)
        self.assertEqual(response.status_code, 200)
        return response.get_json()["snapshot"]

    def test_default_add_shot_validates_and_persists_existing_image_reference(self):
        with patch.object(studio, "_validate_candidate", wraps=studio._validate_candidate) as validate:
            response = self.post_shot()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["validation"]["shacl_conforms"])
        validate.assert_called_once()
        self.assertEqual(validate.call_args.args[1], "mv")
        graph = Graph().parse(self.source, format="turtle")
        shot = self.namespace.shot03
        self.assertIn((shot, RDF.type, self.namespace.Shot), graph)
        self.assertEqual(graph.value(shot, self.namespace.usesImage), self.namespace.image02)
        self.assertEqual(graph.value(shot, self.namespace.orderIndex).toPython(), 3)
        self.assertEqual(graph.value(shot, self.namespace.startSecond).toPython(), Decimal("60"))
        self.assertIn((self.namespace.timeline01, self.namespace.hasShot, shot), graph)

    def test_label_is_literal_and_cannot_inject_turtle(self):
        label = '\" ; mv:status \"completed\" .\n<urn:injected> <urn:predicate> \"evil\" . #'
        response = self.post_shot({"label": label})
        self.assertEqual(response.status_code, 200)
        graph = Graph().parse(self.source, format="turtle")
        self.assertEqual(graph.value(self.namespace.shot03, RDFS.label), Literal(label, lang="ko"))
        self.assertEqual(len(list(graph.triples((URIRef("urn:injected"), None, None)))), 0)

    def test_invalid_ids_numbers_times_and_images_preserve_source(self):
        invalid = [
            {"shot_id": "../outside"}, {"shot_id": "bad;id"}, {"shot_id": "x" * 101},
            {"shot_id": None}, {"order_index": 0}, {"order_index": -1},
            {"order_index": 1.5}, {"order_index": True}, {"order_index": "NaN"},
            {"order_index": "Infinity"}, {"start_sec": "-1"}, {"start_sec": "NaN"},
            {"start_sec": "Infinity"}, {"start_sec": 90, "end_sec": 90},
            {"start_sec": 100, "end_sec": 90}, {"end_sec": "NaN"},
            {"end_sec": "Infinity"}, {"start_sec": []},
            {"image_uri": "https://example.org/assets/image02.png"},
            {"image_uri": str(self.namespace.audio01)}, {"image_uri": []}, {"label": {}},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                response = self.post_shot(payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_existing_id_or_order_is_conflict_and_source_preserved(self):
        for payload in ({"shot_id": "shot01"}, {"shot_id": "image02"}, {"order_index": 1}):
            with self.subTest(payload=payload):
                response = self.post_shot(payload)
                self.assertEqual(response.status_code, 409)
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_domains_projects_and_nonobject_bodies_are_rejected(self):
        cases = [
            ("/api/add-shot", {"ont": "devops"}),
            ("/api/add-shot?ont=agent", {}),
            ("/api/add-shot", {"project": "test-project"}),
            ("/api/add-shot?project=test-project", {}),
            ("/api/add-shot", []),
        ]
        for endpoint, payload in cases:
            with self.subTest(endpoint=endpoint, payload=payload):
                response = self.client.post(endpoint, json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.source.read_bytes(), self.original)

    def test_candidate_shacl_failure_returns_422_without_write(self):
        graph = Graph().parse(self.source, format="turtle")
        audio = next(graph.subjects(RDF.type, self.namespace.AudioAsset))
        graph.set((audio, self.namespace.durationSeconds, Literal("0", datatype=XSD.decimal)))
        graph.serialize(destination=self.source, format="turtle")
        before = self.source.read_bytes()
        with patch.object(studio, "write_graph_atomic", wraps=studio.write_graph_atomic) as write:
            response = self.post_shot()
        self.assertEqual(response.status_code, 422)
        self.assertIn("SHACL", response.get_json()["error"])
        write.assert_not_called()
        self.assertEqual(self.source.read_bytes(), before)

    def test_concurrent_adds_with_same_order_have_one_winner(self):
        barrier = threading.Barrier(2)

        def add(shot_id):
            client = studio.app.test_client()
            barrier.wait()
            response = client.post("/api/add-shot", json={"shot_id": shot_id, "order_index": 3})
            return response.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(add, ("concurrent_a", "concurrent_b")))
        self.assertEqual(sorted(codes), [200, 409])
        graph = Graph().parse(self.source, format="turtle")
        self.assertEqual(len(set(graph.subjects(RDF.type, self.namespace.Shot))), 3)
        self.assertEqual(sum(1 for value in graph.objects(None, self.namespace.orderIndex) if value.toPython() == 3), 1)

    def test_snapshot_contains_only_selected_data(self):
        metadata = self.snapshot()
        stored = graph_versioning.load_snapshot_graph(metadata["snapshot_id"])
        source = Graph().parse(self.source, format="turtle")
        self.assertTrue(isomorphic(stored, source))
        self.assertEqual(metadata["source_kind"], "data_only")
        self.assertEqual(metadata["scope"], {"domain": "mv", "project_id": None})
        self.assertGreater(len(studio.load_graph("mv")), len(stored))

    def test_snapshot_list_and_rollback_enforce_project_scope(self):
        self.make_project()
        global_snapshot = self.snapshot()
        project_snapshot = self.snapshot("test-project")
        global_list = self.client.get("/api/v1/snapshots?ont=mv").get_json()["snapshots"]
        project_list = self.client.get("/api/v1/snapshots?ont=mv&project=test-project").get_json()["snapshots"]
        self.assertEqual([item["snapshot_id"] for item in global_list], [global_snapshot["snapshot_id"]])
        self.assertEqual([item["snapshot_id"] for item in project_list], [project_snapshot["snapshot_id"]])
        response = self.client.post("/api/v1/snapshots/rollback", json={
            "ont": "mv", "snapshot_id": project_snapshot["snapshot_id"],
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_project_snapshot_rollback_persists_only_selected_data(self):
        data, _ = self.make_project()
        original_graph = Graph().parse(data, format="turtle")
        metadata = self.snapshot("test-project")
        modified = Graph().parse(data, format="turtle")
        modified.add((URIRef("urn:temporary"), RDFS.label, Literal("Remove on rollback")))
        modified.serialize(destination=data, format="turtle")
        response = self.client.post("/api/v1/snapshots/rollback", json={
            "ont": "mv", "project": "test-project", "snapshot_id": metadata["snapshot_id"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["persisted"])
        self.assertEqual(Path(response.get_json()["destination_path"]), data.resolve())
        self.assertTrue(isomorphic(Graph().parse(data, format="turtle"), original_graph))
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_invalid_snapshot_candidate_returns_422_and_preserves_source(self):
        graph = Graph().parse(self.source, format="turtle")
        audio = next(graph.subjects(RDF.type, self.namespace.AudioAsset))
        graph.set((audio, self.namespace.durationSeconds, Literal("0", datatype=XSD.decimal)))
        metadata = graph_versioning.create_snapshot("mv", graph)
        response = self.client.post("/api/v1/snapshots/rollback", json={
            "ont": "mv", "snapshot_id": metadata["snapshot_id"],
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.source.read_bytes(), self.original)


class TestAcademicDataSeparation(CodexJobTestCase):
    def setUp(self):
        super().setUp()
        source_dir = Path(studio.__file__).resolve().parent
        configuration = dict(studio.ONTOLOGIES["academic"])
        self.assertEqual(configuration["schema"], "academic-schema.ttl")
        self.assertEqual(configuration["example"], "academic-example.ttl")
        self.assertEqual(configuration["shapes"], "academic-shapes.ttl")
        for filename in (configuration["schema"], configuration["example"], configuration["shapes"]):
            shutil.copyfile(source_dir / filename, self.data_dir / filename)
        self.schema = self.data_dir / configuration["schema"]
        self.data = self.data_dir / configuration["example"]
        self.actual_schema = source_dir / configuration["schema"]
        self.schema_digest = hashlib.sha256(self.schema.read_bytes()).hexdigest()
        self.actual_schema_digest = hashlib.sha256(self.actual_schema.read_bytes()).hexdigest()
        self.namespace = Namespace(configuration["prefix"])
        self.initial_graph = Graph().parse(self.data, format="turtle")
        self.initial_subjects = {self.namespace.KimMinSu, self.namespace.DatabaseIntroduction}
        snapshots = patch.object(graph_versioning, "SNAPSHOT_DIR", str(self.directory / "snapshots"))
        snapshots.start()
        self.addCleanup(snapshots.stop)

    def assert_schema_unchanged(self):
        self.assertEqual(hashlib.sha256(self.schema.read_bytes()).hexdigest(), self.schema_digest)
        self.assertEqual(hashlib.sha256(self.actual_schema.read_bytes()).hexdigest(), self.actual_schema_digest)

    def assert_initial_instances_preserved(self):
        graph = Graph().parse(self.data, format="turtle")
        for triple in self.initial_graph:
            self.assertIn(triple, graph)
        self.assert_schema_unchanged()

    def create_student(self, label):
        response = self.client.post("/api/v1/instances", json={
            "ont": "academic", "class_uri": str(self.namespace.Student), "label": label,
            "properties": {"enrollsIn": str(self.namespace.DatabaseIntroduction)},
        })
        self.assertEqual(response.status_code, 200)
        value = response.get_json()
        self.assertTrue(value["success"])
        self.assertTrue(value["shacl_supported"])
        self.assertTrue(value["shacl_conforms"])
        self.assert_initial_instances_preserved()
        return value["instance_uri"]

    def test_academic_crud_and_snapshot_rollback_preserve_schema_and_initial_instances(self):
        self.assertEqual(len(self.initial_graph), 6)
        self.assertEqual(set(self.initial_graph.subjects(RDF.type, OWL.NamedIndividual)), self.initial_subjects)
        snapshot_response = self.client.post("/api/v1/snapshots/create", json={"ont": "academic"})
        self.assertEqual(snapshot_response.status_code, 200)
        metadata = snapshot_response.get_json()["snapshot"]
        snapshot_graph = graph_versioning.load_snapshot_graph(metadata["snapshot_id"])
        self.assertEqual(metadata["source_kind"], "data_only")
        self.assertEqual(metadata["triples_count"], 6)
        self.assertTrue(isomorphic(snapshot_graph, self.initial_graph))
        for schema_type in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.Restriction, OWL.Ontology):
            self.assertEqual(list(snapshot_graph.subjects(RDF.type, schema_type)), [])
        created_uri = self.create_student("임시 학생")
        explorer = self.client.get("/api/explorer?ont=academic")
        self.assertEqual(explorer.status_code, 200)
        instance_uris = {item["uri"] for item in explorer.get_json()["instances"]}
        self.assertEqual(instance_uris, {str(uri) for uri in self.initial_subjects} | {created_uri})
        deleted = self.client.delete("/api/v1/instances", json={"ont": "academic", "uri": created_uri})
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.get_json()["triples_removed"], 3)
        self.assertTrue(deleted.get_json()["shacl_conforms"])
        self.assertTrue(isomorphic(Graph().parse(self.data, format="turtle"), self.initial_graph))
        self.assert_initial_instances_preserved()
        self.create_student("롤백할 학생")
        restored = self.client.post("/api/v1/snapshots/rollback", json={
            "ont": "academic", "snapshot_id": metadata["snapshot_id"],
        })
        self.assertEqual(restored.status_code, 200)
        self.assertTrue(restored.get_json()["persisted"])
        self.assertEqual(Path(restored.get_json()["destination_path"]), self.data.resolve())
        self.assertTrue(isomorphic(Graph().parse(self.data, format="turtle"), self.initial_graph))
        self.assert_initial_instances_preserved()

    def test_academic_validation_uses_its_domain_shapes(self):
        response = self.client.get("/api/validate?ont=academic")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["supported"])
        self.assertTrue(response.get_json()["conforms"])
        validation = studio._validate_candidate(self.initial_graph, "academic")
        self.assertTrue(validation["shacl_supported"])
        self.assertTrue(validation["shacl_conforms"])
        self.assert_initial_instances_preserved()


if __name__ == "__main__":
    unittest.main()
