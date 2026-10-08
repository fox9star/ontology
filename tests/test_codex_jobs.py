"""Durable Codex state transitions with isolated data and no process/network access."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as studio
import codex_jobs
import project_store


class CodexJobTestCase(unittest.TestCase):
    """Shared fixture used by the compatibility API tests as well."""

    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.data_dir = self.directory / "data"
        self.data_dir.mkdir()
        source_dir = Path(studio.__file__).resolve().parent
        for filename in (
            "mv-example.ttl", "mv.owl", "mv-shapes.ttl", "mv-schema.ttl",
            "core-schema.ttl", "core-shapes.ttl", "controlled-vocabularies.ttl",
        ):
            shutil.copyfile(source_dir / filename, self.data_dir / filename)
        self.source = self.data_dir / "mv-example.ttl"
        # The editor tests append a 60-90 second shot. Extend only this isolated
        # temporary example so its target brief/audio/final video remain coherent.
        graph = Graph().parse(self.source, format="turtle")
        mv = Namespace(studio.ONTOLOGIES["mv"]["prefix"])
        for subject, predicate in (
            (mv.brief01, mv.targetDurationSeconds),
            (mv.audio01, mv.durationSeconds),
            (mv.video01, mv.durationSeconds),
        ):
            graph.remove((subject, predicate, None))
            graph.add((subject, predicate, Literal("90", datatype=XSD.decimal)))
        graph.serialize(destination=self.source, format="turtle")
        self.original = self.source.read_bytes()
        self.projects = self.directory / "projects"
        self.projects.mkdir()
        configuration = dict(studio.ONTOLOGIES["mv"])
        self.actual_check_status = codex_jobs.check_codex_status
        self.patches = [
            patch.object(codex_jobs, "JOBS_DIR", self.directory / "jobs"),
            patch.object(studio, "BASE_DIR", str(self.data_dir)),
            patch.dict(studio.ONTOLOGIES, {"mv": configuration}),
            patch.object(project_store, "PROJECTS_DIR", self.projects),
            patch.object(codex_jobs, "check_codex_status", return_value={
                "provider": "codex", "requires_api_key": False,
                "cli_available": False, "authenticated": False,
                "auto_run_available": False, "manual_available": True}),
            patch("subprocess.run", side_effect=AssertionError("Tests must not execute CLI processes")),
            patch("subprocess.Popen", side_effect=AssertionError("Tests must not launch workers")),
            patch("requests.sessions.Session.request", side_effect=AssertionError("Tests must not use network")),
            patch("event_stream.publish_event"),
            patch.dict(studio.app.config, {"TESTING": True, "ONTOLOGY_LOCAL_DOCKER": "0"}),
        ]
        self.mocks = [p.start() for p in self.patches]
        for p in reversed(self.patches):
            self.addCleanup(p.stop)
        self.client = studio.app.test_client()

    def enqueue(self, **extra):
        return codex_jobs.submit_job({"ont": "mv", "prompt": "Write a concise scene description.", **extra})

    def claim(self, **extra):
        queued = self.enqueue(**extra)
        return codex_jobs.claim_job(queued["job_id"])

    def complete(self, claimed, content="Test fixture: neon reflections on a rainy city street."):
        return codex_jobs.complete_job(claimed["job_id"],
                                      {"content": content, "summary": "A test scene description."},
                                      claimed["claim_token"])

    def make_project(self):
        directory = self.projects / "test-project"
        assets = directory / "assets"
        assets.mkdir(parents=True)
        audio = assets / "audio.wav"
        audio.write_bytes(b"isolated integrity test bytes")
        namespace = Namespace(studio.ONTOLOGIES["mv"]["prefix"])
        graph = Graph()
        for triple in [
            (namespace.project, RDF.type, namespace.MusicVideoProject),
            (namespace.project, namespace.hasBrief, namespace.brief),
            (namespace.brief, RDF.type, namespace.CreativeBrief),
            (namespace.brief, namespace.targetDurationSeconds, Literal("60", datatype=XSD.decimal)),
            (namespace.project, namespace.hasAudio, namespace.audio),
            (namespace.audio, RDF.type, namespace.AudioAsset),
            (namespace.audio, namespace.fileUri, URIRef(audio.as_uri())),
            (namespace.audio, namespace.durationSeconds, Literal("60", datatype=XSD.decimal)),
        ]:
            graph.add(triple)
        data = directory / "data.ttl"
        graph.serialize(destination=data, format="turtle")
        (directory / "project.json").write_text(json.dumps({"id": "test-project", "ontology": "mv"}), encoding="utf-8")
        (directory / "manifest.json").write_text(json.dumps({
            "project_id": "test-project", "timeline": [], "assets": [{
                "id": "audio", "kind": "audio", "file_name": "audio.wav",
                "file_uri": audio.as_uri(), "duration_seconds": 60,
                "sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
            }],
        }), encoding="utf-8")
        return data, audio


class TestCodexJobs(CodexJobTestCase):
    def test_enqueue_is_durable_pending_without_fake_completion(self):
        job = self.enqueue()
        self.assertEqual(job["status"], "awaiting_codex")
        self.assertIsNone(job["result"])
        self.assertEqual(job["attempts"], 0)
        self.assertNotIn("claim_token", job)
        self.assertEqual(codex_jobs.load_job(job["job_id"])["status"], "awaiting_codex")
        request = codex_jobs.JOBS_DIR / job["job_id"] / "request.md"
        self.assertIn("Write a concise scene description.", request.read_text(encoding="utf-8"))
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse((request.parent / "output.txt").exists())

    def test_corrupted_nonobject_records_are_conflicts_and_skipped_in_list(self):
        valid = self.enqueue(save_to_graph=False)
        for corrupted in ([], None):
            queued = self.enqueue(save_to_graph=False)
            path = codex_jobs.JOBS_DIR / queued["job_id"] / "job.json"
            path.write_text(json.dumps(corrupted), encoding="utf-8")
            with self.subTest(corrupted=corrupted), self.assertRaises(codex_jobs.JobError) as error:
                codex_jobs.load_job(queued["job_id"])
            self.assertEqual(error.exception.status_code, 409)
            self.assertEqual([job["job_id"] for job in codex_jobs.list_jobs()], [valid["job_id"]])

    def test_invalid_prompt_domain_and_project_create_no_jobs(self):
        invalid_requests = [None, [], {"prompt": ""}, {"prompt": "  "}, {"prompt": 1},
                            {"prompt": "a" * 20001}, {"prompt": "valid", "ont": "unknown"},
                            {"prompt": "valid", "ont": "../mv"},
                            {"prompt": "valid", "project": "../outside"},
                            {"prompt": "valid", "save_to_graph": "false"}]
        for value in invalid_requests:
            with self.subTest(value_type=type(value).__name__), self.assertRaises((codex_jobs.JobError, project_store.ProjectError)):
                codex_jobs.submit_job(value, auto_run=False)
        self.assertEqual(codex_jobs.list_jobs(), [])

    def test_job_id_traversal_rejected(self):
        for job_id in ("../outside", "codex_" + "a" * 32 + "/../outside", "C:\\outside", None, "codex_ABC"):
            with self.subTest(job_id=job_id), self.assertRaises(codex_jobs.JobError):
                codex_jobs.load_job(job_id)

    def test_job_directory_symlink_cannot_escape_jobs_root(self):
        codex_jobs.JOBS_DIR.mkdir()
        job_id = "codex_" + "a" * 32
        try:
            (codex_jobs.JOBS_DIR / job_id).symlink_to(self.data_dir, target_is_directory=True)
        except OSError:
            self.skipTest("Creating symbolic links is unavailable on this host")
        with self.assertRaises(codex_jobs.JobError):
            codex_jobs.load_job(job_id)

    def test_output_symlink_cannot_overwrite_outside_job(self):
        claimed = self.claim(save_to_graph=False)
        target = self.directory / "protected.txt"
        target.write_text("preserve this file", encoding="utf-8")
        try:
            (codex_jobs.JOBS_DIR / claimed["job_id"] / "output.txt").symlink_to(target)
        except OSError:
            self.skipTest("Creating symbolic links is unavailable on this host")
        with self.assertRaises(codex_jobs.JobError):
            self.complete(claimed)
        self.assertEqual(target.read_text(encoding="utf-8"), "preserve this file")
        self.assertEqual(codex_jobs.load_job(claimed["job_id"])["status"], "running")

    def test_concurrent_claim_has_one_winner(self):
        queued = self.enqueue()
        barrier = threading.Barrier(2)

        def compete(_):
            barrier.wait()
            try:
                return codex_jobs.claim_job(queued["job_id"])
            except codex_jobs.JobError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(compete, range(2)))
        winners = [result for result in results if isinstance(result, dict)]
        losers = [result for result in results if isinstance(result, codex_jobs.JobError)]
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(losers), 1)
        self.assertEqual(losers[0].status_code, 409)
        self.assertEqual(codex_jobs.load_job(queued["job_id"])["attempts"], 1)

    def test_completion_persists_real_content_hash_and_validated_provenance(self):
        claimed = self.claim()
        completed = self.complete(claimed, "테스트 장면: 빗물에 반사된 네온.\n도시의 불빛이 천천히 흐릅니다.")
        content = completed["result"]["generated_content"]
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["result"]["sha256"], digest)
        self.assertTrue(completed["result"]["persisted"]["saved"])
        self.assertTrue(completed["result"]["persisted"]["shacl_conforms"])
        self.assertNotIn("claim_token", completed)
        directory = codex_jobs.JOBS_DIR / completed["job_id"]
        self.assertEqual(hashlib.sha256((directory / "output.txt").read_bytes()).hexdigest(), digest)
        self.assertEqual(json.loads((directory / "result.json").read_text(encoding="utf-8"))["content"], content)
        graph = Graph().parse(self.source, format="turtle")
        namespace = Namespace(studio.ONTOLOGIES["mv"]["prefix"])
        output = namespace[completed["job_id"] + "_result"]
        self.assertEqual(str(graph.value(output, codex_jobs.PROV.value)), content)
        self.assertEqual(str(graph.value(output, codex_jobs.CODEX.sha256)), digest)
        self.assertEqual(codex_jobs.public_job(codex_jobs.load_job(completed["job_id"])), completed)
        self.assertEqual(codex_jobs.list_jobs("mv")[0]["status"], "completed")

    def test_wrong_token_and_repeat_completion_do_not_overwrite(self):
        claimed = self.claim(save_to_graph=False)
        directory = codex_jobs.JOBS_DIR / claimed["job_id"]
        with self.assertRaises(codex_jobs.JobError) as error:
            codex_jobs.complete_job(claimed["job_id"], {"content": "wrong", "summary": "wrong"}, "stale-token")
        self.assertEqual(error.exception.status_code, 409)
        self.assertFalse((directory / "output.txt").exists())
        completed = self.complete(claimed)
        output_before = (directory / "output.txt").read_bytes()
        state_before = (directory / "job.json").read_bytes()
        with self.assertRaises(codex_jobs.JobError):
            codex_jobs.complete_job(claimed["job_id"], {"content": "replacement", "summary": "replacement"}, claimed["claim_token"])
        self.assertEqual((directory / "output.txt").read_bytes(), output_before)
        self.assertEqual((directory / "job.json").read_bytes(), state_before)
        self.assertEqual(completed["status"], "completed")

    def test_validation_failure_keeps_source_and_generated_content(self):
        graph = Graph().parse(self.source, format="turtle")
        namespace = Namespace(studio.ONTOLOGIES["mv"]["prefix"])
        subject = next(graph.subjects(RDF.type, namespace.AudioAsset))
        graph.set((subject, namespace.durationSeconds, Literal("0", datatype=XSD.decimal)))
        graph.serialize(destination=self.source, format="turtle")
        original_invalid = self.source.read_bytes()
        completed = self.complete(self.claim())
        self.assertEqual(completed["status"], "validation_failed")
        self.assertFalse(completed["result"]["persisted"]["saved"])
        self.assertIn("SHACL", completed["error"])
        self.assertTrue(completed["result"]["generated_content"])
        self.assertEqual(self.source.read_bytes(), original_invalid)
        self.assertEqual(codex_jobs.load_job(completed["job_id"])["status"], "validation_failed")

    def test_no_graph_persistence_leaves_source_unchanged(self):
        completed = self.complete(self.claim(save_to_graph=False))
        self.assertEqual(completed["status"], "completed")
        self.assertFalse(completed["result"]["persisted"]["saved"])
        self.assertFalse(completed["result"]["persisted"]["requested"])
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_malformed_source_preserves_bytes_and_records_failure(self):
        claimed = self.claim()
        self.source.write_text("This is not valid Turtle {", encoding="utf-8")
        malformed = self.source.read_bytes()
        completed = self.complete(claimed)
        self.assertEqual(completed["status"], "validation_failed")
        self.assertFalse(completed["result"]["persisted"]["saved"])
        self.assertEqual(self.source.read_bytes(), malformed)
        self.assertEqual(codex_jobs.load_job(claimed["job_id"])["status"], "validation_failed")

    def test_invalid_result_cannot_finish_or_create_output(self):
        claimed = self.claim(save_to_graph=False)
        for result in ({}, {"content": "", "summary": "empty"}, {"content": "x"},
                       {"content": "x", "summary": 1}):
            with self.subTest(result=result), self.assertRaises(codex_jobs.JobError):
                codex_jobs.complete_job(claimed["job_id"], result, claimed["claim_token"])
        self.assertEqual(codex_jobs.load_job(claimed["job_id"])["status"], "running")
        self.assertFalse((codex_jobs.JOBS_DIR / claimed["job_id"] / "output.txt").exists())

    def test_registered_media_integrity_checked_before_save(self):
        data, audio = self.make_project()
        valid = self.complete(self.claim(project="test-project"))
        self.assertEqual(valid["status"], "completed")
        self.assertTrue(valid["result"]["persisted"]["saved"])
        before = data.read_bytes()
        audio.write_bytes(b"tampered bytes")
        failed = self.complete(self.claim(project="test-project"))
        self.assertEqual(failed["status"], "validation_failed")
        self.assertIn("무결성", failed["error"])
        self.assertEqual(data.read_bytes(), before)

    def test_missing_registered_file_prevents_graph_save(self):
        data, audio = self.make_project()
        claimed = self.claim(project="test-project")
        original = data.read_bytes()
        audio.unlink()
        completed = self.complete(claimed)
        self.assertEqual(completed["status"], "validation_failed")
        self.assertFalse(completed["result"]["persisted"]["saved"])
        self.assertEqual(data.read_bytes(), original)

    def test_child_environment_has_no_model_api_keys(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai-key", "CODEX_API_KEY": "test-codex-key", "TEST_PARENT_SETTING": "retained"}):
            environment = codex_jobs._environment()
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("CODEX_API_KEY", environment)
        self.assertEqual(environment["TEST_PARENT_SETTING"], "retained")
        self.assertEqual(environment["PYTHONUTF8"], "1")

    def test_launch_failure_preserves_durable_awaiting_job(self):
        with patch.object(codex_jobs, "check_codex_status", return_value={"auto_run_available": True}), \
                patch("codex_jobs.subprocess.Popen", side_effect=OSError("Mocked launch failure")):
            queued = self.enqueue(save_to_graph=False)
        self.assertEqual(queued["status"], "awaiting_codex")
        restored = codex_jobs.load_job(queued["job_id"])
        self.assertEqual(restored["status"], "awaiting_codex")
        self.assertEqual(restored["attempts"], 0)
        self.assertIsNone(restored["result"])

    def test_launch_does_not_claim_or_complete_and_strips_keys(self):
        queued = self.enqueue(save_to_graph=False)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai", "CODEX_API_KEY": "test-codex"}), \
                patch.object(codex_jobs, "check_codex_status", return_value={"auto_run_available": True}), \
                patch("codex_jobs.subprocess.Popen") as launch:
            self.assertTrue(codex_jobs.launch_job(queued["job_id"]))
        environment = launch.call_args.kwargs["env"]
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("CODEX_API_KEY", environment)
        restored = codex_jobs.load_job(queued["job_id"])
        self.assertEqual(restored["status"], "awaiting_codex")
        self.assertIsNone(restored["result"])

    def test_only_chatgpt_login_enables_automatic_execution(self):
        # Recover the real function hidden by the default fixture guard.
        actual = self.actual_check_status
        cases = [(0, "Logged in using ChatGPT", True),
                 (0, "Logged in using an API key", False),
                 (1, "ChatGPT login failed", False)]
        for returncode, text, enabled in cases:
            with self.subTest(returncode=returncode, text=text), \
                    patch("codex_jobs.shutil.which", return_value="codex-test.exe"), \
                    patch("codex_jobs.subprocess.run", return_value=SimpleNamespace(returncode=returncode, stdout=text, stderr="")):
                status = actual()
            self.assertEqual(status["auto_run_available"], enabled)
            self.assertEqual(status["authenticated"], enabled)
            self.assertFalse(status["requires_api_key"])

    def test_mocked_cli_result_is_saved_and_child_keys_removed(self):
        queued = self.enqueue(save_to_graph=False)
        calls = []

        def simulate_cli(command, **kwargs):
            calls.append((command, kwargs))
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            self.assertNotIn("CODEX_API_KEY", kwargs["env"])
            destination = Path(command[command.index("--output-last-message") + 1])
            destination.write_text(json.dumps({"content": "Mocked CLI fixture text.", "summary": "CLI fixture."}), encoding="utf-8")
            return SimpleNamespace(returncode=0)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-openai", "CODEX_API_KEY": "test-codex"}), \
                patch.object(codex_jobs, "check_codex_status", return_value={"auto_run_available": True}), \
                patch("codex_jobs.shutil.which", return_value="codex-test.exe"), \
                patch("codex_jobs.subprocess.run", side_effect=simulate_cli):
            completed = codex_jobs.run_job(queued["job_id"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["result"]["transport"], "codex_cli_chatgpt")
        self.assertEqual(len(calls), 1)
        command, kwargs = calls[0]
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
        self.assertIn("--ignore-user-config", command)
        self.assertEqual(Path(kwargs["cwd"]), codex_jobs.JOBS_DIR / queued["job_id"])
        self.assertEqual(self.source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
