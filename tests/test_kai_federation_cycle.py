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


class PagedStubAdapter:
    def __init__(self, total: int):
        self.total = total

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        offset = int(cursor or "0")
        end = min(offset + max_items, self.total)
        records = [SourceRecord(
            source_id="paged",
            source_kind="TEST",
            source_uri="test://paged",
            logical_path=f"f{index}.txt",
            filename=f"f{index}.txt",
            sha256=f"{index + 1:064x}"[-64:],
        ) for index in range(offset, end)]
        next_cursor = str(end) if end < self.total else None
        return AdapterResult(
            "HEALTHY",
            records,
            [],
            end,
            next_cursor is not None,
            next_cursor,
        )


class FederationCursorResumeTests(unittest.TestCase):
    def test_cycle_resumes_from_saved_cursor(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            ledger = FederationLedger(home / "ledger")
            source = {"source_id": "paged", "kind": "TEST", "enabled": True, "uri": "test://paged"}
            adapter = PagedStubAdapter(total=5)
            runner = FederationCycleRunner(home, ledger, [source], lambda _: adapter)
            first = runner.run(FederationCycleConfig("c1", max_items_per_source=2))
            second = runner.run(FederationCycleConfig("c2", max_items_per_source=2))
            third = runner.run(FederationCycleConfig("c3", max_items_per_source=2))
            self.assertEqual(first["sources"]["paged"]["next_cursor"], "2")
            self.assertEqual(second["sources"]["paged"]["next_cursor"], "4")
            self.assertIsNone(third["sources"]["paged"]["next_cursor"])
            self.assertEqual(len(ledger.query()), 5)
