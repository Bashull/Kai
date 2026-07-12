from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any
import hashlib
import json
import re
import sqlite3


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source_kind: str
    source_uri: str
    logical_path: str
    filename: str
    size_bytes: int | None = None
    sha256: str | None = None
    physical_path: str | None = None
    extension: str | None = None
    modified_at: str | None = None
    created_at: str | None = None
    git_repository: str | None = None
    git_commit: str | None = None
    git_branch: str | None = None
    mime_type: str | None = None
    sensitivity: str = "UNKNOWN"
    availability: str = "AVAILABLE"
    extraction_state: str = "METADATA_ONLY"
    canonical_status: str = "UNKNOWN"
    provenance: dict[str, Any] = field(default_factory=dict)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    record_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_record_id(record: SourceRecord) -> str:
    identity = {
        "source_id": record.source_id,
        "source_kind": record.source_kind,
        "source_uri": record.source_uri,
        "logical_path": record.logical_path,
        "sha256": record.sha256,
    }
    encoded = json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "src_" + hashlib.sha256(encoded).hexdigest()[:32]


def _validate_sha256(value: str | None) -> None:
    if value is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError("sha256 must be 64 hexadecimal characters")


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
  record_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_uri TEXT NOT NULL,
  physical_path TEXT,
  logical_path TEXT NOT NULL,
  filename TEXT NOT NULL,
  extension TEXT,
  size_bytes INTEGER,
  modified_at TEXT,
  created_at TEXT,
  sha256 TEXT,
  git_repository TEXT,
  git_commit TEXT,
  git_branch TEXT,
  mime_type TEXT,
  sensitivity TEXT NOT NULL,
  availability TEXT NOT NULL,
  extraction_state TEXT NOT NULL,
  canonical_status TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  relationships_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_source_id ON records(source_id);
CREATE INDEX IF NOT EXISTS idx_records_source_kind ON records(source_kind);
CREATE INDEX IF NOT EXISTS idx_records_filename ON records(filename);
CREATE INDEX IF NOT EXISTS idx_records_sha256 ON records(sha256);
"""


class FederationLedger:
    def __init__(self, home: Path):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.database_path = self.home / "federation.sqlite3"
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.database_path)
        con.row_factory = sqlite3.Row
        return con

    def _init_schema(self) -> None:
        con = self._connect()
        try:
            con.executescript(SCHEMA)
            con.commit()
        finally:
            con.close()

    def upsert_record(self, record: SourceRecord) -> SourceRecord:
        _validate_sha256(record.sha256)
        normalized = record if record.record_id else replace(record, record_id=_stable_record_id(record))
        values = normalized.to_dict()
        values["provenance_json"] = json.dumps(normalized.provenance, ensure_ascii=False, sort_keys=True)
        values["relationships_json"] = json.dumps(normalized.relationships, ensure_ascii=False, sort_keys=True)
        columns = [
            "record_id", "source_id", "source_kind", "source_uri", "physical_path",
            "logical_path", "filename", "extension", "size_bytes", "modified_at",
            "created_at", "sha256", "git_repository", "git_commit", "git_branch",
            "mime_type", "sensitivity", "availability", "extraction_state",
            "canonical_status", "provenance_json", "relationships_json",
        ]
        payload = {key: values.get(key) for key in columns}
        placeholders = ",".join("?" for _ in columns)
        updates = ",".join(f"{column}=excluded.{column}" for column in columns if column != "record_id")
        sql = (
            f"INSERT INTO records({','.join(columns)}) VALUES({placeholders}) "
            f"ON CONFLICT(record_id) DO UPDATE SET {updates}"
        )
        con = self._connect()
        try:
            with con:
                con.execute(sql, [payload[column] for column in columns])
        finally:
            con.close()
        return normalized

    def upsert_many(self, records: list[SourceRecord]) -> list[SourceRecord]:
        if not records:
            return []
        columns = [
            "record_id", "source_id", "source_kind", "source_uri", "physical_path",
            "logical_path", "filename", "extension", "size_bytes", "modified_at",
            "created_at", "sha256", "git_repository", "git_commit", "git_branch",
            "mime_type", "sensitivity", "availability", "extraction_state",
            "canonical_status", "provenance_json", "relationships_json",
        ]
        normalized_records: list[SourceRecord] = []
        rows: list[list[Any]] = []
        for record in records:
            _validate_sha256(record.sha256)
            normalized = record if record.record_id else replace(record, record_id=_stable_record_id(record))
            values = normalized.to_dict()
            values["provenance_json"] = json.dumps(normalized.provenance, ensure_ascii=False, sort_keys=True)
            values["relationships_json"] = json.dumps(normalized.relationships, ensure_ascii=False, sort_keys=True)
            normalized_records.append(normalized)
            rows.append([values.get(column) for column in columns])

        placeholders = ",".join("?" for _ in columns)
        updates = ",".join(f"{column}=excluded.{column}" for column in columns if column != "record_id")
        sql = (
            f"INSERT INTO records({','.join(columns)}) VALUES({placeholders}) "
            f"ON CONFLICT(record_id) DO UPDATE SET {updates}"
        )
        con = self._connect()
        try:
            with con:
                con.executemany(sql, rows)
        finally:
            con.close()
        return normalized_records

    def get_record(self, record_id: str) -> SourceRecord:
        con = self._connect()
        try:
            row = con.execute("SELECT * FROM records WHERE record_id = ?", (record_id,)).fetchone()
        finally:
            con.close()
        if row is None:
            raise KeyError(record_id)
        return self._from_row(row)

    def query(
        self,
        *,
        source_id: str | None = None,
        source_kind: str | None = None,
        name_contains: str | None = None,
        sha256: str | None = None,
        limit: int = 1000,
    ) -> list[SourceRecord]:
        if limit < 1 or limit > 100000:
            raise ValueError("limit must be between 1 and 100000")
        clauses: list[str] = []
        params: list[Any] = []
        if source_id:
            clauses.append("source_id = ?")
            params.append(source_id)
        if source_kind:
            clauses.append("source_kind = ?")
            params.append(source_kind)
        if name_contains:
            clauses.append("LOWER(filename) LIKE ?")
            params.append("%" + name_contains.lower() + "%")
        if sha256:
            _validate_sha256(sha256)
            clauses.append("LOWER(sha256) = ?")
            params.append(sha256.lower())
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT * FROM records" + where + " ORDER BY source_id, logical_path, record_id LIMIT ?",
                params,
            ).fetchall()
        finally:
            con.close()
        return [self._from_row(row) for row in rows]

    def count_records(self) -> int:
        con = self._connect()
        try:
            return int(con.execute("SELECT COUNT(*) FROM records").fetchone()[0])
        finally:
            con.close()

    def source_summary(self) -> dict[str, int]:
        con = self._connect()
        try:
            rows = con.execute(
                "SELECT source_kind, COUNT(*) AS count FROM records GROUP BY source_kind ORDER BY source_kind"
            ).fetchall()
        finally:
            con.close()
        return {str(row["source_kind"]): int(row["count"]) for row in rows}

    def doctor(self) -> dict[str, Any]:
        checks: dict[str, bool] = {
            "database": self.database_path.is_file(),
            "schema": False,
        }
        record_count = 0
        con = self._connect()
        try:
            names = {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            checks["schema"] = "records" in names
            if checks["schema"]:
                record_count = int(con.execute("SELECT COUNT(*) FROM records").fetchone()[0])
        finally:
            con.close()
        return {
            "status": "HEALTHY" if all(checks.values()) else "DEGRADED",
            "checks": checks,
            "records": record_count,
            "database": str(self.database_path),
        }

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SourceRecord:
        return SourceRecord(
            source_id=row["source_id"],
            source_kind=row["source_kind"],
            source_uri=row["source_uri"],
            logical_path=row["logical_path"],
            filename=row["filename"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            physical_path=row["physical_path"],
            extension=row["extension"],
            modified_at=row["modified_at"],
            created_at=row["created_at"],
            git_repository=row["git_repository"],
            git_commit=row["git_commit"],
            git_branch=row["git_branch"],
            mime_type=row["mime_type"],
            sensitivity=row["sensitivity"],
            availability=row["availability"],
            extraction_state=row["extraction_state"],
            canonical_status=row["canonical_status"],
            provenance=json.loads(row["provenance_json"]),
            relationships=json.loads(row["relationships_json"]),
            record_id=row["record_id"],
        )
