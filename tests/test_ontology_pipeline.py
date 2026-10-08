import unittest
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from rdflib import Graph, Literal, XSD
from rdflib.compare import isomorphic

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ontology_pipeline import MusicVideoOntologyBuilder


def normalize_decimals(graph):
    """Turtle may write decimal 60 as 60.0; compare their numeric meaning."""
    normalized = Graph()
    for subject, predicate, value in graph:
        if isinstance(value, Literal) and value.datatype == XSD.decimal:
            value = Literal(format(value.toPython().normalize(), "f"), datatype=XSD.decimal)
        normalized.add((subject, predicate, value))
    return normalized

class TestOntologyPipeline(unittest.TestCase):
    def test_builder_generation(self):
        builder = MusicVideoOntologyBuilder(project_id="test_proj_01", title="Test MV")
        builder.add_audio("https://example.org/assets/test.wav", duration_sec=60)
        builder.add_timeline_with_shots([
            {"order": 1, "start": 0, "end": 60, "image_uri": "https://example.org/assets/img.png", "label": "Test Shot"}
        ])
        builder.finalize_video("https://example.org/assets/video.mp4", duration_sec=60)
        
        self.assertGreater(len(builder.g), 0)
        
        conforms, _ = builder.validate()
        self.assertTrue(conforms)

    def test_export_round_trip(self):
        builder = MusicVideoOntologyBuilder(project_id="export_test", title="Export Test")
        builder.add_audio("https://example.invalid/audio.wav", duration_sec=60)
        with TemporaryDirectory() as directory:
            ttl, jsonld = builder.export(str(Path(directory) / "export_test"))
            expected = normalize_decimals(builder.g)
            self.assertTrue(isomorphic(expected, normalize_decimals(Graph().parse(ttl, format="turtle"))))
            self.assertTrue(isomorphic(expected, normalize_decimals(Graph().parse(jsonld, format="json-ld"))))

    def test_nonpositive_duration_rejected(self):
        builder = MusicVideoOntologyBuilder(project_id="invalid_test", title="Invalid Demo")
        builder.add_audio("https://example.invalid/audio.wav", duration_sec=0)
        conforms, report = builder.validate()
        self.assertFalse(conforms)
        self.assertIn("MinExclusiveConstraintComponent", report)

if __name__ == "__main__":
    unittest.main()
