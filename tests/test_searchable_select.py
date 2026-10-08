"""Verify selector event behavior without adding a browser/runtime dependency."""
from pathlib import Path
import shutil
import subprocess
import unittest


class TestSearchableSelect(unittest.TestCase):
    def test_component_interaction_contract(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the selector DOM harness")
        script = Path(__file__).with_name("searchable_select_dom.cjs")
        result = subprocess.run([node, str(script)], capture_output=True, text=True,
                                encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
