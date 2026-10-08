"""Snapshot regression tests isolated from production graphs and snapshots."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rdflib import BNode, Graph, Literal, RDF, URIRef
from rdflib.compare import isomorphic

import graph_versioning as versioning
from graph_io import write_graph_atomic


def sample_graph(value="original"):
    graph = Graph()
    graph.add((URIRef("https://example.org/entity"), URIRef("https://example.org/value"), Literal(value)))
    return graph


class TestGraphVersioning(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.patch = patch.object(versioning, "SNAPSHOT_DIR", str(self.root / "snapshots"))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_rapid_snapshots_unique_and_scoped_lists(self):
        global_snapshots = [versioning.create_snapshot("mv", sample_graph()) for _ in range(12)]
        project = versioning.create_snapshot("mv", sample_graph(), project_id="late-night-mood")
        self.assertEqual(len({snapshot["snapshot_id"] for snapshot in global_snapshots}), 12)
        self.assertEqual(len(versioning.list_snapshots("mv", project_id=None)), 12)
        self.assertEqual(versioning.list_snapshots("mv", project_id="late-night-mood")[0]["snapshot_id"], project["snapshot_id"])
        self.assertEqual(len(versioning.list_snapshots("mv")), 13)

    def test_persistent_restore_and_reload(self):
        original = sample_graph()
        metadata = versioning.create_snapshot("mv", original, project_id="project-one")
        target = sample_graph("edited")
        path = self.root / "project.ttl"
        write_graph_atomic(target, path)
        result = versioning.rollback_to_snapshot("mv", metadata["snapshot_id"], target, path, "project-one")
        self.assertTrue(result["persisted"])
        self.assertTrue(isomorphic(target, original))
        self.assertTrue(isomorphic(Graph().parse(path, format="turtle"), original))

    def test_domain_and_project_mismatch_leave_disk_and_memory_intact(self):
        snapshot = versioning.create_snapshot("mv", sample_graph(), project_id="project-one")
        for domain, project_id in [("agent", "project-one"), ("mv", None), ("mv", "project-two")]:
            with self.subTest(domain=domain, project_id=project_id):
                target = sample_graph("edited")
                path = self.root / "target.ttl"
                write_graph_atomic(target, path)
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, "scope"):
                    versioning.rollback_to_snapshot(domain, snapshot["snapshot_id"], target, path, project_id)
                self.assertEqual(path.read_bytes(), before)
                self.assertTrue(isomorphic(target, sample_graph("edited")))

    def test_tampered_snapshot_rejected(self):
        metadata = versioning.create_snapshot("mv", sample_graph())
        Path(metadata["file_path"]).write_text("# tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity"):
            versioning.load_snapshot_graph(metadata["snapshot_id"])
        with self.assertRaisesRegex(ValueError, "integrity"):
            versioning.rollback_to_snapshot("mv", metadata["snapshot_id"], sample_graph(), self.root / "data.ttl")

    def test_invalid_ids_and_scope_components(self):
        for identifier in ["../snap_escape", "snap_x/../../escape", "snap_x\\escape", "/snap_abs", "snap_a.ttl", "snap_a\0"]:
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                versioning.load_snapshot_graph(identifier)
        with self.assertRaises(ValueError):
            versioning.create_snapshot("../mv", sample_graph())

    def test_legacy_snapshot_listed_but_restore_refused(self):
        root = Path(versioning.SNAPSHOT_DIR)
        root.mkdir()
        snapshot_id = "snap_mv_20260101_000000"
        sample_graph().serialize(destination=root / f"{snapshot_id}.ttl", format="turtle")
        (root / f"{snapshot_id}.json").write_text(json.dumps({
            "snapshot_id": snapshot_id, "domain": "mv", "created_at": "2026-01-01 00:00:00"
        }), encoding="utf-8")
        self.assertFalse(versioning.list_snapshots()[0]["restorable"])
        self.assertEqual(len(versioning.load_snapshot_graph(snapshot_id)), 1)
        with self.assertRaisesRegex(ValueError, "Legacy"):
            versioning.rollback_to_snapshot("mv", snapshot_id, sample_graph(), self.root / "data.ttl")

    def test_write_failure_preserves_file_and_graph(self):
        metadata = versioning.create_snapshot("mv", sample_graph())
        target = sample_graph("edited")
        path = self.root / "data.ttl"
        write_graph_atomic(target, path)
        before = path.read_bytes()
        with patch("graph_io.os.replace", side_effect=OSError("replace denied")):
            with self.assertRaises(OSError):
                versioning.rollback_to_snapshot("mv", metadata["snapshot_id"], target, path)
        self.assertEqual(before, path.read_bytes())
        self.assertTrue(isomorphic(target, sample_graph("edited")))
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_missing_destination_refused(self):
        metadata = versioning.create_snapshot("mv", sample_graph())
        with self.assertRaisesRegex(ValueError, "destination_path"):
            versioning.rollback_to_snapshot("mv", metadata["snapshot_id"], sample_graph())

    def test_semantic_blank_nodes_and_full_uri_samples(self):
        one, two = Graph(), Graph()
        one.add((URIRef("https://example.org/long/entity"), RDF.value, BNode("first")))
        one.add((BNode("first"), RDF.value, Literal("same")))
        two.add((URIRef("https://example.org/long/entity"), RDF.value, BNode("second")))
        two.add((BNode("second"), RDF.value, Literal("same")))
        identical = versioning.compute_graph_diff(one, two)
        self.assertEqual((identical["added_count"], identical["removed_count"], identical["unchanged_count"]), (0, 0, 2))
        two.add((URIRef("https://example.org/other/entity"), RDF.value, Literal("new")))
        changed = versioning.compute_graph_diff(one, two)
        self.assertEqual(changed["added_count"], 1)
        self.assertEqual(changed["added"][0]["subject"], "https://example.org/other/entity")

    def test_metadata_path_cannot_redirect_snapshot_load(self):
        metadata = versioning.create_snapshot("mv", sample_graph())
        metadata["file_path"] = str(self.root / "unrelated.ttl")
        sample_graph("unrelated").serialize(destination=metadata["file_path"], format="turtle")
        meta_path = Path(versioning.SNAPSHOT_DIR) / f"{metadata['snapshot_id']}.json"
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        self.assertTrue(isomorphic(versioning.load_snapshot_graph(metadata["snapshot_id"]), sample_graph()))

    def test_missing_hash_or_wrong_count_refused(self):
        for alteration in ["missing_hash", "wrong_count"]:
            with self.subTest(alteration=alteration):
                metadata = versioning.create_snapshot("mv", sample_graph())
                if alteration == "missing_hash":
                    del metadata["sha256"]
                else:
                    metadata["triples_count"] = 999
                meta_path = Path(versioning.SNAPSHOT_DIR) / f"{metadata['snapshot_id']}.json"
                meta_path.write_text(json.dumps(metadata), encoding="utf-8")
                with self.assertRaises(ValueError):
                    versioning.load_snapshot_graph(metadata["snapshot_id"])

    def test_failed_metadata_write_does_not_publish_partial_snapshot(self):
        with patch("graph_versioning.write_bytes_atomic", side_effect=OSError("metadata denied")):
            with self.assertRaises(OSError):
                versioning.create_snapshot("mv", sample_graph())
        self.assertEqual(versioning.list_snapshots(), [])
        self.assertFalse(list(Path(versioning.SNAPSHOT_DIR).glob("*.ttl")))


if __name__ == "__main__":
    unittest.main()
