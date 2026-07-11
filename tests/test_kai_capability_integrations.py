from __future__ import annotations

import json
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.kai_capability_integrations import CapabilityIntegrationManager


TARGETS = {
    "storage-commander": ("kai_storage_commander.cli", "kai-storage-commander"),
    "termux-bridge-planner": ("kai_termux_bridge_planner.cli", "kai-termux-bridge-planner"),
    "backup-manifest": ("kai_backup_manifest.cli", "kai-backup-manifest"),
    "file-indexer": ("kai_file_indexer.cli", "kai-file-indexer"),
    "local-knowledge-vault": ("kai_local_knowledge_vault.cli", "kai-local-knowledge-vault"),
}


class CapabilityIntegrationManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.home = Path(self.tmp.name) / "capabilities"
        self.home.mkdir(parents=True)
        self.records = []
        for index, (slug, (module, script_name)) in enumerate(TARGETS.items(), start=1):
            self._create_package(slug, module, script_name)
            self.records.append(self._registry_record(slug, index))
        (self.home / "capabilities_current.json").write_text(
            json.dumps(self.records, indent=2), encoding="utf-8"
        )
        self.manager = CapabilityIntegrationManager(capability_home=self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def _runtime_path(self, slug: str) -> Path:
        return self.home / "candidates" / slug / "0.1.0"

    def _registry_record(self, slug: str, index: int) -> dict:
        runtime = self._runtime_path(slug)
        return {
            "capability_id": f"cap_{index:032x}",
            "name": slug,
            "state": "PROMOTED",
            "decision": "TOOL_CANDIDATE",
            "artifact_sha256": f"{index:064x}",
            "provenance": {
                "runtime_path": str(runtime),
                "source": str(runtime / "src" / "module.py"),
            },
        }

    def _create_package(self, slug: str, module: str, script_name: str) -> None:
        runtime = self._runtime_path(slug)
        package_name = module.split(".")[0]
        package_dir = runtime / "src" / package_name
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "cli.py").write_text(
            textwrap.dedent(
                """
                import argparse
                import json

                def main():
                    parser = argparse.ArgumentParser()
                    parser.add_argument("args", nargs="*")
                    parser.parse_args()
                    print(json.dumps({"ok": True}))

                if __name__ == "__main__":
                    main()
                """
            ),
            encoding="utf-8",
        )
        (runtime / "manifest.json").write_text(
            json.dumps({
                "schema_version": 1,
                "capability": slug,
                "version": "0.1.0",
                "promotion_state": "NOT_PROMOTED_NOT_CANONICAL",
                "mutation_policy": "READ_ONLY",
            }, indent=2),
            encoding="utf-8",
        )
        (runtime / "pyproject.toml").write_text(
            textwrap.dedent(
                f"""
                [project]
                name = "{slug}"
                version = "0.1.0"

                [project.scripts]
                {script_name} = "{module}:main"
                """
            ),
            encoding="utf-8",
        )

    def test_lists_five_integrations_and_registry_state_wins(self):
        records = {item["slug"]: item for item in self.manager.list_integrations()}
        self.assertEqual(set(records), set(TARGETS))
        self.assertEqual(records["backup-manifest"]["registry_state"], "PROMOTED")
        self.assertTrue(records["backup-manifest"]["available"])
        self.assertTrue(records["backup-manifest"]["promoted"])
        self.assertIn("manifest lifecycle claim differs from registry", records["backup-manifest"]["warnings"])

    def test_probe_runs_safe_help_without_shell(self):
        result = self.manager.probe("backup-manifest")
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["shell"])
        self.assertIn("usage:", result["stdout"].lower())

    def test_disallowed_operation_is_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, "operation is not allowlisted"):
            self.manager.invoke("storage-commander", "execute", ["{}"])

    def test_allowed_operation_returns_structured_result(self):
        result = self.manager.invoke("local-knowledge-vault", "doctor", ["--help"])
        self.assertEqual(result["slug"], "local-knowledge-vault")
        self.assertEqual(result["operation"], "doctor")
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["shell"])

    def test_missing_promoted_runtime_is_reported_without_execution(self):
        missing = self._runtime_path("file-indexer")
        for child in sorted(missing.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        missing.rmdir()

        records = {item["slug"]: item for item in self.manager.list_integrations()}
        self.assertFalse(records["file-indexer"]["available"])
        diagnosis = self.manager.doctor()
        self.assertEqual(diagnosis["status"], "DEGRADED")
        self.assertIn("file-indexer", diagnosis["degraded"])


if __name__ == "__main__":
    unittest.main()
