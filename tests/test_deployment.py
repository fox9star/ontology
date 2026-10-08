"""Deployment contract and Windows process ownership regressions."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell")


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


class TestDeploymentConfig(unittest.TestCase):
    def test_default_compose_is_local_and_independent_of_optional_services(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1:5000:5000"', compose)
        self.assertNotIn("mv-studio:", compose)
        self.assertNotIn("depends_on:", compose)
        self.assertNotIn("FUSEKI_ADMIN_PASSWORD", compose)
        self.assertIn('HOST: "0.0.0.0"', compose)
        self.assertIn('ONTOLOGY_LOCAL_DOCKER: "1"', compose)
        self.assertIn('ONTOLOGY_DOCKER_CLIENT_CIDR: "172.30.71.0/24"', compose)
        self.assertIn("subnet: 172.30.71.0/24", compose)
        self.assertIn('ONTOLOGY_CODEX_JOBS_DIR: "/app/.codex-jobs"', compose)
        # A directory bind shares all mutable RDF files and persistent folders
        # while permitting atomic os.replace writes on either side.
        self.assertIn("- ./:/app", compose)
        self.assertNotIn(".ttl:/app/", compose)

    def test_optional_fuseki_has_explicit_password_and_local_port(self):
        compose = (ROOT / "compose.fuseki.yml").read_text(encoding="utf-8")
        self.assertIn("${FUSEKI_ADMIN_PASSWORD:?", compose)
        self.assertIn('"127.0.0.1:3030:3030"', compose)
        self.assertIn('FUSEKI_ENDPOINT: "http://fuseki:3030/ds"', compose)
        self.assertNotIn("ADMIN_PASSWORD: admin", compose)

    def test_container_health_does_not_depend_on_fuseki_and_ffprobe_is_installed(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("curl ffmpeg", dockerfile)
        self.assertIn("http://127.0.0.1:5000/api/health", dockerfile)
        self.assertNotIn("/api/v1/fuseki/status", dockerfile)

    @unittest.skipUnless(POWERSHELL, "Windows PowerShell unavailable")
    def test_powershell_entrypoints_parse(self):
        for filename in ("run.ps1", "setup.ps1", "start_all.ps1", "stop_all.ps1", "stop.ps1"):
            with self.subTest(filename=filename):
                command = (
                    "$tokens=$null; $errors=$null; "
                    f"[System.Management.Automation.Language.Parser]::ParseFile({ps_literal(ROOT / filename)},[ref]$tokens,[ref]$errors) | Out-Null; "
                    "if ($errors.Count) { $errors | Out-String | Write-Output; exit 1 }"
                )
                result = subprocess.run([POWERSHELL, "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Windows process ownership checks")
class TestSafeStop(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ontology-stop-")
        self.directory = Path(self.temporary.name)
        shutil.copyfile(ROOT / "stop_all.ps1", self.directory / "stop_all.ps1")
        (self.directory / ".runtime").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def run_stop(self):
        return subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.directory / "stop_all.ps1")],
            capture_output=True, text=True, timeout=20)

    def test_malformed_pid_record_does_not_abort_or_kill(self):
        record = self.directory / ".runtime" / "web-studio.process.json"
        record.write_text(json.dumps({"ProcessId": "invalid-pid"}), encoding="utf-8")
        result = self.run_stop()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("invalid process record", result.stdout)
        self.assertFalse(record.exists())

    def _exercise_process(self, *, script_matches, creation_matches):
        expected = self.directory / "app.py"
        script = expected if script_matches else self.directory / "unrelated.py"
        script.write_text("import time\ntime.sleep(60)\n", encoding="utf-8")
        arguments = [sys.executable, str(script)]
        if not script_matches:
            arguments.append(str(expected))  # An app path in an unrelated argument proves no ownership.
        process = subprocess.Popen(arguments)
        try:
            record = self.directory / ".runtime" / "web-studio.process.json"
            ticks = "[string]$owned.CreationDate.ToUniversalTime().Ticks" if creation_matches else "'0'"
            command = (
                f"$owned=Get-CimInstance Win32_Process -Filter 'ProcessId = {process.pid}'; "
                f"@{{ProcessId={process.pid}; ExecutablePath=$owned.ExecutablePath; CreationTicks={ticks}; ScriptPath={ps_literal(expected)}}} "
                f"| ConvertTo-Json | Set-Content -LiteralPath {ps_literal(record)} -Encoding UTF8"
            )
            setup = subprocess.run([POWERSHELL, "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=20)
            self.assertEqual(setup.returncode, 0, setup.stdout + setup.stderr)
            result = self.run_stop()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            if script_matches and creation_matches:
                process.wait(timeout=5)
                self.assertIn("stopped", result.stdout)
            else:
                self.assertIsNone(process.poll(), result.stdout + result.stderr)
                self.assertIn("ownership does not match", result.stdout)
            self.assertFalse(record.exists())
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=5)

    def test_pid_reuse_with_different_creation_time_is_not_stopped(self):
        self._exercise_process(script_matches=True, creation_matches=False)

    def test_unrelated_python_with_matching_pid_and_creation_is_not_stopped(self):
        self._exercise_process(script_matches=False, creation_matches=True)

    def test_owned_process_is_stopped_and_record_removed(self):
        self._exercise_process(script_matches=True, creation_matches=True)


if __name__ == "__main__":
    unittest.main()
