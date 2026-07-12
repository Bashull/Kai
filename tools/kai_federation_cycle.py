from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import json

try:
    from tools.kai_source_federation import FederationLedger
except ModuleNotFoundError:
    import sys
    local_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(local_dir))
    from kai_source_federation import FederationLedger


@dataclass(frozen=True)
class FederationCycleConfig:
    cycle_id: str
    max_items_per_source: int = 10000

    def __post_init__(self) -> None:
        if not str(self.cycle_id).strip():
            raise ValueError("cycle_id is required")
        if self.max_items_per_source < 1:
            raise ValueError("max_items_per_source must be at least 1")


class FederationCycleRunner:
    def __init__(
        self,
        home: Path,
        ledger: FederationLedger,
        sources: list[dict[str, Any]],
        adapter_factory: Callable[[dict[str, Any]], Any],
    ):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger
        self.sources = list(sources)
        self.adapter_factory = adapter_factory
        self.events_path = self.home / "federation_events.jsonl"
        self.coverage_path = self.home / "coverage_current.json"

    def run(self, config: FederationCycleConfig) -> dict[str, Any]:
        source_report: dict[str, Any] = {}
        total_stored = 0

        for source in self.sources:
            source_id = str(source.get("source_id") or "")
            if not source_id:
                raise ValueError("source requires source_id")
            try:
                adapter = self.adapter_factory(source)
                result = adapter.collect(max_items=config.max_items_per_source)
                stored = 0
                for record in result.records:
                    self.ledger.upsert_record(record)
                    stored += 1
                total_stored += stored
                source_report[source_id] = {
                    "status": result.status,
                    "stored": stored,
                    "observed_count": result.observed_count,
                    "truncated": result.truncated,
                    "next_cursor": result.next_cursor,
                    "warnings": result.warnings,
                }
            except Exception as exc:
                source_report[source_id] = {
                    "status": "BLOCKED_WITH_REASON",
                    "stored": 0,
                    "observed_count": 0,
                    "truncated": False,
                    "next_cursor": None,
                    "reason": f"{type(exc).__name__}: {exc}",
                }

        complete = bool(source_report) and all(
            item["status"] == "HEALTHY" and not item.get("truncated", False)
            for item in source_report.values()
        )
        report = {
            "cycle_id": config.cycle_id,
            "complete": complete,
            "stored": total_stored,
            "sources": source_report,
        }
        self._write_current(report)
        self._append_event(report)
        return report

    def _write_current(self, report: dict[str, Any]) -> None:
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        tmp = self.coverage_path.with_suffix(self.coverage_path.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(self.coverage_path)

    def _append_event(self, report: dict[str, Any]) -> None:
        line = json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n"
        with self.events_path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()
