from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.kai_control_plane import COMMAND_ALIASES, KaiControlPlane
from tools.kai_location_policy import PlacementPolicy


class KaiControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.bridge = self.root / "bridge"
        self.state = self.root / "state"
        self.memory = self.root / "memory"
        self.capabilities = self.root / "capabilities"
        self.policy = PlacementPolicy.from_dict({
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
        })
        self.plane = KaiControlPlane(
            repo_root=self.repo,
            bridge_root=self.bridge,
            state_root=self.state,
            memory_home=self.memory,
            capability_home=self.capabilities,
            policy=self.policy,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_command_catalog_contains_conversational_aliases(self):
        required = {
            "/despierta", "/recuerda", "/absorbe", "/cierra",
            "/crea-skill", "/crea-herramienta",
            "/actualiza-skill", "/actualiza-herramienta",
            "/donde-va", "/promueve", "/organiza",
            "/checkpoint", "/evidencia", "/doctor-global",
        }
        self.assertTrue(required.issubset(COMMAND_ALIASES))

    def test_create_skill_writes_only_to_source_until_validated(self):
        result = self.plane.create_skill(
            "testing-memory-paths",
            "Use when validating persistent memory placement and routing",
        )
        source = Path(result["source_path"])
        runtime = Path(result["runtime_target"])
        self.assertTrue(source.is_file())
        self.assertFalse(runtime.exists())
        text = source.read_text(encoding="utf-8")
        self.assertIn("name: testing-memory-paths", text)
        self.assertIn("## Safety contract", text)
        self.assertEqual(result["state"], "CANDIDATE")

    def test_create_skill_rejects_duplicate_without_overwrite(self):
        self.plane.create_skill("safe-routing", "Use when testing safe routing")
        with self.assertRaises(FileExistsError):
            self.plane.create_skill("safe-routing", "Use when testing again")

    def test_create_tool_writes_python_scaffold_to_source_only(self):
        result = self.plane.create_tool("kai_example_tool")
        source = Path(result["source_path"])
        runtime = Path(result["runtime_target"])
        self.assertTrue(source.is_file())
        self.assertFalse(runtime.exists())
        text = source.read_text(encoding="utf-8")
        self.assertIn("def main", text)
        self.assertEqual(result["state"], "CANDIDATE")

    def test_update_skill_creates_snapshot_before_replace(self):
        created = self.plane.create_skill("mutable-skill", "Use when testing updates")
        source = Path(created["source_path"])
        replacement = self.root / "replacement.md"
        replacement.write_text("---\nname: mutable-skill\ndescription: Use when updated\n---\n\n# Updated\n", encoding="utf-8")
        result = self.plane.update_skill("mutable-skill", replacement)
        self.assertTrue(Path(result["snapshot_path"]).is_file())
        self.assertIn("# Updated", source.read_text(encoding="utf-8"))

    def test_where_uses_location_policy(self):
        result = self.plane.where("secret")
        self.assertEqual(result["drive_zone"], "99_PRIVATE_SENSITIVE")
        self.assertEqual(result["drive_id"], "private-id")

    def test_wake_remember_and_close_session_share_memory_runtime(self):
        self.plane.memory_ledger.add_memory({
            "kind": "PROJECT_STATE",
            "scope": "project:kai",
            "title": "Control plane test memory",
            "content": "Persistent memory is available.",
            "priority": 100,
            "confidence": "EVIDENCED",
            "tags": ["control-plane"],
            "provenance": [{"source": "unit-test"}],
        })
        wake = self.plane.wake(project="kai", max_chars=4000)
        self.assertIn("Control plane test memory", wake["markdown"])
        found = self.plane.remember("Persistent memory", limit=5)
        self.assertEqual(len(found), 1)

        summary = {
            "session_id": "control-plane-session",
            "objective": "Verify close session wrapper",
            "actions": ["ran test"],
            "artifacts": [],
            "decisions": [],
            "improvements": [],
            "pending": [],
            "next_step": "continue",
        }
        closed = self.plane.close_session(summary, project="kai")
        self.assertIn("snapshot_path", closed)
        self.assertTrue(Path(closed["snapshot_path"]).is_file())
        self.assertEqual(closed["boot_health"]["omitted"], 0)

    def test_doctor_aggregates_memory_registry_location_and_integrations(self):
        diagnosis = self.plane.doctor()
        self.assertEqual(diagnosis["status"], "DEGRADED")
        self.assertEqual(diagnosis["core_status"], "HEALTHY")
        self.assertEqual(diagnosis["memory"]["status"], "HEALTHY")
        self.assertEqual(diagnosis["capabilities"]["status"], "HEALTHY")
        self.assertTrue(diagnosis["location_policy"]["valid"])
        self.assertEqual(diagnosis["integrations"]["status"], "DEGRADED")

    def test_promote_wrapper_does_not_bypass_registry_guards(self):
        candidate_path = self.root / "candidate.json"
        candidate = {
            "name": "example",
            "sha256": "a" * 64,
            "decision": "TOOL_CANDIDATE",
            "capabilities": ["example"],
            "secret_signals": [],
            "provenance": {"source": "unit-test"},
        }
        candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        registered = self.plane.register_candidate(candidate_path)
        with self.assertRaises(ValueError):
            self.plane.promote(
                registered["capability_id"],
                "VALIDATED",
                {"tests": {"passed": 1, "failed": 0}},
            )


    def test_integrations_expose_five_governed_targets(self):
        items = self.plane.integrations()
        self.assertEqual(
            {item["slug"] for item in items},
            {
                "storage-commander",
                "termux-bridge-planner",
                "backup-manifest",
                "file-indexer",
                "local-knowledge-vault",
            },
        )

    def test_integration_doctor_degrades_when_required_runtimes_are_missing(self):
        diagnosis = self.plane.integration_doctor()
        self.assertEqual(diagnosis["required_count"], 5)
        self.assertEqual(diagnosis["status"], "DEGRADED")
        self.assertEqual(len(diagnosis["degraded"]), 5)

    def test_integration_call_respects_adapter_allowlist(self):
        with self.assertRaisesRegex(ValueError, "operation is not allowlisted"):
            self.plane.integration_call("storage-commander", "execute", ["{}"])


if __name__ == "__main__":
    unittest.main()
