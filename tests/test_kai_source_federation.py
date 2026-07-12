from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.kai_source_federation import FederationLedger, SourceRecord


class FederationLedgerTests(unittest.TestCase):
    def test_record_round_trip_preserves_provenance(self):
        with TemporaryDirectory() as tmp:
            ledger = FederationLedger(Path(tmp))
            record = SourceRecord(
                source_id="pc:kai-root",
                source_kind="PC",
                source_uri="file:///C:/Users/ASIER/OneDrive/Desktop/KAI",
                logical_path="repos_cache/00_kai_own/Kai/README.md",
                filename="README.md",
                size_bytes=4711,
                sha256="a" * 64,
                provenance={"adapter": "test", "observed_at": "2026-07-12T00:00:00Z"},
            )
            stored = ledger.upsert_record(record)
            loaded = ledger.get_record(stored.record_id)
            self.assertEqual(loaded.sha256, "a" * 64)
            self.assertEqual(loaded.provenance["adapter"], "test")

    def test_query_summary_and_doctor(self):
        with TemporaryDirectory() as tmp:
            ledger = FederationLedger(Path(tmp))
            ledger.upsert_record(SourceRecord(
                source_id="s24:kai-nido",
                source_kind="S24",
                source_uri="adb://SM-S928B/sdcard/Kai_Nido",
                logical_path="Kai-main/README.md",
                filename="README.md",
                size_bytes=100,
            ))
            self.assertEqual(len(ledger.query(source_kind="S24")), 1)
            self.assertEqual(ledger.source_summary()["S24"], 1)
            self.assertEqual(ledger.doctor()["status"], "HEALTHY")

    def test_exact_reingest_is_idempotent(self):
        with TemporaryDirectory() as tmp:
            ledger = FederationLedger(Path(tmp))
            record = SourceRecord(
                source_id="pc:test",
                source_kind="PC",
                source_uri="file:///tmp",
                logical_path="same.txt",
                filename="same.txt",
                sha256="f" * 64,
            )
            first = ledger.upsert_record(record)
            second = ledger.upsert_record(record)
            self.assertEqual(first.record_id, second.record_id)
            self.assertEqual(len(ledger.query()), 1)


if __name__ == "__main__":
    unittest.main()
