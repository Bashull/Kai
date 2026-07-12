from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import subprocess
import unittest

from tools.kai_source_adapters import (
    ConnectorSnapshotAdapter,
    LocalGitAdapter,
    SourceRegistry,
)


class SourceAdapterTests(unittest.TestCase):
    def test_registry_loads_enabled_sources(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps({"sources": [
                {"source_id": "pc:kai", "kind": "PC", "enabled": True, "uri": "file:///KAI"},
                {"source_id": "disabled", "kind": "PC", "enabled": False, "uri": "file:///none"},
            ]}), encoding="utf-8")
            registry = SourceRegistry.from_json(path)
            self.assertEqual([item["source_id"] for item in registry.enabled()], ["pc:kai"])

    def test_local_git_adapter_emits_repository_record(self):
        with TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run([
                "git", "-C", str(repo), "-c", "user.name=Test",
                "-c", "user.email=test@example.com", "commit", "-m", "init"
            ], check=True, capture_output=True)

            adapter = LocalGitAdapter(source_id="pc:repos", roots=[repo])
            result = adapter.collect(max_items=10)
            self.assertEqual(result.status, "HEALTHY")
            self.assertEqual(len(result.records), 1)
            self.assertEqual(result.records[0].git_branch, "main")
            self.assertTrue(result.records[0].git_commit)
            self.assertIsNone(result.next_cursor)

    def test_connector_snapshot_adapter_preserves_external_ids(self):
        with TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "github.json"
            snapshot.write_text(json.dumps({
                "items": [{
                    "external_id": "1069592908",
                    "name": "Kai",
                    "url": "https://github.com/Bashull/Kai",
                    "size_bytes": 55880,
                    "metadata": {"default_branch": "main", "visibility": "public"},
                }]
            }), encoding="utf-8")
            adapter = ConnectorSnapshotAdapter(
                source_id="github:bashull",
                source_kind="GITHUB",
                snapshot_path=snapshot,
            )
            result = adapter.collect(max_items=100)
            self.assertEqual(result.records[0].provenance["external_id"], "1069592908")
            self.assertEqual(result.records[0].source_kind, "GITHUB")

    def test_connector_snapshot_rejects_secret_fields(self):
        with TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "bad.json"
            snapshot.write_text(json.dumps({"items": [{"name": "x", "client_secret": "hidden"}]}), encoding="utf-8")
            adapter = ConnectorSnapshotAdapter("drive:test", "GOOGLE_DRIVE", snapshot)
            with self.assertRaisesRegex(ValueError, "secret field"):
                adapter.collect(max_items=10)


if __name__ == "__main__":
    unittest.main()
