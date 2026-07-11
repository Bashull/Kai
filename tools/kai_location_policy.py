from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DRIVE_ROUTE_GROUPS = {
    "core": "00_KAI_CORE",
    "directive": "00_KAI_CORE",
    "bootstrap": "00_KAI_CORE",
    "memory-index": "00_KAI_CORE",
    "brain-core": "00_KAI_CORE",
    "audit": "10_KAI_LAB_INGESTION_FORENSICS",
    "forensic": "10_KAI_LAB_INGESTION_FORENSICS",
    "extraction": "10_KAI_LAB_INGESTION_FORENSICS",
    "candidate": "10_KAI_LAB_INGESTION_FORENSICS",
    "test-evidence": "10_KAI_LAB_INGESTION_FORENSICS",
    "migration-log": "10_KAI_LAB_INGESTION_FORENSICS",
    "project": "20_PROJECTS",
    "ai-workspace": "30_AI_WORKSPACES",
    "reference": "40_LIBRARY_REFERENCE",
    "research": "40_LIBRARY_REFERENCE",
    "library": "40_LIBRARY_REFERENCE",
    "unknown": "80_INBOX_UNCLASSIFIED",
    "snapshot": "90_ARCHIVE_HISTORICAL",
    "historical": "90_ARCHIVE_HISTORICAL",
    "superseded": "90_ARCHIVE_HISTORICAL",
    "secret": "99_PRIVATE_SENSITIVE",
    "personal": "99_PRIVATE_SENSITIVE",
    "financial": "99_PRIVATE_SENSITIVE",
    "legal": "99_PRIVATE_SENSITIVE",
    "sensitive": "99_PRIVATE_SENSITIVE",
}


class PlacementPolicy:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.schema_version = int(data.get("schema_version", 1))
        self.local = dict(data.get("local", {}))
        self.drive = dict(data.get("drive", {}))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlacementPolicy":
        if not isinstance(data, dict):
            raise TypeError("location policy must be a dictionary")
        if not isinstance(data.get("local"), dict):
            raise ValueError("location policy requires local roots")
        if not isinstance(data.get("drive"), dict):
            raise ValueError("location policy requires drive zones")
        return cls(data)

    @classmethod
    def from_json(cls, path: Path) -> "PlacementPolicy":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def _local_root(self, key: str) -> Path:
        value = str(self.local.get(key, "")).strip()
        if not value:
            raise ValueError(f"missing local root: {key}")
        return Path(value)

    def route(self, artifact_kind: str) -> dict[str, Any]:
        kind = str(artifact_kind).strip().lower()
        if kind == "skill":
            repo_root = self._local_root("repo_root")
            bridge_root = self._local_root("bridge_root")
            return {
                "kind": "skill",
                "state": "CANDIDATE_UNTIL_VALIDATED",
                "local_source_root": str(repo_root / "skills"),
                "local_runtime_root": str(bridge_root / "skills"),
                "drive_evidence_zone": "10_KAI_LAB_INGESTION_FORENSICS",
                "drive_canonical_zone": "00_KAI_CORE",
            }
        if kind == "tool":
            repo_root = self._local_root("repo_root")
            bridge_root = self._local_root("bridge_root")
            return {
                "kind": "tool",
                "state": "CANDIDATE_UNTIL_VALIDATED",
                "local_source_root": str(repo_root / "tools"),
                "local_runtime_root": str(bridge_root / "agent_tools"),
                "drive_evidence_zone": "10_KAI_LAB_INGESTION_FORENSICS",
                "drive_canonical_zone": "00_KAI_CORE",
            }

        zone = DRIVE_ROUTE_GROUPS.get(kind, "80_INBOX_UNCLASSIFIED")
        return {
            "kind": kind or "unknown",
            "state": "ROUTED",
            "drive_zone": zone,
            "drive_id": self.drive_zone(zone).get("id"),
        }

    def drive_zone(self, zone_name: str) -> dict[str, Any]:
        zone = self.drive.get(zone_name)
        if not isinstance(zone, dict):
            raise KeyError(zone_name)
        return dict(zone)

    def location_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "local": {key: self.local[key] for key in sorted(self.local)},
            "drive": {
                key: self.drive[key]
                for key in sorted(self.drive)
            },
            "routes": {
                key: DRIVE_ROUTE_GROUPS[key]
                for key in sorted(DRIVE_ROUTE_GROUPS)
            },
        }
