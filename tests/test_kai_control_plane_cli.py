from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class KaiControlPlaneCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.bridge = self.root / "bridge"
        self.state = self.root / "state"
        self.memory = self.root / "memory"
        self.capabilities = self.root / "capabilities"
        self.policy = self.root / "policy.json"
        self.script = Path(__file__).resolve().parents[1] / "tools" / "kai_control_plane.py"
        self.policy.write_text(json.dumps({
            "schema_version": 1,
            "local": {
                "repo_root": str(self.repo),
                "bridge_root": str(self.bridge),
                "state_root": str(self.state),
            },
            "drive": {
                "00_KAI_CORE": {"id": "core-id"},
                "10_KAI_LAB_INGESTION_FORENSICS": {"id": "lab-id"},
                "20_PROJECTS": {"id": "projects-id"},
                "30_AI_WORKSPACES": {"id": "ai-id"},
                "40_LIBRARY_REFERENCE": {"id": "library-id"},
                "80_INBOX_UNCLASSIFIED": {"id": "inbox-id"},
                "90_ARCHIVE_HISTORICAL": {"id": "archive-id"},
                "99_PRIVATE_SENSITIVE": {"id": "private-id"},
            },
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args: str) -> dict:
        command = [
            sys.executable,
            str(self.script),
            "--policy", str(self.policy),
            "--repo-root", str(self.repo),
            "--bridge-root", str(self.bridge),
            "--state-root", str(self.state),
            "--memory-home", str(self.memory),
            "--capability-home", str(self.capabilities),
            *args,
        ]
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return json.loads(result.stdout)

    def test_commands_returns_slash_alias_catalog(self):
        result = self.run_cli("commands")
        self.assertEqual(result["/despierta"], "wake")
        self.assertEqual(result["/crea-skill"], "create-skill")
        self.assertEqual(result["/doctor-global"], "doctor")

    def test_where_returns_drive_destination(self):
        result = self.run_cli("where", "--kind", "secret")
        self.assertEqual(result["drive_zone"], "99_PRIVATE_SENSITIVE")
        self.assertEqual(result["drive_id"], "private-id")

    def test_create_skill_uses_repo_source_not_runtime(self):
        result = self.run_cli(
            "create-skill",
            "--name", "cli-created-skill",
            "--description", "Use when testing CLI skill creation",
        )
        self.assertTrue(Path(result["source_path"]).is_file())
        self.assertFalse(Path(result["runtime_target"]).exists())
        self.assertEqual(result["state"], "CANDIDATE")

    def test_doctor_returns_healthy_for_fresh_runtime(self):
        result = self.run_cli("doctor")
        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["memory"]["status"], "HEALTHY")
        self.assertEqual(result["capabilities"]["status"], "HEALTHY")


if __name__ == "__main__":
    unittest.main()
