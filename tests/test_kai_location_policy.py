from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.kai_location_policy import PlacementPolicy


class KaiLocationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        self.policy = PlacementPolicy.from_dict({
            "schema_version": 1,
            "local": {
                "repo_root": str(root / "repo"),
                "bridge_root": str(root / "bridge"),
                "state_root": str(root / "state"),
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

    def tearDown(self):
        self.tmp.cleanup()

    def test_skill_routes_to_repo_source_runtime_and_lab_evidence(self):
        route = self.policy.route("skill")
        self.assertTrue(route["local_source_root"].endswith("repo\\skills"))
        self.assertTrue(route["local_runtime_root"].endswith("bridge\\skills"))
        self.assertEqual(route["drive_evidence_zone"], "10_KAI_LAB_INGESTION_FORENSICS")
        self.assertEqual(route["drive_canonical_zone"], "00_KAI_CORE")
        self.assertEqual(route["state"], "CANDIDATE_UNTIL_VALIDATED")

    def test_tool_routes_to_repo_source_runtime_and_lab_evidence(self):
        route = self.policy.route("tool")
        self.assertTrue(route["local_source_root"].endswith("repo\\tools"))
        self.assertTrue(route["local_runtime_root"].endswith("bridge\\agent_tools"))
        self.assertEqual(route["drive_evidence_zone"], "10_KAI_LAB_INGESTION_FORENSICS")
    def test_sensitive_and_unknown_artifacts_have_safe_destinations(self):
        sensitive = self.policy.route("secret")
        unknown = self.policy.route("unknown")
        self.assertEqual(sensitive["drive_zone"], "99_PRIVATE_SENSITIVE")
        self.assertEqual(unknown["drive_zone"], "80_INBOX_UNCLASSIFIED")

    def test_snapshot_and_historical_material_route_to_archive(self):
        self.assertEqual(self.policy.route("snapshot")["drive_zone"], "90_ARCHIVE_HISTORICAL")
        self.assertEqual(self.policy.route("superseded")["drive_zone"], "90_ARCHIVE_HISTORICAL")

    def test_project_and_reference_routes_are_explicit(self):
        self.assertEqual(self.policy.route("project")["drive_zone"], "20_PROJECTS")
        self.assertEqual(self.policy.route("research")["drive_zone"], "40_LIBRARY_REFERENCE")
        self.assertEqual(self.policy.route("ai-workspace")["drive_zone"], "30_AI_WORKSPACES")

    def test_drive_zone_lookup_exposes_canonical_id(self):
        zone = self.policy.drive_zone("00_KAI_CORE")
        self.assertEqual(zone["id"], "core-id")

    def test_manifest_is_deterministic(self):
        first = self.policy.location_manifest()
        second = self.policy.location_manifest()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
