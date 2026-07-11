from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATES = {
    "DISCOVERED", "CLASSIFIED", "CANDIDATE", "TESTING", "VALIDATED",
    "PROMOTED", "CANONICAL", "QUARANTINED", "SUPERSEDED", "REJECTED",
}

TRANSITIONS = {
    "DISCOVERED": {"CLASSIFIED", "QUARANTINED", "REJECTED"},
    "CLASSIFIED": {"CANDIDATE", "QUARANTINED", "REJECTED"},
    "CANDIDATE": {"TESTING", "QUARANTINED", "REJECTED"},
    "TESTING": {"VALIDATED", "QUARANTINED", "REJECTED"},
    "VALIDATED": {"PROMOTED", "SUPERSEDED"},
    "PROMOTED": {"CANONICAL", "SUPERSEDED"},
    "CANONICAL": {"SUPERSEDED"},
    "QUARANTINED": {"CLASSIFIED", "REJECTED"},
    "SUPERSEDED": set(),
    "REJECTED": set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CapabilityRegistry:
    def __init__(self, home: Path):
        self.home = Path(home).expanduser().resolve()
        self.events_path = self.home / "capability_events.jsonl"
        self.current_path = self.home / "capabilities_current.json"
        self.home.mkdir(parents=True, exist_ok=True)
        self.events_path.touch(exist_ok=True)
        if not self.current_path.exists():
            self._write_current([])

    def _load_current(self) -> list[dict[str, Any]]:
        data = json.loads(self.current_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("capabilities_current.json must contain a list")
        return data

    def _write_current(self, records: list[dict[str, Any]]) -> None:
        ordered = sorted(records, key=lambda item: item["capability_id"])
        tmp = self.current_path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(ordered, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.current_path)

    def _append_event(self, event_type: str, capability_id: str, data: dict[str, Any]) -> None:
        event = {
            "timestamp": utc_now(),
            "event_type": event_type,
            "capability_id": capability_id,
            "data": data,
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _capability_id(candidate: dict[str, Any]) -> str:
        digest = str(candidate.get("sha256", "")).lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("candidate requires a valid SHA-256")
        return "cap_" + digest[:32]

    def current_manifest(self) -> list[dict[str, Any]]:
        return self._load_current()

    def _get(self, capability_id: str) -> dict[str, Any]:
        for record in self._load_current():
            if record["capability_id"] == capability_id:
                return record
        raise KeyError(capability_id)

    def register(self, candidate: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, dict):
            raise TypeError("candidate must be a dictionary")
        capability_id = self._capability_id(candidate)
        records = self._load_current()
        for record in records:
            if record["capability_id"] == capability_id:
                return {
                    "decision": "SKIP_EXACT_DUPLICATE",
                    "capability_id": capability_id,
                    "state": record["state"],
                }

        provenance = candidate.get("provenance")
        if not isinstance(provenance, dict) or not str(provenance.get("source", "")).strip():
            raise ValueError("candidate requires provenance with a source")

        now = utc_now()
        initial_state = "QUARANTINED" if candidate.get("decision") == "QUARANTINED" else "DISCOVERED"
        record = {
            "capability_id": capability_id,
            "name": str(candidate.get("name", capability_id)),
            "artifact_sha256": str(candidate["sha256"]).lower(),
            "state": initial_state,
            "decision": str(candidate.get("decision", "NEEDS_RESEARCH")),
            "capabilities": sorted({str(item) for item in candidate.get("capabilities", [])}),
            "secret_signals": sorted({str(item) for item in candidate.get("secret_signals", [])}),
            "provenance": provenance,
            "created_at": now,
            "updated_at": now,
            "evidence": [],
        }
        records.append(record)
        self._write_current(records)
        self._append_event("REGISTERED", capability_id, record)
        return {"decision": "REGISTERED", "capability_id": capability_id, "state": initial_state}

    @staticmethod
    def _validate_transition_guard(
        record: dict[str, Any],
        new_state: str,
        evidence: dict[str, Any],
    ) -> None:
        if new_state == "VALIDATED":
            tests = evidence.get("tests")
            if not isinstance(tests, dict):
                raise ValueError("VALIDATED requires test evidence")
            passed = int(tests.get("passed", 0))
            failed = int(tests.get("failed", -1))
            if passed <= 0 or failed != 0:
                raise ValueError("VALIDATED requires at least one passing test and zero failures")
            if not record.get("provenance"):
                raise ValueError("VALIDATED requires provenance")
        if new_state == "CANONICAL" and evidence.get("explicit_approval") is not True:
            raise ValueError("CANONICAL requires explicit approval evidence")

    def transition(
        self,
        capability_id: str,
        new_state: str,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        new_state = str(new_state).upper()
        if new_state not in STATES:
            raise ValueError(f"unknown state: {new_state}")
        if not isinstance(evidence, dict):
            raise TypeError("evidence must be a dictionary")

        records = self._load_current()
        target = next((item for item in records if item["capability_id"] == capability_id), None)
        if target is None:
            raise KeyError(capability_id)
        current_state = target["state"]
        if new_state not in TRANSITIONS[current_state]:
            raise ValueError(f"invalid transition: {current_state} -> {new_state}")

        self._validate_transition_guard(target, new_state, evidence)
        now = utc_now()
        target["state"] = new_state
        target["updated_at"] = now
        target.setdefault("evidence", []).append({
            "state": new_state,
            "timestamp": now,
            "data": evidence,
        })
        self._write_current(records)
        self._append_event(
            "STATE_TRANSITION",
            capability_id,
            {"from": current_state, "to": new_state, "evidence": evidence},
        )
        return {"capability_id": capability_id, "state": new_state}


    def doctor(self) -> dict[str, Any]:
        checks = {
            "events_log": self.events_path.is_file(),
            "current_manifest": self.current_path.is_file(),
        }
        capability_count = 0
        event_count = 0
        try:
            manifest = self._load_current()
            capability_count = len(manifest)
            checks["manifest_shape"] = isinstance(manifest, list) and all(
                isinstance(item, dict)
                and "capability_id" in item
                and item.get("state") in STATES
                for item in manifest
            )
        except (OSError, ValueError, json.JSONDecodeError):
            checks["manifest_shape"] = False

        try:
            with self.events_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        json.loads(line)
                        event_count += 1
            checks["event_log_parse"] = True
        except (OSError, json.JSONDecodeError):
            checks["event_log_parse"] = False

        healthy = all(checks.values())
        return {
            "status": "HEALTHY" if healthy else "DEGRADED",
            "home": str(self.home),
            "checks": checks,
            "capability_count": capability_count,
            "event_count": event_count,
        }


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kai governed capability registry")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register one scanned capability candidate")
    register.add_argument("--home", type=Path, required=True)
    register.add_argument("--candidate", type=Path, required=True)

    transition = subparsers.add_parser("transition", help="Move a capability through a governed state")
    transition.add_argument("--home", type=Path, required=True)
    transition.add_argument("--capability-id", required=True)
    transition.add_argument("--state", required=True)
    transition.add_argument("--evidence", type=Path, required=True)

    manifest = subparsers.add_parser("manifest", help="Print deterministic current capability manifest")
    manifest.add_argument("--home", type=Path, required=True)

    doctor = subparsers.add_parser("doctor", help="Check registry integrity")
    doctor.add_argument("--home", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)
    registry = CapabilityRegistry(args.home)

    if args.command == "register":
        print_json(registry.register(load_json_object(args.candidate)))
        return 0

    if args.command == "transition":
        print_json(registry.transition(
            args.capability_id,
            args.state,
            load_json_object(args.evidence),
        ))
        return 0

    if args.command == "manifest":
        print_json(registry.current_manifest())
        return 0

    if args.command == "doctor":
        diagnosis = registry.doctor()
        print_json(diagnosis)
        return 0 if diagnosis["status"] == "HEALTHY" else 2

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
