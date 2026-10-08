"""An explicit source URI mapping preserves containment and integrity checks."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, URIRef, XSD

import project_store

MV = Namespace("https://example.org/mv#")
ORIGINAL_ROOT = "file:///C:/Users/example/Desktop/original%20workspace/ontology/"


class TestProjectPortability(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ontology-portability-")
        self.addCleanup(self.temporary.cleanup)
        self.projects = Path(self.temporary.name) / "relocated" / "projects"
        self.directory = self.projects / "fixture"
        self.filename = "posters/cover #한글.png"
        self.asset = self.directory / "assets" / self.filename
        self.asset.parent.mkdir(parents=True)
        self.asset.write_bytes(b"registered bytes")
        (self.directory / "project.json").write_text(json.dumps({"id": "fixture", "ontology": "mv"}), encoding="utf-8")
        self.manifest = {"project_id": "fixture", "timeline": [], "assets": [{
            "id": "image01", "kind": "image", "file_name": self.filename,
            "file_uri": self.asset.as_uri(), "width": 1, "height": 1,
            "sha256": hashlib.sha256(self.asset.read_bytes()).hexdigest(),
        }]}
        self.graph = Graph()
        self.graph.add((MV.image01, MV.width, Literal(1, datatype=XSD.integer)))
        self.graph.add((MV.image01, MV.height, Literal(1, datatype=XSD.integer)))
        self.store_patch = patch.object(project_store, "PROJECTS_DIR", self.projects)
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)
        self.env_patch = patch.dict("os.environ", {"ONTOLOGY_REGISTERED_ROOT_URI": ""})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.set_uri(self.asset.as_uri())

    def set_uri(self, uri):
        self.manifest["assets"][0]["file_uri"] = uri
        self.graph.set((MV.image01, MV.fileUri, URIRef(uri)))
        self.write_manifest()

    def write_manifest(self):
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

    def check(self):
        return project_store.check_assets("fixture", self.graph, MV)[0]

    def mapped_uri(self):
        return ORIGINAL_ROOT + "projects/fixture/assets/" + "/".join(quote(part, safe="") for part in Path(self.filename).parts)

    def test_default_preserves_strict_native_uri_check(self):
        self.assertTrue(self.check()["valid"])
        self.set_uri(self.mapped_uri())
        self.assertFalse(self.check()["valid"])

    def test_explicit_root_accepts_registered_source_uri_and_encodes_parts(self):
        mapped = self.mapped_uri()
        self.set_uri(mapped)
        with patch.dict("os.environ", {"ONTOLOGY_REGISTERED_ROOT_URI": ORIGINAL_ROOT}):
            result = self.check()
        self.assertTrue(result["valid"], result["errors"])
        self.assertTrue(result["sha256_matches"])
        self.assertIn("cover%20%23%ED%95%9C%EA%B8%80.png", mapped)
        self.assertEqual(self.manifest["assets"][0]["file_uri"], mapped)

    def test_same_foreign_uri_in_manifest_and_rdf_still_fails(self):
        self.set_uri("file:///C:/different/ontology/projects/fixture/assets/cover.png")
        with patch.dict("os.environ", {"ONTOLOGY_REGISTERED_ROOT_URI": ORIGINAL_ROOT}):
            result = self.check()
        self.assertFalse(result["valid"])
        self.assertTrue(result["sha256_matches"])

    def test_mapping_does_not_accept_relocated_uri_instead_of_registered_uri(self):
        with patch.dict("os.environ", {"ONTOLOGY_REGISTERED_ROOT_URI": ORIGINAL_ROOT}):
            result = self.check()
        self.assertFalse(result["valid"])

    def test_hash_tampering_is_rejected_with_mapping_enabled(self):
        self.set_uri(self.mapped_uri())
        self.asset.write_bytes(b"tampered bytes")
        with patch.dict("os.environ", {"ONTOLOGY_REGISTERED_ROOT_URI": ORIGINAL_ROOT}):
            result = self.check()
        self.assertFalse(result["valid"])
        self.assertFalse(result["sha256_matches"])

    def test_traversal_filename_is_rejected_with_mapping_enabled(self):
        self.manifest["assets"][0]["file_name"] = "../outside.png"
        self.write_manifest()
        with patch.dict("os.environ", {"ONTOLOGY_REGISTERED_ROOT_URI": ORIGINAL_ROOT}):
            result = self.check()
        self.assertFalse(result["valid"])
        self.assertFalse(result["exists"])

    def test_invalid_or_traversing_root_fails_closed(self):
        roots = (
            "https://example.org/ontology/", "file://remote-host/ontology/", "file:///C:/ontology",
            "file:///C:/ontology/../other/", "file:///C:/ontology/%2e%2e/",
            "file:///C:/ontology/%2Fother/", "file:///C:/ontology/%5Cother/",
            "file:///C:/ontology/?query=1", "file:///C:/ontology/#fragment", "file:///C:/bad%XX/",
            "file:///C:/bad\nroot/", "file:///C:/bad%00root/", "file:///C://ontology/",
        )
        for root in roots:
            with self.subTest(root=root), patch.dict("os.environ", {"ONTOLOGY_REGISTERED_ROOT_URI": root}):
                with self.assertRaises(project_store.ProjectError):
                    self.check()


if __name__ == "__main__":
    unittest.main()
