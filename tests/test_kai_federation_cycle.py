from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from tools.kai_federation_cycle import FederationCycleConfig, FederationCycleRunner
from tools.kai_source_adapters import AdapterResult
from tools.kai_source_federation import FederationLedger, SourceRecord


class StubAdapter:
    def __init__(self, result: AdapterResult):
        self.result = result

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        return self.result


class FederationCycleTests(unittest.TestCase):
    def test_cycle_records_healthy_and_blocked_sources_without_claiming_full_coverage(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            ledger = FederationLedger(home / "ledger")
            sources = [
                {"source_id": "pc:test", "kind": "PC", "enabled": True, "uri": "file:///tmp"},
                {"source_id": "drive:test", "kind": "GOOGLE_DRIVE", "enabled": True, "uri": "gdrive://root"},
            ]
            def factory(source):
                if source["source_id"] == "drive:test":
                    raise PermissionError("connector write scope unavailable")
                return StubAdapter(AdapterResult(
                    "HEALTHY",
                    [SourceRecord(
                        source_id="pc:test",
                        source_kind="PC",
                        source_uri="file:///tmp",
                        logical_path="a.txt",
                        filename="a.txt",
                    )],
                    [],
                    1,
                    False,
                    None,
                ))

            runner = FederationCycleRunner(home, ledger, sources, factory)
            report = runner.run(FederationCycleConfig("cycle-test", max_items_per_source=10))
            self.assertEqual(report["sources"]["pc:test"]["status"], "HEALTHY")
            self.assertEqual(report["sources"]["drive:test"]["status"], "BLOCKED_WITH_REASON")
            self.assertFalse(report["complete"])
            self.assertTrue((home / "coverage_current.json").is_file())
            self.assertTrue((home / "federation_events.jsonl").is_file())

    def test_second_cycle_updates_current_and_appends_history(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            ledger = FederationLedger(home / "ledger")
            source = {"source_id": "pc:test", "kind": "PC", "enabled": True, "uri": "file:///tmp"}
            adapter = StubAdapter(AdapterResult(
                "HEALTHY",
                [SourceRecord(
                    source_id="pc:test",
                    source_kind="PC",
                    source_uri="file:///tmp",
                    logical_path="same.txt",
                    filename="same.txt",
                    sha256="e" * 64,
                )],
                [],
                1,
                False,
                None,
            ))
            runner = FederationCycleRunner(home, ledger, [source], lambda _: adapter)
            runner.run(FederationCycleConfig("cycle-1", 10))
            runner.run(FederationCycleConfig("cycle-2", 10))
            events = (home / "federation_events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 2)
            self.assertEqual(len(ledger.query()), 1)


if __name__ == "__main__":
    unittest.main()
