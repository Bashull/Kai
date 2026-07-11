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


if __name__ == "__main__":
    unittest.main()
