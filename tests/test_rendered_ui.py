"""Static checks of rendered browser code; Node parses without executing the UI."""

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import app as studio


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attributes = dict(attrs)
            self.current = [] if "src" not in attributes else None

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append("".join(self.current))
            self.current = None


class TestRenderedUI(unittest.TestCase):
    def setUp(self):
        with patch.dict(studio.app.config, {"TESTING": True, "ONTOLOGY_LOCAL_DOCKER": "0"}):
            response = studio.app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.html = response.get_data(as_text=True)
        parser = InlineScripts()
        parser.feed(self.html)
        self.assertTrue(parser.scripts)
        self.script = "\n".join(parser.scripts)

    def test_rendered_javascript_has_valid_syntax(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is not installed; static syntax check unavailable")
        with TemporaryDirectory() as directory:
            script = Path(directory) / "rendered-ui.js"
            script.write_text(self.script, encoding="utf-8")
            checked = subprocess.run([node, "--check", str(script)], capture_output=True,
                                     text=True, encoding="utf-8", timeout=15)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_removed_api_key_role_flow_and_single_fetch_helper(self):
        self.assertNotIn("currentApiKey", self.script)
        self.assertNotIn("switchRole", self.script)
        definitions = re.findall(r"\b(?:async\s+)?function\s+fetchJSON\s*\(", self.script)
        self.assertEqual(len(definitions), 1)

    def test_saved_codex_job_is_polled_and_result_text_is_loaded(self):
        self.assertIn("localStorage.getItem('ontology_codex_job')", self.script)
        self.assertIn("localStorage.setItem('ontology_codex_job', codexJobId)", self.script)
        self.assertIn("async function pollCodexJob()", self.script)
        self.assertIn("'/api/v1/codex/jobs/' + encodeURIComponent(codexJobId)", self.script)
        self.assertIn("setTimeout(pollCodexJob, 2000)", self.script)
        self.assertIn("displayCodexJob(job)", self.script)
        self.assertIn("textContent = job.result.generated_content", self.script)
        self.assertIn("결과 생성됨 · 그래프 저장 실패", self.html)
        self.assertIn("Codex 처리 대기", self.html)
        self.assertIn("Codex 처리 결과", self.html)


if __name__ == "__main__":
    unittest.main()
