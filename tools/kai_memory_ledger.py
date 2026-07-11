from __future__ import annotations

import argparse
import hashlib
import json
import os
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

    @staticmethod
    def _format_list(values: Any) -> list[str]:
        if not isinstance(values, list):
            return []
        rendered: list[str] = []
        for value in values:
            if isinstance(value, dict):
                path = str(value.get("path", "")).strip()
                digest = str(value.get("sha256", "")).strip()
                label = path or json.dumps(value, ensure_ascii=False, sort_keys=True)
                if digest:
                    label += f" [sha256={digest}]"
                rendered.append(label)
            else:
                text = str(value).strip()
                if text:
                    rendered.append(text)
        return rendered

    def _format_session_content(self, summary: dict[str, Any]) -> str:
        lines = [f"Objective: {summary['objective']}"]
        sections = (
            ("Actions", "actions"),
            ("Artifacts", "artifacts"),
            ("Decisions", "decisions"),
            ("Improvements", "improvements"),
            ("Pending", "pending"),
        )
        for heading, key in sections:
            values = self._format_list(summary.get(key, []))
            if values:
                lines.append(f"{heading}:")
                lines.extend(f"- {value}" for value in values)
        next_step = str(summary.get("next_step", "")).strip()
        if next_step:
            lines.append(f"Next step: {next_step}")
        return "\n".join(lines)

    def close_session(self, summary: dict[str, Any]) -> dict[str, str]:
        safe_summary = redact_value(summary)
        if not isinstance(safe_summary, dict):
            raise TypeError("session summary must be a dictionary")
        objective = str(safe_summary.get("objective", "")).strip()
        if not objective:
            raise ValueError("session objective is required")

        raw_session_id = str(safe_summary.get("session_id", "")).strip()
        if not raw_session_id:
            seed = objective + "|" + utc_now()
            raw_session_id = "session-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        session_id = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_session_id).strip("-._")
        if not session_id:
            raise ValueError("session_id has no safe characters")

        captured_at = str(safe_summary.get("captured_at", "")).strip() or utc_now()
        payload = dict(safe_summary)
        payload["session_id"] = session_id
        payload["captured_at"] = captured_at
        payload.setdefault("scope", "project:kai")
        payload.setdefault("actions", [])
        payload.setdefault("artifacts", [])
        payload.setdefault("decisions", [])
        payload.setdefault("improvements", [])
        payload.setdefault("pending", [])
        payload.setdefault("next_step", "")

        session_file = self.sessions_dir / f"{session_id}.json"
        serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        try:
            with session_file.open("x", encoding="utf-8") as handle:
                handle.write(serialized)
        except FileExistsError:
            existing = session_file.read_text(encoding="utf-8")
            if existing != serialized:
                raise FileExistsError(f"session already exists with different content: {session_id}")

        memory_result = self.add_memory({
            "kind": "SESSION",
            "scope": str(payload.get("scope", "project:kai")),
            "title": objective,
            "content": self._format_session_content(payload),
            "priority": 85,
            "confidence": "EVIDENCED",
            "tags": ["session", "continuity", session_id],
            "provenance": [{"source_type": "SESSION_FILE", "source": str(session_file)}],
        })
        self._append_event(
            "SESSION_CLOSED",
            memory_result["memory_id"],
            {"session_id": session_id, "session_file": str(session_file)},
        )
        return {
            "session_id": session_id,
            "session_file": str(session_file),
            "memory_id": memory_result["memory_id"],
            "decision": memory_result["decision"],
        }

    def _boot_records(self, project: str | None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM memories WHERE status = 'ACTIVE'"
        params: list[Any] = []
        if project:
            project_scope = f"project:{project}"
            sql += " AND (scope = 'global' OR scope = ? OR scope LIKE ?)"
            params.extend([project_scope, project_scope + ":%"])
        sql += " ORDER BY priority DESC, updated_at DESC, memory_id ASC"
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _boot_section(kind: str) -> str:
        mapping = {
            "CORE_IDENTITY": "Identity and directives",
            "PREFERENCE": "Collaboration preferences",
            "PROJECT_STATE": "Current project state",
            "DECISION": "Validated decisions",
            "ACTION": "Recent work",
            "SESSION": "Recent work",
            "ARTIFACT": "Artifacts and locations",
            "IMPROVEMENT": "Improvements and capabilities",
            "PENDING": "Pending work",
            "LESSON": "Lessons",
            "CONTEXT": "Additional context",
        }
        return mapping.get(kind, "Additional context")

    @staticmethod
    def _boot_item(record: dict[str, Any], content_limit: int | None = None) -> str:
        content = " ".join(str(record["content"]).split())
        if content_limit is not None:
            if content_limit <= 0:
                content = ""
            elif len(content) > content_limit:
                content = content[: max(0, content_limit - 1)].rstrip() + "ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦"
        meta = f"{record['confidence']}; priority {record['priority']}"
        line = f"- **{record['title']}** [{meta}]"
        if content:
            line += f" ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â {content}"
        return line

    def _render_boot_markdown(
        self,
        records: list[dict[str, Any]],
        project: str | None,
        content_limit: int | None = None,
    ) -> str:
        project_label = project or "all"
        lines = [
            "# Kai Long-Term Memory Boot Packet",
            "",
            f"Project: {project_label}",
            "",
            "Use this packet as durable external context. Verify exact paths, versions and claims against provenance when precision matters.",
        ]
        section_order = (
            "Identity and directives",
            "Collaboration preferences",
            "Current project state",
            "Validated decisions",
            "Recent work",
            "Artifacts and locations",
            "Improvements and capabilities",
            "Pending work",
            "Lessons",
            "Additional context",
        )
        grouped: dict[str, list[dict[str, Any]]] = {section: [] for section in section_order}
        for record in records:
            grouped[self._boot_section(record["kind"])].append(record)

        for section in section_order:
            items = grouped[section]
            if not items:
                continue
            lines.extend(["", f"## {section}", ""])
            lines.extend(self._boot_item(record, content_limit) for record in items)

        return "\n".join(lines).rstrip() + "\n"

    def build_boot_packet(
        self,
        max_chars: int = 12000,
        project: str | None = None,
    ) -> dict[str, Any]:
        if max_chars < 256:
            raise ValueError("max_chars must be at least 256")

        records = self._boot_records(project)
        critical_kinds = {"CORE_IDENTITY", "PENDING"}
        critical = [record for record in records if record["kind"] in critical_kinds]
        optional = [record for record in records if record["kind"] not in critical_kinds]

        selected = list(critical)
        markdown = self._render_boot_markdown(selected, project)
        if len(markdown) > max_chars:
            for limit in (240, 160, 100, 60, 30, 0):
                markdown = self._render_boot_markdown(selected, project, content_limit=limit)
                if len(markdown) <= max_chars:
                    break
        if len(markdown) > max_chars:
            raise ValueError("critical memory titles exceed boot packet budget")

        for record in optional:
            candidate = selected + [record]
            candidate_markdown = self._render_boot_markdown(candidate, project)
            if len(candidate_markdown) <= max_chars:
                selected = candidate
                markdown = candidate_markdown

        selected_ids = [record["memory_id"] for record in selected]
        return {
            "schema_version": 1,
            "generated_at": utc_now(),
            "project": project,
            "max_chars": max_chars,
            "selected_ids": selected_ids,
            "health": {
                "active_total": len(records),
                "selected": len(selected),
                "omitted": len(records) - len(selected),
            },
            "markdown": markdown,
        }

    def write_boot_packet(
        self,
        max_chars: int = 12000,
        project: str | None = None,
    ) -> tuple[Path, Path]:
        packet = self.build_boot_packet(max_chars=max_chars, project=project)
        markdown_path = self.home / "boot_packet.md"
        json_path = self.home / "boot_packet.json"
        markdown_tmp = markdown_path.with_suffix(".md.tmp")
        json_tmp = json_path.with_suffix(".json.tmp")
        markdown_tmp.write_text(packet["markdown"], encoding="utf-8")
        json_tmp.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        markdown_tmp.replace(markdown_path)
        json_tmp.replace(json_path)
        self._append_event(
            "BOOT_PACKET_WRITTEN",
            "boot_packet",
            {"markdown_path": str(markdown_path), "json_path": str(json_path)},
        )
        return markdown_path, json_path
    def doctor(self) -> dict[str, Any]:
        expected_columns = {
            "memory_id", "created_at", "updated_at", "kind", "scope", "title",
            "content", "status", "priority", "confidence", "tags_json",
            "provenance_json", "supersedes_json",
        }
        checks = {
            "database": self.db_path.is_file(),
            "events_log": self.events_path.is_file(),
            "sessions_directory": self.sessions_dir.is_dir(),
            "boot_packet_markdown": (self.home / "boot_packet.md").is_file(),
            "boot_packet_json": (self.home / "boot_packet.json").is_file(),
        }
        try:
            with self._connect() as conn:
                rows = conn.execute("PRAGMA table_info(memories)").fetchall()
                columns = {str(row[1]) for row in rows}
                memory_count = int(conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
            checks["schema"] = expected_columns.issubset(columns)
        except sqlite3.Error:
            checks["schema"] = False
            memory_count = 0

        healthy = all(checks.values())
        return {
            "status": "HEALTHY" if healthy else "DEGRADED",
            "home": str(self.home),
            "checks": checks,
            "memory_count": memory_count,
        }

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


def default_memory_home() -> Path:
    configured = os.environ.get("KAI_MEMORY_HOME", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".kai_memory"


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def add_home_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--home", type=Path, default=None)


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kai durable long-term memory ledger")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize memory storage")
    add_home_argument(init_parser)

    remember = subparsers.add_parser("remember", help="Store a durable memory")
    add_home_argument(remember)
    remember.add_argument("--json-file", type=Path)
    remember.add_argument("--kind", default="CONTEXT")
    remember.add_argument("--scope", default="global")
    remember.add_argument("--title")
    remember.add_argument("--content")
    remember.add_argument("--priority", type=int, default=50)
    remember.add_argument("--confidence", default="UNKNOWN")
    remember.add_argument("--tag", action="append", default=[])
    remember.add_argument("--source", action="append", default=[])

    search = subparsers.add_parser("search", help="Search active memories")
    add_home_argument(search)
    search.add_argument("--query", default="")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--scope")

    boot = subparsers.add_parser("boot", help="Generate Markdown and JSON boot packets")
    add_home_argument(boot)
    boot.add_argument("--project")
    boot.add_argument("--max-chars", type=int, default=12000)

    session_close = subparsers.add_parser("session-close", help="Record a completed work session")
    add_home_argument(session_close)
    session_close.add_argument("--json-file", type=Path, required=True)

    doctor = subparsers.add_parser("doctor", help="Check memory storage health")
    add_home_argument(doctor)

    export = subparsers.add_parser("export", help="Export canonical memories as deterministic JSON")
    add_home_argument(export)
    export.add_argument("--out", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)
    home = (args.home or default_memory_home()).expanduser()
    ledger = MemoryLedger(home)

    if args.command == "init":
        print_json({"status": "initialized", "home": str(ledger.home)})
        return 0

    if args.command == "remember":
        if args.json_file:
            record = load_json_object(args.json_file)
        else:
            if not args.title or not args.content:
                parser.error("remember requires --json-file or both --title and --content")
            record = {
                "kind": args.kind,
                "scope": args.scope,
                "title": args.title,
                "content": args.content,
                "priority": args.priority,
                "confidence": args.confidence,
                "tags": args.tag,
                "provenance": [
                    {"source_type": "CLI", "source": source}
                    for source in args.source
                ],
            }
        print_json(ledger.add_memory(record))
        return 0

    if args.command == "search":
        print_json(ledger.search(args.query, limit=args.limit, scope=args.scope))
        return 0

    if args.command == "session-close":
        print_json(ledger.close_session(load_json_object(args.json_file)))
        return 0

    if args.command == "boot":
        markdown_path, json_path = ledger.write_boot_packet(
            max_chars=args.max_chars,
            project=args.project,
        )
        packet = json.loads(json_path.read_text(encoding="utf-8"))
        print_json({
            "markdown_path": str(markdown_path),
            "json_path": str(json_path),
            "health": packet["health"],
            "selected_ids": packet["selected_ids"],
        })
        return 0

    if args.command == "doctor":
        diagnosis = ledger.doctor()
        print_json(diagnosis)
        return 0 if diagnosis["status"] == "HEALTHY" else 2

    if args.command == "export":
        exported = ledger.export_json()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(exported + "\n", encoding="utf-8")
            print_json({"out": str(args.out.resolve())})
        else:
            print(exported)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
