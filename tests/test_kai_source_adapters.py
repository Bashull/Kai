from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sqlite3
import subprocess
import unittest

from tools.kai_source_adapters import (
    BackupManifestAdapter,
    ConnectorSnapshotAdapter,
    FileIndexDatabaseAdapter,
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


class InventoryEvidenceAdapterTests(unittest.TestCase):
    def test_backup_manifest_adapter_preserves_sha256_and_root(self):
        with TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "capability": "backup-manifest",
                "version": "0.1.0",
                "roots": ["C:/KAI"],
                "entries": [{
                    "root": "C:/KAI",
                    "relative_path": "core/brain.py",
                    "size": 123,
                    "mtime_ns": 42,
                    "sha256": "b" * 64,
                }],
                "summary": {"files": 1, "bytes": 123, "skipped_symlinks": 0},
            }), encoding="utf-8")
            result = BackupManifestAdapter("pc:kai-root", manifest).collect(max_items=10)
            record = result.records[0]
            self.assertEqual(record.sha256, "b" * 64)
            self.assertEqual(record.logical_path, "core/brain.py")
            self.assertEqual(record.provenance["manifest_capability"], "backup-manifest")

    def test_file_index_database_adapter_reads_existing_index_schema(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "files.sqlite3"
            con = sqlite3.connect(db)
            con.executescript("""
            CREATE TABLE files (
              manifest_id TEXT NOT NULL,
              root TEXT NOT NULL,
              relative_path TEXT NOT NULL,
              name TEXT NOT NULL,
              ext TEXT NOT NULL,
              size INTEGER NOT NULL,
              mtime_ns INTEGER NOT NULL,
              sha256 TEXT NOT NULL
            );
            """)
            con.execute(
                "INSERT INTO files VALUES(?,?,?,?,?,?,?,?)",
                ("m1", "C:/KAI", "tools/x.py", "x.py", ".py", 12, 99, "c" * 64),
            )
            con.commit()
            con.close()
            result = FileIndexDatabaseAdapter("pc:file-index", db).collect(max_items=10)
            self.assertEqual(len(result.records), 1)
            self.assertEqual(result.records[0].sha256, "c" * 64)
