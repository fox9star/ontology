"""Exercise CRUD transactions with a temporary ontology and data files."""

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph, Literal, RDF, URIRef

import app as studio
import instance_editor
import project_store


EX = "https://example.org/crud#"


class TestInstanceCRUD(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = self.root / "data.ttl"
        self.data.write_text("", encoding="utf-8")
        schema = self.root / "schema.ttl"
        schema.write_text(
            '@prefix ex: <https://example.org/crud#> .\n'
            '@prefix owl: <http://www.w3.org/2002/07/owl#> .\n'
            '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n'
            '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n'
            'ex:Thing a rdfs:Class . ex:Linked a rdfs:Class .\n'
            'ex:kept a owl:DatatypeProperty ; rdfs:domain ex:Thing ; rdfs:range xsd:string .\n',
            encoding="utf-8")
        ontology = self.root / "ontology.owl"
        Graph().parse(schema, format="turtle").serialize(destination=ontology, format="xml")
        shapes = self.root / "shapes.ttl"
        shapes.write_text(
            '@prefix ex: <https://example.org/crud#> .\n'
            '@prefix sh: <http://www.w3.org/ns/shacl#> .\n'
            'ex:LinkedShape a sh:NodeShape; sh:targetClass ex:Linked;\n'
            '  sh:property [ sh:path ex:link; sh:minCount 1 ] .\n', encoding="utf-8")
        cfg = {"name": "CRUD test", "schema": str(schema), "owl": str(ontology),
               "shapes": str(shapes), "example": str(self.data), "prefix": EX}
        self.config_patch = patch.dict(studio.ONTOLOGIES, {"crud": cfg})
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.client = studio.app.test_client()

    def _read(self):
        return Graph().parse(self.data, format="turtle")

    def test_create_and_delete_persisted_instance(self):
        result = self.client.post("/api/v1/instances", json={
            "ont": "crud", "class_uri": EX + "Thing", "label": "테스트 개체", "properties": {}
        })
        self.assertEqual(result.status_code, 200, result.json)
        self.assertTrue(result.json["success"])
        self.assertTrue(result.json["shacl_conforms"])
        self.assertEqual(result.json["triples_added"], 2)
        uri = result.json["instance_uri"]
        self.assertEqual(len(self._read()), 2)
        deleted = self.client.delete("/api/v1/instances", query_string={"ont": "crud", "uri": uri})
        self.assertEqual(deleted.status_code, 200, deleted.json)
        self.assertTrue(deleted.json["success"])
        self.assertEqual(deleted.json["triples_removed"], 2)
        self.assertEqual(len(self._read()), 0)

    def test_create_instance_missing_fields(self):
        result = self.client.post("/api/v1/instances", json={"ont": "crud", "label": "이름"})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(self.data.read_bytes(), b"")

    def test_creation_shacl_failure_preserves_original(self):
        before = self.data.read_bytes()
        with self.assertRaises(project_store.ProjectError) as failed:
            instance_editor.create_instance("crud", EX + "Linked", "invalid")
        self.assertEqual(failed.exception.status_code, 422)
        self.assertEqual(self.data.read_bytes(), before)

    def test_deletion_that_breaks_required_reference_is_rejected(self):
        graph = Graph()
        target, linked = URIRef(EX + "target"), URIRef(EX + "linked")
        graph.add((target, RDF.type, URIRef(EX + "Thing")))
        graph.add((linked, RDF.type, URIRef(EX + "Linked")))
        graph.add((linked, URIRef(EX + "link"), target))
        graph.serialize(destination=self.data, format="turtle")
        before = self.data.read_bytes()
        with self.assertRaises(project_store.ProjectError) as failed:
            instance_editor.delete_instance("crud", str(target))
        self.assertEqual(failed.exception.status_code, 422)
        self.assertEqual(self.data.read_bytes(), before)
        self.assertEqual(len(self._read()), 3)

    def test_atomic_replace_failure_preserves_original(self):
        before = self.data.read_bytes()
        with patch("graph_io.os.replace", side_effect=OSError("replace denied")):
            with self.assertRaises(OSError):
                instance_editor.create_instance("crud", EX + "Thing", "unsaved")
        self.assertEqual(self.data.read_bytes(), before)

    def test_validation_project_scope_passed_and_media_failure_preserves_original(self):
        before = self.data.read_bytes()
        rejection = project_store.ProjectError("asset integrity mismatch", 422)
        with patch.object(studio, "selected_data_path", return_value=str(self.data)), \
                patch.object(studio, "_validate_candidate", side_effect=rejection) as validation:
            with self.assertRaises(project_store.ProjectError):
                instance_editor.create_instance("crud", EX + "Thing", "asset test", project_id="test-project")
            self.assertEqual(validation.call_args.args[1:], ("crud", "test-project"))
        self.assertEqual(self.data.read_bytes(), before)

    def test_concurrent_creations_preserve_every_instance(self):
        errors = []

        def create(index):
            try:
                instance_editor.create_instance("crud", EX + "Thing", f"item-{index}")
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=create, args=(index,)) for index in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(self._read()), 12)

    def test_counts_ignore_skipped_empty_properties(self):
        result = instance_editor.create_instance("crud", EX + "Thing", "values", {"empty": "", "kept": "value"})
        self.assertEqual(result["triples_added"], 3)
        self.assertEqual(len(self._read()), 3)


if __name__ == "__main__":
    unittest.main()
