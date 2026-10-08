"""Provenance must preserve unknown facts and render graph data safely."""

from datetime import datetime
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef

import audit_report

PROV = audit_report.PROV_NS
MV = audit_report.MV_NS
CODEX = audit_report.CODEX_NS
EX = Namespace("https://example.org/test#")


class TestAuditReport(unittest.TestCase):
    def test_missing_model_source_and_generation_remain_unknown(self):
        graph = Graph()
        graph.add((EX.asset, RDF.type, MV.ImageAsset))
        record = audit_report.extract_audit_trail(graph)["records"][0]
        self.assertEqual(record["model_version"], audit_report.UNKNOWN)
        self.assertEqual(record["source"], audit_report.UNKNOWN)
        self.assertEqual(record["task_name"], audit_report.UNKNOWN)
        self.assertEqual(record["verification"], "graph_record_only")
        self.assertIsNone(record["task_uri"])
        self.assertNotIn("v1.0-standard", str(record))

    def test_import_tool_version_is_not_claimed_as_generation_model(self):
        graph = Graph()
        graph.add((EX.audio, RDF.type, MV.AudioAsset))
        graph.add((EX.audio, PROV.wasGeneratedBy, EX.import_run))
        graph.add((EX.audio, PROV.wasDerivedFrom, URIRef("file:///original.wav")))
        graph.add((EX.import_run, PROV.wasAssociatedWith, MV.localImportAgent))
        graph.add((EX.import_run, MV.modelVersion, Literal("local-media-importer-1.0; ffprobe 9")))
        graph.add((EX.import_run, RDFS.comment, Literal("Original generation model and prompt are unknown.")))
        record = audit_report.extract_audit_trail(graph)["records"][0]
        self.assertEqual(record["activity_kind"], "import_registration")
        self.assertEqual(record["model_version"], audit_report.UNKNOWN)
        self.assertEqual(record["tool_version"], "local-media-importer-1.0; ffprobe 9")
        self.assertEqual(record["source"], "file:///original.wav")
        self.assertIn("unknown", record["notes"])

    def test_codex_generic_prov_output_location_checksum_and_model_uncertainty(self):
        graph = Graph()
        graph.add((EX.output, RDF.type, PROV.Entity))
        graph.add((EX.output, RDFS.label, Literal("Codex result")))
        graph.add((EX.output, PROV.wasGeneratedBy, EX.execution))
        graph.add((EX.output, PROV.wasDerivedFrom, EX.input))
        graph.add((EX.output, PROV.atLocation, URIRef("file:///results/output.txt")))
        graph.add((EX.output, CODEX.sha256, Literal("f" * 64)))
        graph.add((EX.execution, RDF.type, PROV.Activity))
        graph.add((EX.execution, RDFS.label, Literal("Create text")))
        graph.add((EX.execution, PROV.wasAssociatedWith, EX.codex))
        graph.add((EX.execution, CODEX.modelProvenance, Literal("unverified: Codex selected its configured model")))
        graph.add((EX.codex, RDFS.label, Literal("Codex")))
        record = audit_report.extract_audit_trail(graph)["records"][0]
        self.assertEqual(record["file_uri"], "file:///results/output.txt")
        self.assertEqual(record["agent_name"], "Codex")
        self.assertEqual(record["checksum"], "f" * 64)
        self.assertEqual(record["model_version"], audit_report.UNKNOWN)
        self.assertIn("unverified", record["model_provenance"])
        self.assertEqual(record["source_uris"], [str(EX.input)])

    def test_all_sources_and_multiple_activities_are_preserved(self):
        graph = Graph()
        graph.add((EX.output, PROV.wasGeneratedBy, EX.first))
        graph.add((EX.output, PROV.wasGeneratedBy, EX.second))
        graph.add((EX.output, PROV.wasDerivedFrom, EX.source_a))
        graph.add((EX.output, PROV.wasDerivedFrom, EX.source_b))
        trail = audit_report.extract_audit_trail(graph)
        self.assertEqual(trail["total_artifacts"], 1)
        self.assertEqual(trail["total_records"], 2)
        self.assertEqual({record["task_uri"] for record in trail["records"]}, {str(EX.first), str(EX.second)})
        for record in trail["records"]:
            self.assertEqual(record["source_uris"], [str(EX.source_a), str(EX.source_b)])

    def test_timestamp_is_timezone_aware_utc(self):
        timestamp = datetime.fromisoformat(audit_report.extract_audit_trail(Graph())["generated_at"])
        self.assertIsNotNone(timestamp.tzinfo)
        self.assertEqual(timestamp.utcoffset().total_seconds(), 0)

    def test_html_escapes_all_dynamic_text_and_makes_no_false_certification(self):
        hostile = '<script>alert("x")</script>'
        record = {key: hostile for key in ("asset_name", "file_uri", "task_name", "agent_name", "model_version", "source", "model_provenance", "tool_version", "checksum", "recorded_status", "started_at", "ended_at", "notes")}
        data = {"domain": hostile, "project_id": hostile, "generated_at": hostile, "records": [record]}
        html = audit_report.render_html_certificate(data)
        self.assertNotIn("<script>", html)
        self.assertNotIn(hostile, html)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", html)
        self.assertNotIn("VERIFIED", html)
        self.assertNotIn("100% Pass", html)
        self.assertNotIn("Trust Authority", html)
        self.assertIn("미확인", html)

    def test_audit_api_uses_only_supplied_temporary_graph(self):
        from app import app
        graph = Graph()
        graph.add((EX.output, PROV.wasGeneratedBy, EX.execution))
        with patch("app.load_graph", return_value=graph):
            client = app.test_client()
            data = client.get("/api/v1/audit-data?ont=mv")
            self.assertEqual(data.status_code, 200)
            self.assertEqual(data.json["total_artifacts"], 1)
            report = client.get("/api/v1/audit-report?ont=mv")
            self.assertEqual(report.status_code, 200)
            self.assertIn("등록된 출처 및 작업 이력 보고서".encode("utf-8"), report.data)


if __name__ == "__main__":
    unittest.main()
