from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import subprocess

try:
    from tools.kai_source_federation import SourceRecord
except ModuleNotFoundError:
    import sys
    local_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(local_dir))
    from kai_source_federation import SourceRecord


SECRET_FIELD_NAMES = {
    "api_key",
    "access_token",
    "refresh_token",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
}


@dataclass(frozen=True)
class AdapterResult:
    status: str
    records: list[SourceRecord]
    warnings: list[str]
    observed_count: int
    truncated: bool = False
    next_cursor: str | None = None


class SourceRegistry:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    @classmethod
    def from_json(cls, path: Path) -> "SourceRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
            raise ValueError("source registry requires a sources list")
        return cls(data)

    def enabled(self) -> list[dict[str, Any]]:
        items = [item for item in self.payload.get("sources", []) if item.get("enabled", True)]
        return sorted(items, key=lambda item: str(item.get("source_id", "")))


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).strip().lower() in SECRET_FIELD_NAMES:
                return True
            if _contains_secret_field(child):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_field(item) for item in value)
    return False


class LocalGitAdapter:
    def __init__(self, source_id: str, roots: list[Path], timeout_seconds: int = 10):
        self.source_id = source_id
        self.roots = [Path(root).resolve() for root in roots]
        self.timeout_seconds = timeout_seconds

    def _git(self, repo: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            shell=False,
        )
        return completed.stdout.strip()

    def _origin(self, repo: Path) -> str | None:
        try:
            return self._git(repo, "remote", "get-url", "origin") or None
        except subprocess.CalledProcessError:
            return None

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        offset = int(cursor or "0")
        roots = sorted(self.roots, key=lambda item: str(item).lower())
        selected = roots[offset: offset + max_items + 1]
        truncated = len(selected) > max_items
        selected = selected[:max_items]
        records: list[SourceRecord] = []
        warnings: list[str] = []
        for repo in selected:
            try:
                commit = self._git(repo, "rev-parse", "HEAD")
                branch = self._git(repo, "branch", "--show-current") or "DETACHED"
                remote = self._origin(repo)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                warnings.append(f"{repo}: {type(exc).__name__}")
                continue
            records.append(SourceRecord(
                source_id=self.source_id,
                source_kind="GIT_LOCAL",
                source_uri=repo.as_uri(),
                physical_path=str(repo),
                logical_path=repo.name,
                filename=repo.name,
                git_repository=remote,
                git_commit=commit,
                git_branch=branch,
                extraction_state="REPOSITORY_METADATA",
                provenance={"adapter": "LocalGitAdapter"},
            ))
        next_cursor = str(offset + len(selected)) if truncated else None
        status = "HEALTHY" if not warnings else "DEGRADED"
        return AdapterResult(
            status=status,
            records=records,
            warnings=warnings,
            observed_count=offset + len(selected),
            truncated=truncated,
            next_cursor=next_cursor,
        )


class ConnectorSnapshotAdapter:
    def __init__(self, source_id: str, source_kind: str, snapshot_path: Path):
        self.source_id = source_id
        self.source_kind = source_kind
        self.snapshot_path = Path(snapshot_path)

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("connector snapshot requires an items list")
        if _contains_secret_field(payload):
            raise ValueError("connector snapshot contains secret field")
        items = payload["items"]
        offset = int(cursor or "0")
        page = items[offset: offset + max_items + 1]
        local_truncated = len(page) > max_items
        selected = page[:max_items]
        source_incomplete = (
            payload.get("complete") is False
            or bool(payload.get("next_page_token"))
            or bool(payload.get("truncated"))
        )
        records: list[SourceRecord] = []
        for item in selected:
            if not isinstance(item, dict):
                raise ValueError("connector snapshot item must be an object")
            name = str(item.get("name") or item.get("title") or item.get("external_id") or "unnamed")
            url = str(item.get("url") or item.get("web_url") or self.snapshot_path.as_uri())
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            records.append(SourceRecord(
                source_id=self.source_id,
                source_kind=self.source_kind,
                source_uri=url,
                logical_path=name,
                filename=name,
                size_bytes=int(item["size_bytes"]) if item.get("size_bytes") is not None else None,
                extraction_state="CONNECTOR_METADATA",
                provenance={
                    "adapter": "ConnectorSnapshotAdapter",
                    "snapshot_path": str(self.snapshot_path),
                    "external_id": str(item.get("external_id")) if item.get("external_id") is not None else None,
                    "metadata": metadata,
                },
            ))
        next_cursor = str(offset + len(selected)) if local_truncated else None
        truncated = local_truncated or source_incomplete
        warnings = ["SOURCE_SNAPSHOT_INCOMPLETE"] if source_incomplete else []
        return AdapterResult(
            status="DEGRADED" if source_incomplete else "HEALTHY",
            records=records,
            warnings=warnings,
            observed_count=offset + len(selected),
            truncated=truncated,
            next_cursor=next_cursor,
        )


class BackupManifestAdapter:
    def __init__(self, source_id: str, manifest_path: Path):
        self.source_id = source_id
        self.manifest_path = Path(manifest_path)

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8-sig"))
        if payload.get("capability") != "backup-manifest":
            raise ValueError("expected backup-manifest document")
        entries = payload.get("entries")
        if not isinstance(entries, list):
            raise ValueError("backup-manifest requires entries list")
        offset = int(cursor or "0")
        page = entries[offset: offset + max_items + 1]
        truncated = len(page) > max_items
        selected = page[:max_items]
        records: list[SourceRecord] = []
        for entry in selected:
            root = str(entry["root"])
            relative = str(entry["relative_path"])
            digest = str(entry["sha256"]).lower()
            records.append(SourceRecord(
                source_id=self.source_id,
                source_kind="FILE_MANIFEST",
                source_uri=self.manifest_path.as_uri(),
                physical_path=str(Path(root) / Path(relative)),
                logical_path=relative,
                filename=Path(relative).name,
                extension=Path(relative).suffix.lower() or None,
                size_bytes=int(entry["size"]),
                modified_at=str(entry.get("mtime_ns")) if entry.get("mtime_ns") is not None else None,
                sha256=digest,
                extraction_state="HASHED_METADATA",
                provenance={
                    "adapter": "BackupManifestAdapter",
                    "manifest_capability": "backup-manifest",
                    "manifest_path": str(self.manifest_path),
                    "root": root,
                },
            ))
        next_cursor = str(offset + len(selected)) if truncated else None
        return AdapterResult("HEALTHY", records, [], offset + len(selected), truncated, next_cursor)


class FileIndexDatabaseAdapter:
    def __init__(self, source_id: str, db_path: Path):
        self.source_id = source_id
        self.db_path = Path(db_path)

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        import sqlite3
        offset = int(cursor or "0")
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT manifest_id, root, relative_path, name, ext, size, mtime_ns, sha256 "
                "FROM files ORDER BY root, relative_path, manifest_id LIMIT ? OFFSET ?",
                (max_items + 1, offset),
            ).fetchall()
        finally:
            con.close()
        truncated = len(rows) > max_items
        selected = rows[:max_items]
        records: list[SourceRecord] = []
        for row in selected:
            records.append(SourceRecord(
                source_id=self.source_id,
                source_kind="FILE_INDEX",
                source_uri=self.db_path.as_uri(),
                physical_path=str(Path(row["root"]) / Path(row["relative_path"])),
                logical_path=row["relative_path"],
                filename=row["name"],
                extension=row["ext"] or None,
                size_bytes=int(row["size"]),
                modified_at=str(row["mtime_ns"]),
                sha256=row["sha256"],
                extraction_state="HASHED_METADATA",
                provenance={
                    "adapter": "FileIndexDatabaseAdapter",
                    "manifest_id": row["manifest_id"],
                    "root": row["root"],
                },
            ))
        next_cursor = str(offset + len(selected)) if truncated else None
        return AdapterResult(
            "HEALTHY",
            records,
            [],
            offset + len(selected),
            truncated,
            next_cursor,
        )


class AdbTreeAdapter:
    def __init__(
        self,
        source_id: str,
        adb_executable: Path,
        serial: str,
        remote_root: str,
        timeout_seconds: int = 60,
    ):
        self.source_id = source_id
        self.adb_executable = Path(adb_executable)
        self.serial = serial
        self.remote_root = remote_root.rstrip("/") or "/"
        self.timeout_seconds = timeout_seconds

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        if cursor is not None:
            raise ValueError("cursor is not supported for direct ADB probes")
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        command = [
            str(self.adb_executable),
            "-s",
            self.serial,
            "shell",
            "find",
            self.remote_root,
            "-type",
            "f",
            "-print",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )
        lines: list[str] = []
        try:
            if process.stdout is None:
                process.kill()
                process.wait()
                return AdapterResult("DEGRADED", [], ["ADB_STDOUT_UNAVAILABLE"], 0)
            for raw in process.stdout:
                value = raw.strip()
                if value:
                    lines.append(value)
                if len(lines) > max_items:
                    process.terminate()
                    break
            process.wait(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return AdapterResult("DEGRADED", [], ["ADB_TIMEOUT"], 0)

        truncated = len(lines) > max_items
        selected = lines[:max_items]
        records: list[SourceRecord] = []
        for remote_path in selected:
            relative = remote_path.removeprefix(self.remote_root).lstrip("/")
            records.append(SourceRecord(
                source_id=self.source_id,
                source_kind="S24_ADB",
                source_uri=f"adb://{self.serial}{remote_path}",
                physical_path=remote_path,
                logical_path=relative or Path(remote_path).name,
                filename=Path(remote_path).name,
                extension=Path(remote_path).suffix.lower() or None,
                extraction_state="PATH_ONLY",
                provenance={
                    "adapter": "AdbTreeAdapter",
                    "serial": self.serial,
                    "remote_root": self.remote_root,
                },
            ))
        return AdapterResult(
            status="HEALTHY",
            records=records,
            warnings=[],
            observed_count=len(lines),
            truncated=truncated,
            next_cursor=None,
        )
