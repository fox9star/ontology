"""File locking and atomic write checks using temporary resources only."""

import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from rdflib import Graph, Literal, URIRef

from graph_io import graph_file_lock, write_bytes_atomic, write_graph_atomic


class TestGraphIO(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "data.ttl"

    def test_reentrant_atomic_write_and_replace_failure(self):
        graph = Graph()
        graph.add((URIRef("urn:s"), URIRef("urn:p"), Literal("safe")))
        with graph_file_lock(self.path, timeout=0):
            with graph_file_lock(self.path, timeout=0):
                write_graph_atomic(graph, self.path)
        original = self.path.read_bytes()
        with patch("graph_io.os.replace", side_effect=OSError("replace denied")):
            with self.assertRaises(OSError):
                write_bytes_atomic(b"replacement", self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(list(self.path.parent.glob("*.tmp")))

    def test_thread_lock_exclusion(self):
        outcomes = []

        def contender():
            try:
                with graph_file_lock(self.path, timeout=0.05):
                    outcomes.append("acquired")
            except TimeoutError:
                outcomes.append("timeout")

        with graph_file_lock(self.path):
            thread = threading.Thread(target=contender)
            thread.start()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes, ["timeout"])

    def test_serialization_failure_preserves_original(self):
        write_bytes_atomic(b"original", self.path)
        graph = Graph()
        with patch.object(graph, "serialize", side_effect=ValueError("serialize denied")):
            with self.assertRaises(ValueError):
                write_graph_atomic(graph, self.path)
        self.assertEqual(self.path.read_bytes(), b"original")

    def test_process_lock_exclusion_and_release(self):
        script = (
            "import sys; from graph_io import graph_file_lock\n"
            "try:\n"
            "    with graph_file_lock(sys.argv[1], timeout=0.1): print('acquired')\n"
            "except TimeoutError: print('timeout')\n"
        )
        project_root = Path(__file__).resolve().parents[1]
        with graph_file_lock(self.path):
            blocked = subprocess.run([sys.executable, "-c", script, str(self.path)], capture_output=True, text=True, timeout=5, cwd=project_root)
        acquired = subprocess.run([sys.executable, "-c", script, str(self.path)], capture_output=True, text=True, timeout=5, cwd=project_root)
        self.assertEqual(blocked.returncode, 0, blocked.stderr)
        self.assertEqual(blocked.stdout.strip(), "timeout")
        self.assertEqual(acquired.returncode, 0, acquired.stderr)
        self.assertEqual(acquired.stdout.strip(), "acquired")


if __name__ == "__main__":
    unittest.main()
