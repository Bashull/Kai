from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_CONFIDENCE = {"EXPLICIT", "EVIDENCED", "INFERRED", "UNKNOWN"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MemoryLedger:
    def __init__(self, home: Path):
        self.home = Path(home).expanduser().resolve()
        self.db_path = self.home / "memory.sqlite3"
        self.events_path = self.home / "events.jsonl"
        self.sessions_dir = self.home / "sessions"
        self.init_storage()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def init_storage(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.events_path.touch(exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    confidence TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    supersedes_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        safe_record = redact_value(record)
        title = str(safe_record.get("title", "")).strip()
        content = str(safe_record.get("content", "")).strip()
        if not title:
            raise ValueError("title is required")
        if not content:
            raise ValueError("content is required")

        confidence = str(safe_record.get("confidence", "UNKNOWN")).upper()
        if confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"invalid confidence: {confidence}")

        priority = int(safe_record.get("priority", 50))
        if not 0 <= priority <= 100:
            raise ValueError("priority must be between 0 and 100")

        tags = sorted({str(tag).strip().lower() for tag in safe_record.get("tags", []) if str(tag).strip()})
        provenance = list(safe_record.get("provenance", []))
        supersedes = sorted({str(item) for item in safe_record.get("supersedes", []) if str(item)})

        return {
            "kind": str(safe_record.get("kind", "CONTEXT")).upper(),
            "scope": str(safe_record.get("scope", "global")).strip() or "global",
            "title": title,
            "content": content,
            "status": str(safe_record.get("status", "ACTIVE")).upper(),
            "priority": priority,
            "confidence": confidence,
            "tags": tags,
            "provenance": provenance,
            "supersedes": supersedes,
        }

    def _stable_memory_id(self, record: dict[str, Any]) -> str:
        identity = {
            "kind": record["kind"],
            "scope": record["scope"],
            "title": record["title"],
            "content": record["content"],
            "tags": record["tags"],
            "provenance": record["provenance"],
        }
        payload = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "mem_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def _exists(self, memory_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
        return row is not None

    def _append_event(self, event_type: str, memory_id: str, data: dict[str, Any]) -> None:
        event = {
            "timestamp": utc_now(),
            "event_type": event_type,
            "memory_id": memory_id,
            "data": data,
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def _insert(self, memory_id: str, record: dict[str, Any]) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    memory_id, created_at, updated_at, kind, scope, title, content,
                    status, priority, confidence, tags_json, provenance_json, supersedes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    now,
                    now,
                    record["kind"],
                    record["scope"],
                    record["title"],
                    record["content"],
                    record["status"],
                    record["priority"],
                    record["confidence"],
                    json.dumps(record["tags"], ensure_ascii=False, sort_keys=True),
                    json.dumps(record["provenance"], ensure_ascii=False, sort_keys=True),
                    json.dumps(record["supersedes"], ensure_ascii=False, sort_keys=True),
                ),
            )
            conn.commit()

    def add_memory(self, record: dict[str, Any]) -> dict[str, str]:
        normalized = self._normalize_record(record)
        memory_id = self._stable_memory_id(normalized)
        if self._exists(memory_id):
            return {"decision": "SKIP_EXACT_DUPLICATE", "memory_id": memory_id}
        self._insert(memory_id, normalized)
        self._append_event("MEMORY_INSERTED", memory_id, normalized)
        return {"decision": "INSERTED", "memory_id": memory_id}

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "memory_id": row["memory_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "kind": row["kind"],
            "scope": row["scope"],
            "title": row["title"],
            "content": row["content"],
            "status": row["status"],
            "priority": row["priority"],
            "confidence": row["confidence"],
            "tags": json.loads(row["tags_json"]),
            "provenance": json.loads(row["provenance_json"]),
            "supersedes": json.loads(row["supersedes_json"]),
        }

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def search(self, query: str, limit: int = 20, scope: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM memories WHERE status = 'ACTIVE'"
        params: list[Any] = []
        if scope:
            sql += " AND scope = ?"
            params.append(scope)
        if query.strip():
            sql += " AND (title LIKE ? COLLATE NOCASE OR content LIKE ? COLLATE NOCASE OR tags_json LIKE ? COLLATE NOCASE)"
            needle = f"%{query.strip()}%"
            params.extend([needle, needle, needle])
        sql += " ORDER BY priority DESC, updated_at DESC, memory_id ASC LIMIT ?"
        params.append(max(1, int(limit)))

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]


    def export_json(self) -> str:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY memory_id ASC"
            ).fetchall()
        records = [self._row_to_record(row) for row in rows]
        return json.dumps(
            records,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


    def supersede(self, old_id: str, new_id: str) -> None:
        if old_id == new_id:
            raise ValueError("a memory cannot supersede itself")
        old_record = self.get_memory(old_id)
        new_record = self.get_memory(new_id)
        if old_record is None:
            raise KeyError(f"unknown memory: {old_id}")
        if new_record is None:
            raise KeyError(f"unknown memory: {new_id}")

        now = utc_now()
        supersedes = sorted(set(new_record["supersedes"] + [old_id]))
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET status = 'SUPERSEDED', updated_at = ? WHERE memory_id = ?",
                (now, old_id),
            )
            conn.execute(
                "UPDATE memories SET supersedes_json = ?, updated_at = ? WHERE memory_id = ?",
                (json.dumps(supersedes, ensure_ascii=False, sort_keys=True), now, new_id),
            )
            conn.commit()
        self._append_event("MEMORY_SUPERSEDED", old_id, {"superseded_by": new_id})

SENSITIVE_PATTERNS = (
    ("OPENAI_KEY", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
)


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    redacted = text
    labels: list[str] = []
    for label, pattern in SENSITIVE_PATTERNS:
        if pattern.search(redacted):
            labels.append(label)
            redacted = pattern.sub(f"[REDACTED:{label}]", redacted)
    return redacted, labels


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive(value)[0]
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    if isinstance(value, dict):
        return {str(key): redact_value(item) for key, item in value.items()}
    return value
