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

    def run_cli_process(self, *args: str) -> subprocess.CompletedProcess[str]:
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
        return subprocess.run(command, check=False, text=True, capture_output=True)

    def run_cli(self, *args: str) -> dict:
        result = self.run_cli_process(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_commands_returns_slash_alias_catalog(self):
        result = self.run_cli("commands")
        self.assertEqual(result["/despierta"], "wake")
        self.assertEqual(result["/crea-skill"], "create-skill")
        self.assertEqual(result["/doctor-global"], "doctor")
        self.assertEqual(result["/integraciones"], "integrations")
        self.assertEqual(result["/doctor-integraciones"], "integration-doctor")
        self.assertEqual(result["/usa-capacidad"], "integration-call")

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

    def test_doctor_reports_healthy_core_and_degraded_integrations_for_fresh_runtime(self):
        process = self.run_cli_process("doctor")
        self.assertEqual(process.returncode, 2)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["core_status"], "HEALTHY")
        self.assertEqual(result["memory"]["status"], "HEALTHY")
        self.assertEqual(result["capabilities"]["status"], "HEALTHY")
        self.assertEqual(result["integrations"]["status"], "DEGRADED")


    def test_integrations_returns_five_governed_targets(self):
        result = self.run_cli("integrations")
        self.assertEqual(
            {item["slug"] for item in result},
            {
                "storage-commander",
                "termux-bridge-planner",
                "backup-manifest",
                "file-indexer",
                "local-knowledge-vault",
            },
        )

    def test_integration_doctor_returns_degraded_for_empty_temp_runtime(self):
        process = self.run_cli_process("integration-doctor")
        self.assertEqual(process.returncode, 2)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["required_count"], 5)


    def test_integration_call_rejects_disallowed_operation_with_clear_error(self):
        process = self.run_cli_process(
            "integration-call",
            "--name", "storage-commander",
            "--operation", "execute",
            "{}",
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("operation is not allowlisted", process.stderr)


if __name__ == "__main__":
    unittest.main()


class KaiControlPlaneDeployedRuntimeTests(unittest.TestCase):
    def test_deployed_script_imports_sibling_location_policy_without_tools_package(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "bridge" / "agent_tools" / "kai_control_plane"
            runtime.mkdir(parents=True)
            source_root = Path(__file__).resolve().parents[1]
            script = runtime / "kai_control_plane.py"
            policy_module = runtime / "kai_location_policy.py"
            integrations_module = runtime / "kai_capability_integrations.py"
            script.write_bytes((source_root / "tools" / "kai_control_plane.py").read_bytes())
            policy_module.write_bytes((source_root / "tools" / "kai_location_policy.py").read_bytes())
            integrations_module.write_bytes((source_root / "tools" / "kai_capability_integrations.py").read_bytes())
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


    def test_deployed_script_lists_integrations_with_sibling_integration_module(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "bridge" / "agent_tools" / "kai_control_plane"
            runtime.mkdir(parents=True)
            source_root = Path(__file__).resolve().parents[1]
            for name in ("kai_control_plane.py", "kai_location_policy.py", "kai_capability_integrations.py"):
                (runtime / name).write_bytes((source_root / "tools" / name).read_bytes())
            policy = root / "policy.json"
            policy.write_text(json.dumps({
                "schema_version": 1,
                "local": {"repo_root": str(root / "repo"), "bridge_root": str(root / "bridge"), "state_root": str(root / "state")},
                "drive": {zone: {"id": zone.lower()} for zone in (
                    "00_KAI_CORE", "10_KAI_LAB_INGESTION_FORENSICS", "20_PROJECTS", "30_AI_WORKSPACES",
                    "40_LIBRARY_REFERENCE", "80_INBOX_UNCLASSIFIED", "90_ARCHIVE_HISTORICAL", "99_PRIVATE_SENSITIVE",
                )},
            }), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(runtime / "kai_control_plane.py"),
                    "--policy", str(policy),
                    "--repo-root", str(root / "repo"),
                    "--bridge-root", str(root / "bridge"),
                    "--state-root", str(root / "state"),
                    "--memory-home", str(root / "memory"),
                    "--capability-home", str(root / "capabilities"),
                    "integrations",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload), 5)
