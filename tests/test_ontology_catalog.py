"""Local draft creation keeps its file boundary and supports usable RDF from restart."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyshacl
from rdflib import Graph, Namespace
from rdflib.compare import isomorphic
from rdflib.namespace import RDF

import ontology_catalog as catalog


class OntologyCatalogTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.builtins = {"mv": {"name": "뮤직비디오", "version": "1.2.1"}}
        self.payload = {"id": "film-draft", "name": "영화 제작 기록", "description": "영화 제작에 필요한 기록을 정리합니다."}

    def create(self, payload=None):
        return catalog.create_ontology(payload or self.payload, self.builtins, self.root)

    def test_restart_discovers_complete_profile_and_canonical_exports(self):
        created = self.create()
        profiles = catalog.load_custom_profiles(self.root)
        self.assertEqual(profiles["film-draft"], created["config"])
        self.assertEqual(catalog.custom_modules(self.root), [created["module"]])
        self.assertEqual([row["id"] for row in catalog.public_catalog(self.builtins, self.root)], ["mv", "film-draft"])
        self.assertTrue(catalog.public_catalog(self.builtins, self.root)[1]["draft"])
        schema = Graph().parse(self.root / created["config"]["schema"])
        owl = Graph().parse(self.root / created["config"]["owl"], format="xml")
        self.assertTrue(isomorphic(schema, owl))

    def test_raw_example_conforms_and_query_exposes_missing_type_or_label(self):
        created = self.create()
        config = created["config"]
        schema = Graph().parse(self.root / config["schema"])
        shapes = Graph().parse(self.root / config["shapes"])
        data = Graph().parse(self.root / config["example"])
        ns = Namespace(config["prefix"])
        query = f"SELECT ?record ?name WHERE {{ ?record a <{ns.Record}> ; <{ns.displayName}> ?name }}"
        self.assertTrue(pyshacl.validate(data, shacl_graph=shapes, ont_graph=schema, inference="none")[0])
        self.assertEqual(len(list(data.query(query))), 1)
        for removed in [(ns.sampleRecord, RDF.type, ns.Record), (ns.sampleRecord, ns.displayName, None)]:
            with self.subTest(removed=removed):
                incomplete = Graph() + data
                incomplete.remove(removed)
                self.assertFalse(pyshacl.validate(incomplete, shacl_graph=shapes, ont_graph=schema, inference="none")[0])
                self.assertEqual(len(list(incomplete.query(query))), 0)

    def test_invalid_identifiers_never_create_directories(self):
        for identifier in ("../outside", "/outside", "..", "CON", "con", "a", "two--hyphens", "a/b", "한국어", "x" * 49):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                self.create({**self.payload, "id": identifier})
        self.assertFalse((self.root / "custom-ontologies").exists())

    def test_missing_description_and_non_object_payload_are_rejected(self):
        for payload in ({"id": "film-draft", "name": "영화"}, {**self.payload, "description": 12}, []):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                catalog.create_ontology(payload, self.builtins, self.root)

    def test_duplicates_and_builtin_ids_never_overwrite(self):
        with self.assertRaises(FileExistsError):
            self.create({**self.payload, "id": "mv"})
        created = self.create()
        example = self.root / created["config"]["example"]
        original = example.read_bytes()
        with self.assertRaises(FileExistsError):
            self.create({**self.payload, "name": "덮어쓰기"})
        self.assertEqual(example.read_bytes(), original)

    def test_concurrent_same_id_has_exactly_one_winner(self):
        def attempt():
            try:
                return self.create()["id"]
            except FileExistsError:
                return "duplicate"
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(results, ["film-draft", "duplicate"])
        self.assertEqual(len(catalog.load_custom_profiles(self.root)), 1)

    def test_failure_before_publish_leaves_no_partial_profile(self):
        real_write = catalog._write
        def fail_on_metadata(path, content):
            if path.name == "profile.json":
                raise OSError("simulated interruption")
            real_write(path, content)
        with patch.object(catalog, "_write", side_effect=fail_on_metadata), self.assertRaises(OSError):
            self.create()
        self.assertEqual(catalog.load_custom_profiles(self.root), {})
        self.assertFalse((self.root / "custom-ontologies" / "film-draft").exists())
        self.assertFalse(list((self.root / "custom-ontologies").glob(".creating-*")))

    def test_metadata_path_and_identifier_tampering_are_rejected(self):
        self.create()
        metadata = self.root / "custom-ontologies/film-draft/profile.json"
        original = json.loads(metadata.read_text(encoding="utf-8"))
        for changes in ({"schema": "../../outside.ttl"}, {"id": "other-id"}, {"prefix": "https://foreign.example/#"}, {"custom": False}):
            metadata.write_text(json.dumps({**original, **changes}), encoding="utf-8")
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                catalog.load_custom_profiles(self.root)

    def test_missing_or_invalid_metadata_cannot_be_loaded(self):
        self.create()
        metadata = self.root / "custom-ontologies/film-draft/profile.json"
        for text in ("[]", "null", "not-json"):
            metadata.write_text(text, encoding="utf-8")
            with self.subTest(text=text), self.assertRaises(ValueError):
                catalog.load_custom_profiles(self.root)
        metadata.unlink()
        with self.assertRaises(ValueError):
            catalog.load_custom_profiles(self.root)

    def test_a_linked_catalog_is_rejected_before_writing(self):
        linked = self.root / "custom-ontologies"
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path == linked or original(path)):
            with self.assertRaisesRegex(ValueError, "링크"):
                self.create()
        self.assertFalse(linked.exists())

    def test_rdf_content_is_serialized_as_literals(self):
        malicious_name = '영화 " ; <https://foreign.example/p> "injected'
        result = self.create({**self.payload, "name": malicious_name})
        data = Graph().parse(self.root / result["config"]["example"])
        self.assertEqual(len(data), 2)
        self.assertIn(malicious_name, str(next(data.objects(None, Namespace(result["config"]["prefix"]).displayName))))


if __name__ == "__main__":
    unittest.main()
