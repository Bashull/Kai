from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.kai_memory_ledger import MemoryLedger


class MemoryLedgerTests(unittest.TestCase):
    def sample_record(self) -> dict:
        return {
            "kind": "DECISION",
            "scope": "project:kai",
            "title": "Use SHA-256",
            "content": "Hashes decide exact duplicates.",
            "priority": 90,
            "confidence": "EXPLICIT",
            "tags": ["hash", "dedupe"],
            "provenance": [],
        }

    def test_persists_and_skips_exact_duplicate(self):
        with TemporaryDirectory() as tmp:
            ledger = MemoryLedger(Path(tmp))
            first = ledger.add_memory(self.sample_record())
            second = ledger.add_memory(self.sample_record())
            self.assertEqual(first["decision"], "INSERTED")
            self.assertEqual(second["decision"], "SKIP_EXACT_DUPLICATE")
            self.assertEqual(len(ledger.search("SHA-256")), 1)

    def test_survives_new_ledger_instance(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            MemoryLedger(home).add_memory(self.sample_record())
            reopened = MemoryLedger(home)
            results = reopened.search("SHA-256")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Use SHA-256")

    def test_export_json_is_deterministic(self):
        with TemporaryDirectory() as tmp:
            ledger = MemoryLedger(Path(tmp))
            ledger.add_memory(self.sample_record())
            first = ledger.export_json()
            second = ledger.export_json()
            self.assertEqual(first, second)
            parsed = json.loads(first)
            self.assertEqual(parsed[0]["title"], "Use SHA-256")

    def test_redacts_sensitive_values_before_storage_and_events(self):
        with TemporaryDirectory() as tmp:
            ledger = MemoryLedger(Path(tmp))
            record = self.sample_record()
            record["content"] = "api_key=AIza" + "A" * 35
            result = ledger.add_memory(record)
            stored = ledger.get_memory(result["memory_id"])
            self.assertIsNotNone(stored)
            assert stored is not None
            self.assertNotIn("AIza", stored["content"])
            self.assertIn("[REDACTED:GOOGLE_API_KEY]", stored["content"])
            self.assertNotIn("AIza", ledger.events_path.read_text(encoding="utf-8"))

    def test_superseded_record_is_not_in_default_search(self):
        with TemporaryDirectory() as tmp:
            ledger = MemoryLedger(Path(tmp))
            old_record = {**self.sample_record(), "title": "Old path", "content": "Path C:/old"}
            new_record = {**self.sample_record(), "title": "New path", "content": "Path C:/new"}
            old_id = ledger.add_memory(old_record)["memory_id"]
            new_id = ledger.add_memory(new_record)["memory_id"]
            ledger.supersede(old_id, new_id)
            self.assertEqual([item["memory_id"] for item in ledger.search("Path")], [new_id])
            self.assertEqual(ledger.get_memory(old_id)["status"], "SUPERSEDED")

    def test_session_close_records_context(self):
        with TemporaryDirectory() as tmp:
            ledger = MemoryLedger(Path(tmp))
            result = ledger.close_session({
                "session_id": "session-001",
                "scope": "project:kai",
                "objective": "Build persistent memory",
                "actions": ["Created persistent ledger"],
                "artifacts": [{"path": "tools/kai_memory_ledger.py", "sha256": "synthetic-hash"}],
                "decisions": ["Use SQLite plus JSONL"],
                "improvements": ["Context survives process restart"],
                "pending": ["Publish current boot packet to private Drive"],
                "next_step": "Create GPT memory skill",
            })
            self.assertTrue(Path(result["session_file"]).exists())
            saved = json.loads(Path(result["session_file"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["objective"], "Build persistent memory")
            packet = ledger.build_boot_packet(project="kai")
            self.assertIn("Build persistent memory", packet["markdown"])
            self.assertIn("Publish current boot packet to private Drive", packet["markdown"])

    def test_boot_packet_is_deterministic_and_budgeted(self):
        with TemporaryDirectory() as tmp:
            ledger = MemoryLedger(Path(tmp))
            ledger.add_memory({"kind": "CORE_IDENTITY", "scope": "global", "title": "Companion identity", "content": "Kai preserves truth, provenance and continuity with Asier.", "priority": 100, "confidence": "EXPLICIT", "tags": ["identity"], "provenance": []})
            ledger.add_memory({"kind": "PENDING", "scope": "project:kai", "title": "Next work", "content": "Finish the continuous improvement forge.", "priority": 100, "confidence": "EXPLICIT", "tags": ["pending"], "provenance": []})
            for index in range(20):
                ledger.add_memory({"kind": "CONTEXT", "scope": "project:kai", "title": f"Context {index:02d}", "content": "x" * 300, "priority": index, "confidence": "EVIDENCED", "tags": ["bulk"], "provenance": []})
            first = ledger.build_boot_packet(max_chars=1500, project="kai")
            second = ledger.build_boot_packet(max_chars=1500, project="kai")
            self.assertEqual(first["markdown"], second["markdown"])
            self.assertLessEqual(len(first["markdown"]), 1500)
            self.assertIn("Companion identity", first["markdown"])
            self.assertIn("Next work", first["markdown"])


if __name__ == "__main__":
    unittest.main()
