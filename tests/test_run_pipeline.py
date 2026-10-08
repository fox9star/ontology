"""Demo pipeline tests run locally and never deliver remote writes or messages."""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from rdflib import Graph, Literal, XSD
from rdflib.compare import isomorphic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ontology_pipeline import MV, PROV, MusicVideoOntologyBuilder
from run_pipeline import DEMO, execute_end_to_end_pipeline, main


def normalize_decimals(graph):
    normalized = Graph()
    for subject, predicate, value in graph:
        if isinstance(value, Literal) and value.datatype == XSD.decimal:
            value = Literal(format(value.toPython().normalize(), "f"), datatype=XSD.decimal)
        normalized.add((subject, predicate, value))
    return normalized


class TestRunPipeline(unittest.TestCase):
    def setUp(self):
        self.remote = patch("requests.sessions.Session.request", side_effect=AssertionError("Network disabled in tests"))
        self.request = self.remote.start()
        self.addCleanup(self.remote.stop)

    def run_demo(self, directory, **kwargs):
        with redirect_stdout(io.StringIO()):
            success = execute_end_to_end_pipeline(directory, **kwargs)
        summary_path = sorted(Path(directory).glob("*/summary.json"))[-1]
        return success, json.loads(summary_path.read_text(encoding="utf-8"))

    def test_default_is_local_simulated_and_preserves_outputs(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {
            "SLACK_WEBHOOK_URL": "https://example.invalid/never",
            "GRAPH_STORE_UPDATE_ENDPOINT": "https://example.invalid/never",
        }):
            source = Path(directory) / "demo_project.ttl"
            source.write_text("source fixture", encoding="utf-8")
            success, summary = self.run_demo(directory)
            self.assertTrue(success)
            self.assertTrue(summary["simulated"])
            self.assertFalse(summary["media_generated"])
            self.assertEqual(summary["remote_update"], "not_requested")
            self.assertEqual(summary["webhook"], "not_requested")
            self.assertEqual(source.read_text(encoding="utf-8"), "source fixture")
            graph = Graph().parse(summary["outputs"]["turtle"], format="turtle")
            jsonld = Graph().parse(summary["outputs"]["jsonld"], format="json-ld")
            self.assertTrue(isomorphic(normalize_decimals(graph), normalize_decimals(jsonld)))
            self.assertIn((MV.demo_project, DEMO.simulated, Literal(True)), graph)
            self.assertEqual(set(graph.objects(None, MV.status)), {Literal("planned")})
            self.assertEqual(len(list(graph.triples((None, PROV.wasGeneratedBy, None)))), 0)
            self.request.assert_not_called()
            self.run_demo(directory)
            self.assertEqual(len(list(Path(directory).glob("*/summary.json"))), 2)

    def test_validation_failure_returns_failure_and_skips_remote(self):
        with TemporaryDirectory() as directory, patch.object(MusicVideoOntologyBuilder, "validate", return_value=(False, "Invalid demo")):
            success, summary = self.run_demo(directory, update_endpoint="https://example.invalid/update")
            self.assertFalse(success)
            self.assertEqual(summary["remote_update"], "skipped_invalid_graph")
            self.assertFalse(summary["conforms"])
            self.request.assert_not_called()

    def test_explicit_remote_failure_is_not_success(self):
        self.request.side_effect = None
        self.request.return_value = Mock(status_code=503)
        with TemporaryDirectory() as directory:
            success, summary = self.run_demo(directory, update_endpoint="https://example.invalid/update")
            self.assertFalse(success)
            self.assertEqual(summary["remote_update"], "failed")
            self.request.assert_called_once()

    def test_explicit_webhook_is_mocked(self):
        self.request.side_effect = None
        self.request.return_value = Mock(status_code=204)
        with TemporaryDirectory() as directory:
            success, summary = self.run_demo(directory, webhook_url="https://example.invalid/webhook")
            self.assertTrue(success)
            self.assertEqual(summary["webhook"], "delivered")
            self.request.assert_called_once()

    def test_cli_status(self):
        with TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--output-dir", directory]), 0)


if __name__ == "__main__":
    unittest.main()
