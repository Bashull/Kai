from __future__ import annotations

import re
import unittest
from pathlib import Path


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_gpt_long_term_memory_skill_contract(self):
        skill = self.root / "skills" / "gpt-long-term-memory" / "SKILL.md"
        self.assertTrue(skill.exists(), f"Missing skill: {skill}")
        text = skill.read_text(encoding="utf-8")

        self.assertIn("name: gpt-long-term-memory", text)
        description = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        self.assertIsNotNone(description)
        assert description is not None
        self.assertTrue(description.group(1).startswith("Use when"))

        for heading in (
            "## Overview",
            "## When to use",
            "## Memory loading contract",
            "## Memory writing contract",
            "## Evidence and confidence",
            "## Safety contract",
            "## New-chat boot sequence",
            "## Decision labels",
        ):
            self.assertIn(heading, text)

        required_phrases = (
            "EXPLICIT",
            "EVIDENCED",
            "INFERRED",
            "UNKNOWN",
            "boot_packet.md",
            "do not invent continuity",
            "session-close",
            "provenance",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, text)



    def _assert_forge_skill_shape(self, name: str) -> str:
        skill = self.root / "skills" / name / "SKILL.md"
        self.assertTrue(skill.exists(), f"Missing skill: {skill}")
        text = skill.read_text(encoding="utf-8")
        self.assertIn(f"name: {name}", text)
        description = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        self.assertIsNotNone(description)
        assert description is not None
        self.assertTrue(description.group(1).startswith("Use when"))
        for heading in (
            "## Overview",
            "## When to use",
            "## Evidence contract",
            "## Safety contract",
            "## Workflow",
            "## Decision labels",
        ):
            self.assertIn(heading, text)
        return text

    def test_continuous_improvement_forge_skill_contract(self):
        text = self._assert_forge_skill_shape("kai-continuous-improvement-forge")
        for phrase in (
            "No promotion without provenance",
            "kai_capability_scanner.py",
            "kai_capability_registry.py",
            "DISCOVERED",
            "VALIDATED",
            "PROMOTED",
            "CANONICAL",
            "gpt-long-term-memory",
        ):
            self.assertIn(phrase, text)

    def test_discovery_to_capability_skill_contract(self):
        text = self._assert_forge_skill_shape("kai-discovery-to-capability")
        for phrase in (
            "kai_capability_scanner.py",
            "SHA-256",
            "provenance",
            "QUARANTINED",
            "DUPLICATE",
            "do not execute discovered code",
        ):
            self.assertIn(phrase, text)

    def test_genealogy_mining_skill_contract(self):
        text = self._assert_forge_skill_shape("kai-genealogy-mining")
        for phrase in (
            "kai_genealogy_miner.py",
            "SHA-256",
            "timestamps alone never prove ancestry",
            "EXACT_COPY",
            "FUNCTIONAL_ANCESTOR_CANDIDATE",
            "DIVERGED_BRANCH",
            "UNRELATED_OR_UNKNOWN",
        ):
            self.assertIn(phrase, text)

if __name__ == "__main__":
    unittest.main()


class KaiControlPlaneSkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def _read_skill(self, name: str) -> str:
        skill = self.root / "skills" / name / "SKILL.md"
        self.assertTrue(skill.exists(), f"Missing skill: {skill}")
        text = skill.read_text(encoding="utf-8")
        self.assertIn(f"name: {name}", text)
        description = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        self.assertIsNotNone(description)
        assert description is not None
        self.assertTrue(description.group(1).startswith("Use when"))
        return text

    def test_kai_control_plane_skill_contract(self):
        text = self._read_skill("kai-control-plane")
        for heading in (
            "## Overview", "## When to use", "## Commands",
            "## Placement contract", "## Memory contract",
            "## Safety contract", "## Decision labels",
        ):
            self.assertIn(heading, text)
        for phrase in (
            "/despierta", "/recuerda", "/absorbe", "/cierra",
            "/crea-skill", "/crea-herramienta",
            "/actualiza-skill", "/actualiza-herramienta",
            "/donde-va", "/promueve", "/organiza",
            "/checkpoint", "/evidencia", "/doctor-global",
            "kai_control_plane.py",
            "do not bypass guardrails",
        ):
            self.assertIn(phrase, text)

    def test_kai_artifact_placement_skill_contract(self):
        text = self._read_skill("kai-artifact-placement")
        for phrase in (
            "00_KAI_CORE", "10_KAI_LAB_INGESTION_FORENSICS",
            "20_PROJECTS", "30_AI_WORKSPACES", "40_LIBRARY_REFERENCE",
            "80_INBOX_UNCLASSIFIED", "90_ARCHIVE_HISTORICAL",
            "99_PRIVATE_SENSITIVE", "kai_location_policy.json",
            "unknown material goes to 80_INBOX_UNCLASSIFIED",
            "sensitive material goes to 99_PRIVATE_SENSITIVE",
        ):
            self.assertIn(phrase, text)

    def test_kai_capability_authoring_skill_contract(self):
        text = self._read_skill("kai-capability-authoring")
        for heading in (
            "## Overview", "## When to use", "## Creation workflow",
            "## Update workflow", "## Storage contract",
            "## Test and promotion contract", "## Safety contract",
        ):
            self.assertIn(heading, text)
        for phrase in (
            "create-skill", "create-tool", "update-skill", "update-tool",
            "snapshot before replace", "source before runtime",
            "CANDIDATE", "TESTING", "VALIDATED", "PROMOTED", "CANONICAL",
            "writing-skills", "test-driven-development",
        ):
            self.assertIn(phrase, text)
