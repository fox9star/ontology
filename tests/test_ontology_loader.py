"""Local import closure must be complete, deterministic and offline."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF
from ontology_loader import load_schema_bundle, load_schema_graph

NS = Namespace("https://example.test/modules/")


class ModuleLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def module(self, name, imports=(), version_iri=None):
        graph = Graph()
        graph.add((NS[name], RDF.type, OWL.Ontology))
        graph.add((NS[name], OWL.versionInfo, Literal("1.0.0")))
        graph.add((NS[name + "Term"], RDF.type, OWL.Class))
        for imported in imports:
            graph.add((NS[name], OWL.imports, imported))
        if version_iri:
            graph.add((NS[name], OWL.versionIRI, version_iri))
        graph.serialize(self.root / (name + "-schema.ttl"), format="turtle")

    def test_transitive_version_iri_import_is_loaded_without_fetching_external(self):
        external = URIRef("http://www.w3.org/ns/prov-o#")
        self.module("a", (NS.bVersion,))
        self.module("b", (NS.c, external), NS.bVersion)
        self.module("c")
        with patch("urllib.request.urlopen", side_effect=AssertionError("network not allowed")):
            graph, metadata = load_schema_bundle(self.root, "a-schema.ttl")
        self.assertIn((NS.cTerm, RDF.type, OWL.Class), graph)
        self.assertEqual(len(metadata["modules"]), 3)
        self.assertEqual(metadata["external_references_not_loaded"], [str(external)])
        self.assertFalse(metadata["network_imports"])

    def test_unknown_import_cannot_silently_return_partial_graph(self):
        self.module("a", (NS.missing,))
        with self.assertRaisesRegex(FileNotFoundError, "Unresolved"):
            load_schema_graph(self.root, "a-schema.ttl")

    def test_import_cycle_is_rejected(self):
        self.module("a", (NS.b,))
        self.module("b", (NS.a,))
        with self.assertRaisesRegex(ValueError, "cycle"):
            load_schema_graph(self.root, "a-schema.ttl")

    def test_version_alias_collision_is_rejected(self):
        self.module("a", version_iri=NS.alias)
        self.module("b", version_iri=NS.alias)
        with self.assertRaisesRegex(ValueError, "collision"):
            load_schema_graph(self.root, "a-schema.ttl")

    def test_manifest_paths_cannot_escape_root(self):
        self.module("a")
        (self.root / "ontology_modules.json").write_text(json.dumps({"format_version": 1, "modules": [{"schema": "../outside-schema.ttl"}]}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "inside"):
            load_schema_graph(self.root, "a-schema.ttl")

    def test_manifest_missing_module_is_a_failure(self):
        self.module("a")
        (self.root / "ontology_modules.json").write_text(json.dumps({"format_version": 1, "modules": [{"schema": "a-schema.ttl"}, {"schema": "absent-schema.ttl"}]}), encoding="utf-8")
        with self.assertRaisesRegex(FileNotFoundError, "missing"):
            load_schema_graph(self.root, "a-schema.ttl")

    def test_supplemental_examples_and_questions_cannot_escape_root(self):
        self.module('a')
        for field in ('example', 'questions'):
            with self.subTest(field=field):
                (self.root / 'ontology_modules.json').write_text(json.dumps({
                    'format_version': 1, 'modules': [{'schema': 'a-schema.ttl', field: '../outside'}]}), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'inside'):
                    load_schema_graph(self.root, 'a-schema.ttl')

    def test_source_change_is_observed_on_next_read(self):
        self.module("a", (NS.b,))
        self.module("b")
        _, previous = load_schema_bundle(self.root, "a-schema.ttl")
        self.module("b", (NS.c,))
        self.module("c")
        _, current = load_schema_bundle(self.root, "a-schema.ttl")
        old_hash = next(item["sha256"] for item in previous["modules"] if item["file"] == "b-schema.ttl")
        new_hash = next(item["sha256"] for item in current["modules"] if item["file"] == "b-schema.ttl")
        self.assertNotEqual(old_hash, new_hash)
        self.assertEqual(len(current["modules"]), 3)

    def test_alternate_serialization_must_match_canonical_registered_graph(self):
        self.module('a')
        graph = Graph().parse(self.root / 'a-schema.ttl')
        graph.serialize(self.root / 'a.owl', format='xml')
        self.assertIn((NS.aTerm, RDF.type, OWL.Class), load_schema_graph(self.root, 'a.owl'))
        graph.add((NS.drift, RDF.type, OWL.Class))
        graph.serialize(self.root / 'a.owl', format='xml')
        with self.assertRaisesRegex(ValueError, 'differs'):
            load_schema_graph(self.root, 'a.owl')


if __name__ == "__main__":
    unittest.main()
