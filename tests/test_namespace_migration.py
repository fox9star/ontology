"""Safety checks for the prepared placeholder namespace migration."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from namespace_migration import apply_migration, namespace_map, plan_migration, replace_namespaces


class NamespaceMigrationTests(unittest.TestCase):
    def test_host_must_be_a_nonplaceholder_hostname(self):
        for invalid in ("example.org", "https://owned.example", "owned.example/path", "owned.example:443"):
            with self.subTest(host=invalid), self.assertRaises(ValueError):
                namespace_map(invalid)

    def test_replacement_preserves_unrelated_example_org_asset_uris(self):
        content = (
            "@prefix mv: <https://example.org/mv#> .\n"
            "<https://example.org/mv> a <http://www.w3.org/2002/07/owl#Ontology> .\n"
            "<https://example.org/assets/image.png> <https://example.org/mv#fileUri> ?file .\n"
        )
        rewritten = replace_namespaces(content, namespace_map("ontology.acme.test"))
        self.assertIn("https://ontology.acme.test/mv#", rewritten)
        self.assertIn("https://example.org/assets/image.png", rewritten)
        self.assertNotIn("https://example.org/mv#", rewritten)

    def test_plan_is_read_only_and_apply_creates_exact_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "schema.ttl"
            source.write_text("<https://example.org/ontology/core> a <urn:Ontology> .\n", encoding="utf-8")
            _, planned = plan_migration(root, "ontology.acme.test")
            self.assertIn(source, planned)
            self.assertIn("https://example.org/ontology/core", source.read_text(encoding="utf-8"))

            _, changed, backup_root = apply_migration(root, "ontology.acme.test")
            self.assertEqual(set(changed), {source})
            self.assertIn("https://ontology.acme.test/ontology/core", source.read_text(encoding="utf-8"))
            backup = backup_root / "schema.ttl"
            self.assertTrue(backup.is_file())
            self.assertIn("https://example.org/ontology/core", backup.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
