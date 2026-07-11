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
