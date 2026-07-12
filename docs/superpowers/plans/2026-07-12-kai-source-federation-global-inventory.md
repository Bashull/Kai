# KAI Source Federation + Global Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one governed inventory layer that normalizes source evidence from PC, local Git repositories, GitHub snapshots, Drive snapshots, S24/ADB and future adapters without destroying provenance or duplicating existing promoted capabilities.

**Architecture:** A SQLite-backed federation ledger stores normalized source records. Source adapters emit deterministic records into the ledger. Existing promoted capabilities such as backup-manifest, file-indexer, project-extractor, storage-commander and termux-bridge-planner remain authoritative for their own scopes and are composed rather than reimplemented. KAI Control Plane gains read-only commands for source status, ingestion and global inventory queries.

**Tech Stack:** Python 3 standard library (`sqlite3`, `json`, `hashlib`, `pathlib`, `subprocess`, `dataclasses`, `typing`), existing KAI Control Plane, existing capability registry, unittest.

## Global Constraints

- Core implementation must remain free-first and require no paid infrastructure.
- Original sources are read-only by default.
- Exact duplicate status requires SHA-256 or byte-level proof.
- Secrets may be used by authorized runtimes but secret values must never appear in general inventory, memory, logs, evidence or reports.
- Missing data remains explicit `UNKNOWN` or null; never infer absent evidence as fact.
- Bounded scans only: every adapter receives scope and item limits.
- Existing promoted capabilities must be reused before creating replacements.
- `PROMOTED` does not imply `CANONICAL`.
- Every material change must leave tests, evidence and memory.

---
### Task 1: Normalized Source Record and SQLite Federation Ledger

**Files:**
- Create: `tools/kai_source_federation.py`
- Test: `tests/test_kai_source_federation.py`

**Interfaces:**
- Produces: `SourceRecord`, `FederationLedger`, `FederationLedger.upsert_record()`, `get_record()`, `query()`, `source_summary()`, `doctor()`.
- Consumes: only Python standard library.

- [ ] **Step 1: Write the failing record round-trip test**

```python
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
```
- [ ] **Step 2: Run the test and verify RED**

Run:
```powershell
python -m unittest tests.test_kai_source_federation.FederationLedgerTests.test_record_round_trip_preserves_provenance -v
```
Expected: `ModuleNotFoundError` for `tools.kai_source_federation`.

- [ ] **Step 3: Implement the normalized record and SQLite schema**

Create `tools/kai_source_federation.py` with:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import json
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
```
Add deterministic record IDs and SQLite-backed persistence:

```python
def _stable_record_id(record: SourceRecord) -> str:
    identity = {
        "source_id": record.source_id,
        "source_kind": record.source_kind,
        "source_uri": record.source_uri,
        "logical_path": record.logical_path,
        "sha256": record.sha256,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"src_{digest[:32]}"

class FederationLedger:
    def __init__(self, home: Path):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.database_path = self.home / "federation.sqlite3"
        self._init_schema()
```

The schema must use one `records` table with `record_id` as primary key and JSON text columns for `provenance` and `relationships`. Every connection must be explicitly closed.

- [ ] **Step 4: Add query, summary and doctor tests**

```python
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
```
- [ ] **Step 5: Run Task 1 tests and verify GREEN**

Run:
```powershell
python -m unittest tests.test_kai_source_federation -v
```
Expected: all Task 1 tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add tools/kai_source_federation.py tests/test_kai_source_federation.py
git commit -m "feat: add source federation ledger"
```

---
### Task 2: Source Registry, Git Adapter and Connector Snapshot Adapter

**Files:**
- Create: `tools/kai_source_adapters.py`
- Create: `config/kai_source_registry.json`
- Test: `tests/test_kai_source_adapters.py`

**Interfaces:**
- Consumes: `SourceRecord` from `tools.kai_source_federation`.
- Produces: `SourceRegistry`, `LocalGitAdapter`, `ConnectorSnapshotAdapter`, `AdapterResult`.

- [ ] **Step 1: Write RED tests for registry loading and Git repository metadata**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import unittest

from tools.kai_source_adapters import LocalGitAdapter, SourceRegistry

class SourceAdapterTests(unittest.TestCase):
    def test_registry_loads_enabled_sources(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps({"sources": [
                {"source_id": "pc:kai", "kind": "PC", "enabled": True, "uri": "file:///KAI"},
                {"source_id": "disabled", "kind": "PC", "enabled": False, "uri": "file:///none"},
            ]}), encoding="utf-8")
            registry = SourceRegistry.from_json(path)
            self.assertEqual([item["source_id"] for item in registry.enabled()], ["pc:kai"])
```
Add the Git adapter test:

```python
def test_local_git_adapter_emits_repository_record(self):
    with TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
        (repo / "README.md").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
        subprocess.run([
            "git", "-C", str(repo), "-c", "user.name=Test",
            "-c", "user.email=test@example.com", "commit", "-m", "init"
        ], check=True, capture_output=True)

        adapter = LocalGitAdapter(source_id="pc:repos", roots=[repo])
        result = adapter.collect(max_items=10)
        self.assertEqual(result.status, "HEALTHY")
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].git_branch, "main")
        self.assertTrue(result.records[0].git_commit)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:
```powershell
python -m unittest tests.test_kai_source_adapters.SourceAdapterTests -v
```
Expected: `ModuleNotFoundError` for `tools.kai_source_adapters`.
- [ ] **Step 3: Implement registry and adapter result types**

Create `tools/kai_source_adapters.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import subprocess

from tools.kai_source_federation import SourceRecord

@dataclass(frozen=True)
class AdapterResult:
    status: str
    records: list[SourceRecord]
    warnings: list[str]
    observed_count: int
    truncated: bool = False

class SourceRegistry:
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    @classmethod
    def from_json(cls, path: Path) -> "SourceRegistry":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def enabled(self) -> list[dict[str, Any]]:
        return [item for item in self.payload.get("sources", []) if item.get("enabled", True)]
```
Implement `LocalGitAdapter` with `shell=False` and explicit timeouts:

```python
class LocalGitAdapter:
    def __init__(self, source_id: str, roots: list[Path], timeout_seconds: int = 10):
        self.source_id = source_id
        self.roots = [Path(root) for root in roots]
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

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        records: list[SourceRecord] = []
        warnings: list[str] = []
        for repo in sorted(self.roots, key=lambda item: str(item).lower())[:max_items]:
            try:
                commit = self._git(repo, "rev-parse", "HEAD")
                branch = self._git(repo, "branch", "--show-current") or "DETACHED"
                remote = self._git(repo, "remote", "get-url", "origin") if self._has_origin(repo) else None
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
        return AdapterResult("HEALTHY" if not warnings else "DEGRADED", records, warnings, len(records))
```
- [ ] **Step 4: Add connector snapshot ingestion test**

```python
def test_connector_snapshot_adapter_preserves_external_ids(self):
    with TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / "github.json"
        snapshot.write_text(json.dumps({"items": [{
            "external_id": "1069592908",
            "name": "Kai",
            "url": "https://github.com/Bashull/Kai",
            "size_bytes": 55880,
            "metadata": {"default_branch": "main", "visibility": "public"},
        }]}), encoding="utf-8")
        adapter = ConnectorSnapshotAdapter(
            source_id="github:bashull",
            source_kind="GITHUB",
            snapshot_path=snapshot,
        )
        result = adapter.collect(max_items=100)
        self.assertEqual(result.records[0].provenance["external_id"], "1069592908")
        self.assertEqual(result.records[0].source_kind, "GITHUB")
```

Implement `ConnectorSnapshotAdapter` so it accepts only local JSON snapshots, never secret fields, and marks `truncated=True` when the source snapshot declares pagination or clipping.

- [ ] **Step 5: Create initial source registry config**

Create `config/kai_source_registry.json`:

```json
{
  "schema_version": 1,
  "sources": [
    {"source_id": "pc:kai-root", "kind": "PC", "enabled": true, "uri": "file:///C:/Users/ASIER/OneDrive/Desktop/KAI"},
    {"source_id": "pc:git-repos", "kind": "GIT_LOCAL", "enabled": true, "uri": "file:///C:/Users/ASIER/OneDrive/Desktop/KAI"},
    {"source_id": "s24:kai-nido", "kind": "S24", "enabled": true, "uri": "adb://SM-S928B/sdcard/Kai_Nido"},
    {"source_id": "github:bashull", "kind": "GITHUB", "enabled": true, "uri": "https://github.com/Bashull"},
    {"source_id": "drive:kai", "kind": "GOOGLE_DRIVE", "enabled": true, "uri": "gdrive://my-drive"}
  ]
}
```
- [ ] **Step 6: Run Task 2 tests and verify GREEN**

Run:
```powershell
python -m unittest tests.test_kai_source_adapters -v
```
Expected: all Task 2 tests pass.

- [ ] **Step 7: Commit Task 2**

```powershell
git add tools/kai_source_adapters.py config/kai_source_registry.json tests/test_kai_source_adapters.py
git commit -m "feat: add source registry and git snapshot adapters"
```

---
### Task 3: Compose Existing backup-manifest and file-indexer Evidence

**Files:**
- Modify: `tools/kai_source_adapters.py`
- Test: `tests/test_kai_source_adapters.py`

**Interfaces:**
- Produces: `BackupManifestAdapter`, `FileIndexDatabaseAdapter`.
- Consumes: backup-manifest schema v1 and file-indexer SQLite schema already present in promoted capabilities.

- [ ] **Step 1: Add RED test for backup-manifest normalization**

```python
def test_backup_manifest_adapter_preserves_sha256_and_root(self):
    with TemporaryDirectory() as tmp:
        manifest = Path(tmp) / "manifest.json"
        manifest.write_text(json.dumps({
            "schema_version": 1,
            "capability": "backup-manifest",
            "version": "0.1.0",
            "roots": ["C:/KAI"],
            "entries": [{
                "root": "C:/KAI",
                "relative_path": "core/brain.py",
                "size": 123,
                "mtime_ns": 42,
                "sha256": "b" * 64,
            }],
            "summary": {"files": 1, "bytes": 123, "skipped_symlinks": 0},
        }), encoding="utf-8")
        result = BackupManifestAdapter("pc:kai-root", manifest).collect(max_items=10)
        record = result.records[0]
        self.assertEqual(record.sha256, "b" * 64)
        self.assertEqual(record.logical_path, "core/brain.py")
        self.assertEqual(record.provenance["manifest_capability"], "backup-manifest")
```
- [ ] **Step 2: Add RED test for file-indexer SQLite import**

```python
def test_file_index_database_adapter_reads_existing_index_schema(self):
    with TemporaryDirectory() as tmp:
        db = Path(tmp) / "files.sqlite3"
        import sqlite3
        con = sqlite3.connect(db)
        con.executescript("""
        CREATE TABLE files (
          manifest_id TEXT NOT NULL,
          root TEXT NOT NULL,
          relative_path TEXT NOT NULL,
          name TEXT NOT NULL,
          ext TEXT NOT NULL,
          size INTEGER NOT NULL,
          mtime_ns INTEGER NOT NULL,
          sha256 TEXT NOT NULL
        );
        """)
        con.execute(
            "INSERT INTO files VALUES(?,?,?,?,?,?,?,?)",
            ("m1", "C:/KAI", "tools/x.py", "x.py", ".py", 12, 99, "c" * 64),
        )
        con.commit()
        con.close()
        result = FileIndexDatabaseAdapter("pc:file-index", db).collect(max_items=10)
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].sha256, "c" * 64)
```

- [ ] **Step 3: Run the two new tests and verify RED**

Run:
```powershell
python -m unittest \
  tests.test_kai_source_adapters.SourceAdapterTests.test_backup_manifest_adapter_preserves_sha256_and_root \
  tests.test_kai_source_adapters.SourceAdapterTests.test_file_index_database_adapter_reads_existing_index_schema -v
```
Expected: import errors for the two new adapters.
- [ ] **Step 4: Implement backup-manifest adapter**

Add to `tools/kai_source_adapters.py`:

```python
class BackupManifestAdapter:
    def __init__(self, source_id: str, manifest_path: Path):
        self.source_id = source_id
        self.manifest_path = Path(manifest_path)

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8-sig"))
        if payload.get("capability") != "backup-manifest":
            raise ValueError("expected backup-manifest document")
        entries = payload.get("entries", [])
        records: list[SourceRecord] = []
        for entry in entries[:max_items]:
            root = str(entry["root"])
            relative = str(entry["relative_path"])
            records.append(SourceRecord(
                source_id=self.source_id,
                source_kind="FILE_MANIFEST",
                source_uri=self.manifest_path.as_uri(),
                physical_path=str(Path(root) / Path(relative)),
                logical_path=relative,
                filename=Path(relative).name,
                size_bytes=int(entry["size"]),
                modified_at=str(entry.get("mtime_ns")),
                sha256=str(entry["sha256"]).lower(),
                extraction_state="HASHED_METADATA",
                provenance={
                    "adapter": "BackupManifestAdapter",
                    "manifest_capability": "backup-manifest",
                    "manifest_path": str(self.manifest_path),
                    "root": root,
                },
            ))
        return AdapterResult(
            status="HEALTHY",
            records=records,
            warnings=[],
            observed_count=len(entries),
            truncated=len(entries) > max_items,
        )
```
- [ ] **Step 5: Implement file-indexer SQLite adapter**

Add:

```python
class FileIndexDatabaseAdapter:
    def __init__(self, source_id: str, db_path: Path):
        self.source_id = source_id
        self.db_path = Path(db_path)

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        import sqlite3
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT manifest_id, root, relative_path, name, ext, size, mtime_ns, sha256 "
                "FROM files ORDER BY root, relative_path, manifest_id LIMIT ?",
                (max_items + 1,),
            ).fetchall()
        finally:
            con.close()
        truncated = len(rows) > max_items
        rows = rows[:max_items]
        records = [SourceRecord(
            source_id=self.source_id,
            source_kind="FILE_INDEX",
            source_uri=self.db_path.as_uri(),
            physical_path=str(Path(row["root"]) / Path(row["relative_path"])),
            logical_path=row["relative_path"],
            filename=row["name"],
            size_bytes=int(row["size"]),
            modified_at=str(row["mtime_ns"]),
            sha256=row["sha256"],
            extraction_state="HASHED_METADATA",
            provenance={
                "adapter": "FileIndexDatabaseAdapter",
                "manifest_id": row["manifest_id"],
                "root": row["root"],
            },
        ) for row in rows]
        return AdapterResult("HEALTHY", records, [], len(records) + int(truncated), truncated)
```
- [ ] **Step 6: Run Task 3 tests and verify GREEN**

Run:
```powershell
python -m unittest tests.test_kai_source_adapters -v
```
Expected: all adapter tests pass.

- [ ] **Step 7: Commit Task 3**

```powershell
git add tools/kai_source_adapters.py tests/test_kai_source_adapters.py
git commit -m "feat: compose existing file inventory evidence"
```

---
### Task 4: Bounded S24/ADB Inventory Adapter

**Files:**
- Modify: `tools/kai_source_adapters.py`
- Test: `tests/test_kai_source_adapters.py`

**Interfaces:**
- Produces: `AdbTreeAdapter.collect(max_items: int) -> AdapterResult`.
- Consumes: ADB executable, device serial and explicit remote root.

- [ ] **Step 1: Add RED test using a fake adb executable**

```python
def test_adb_tree_adapter_is_bounded_and_never_uses_shell_true(self):
    with TemporaryDirectory() as tmp:
        fake = Path(tmp) / ("adb.cmd" if os.name == "nt" else "adb")
        if os.name == "nt":
            fake.write_text(
                "@echo off\r\n"
                "echo /sdcard/Kai_Nido/a.txt\r\n"
                "echo /sdcard/Kai_Nido/b.py\r\n"
                "echo /sdcard/Kai_Nido/c.json\r\n",
                encoding="utf-8",
            )
        else:
            fake.write_text(
                "#!/bin/sh\n"
                "printf '/sdcard/Kai_Nido/a.txt\\n/sdcard/Kai_Nido/b.py\\n/sdcard/Kai_Nido/c.json\\n'\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)

        adapter = AdbTreeAdapter(
            source_id="s24:kai-nido",
            adb_executable=fake,
            serial="SM-S928B",
            remote_root="/sdcard/Kai_Nido",
        )
        result = adapter.collect(max_items=2)
        self.assertEqual(len(result.records), 2)
        self.assertTrue(result.truncated)
        self.assertEqual(result.records[0].source_kind, "S24_ADB")
```
- [ ] **Step 2: Run the ADB test and verify RED**

Run:
```powershell
python -m unittest tests.test_kai_source_adapters.SourceAdapterTests.test_adb_tree_adapter_is_bounded_and_never_uses_shell_true -v
```
Expected: `ImportError` or missing `AdbTreeAdapter`.

- [ ] **Step 3: Implement bounded ADB collection**

Add to `tools/kai_source_adapters.py`:

```python
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
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        command = [
            str(self.adb_executable), "-s", self.serial,
            "shell", "find", self.remote_root, "-type", "f", "-print",
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
            assert process.stdout is not None
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
            return AdapterResult("DEGRADED", [], ["ADB_TIMEOUT"], 0, False)
```
Complete record creation after the process returns:

```python
        truncated = len(lines) > max_items
        selected = lines[:max_items]
        records = []
        for remote_path in selected:
            relative = remote_path.removeprefix(self.remote_root).lstrip("/")
            records.append(SourceRecord(
                source_id=self.source_id,
                source_kind="S24_ADB",
                source_uri=f"adb://{self.serial}{remote_path}",
                physical_path=remote_path,
                logical_path=relative or Path(remote_path).name,
                filename=Path(remote_path).name,
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
        )
```

- [ ] **Step 4: Run adapter tests and verify GREEN**

Run:
```powershell
python -m unittest tests.test_kai_source_adapters -v
```
Expected: all adapter tests pass.

- [ ] **Step 5: Commit Task 4**

```powershell
git add tools/kai_source_adapters.py tests/test_kai_source_adapters.py
git commit -m "feat: add bounded S24 adb inventory adapter"
```

---
### Task 5: Integrate Federation into KAI Control Plane

**Files:**
- Modify: `tools/kai_control_plane.py`
- Modify: `skills/kai-control-plane/SKILL.md`
- Test: `tests/test_kai_control_plane.py`
- Test: `tests/test_kai_control_plane_cli.py`

**Interfaces:**
- Consumes: `FederationLedger`, `SourceRegistry`, `ConnectorSnapshotAdapter`.
- Produces methods: `federation_sources()`, `federation_doctor()`, `federation_query()`, `federation_ingest_snapshot()`.
- Produces CLI commands: `sources`, `source-doctor`, `source-ingest`, `global-query`.
- Produces conversational aliases: `/fuentes`, `/doctor-unificacion`, `/ingesta-fuente`, `/buscar-global`.

- [ ] **Step 1: Write RED API tests**

```python
def test_federation_methods_expose_sources_and_query(self):
    plane = self.make_plane()
    sources = plane.federation_sources()
    self.assertIsInstance(sources, list)
    self.assertTrue(any(item["source_id"] == "pc:kai-root" for item in sources))
    doctor = plane.federation_doctor()
    self.assertIn(doctor["status"], {"HEALTHY", "DEGRADED"})


def test_federation_query_returns_normalized_records(self):
    plane = self.make_plane()
    plane.federation_ledger.upsert_record(SourceRecord(
        source_id="pc:test",
        source_kind="PC",
        source_uri="file:///tmp",
        logical_path="core/kai.py",
        filename="kai.py",
        sha256="d" * 64,
    ))
    rows = plane.federation_query(name_contains="kai")
    self.assertEqual(rows[0]["filename"], "kai.py")
```
- [ ] **Step 2: Write RED CLI and alias tests**

```python
def test_new_federation_aliases_are_registered(self):
    plane = self.make_plane()
    aliases = plane.command_catalog()
    self.assertEqual(aliases["/fuentes"], "sources")
    self.assertEqual(aliases["/doctor-unificacion"], "source-doctor")
    self.assertEqual(aliases["/ingesta-fuente"], "source-ingest")
    self.assertEqual(aliases["/buscar-global"], "global-query")


def test_sources_cli_returns_json(self):
    result = self.run_cli("sources")
    self.assertEqual(result.returncode, 0)
    payload = json.loads(result.stdout)
    self.assertTrue(any(item["source_id"] == "pc:kai-root" for item in payload))
```

- [ ] **Step 3: Run RED tests**

Run:
```powershell
python -m unittest \
  tests.test_kai_control_plane.KaiControlPlaneTests.test_federation_methods_expose_sources_and_query \
  tests.test_kai_control_plane.KaiControlPlaneTests.test_federation_query_returns_normalized_records \
  tests.test_kai_control_plane_cli.KaiControlPlaneCliTests.test_new_federation_aliases_are_registered \
  tests.test_kai_control_plane_cli.KaiControlPlaneCliTests.test_sources_cli_returns_json -v
```
Expected: missing methods, aliases or commands.
- [ ] **Step 4: Add safe imports and optional federation paths**

In `tools/kai_control_plane.py`, import federation modules using the same repo/runtime sibling fallback pattern already used for `kai_location_policy` and `kai_capability_integrations`.

Extend the constructor without breaking existing callers:

```python
def __init__(
    self,
    repo_root: Path,
    bridge_root: Path,
    state_root: Path,
    memory_home: Path,
    capability_home: Path,
    policy: PlacementPolicy,
    federation_home: Path | None = None,
    source_registry_path: Path | None = None,
):
    self.repo_root = Path(repo_root)
    self.state_root = Path(state_root)
    self.federation_home = Path(federation_home or (self.state_root / "federation"))
    self.source_registry_path = Path(
        source_registry_path or (self.repo_root / "config" / "kai_source_registry.json")
    )
    self.federation_ledger = FederationLedger(self.federation_home)
    self.source_registry = SourceRegistry.from_json(self.source_registry_path)
```

Do not change existing defaults for memory, capabilities or placement.

- [ ] **Step 5: Implement federation methods**

```python
def federation_sources(self) -> list[dict[str, Any]]:
    return self.source_registry.enabled()


def federation_doctor(self) -> dict[str, Any]:
    ledger = self.federation_ledger.doctor()
    sources = self.federation_sources()
    return {
        "status": "HEALTHY" if ledger["status"] == "HEALTHY" and sources else "DEGRADED",
        "ledger": ledger,
        "enabled_sources": len(sources),
        "summary": self.federation_ledger.source_summary(),
    }
```
Add query and connector snapshot ingestion:

```python
def federation_query(self, **filters: Any) -> list[dict[str, Any]]:
    return [record.to_dict() for record in self.federation_ledger.query(**filters)]


def federation_ingest_snapshot(
    self,
    *,
    source_id: str,
    source_kind: str,
    snapshot_path: Path,
    max_items: int = 10000,
) -> dict[str, Any]:
    adapter = ConnectorSnapshotAdapter(
        source_id=source_id,
        source_kind=source_kind,
        snapshot_path=Path(snapshot_path),
    )
    result = adapter.collect(max_items=max_items)
    stored = [self.federation_ledger.upsert_record(record) for record in result.records]
    return {
        "status": result.status,
        "stored": len(stored),
        "observed_count": result.observed_count,
        "truncated": result.truncated,
        "warnings": result.warnings,
    }
```

- [ ] **Step 6: Add parser commands and dispatch**

Add global options:
```python
parser.add_argument("--federation-home", type=Path)
parser.add_argument("--source-registry", type=Path)
```

Add subcommands:
```python
sub.add_parser("sources")
sub.add_parser("source-doctor")

ingest = sub.add_parser("source-ingest")
ingest.add_argument("--source-id", required=True)
ingest.add_argument("--source-kind", required=True)
ingest.add_argument("--snapshot", type=Path, required=True)
ingest.add_argument("--max-items", type=int, default=10000)

query = sub.add_parser("global-query")
query.add_argument("--name-contains")
query.add_argument("--source-kind")
query.add_argument("--sha256")
query.add_argument("--limit", type=int, default=100)
```
Dispatch commands with JSON output and non-zero exit codes for degraded doctor state:

```python
if args.command == "sources":
    payload = plane.federation_sources()
elif args.command == "source-doctor":
    payload = plane.federation_doctor()
elif args.command == "source-ingest":
    payload = plane.federation_ingest_snapshot(
        source_id=args.source_id,
        source_kind=args.source_kind,
        snapshot_path=args.snapshot,
        max_items=args.max_items,
    )
elif args.command == "global-query":
    payload = plane.federation_query(
        name_contains=args.name_contains,
        source_kind=args.source_kind,
        sha256=args.sha256,
        limit=args.limit,
    )
```

Add aliases to `command_catalog()`:

```python
"/fuentes": "sources",
"/doctor-unificacion": "source-doctor",
"/ingesta-fuente": "source-ingest",
"/buscar-global": "global-query",
```

- [ ] **Step 7: Update the `kai-control-plane` skill contract**

Add a section stating:

```markdown
## Global source federation

Use `/fuentes`, `/doctor-unificacion`, `/ingesta-fuente` and `/buscar-global` for global inventory work.

The federation layer never treats an inaccessible source as inspected. It records blocked sources with explicit reasons and preserves provenance across PC, S24, GitHub, Drive, repositories and archives.
```
- [ ] **Step 8: Run Control Plane tests and verify GREEN**

Run:
```powershell
python -m unittest tests.test_kai_control_plane tests.test_kai_control_plane_cli -v
```
Expected: all Control Plane and CLI tests pass.

- [ ] **Step 9: Add isolated runtime regression**

Extend the existing deployed-runtime regression fixture so it copies these sibling modules together:

```text
a gent_tools/kai_control_plane/
  kai_control_plane.py
  kai_location_policy.py
  kai_capability_integrations.py
  kai_source_federation.py
  kai_source_adapters.py
```

Execute:
```powershell
python kai_control_plane.py --help
python kai_control_plane.py sources
```
Expected: both commands return exit code 0 without a `tools` package.

- [ ] **Step 10: Run regression and full Control Plane suite**

Run:
```powershell
python -m unittest tests.test_kai_control_plane_cli.KaiControlPlaneDeployedRuntimeTests -v
python -m unittest tests.test_kai_control_plane tests.test_kai_control_plane_cli -v
```
Expected: all tests pass.

- [ ] **Step 11: Commit Task 5**

```powershell
git add tools/kai_control_plane.py skills/kai-control-plane/SKILL.md tests/test_kai_control_plane.py tests/test_kai_control_plane_cli.py
git commit -m "feat: integrate global source federation into control plane"
```

---
### Task 6: Bounded Federation Cycle Runner and Coverage Report

**Files:**
- Create: `tools/kai_federation_cycle.py`
- Test: `tests/test_kai_federation_cycle.py`

**Interfaces:**
- Consumes: `FederationLedger`, `SourceRegistry`, adapter factory callable.
- Produces: `FederationCycleConfig`, `FederationCycleRunner.run()`, append-only `federation_events.jsonl`, deterministic `coverage_current.json`.

- [ ] **Step 1: Write RED test for mixed healthy and blocked sources**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.kai_federation_cycle import FederationCycleConfig, FederationCycleRunner
from tools.kai_source_adapters import AdapterResult
from tools.kai_source_federation import FederationLedger, SourceRecord

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
                    [SourceRecord("pc:test", "PC", "file:///tmp", "a.txt", "a.txt")],
                    [],
                    1,
                    False,
                ))

            runner = FederationCycleRunner(home, ledger, sources, factory)
            report = runner.run(FederationCycleConfig("cycle-test", max_items_per_source=10))
            self.assertEqual(report["sources"]["pc:test"]["status"], "HEALTHY")
            self.assertEqual(report["sources"]["drive:test"]["status"], "BLOCKED_WITH_REASON")
            self.assertFalse(report["complete"])
```
- [ ] **Step 2: Run RED test**

Run:
```powershell
python -m unittest tests.test_kai_federation_cycle.FederationCycleTests.test_cycle_records_healthy_and_blocked_sources_without_claiming_full_coverage -v
```
Expected: `ModuleNotFoundError` for `tools.kai_federation_cycle`.

- [ ] **Step 3: Implement cycle config and runner**

Create `tools/kai_federation_cycle.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import json

from tools.kai_source_federation import FederationLedger

@dataclass(frozen=True)
class FederationCycleConfig:
    cycle_id: str
    max_items_per_source: int = 10000


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
        self.sources = sources
        self.adapter_factory = adapter_factory
        self.events_path = self.home / "federation_events.jsonl"
        self.coverage_path = self.home / "coverage_current.json"
```
Implement `run()` with explicit status handling:

```python
    def run(self, config: FederationCycleConfig) -> dict[str, Any]:
        source_report: dict[str, Any] = {}
        total_stored = 0

        for source in self.sources:
            source_id = source["source_id"]
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
                    "warnings": result.warnings,
                }
            except Exception as exc:
                source_report[source_id] = {
                    "status": "BLOCKED_WITH_REASON",
                    "stored": 0,
                    "observed_count": 0,
                    "truncated": False,
                    "reason": f"{type(exc).__name__}: {exc}",
                }

        complete = all(
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
```
Use atomic replacement for `coverage_current.json` and append one JSON object per line to `federation_events.jsonl`. Sort JSON keys for deterministic output.

- [ ] **Step 4: Add idempotency and event-history test**

```python
def test_second_cycle_updates_current_and_appends_history(self):
    with TemporaryDirectory() as tmp:
        home = Path(tmp)
        ledger = FederationLedger(home / "ledger")
        source = {"source_id": "pc:test", "kind": "PC", "enabled": True, "uri": "file:///tmp"}
        adapter = StubAdapter(AdapterResult(
            "HEALTHY",
            [SourceRecord("pc:test", "PC", "file:///tmp", "same.txt", "same.txt", sha256="e" * 64)],
            [],
            1,
            False,
        ))
        runner = FederationCycleRunner(home, ledger, [source], lambda _: adapter)
        runner.run(FederationCycleConfig("cycle-1", 10))
        runner.run(FederationCycleConfig("cycle-2", 10))
        events = (home / "federation_events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(events), 2)
        self.assertEqual(len(ledger.query()), 1)
```

- [ ] **Step 5: Run Task 6 tests and verify GREEN**

Run:
```powershell
python -m unittest tests.test_kai_federation_cycle -v
```
Expected: all cycle tests pass.

- [ ] **Step 6: Commit Task 6**

```powershell
git add tools/kai_federation_cycle.py tests/test_kai_federation_cycle.py
git commit -m "feat: add bounded federation inventory cycles"
```

---
### Task 7: Import Existing Full-Inventory Evidence with Cursor Pagination

**Files:**
- Modify: `tools/kai_source_adapters.py`
- Modify: `tools/kai_federation_cycle.py`
- Test: `tests/test_kai_source_adapters.py`
- Test: `tests/test_kai_federation_cycle.py`

**Interfaces:**
- All adapters accept `collect(max_items: int, cursor: str | None = None)`.
- `AdapterResult` adds `next_cursor: str | None = None`.
- Produces: `KaiMasterInventoryAdapter`, `PowerShellCsvInventoryAdapter`, `PathListAdapter`.
- Federation cycle persists per-source cursors and continues bounded ingestion across cycles.

- [ ] **Step 1: Add RED test for paginated existing master inventory database**

```python
def test_kai_master_inventory_adapter_pages_without_duplicates(self):
    with TemporaryDirectory() as tmp:
        db = Path(tmp) / "master.sqlite3"
        import sqlite3
        con = sqlite3.connect(db)
        con.execute("""
            CREATE TABLE files (
              path TEXT PRIMARY KEY, root TEXT NOT NULL, name TEXT NOT NULL,
              ext TEXT, size INTEGER, mtime REAL, category TEXT,
              ownership TEXT, sha256 TEXT, text_lines INTEGER,
              syntax_ok INTEGER, secret_risk INTEGER DEFAULT 0,
              error TEXT, indexed_at REAL NOT NULL
            )
        """)
        for index in range(5):
            con.execute(
                "INSERT INTO files(path, root, name, size, indexed_at) VALUES(?,?,?,?,?)",
                (f"C:/KAI/f{index}.py", "C:/KAI", f"f{index}.py", index, 1.0),
            )
        con.commit()
        con.close()

        adapter = KaiMasterInventoryAdapter("pc:kai-master-inventory", db)
        first = adapter.collect(max_items=2)
        second = adapter.collect(max_items=2, cursor=first.next_cursor)
        self.assertEqual([r.filename for r in first.records], ["f0.py", "f1.py"])
        self.assertEqual([r.filename for r in second.records], ["f2.py", "f3.py"])
        self.assertEqual(second.next_cursor, "4")
```
- [ ] **Step 2: Add RED tests for CSV and path-list pagination**

```python
def test_powershell_csv_adapter_preserves_file_and_directory_state(self):
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "pc.csv"
        path.write_text(
            '"FullName","PSIsContainer","Length","CreationTimeUtc","LastWriteTimeUtc","Attributes","Extension"\n'
            '"C:\\\\KAI","True",,"2026-01-01","2026-01-02","Directory",""\n'
            '"C:\\\\KAI\\\\a.py","False","12","2026-01-01","2026-01-02","Archive",".py"\n',
            encoding="utf-8-sig",
        )
        result = PowerShellCsvInventoryAdapter("pc:c-drive", path).collect(max_items=10)
        self.assertEqual(result.records[0].extraction_state, "DIRECTORY_METADATA")
        self.assertEqual(result.records[1].filename, "a.py")


def test_path_list_adapter_pages_android_inventory(self):
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "android.txt"
        path.write_text("/sdcard/A\n/sdcard/B\n/sdcard/C\n", encoding="utf-8")
        adapter = PathListAdapter("s24:shared-storage", "S24_ADB", path, "/sdcard")
        first = adapter.collect(max_items=2)
        second = adapter.collect(max_items=2, cursor=first.next_cursor)
        self.assertEqual(len(first.records), 2)
        self.assertEqual(second.records[0].logical_path, "C")
        self.assertIsNone(second.next_cursor)
```

- [ ] **Step 3: Run RED tests**

Run:
```powershell
python -m unittest \
  tests.test_kai_source_adapters.SourceAdapterTests.test_kai_master_inventory_adapter_pages_without_duplicates \
  tests.test_kai_source_adapters.SourceAdapterTests.test_powershell_csv_adapter_preserves_file_and_directory_state \
  tests.test_kai_source_adapters.SourceAdapterTests.test_path_list_adapter_pages_android_inventory -v
```
Expected: missing adapters or missing cursor support.
- [ ] **Step 4: Add cursor support to every adapter result**

Change the shared result type to:

```python
@dataclass(frozen=True)
class AdapterResult:
    status: str
    records: list[SourceRecord]
    warnings: list[str]
    observed_count: int
    truncated: bool = False
    next_cursor: str | None = None
```

Update every adapter signature to:

```python
def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
    ...
```

Cursor migration is explicit: `LocalGitAdapter`, `ConnectorSnapshotAdapter`, `BackupManifestAdapter`, `FileIndexDatabaseAdapter`, `KaiMasterInventoryAdapter`, `PowerShellCsvInventoryAdapter` and `PathListAdapter` paginate by integer offset and return `next_cursor`. `AdbTreeAdapter` remains a direct bounded live probe and must reject non-null cursors; complete S24 ingestion uses existing path-list evidence or a separately captured snapshot.

- [ ] **Step 5: Implement `KaiMasterInventoryAdapter`**

```python
class KaiMasterInventoryAdapter:
    def __init__(self, source_id: str, db_path: Path):
        self.source_id = source_id
        self.db_path = Path(db_path)

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        import sqlite3
        offset = int(cursor or "0")
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT path, root, name, ext, size, mtime, category, ownership, "
                "sha256, text_lines, syntax_ok, secret_risk, error, indexed_at "
                "FROM files ORDER BY path LIMIT ? OFFSET ?",
                (max_items + 1, offset),
            ).fetchall()
        finally:
            con.close()
        truncated = len(rows) > max_items
        selected = rows[:max_items]
        next_cursor = str(offset + len(selected)) if truncated else None
        records = [SourceRecord(
            source_id=self.source_id,
            source_kind="KAI_MASTER_INVENTORY",
            source_uri=self.db_path.as_uri(),
            physical_path=row["path"],
            logical_path=row["path"],
            filename=row["name"],
            size_bytes=row["size"],
            modified_at=str(row["mtime"]) if row["mtime"] is not None else None,
            sha256=row["sha256"],
            sensitivity="SENSITIVE_SIGNAL" if row["secret_risk"] else "UNKNOWN",
            extraction_state="INDEXED_METADATA",
            provenance={"adapter": "KaiMasterInventoryAdapter", "category": row["category"], "ownership": row["ownership"]},
        ) for row in selected]
        return AdapterResult("HEALTHY", records, [], offset + len(selected), truncated, next_cursor)
```
- [ ] **Step 6: Implement CSV and path-list adapters**

Use `csv.DictReader` and line-by-line reading so large evidence files are not loaded fully into memory:

```python
class PowerShellCsvInventoryAdapter:
    def __init__(self, source_id: str, csv_path: Path):
        self.source_id = source_id
        self.csv_path = Path(csv_path)

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        import csv
        offset = int(cursor or "0")
        records: list[SourceRecord] = []
        with self.csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader):
                if index < offset:
                    continue
                if len(records) >= max_items + 1:
                    break
                raw_path = str(row.get("FullName") or "")
                is_dir = str(row.get("PSIsContainer") or "").lower() == "true"
                records.append(SourceRecord(
                    source_id=self.source_id,
                    source_kind="PC_FILE_CSV",
                    source_uri=self.csv_path.as_uri(),
                    physical_path=raw_path,
                    logical_path=raw_path,
                    filename=Path(raw_path).name,
                    size_bytes=None if is_dir or not row.get("Length") else int(row["Length"]),
                    created_at=row.get("CreationTimeUtc") or None,
                    modified_at=row.get("LastWriteTimeUtc") or None,
                    extraction_state="DIRECTORY_METADATA" if is_dir else "FILE_METADATA",
                    provenance={"adapter": "PowerShellCsvInventoryAdapter", "attributes": row.get("Attributes")},
                ))
        truncated = len(records) > max_items
        selected = records[:max_items]
        next_cursor = str(offset + len(selected)) if truncated else None
        return AdapterResult("HEALTHY", selected, [], offset + len(selected), truncated, next_cursor)
```
Add `PathListAdapter`:

```python
class PathListAdapter:
    def __init__(self, source_id: str, source_kind: str, path: Path, logical_root: str):
        self.source_id = source_id
        self.source_kind = source_kind
        self.path = Path(path)
        self.logical_root = logical_root.rstrip("/")

    def collect(self, max_items: int, cursor: str | None = None) -> AdapterResult:
        offset = int(cursor or "0")
        selected: list[str] = []
        observed = 0
        with self.path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for index, raw in enumerate(handle):
                if index < offset:
                    continue
                value = raw.strip()
                if not value:
                    continue
                selected.append(value)
                observed += 1
                if len(selected) > max_items:
                    break
        truncated = len(selected) > max_items
        selected = selected[:max_items]
        records = [SourceRecord(
            source_id=self.source_id,
            source_kind=self.source_kind,
            source_uri=self.path.as_uri(),
            physical_path=value,
            logical_path=value.removeprefix(self.logical_root).lstrip("/\\"),
            filename=Path(value).name,
            extraction_state="PATH_ONLY",
            provenance={"adapter": "PathListAdapter", "evidence_file": str(self.path)},
        ) for value in selected]
        next_cursor = str(offset + len(records)) if truncated else None
        return AdapterResult("HEALTHY", records, [], offset + observed, truncated, next_cursor)
```
- [ ] **Step 7: Persist per-source cursors in the cycle runner**

Add `cursors_current.json` under the federation cycle home. Before each source collection, read its cursor. After a successful batch, store `result.next_cursor`. Remove the cursor when `next_cursor is None`.

Use this exact source report shape:

```python
source_report[source_id] = {
    "status": result.status,
    "stored": stored,
    "observed_count": result.observed_count,
    "truncated": result.truncated,
    "next_cursor": result.next_cursor,
    "warnings": result.warnings,
}
```

Add a test:

```python
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
```
- [ ] **Step 8: Run pagination tests and verify GREEN**

Run:
```powershell
python -m unittest tests.test_kai_source_adapters tests.test_kai_federation_cycle -v
```
Expected: all adapter and cycle tests pass, including cursor resume.

- [ ] **Step 9: Commit Task 7**

```powershell
git add tools/kai_source_adapters.py tools/kai_federation_cycle.py tests/test_kai_source_adapters.py tests/test_kai_federation_cycle.py
git commit -m "feat: ingest existing full inventory evidence with cursors"
```

---
### Task 8: Runtime Adapter Factory, Federation Cycle CLI and Real Baseline Ingestion

**Files:**
- Create: `tools/kai_federation_bootstrap.py`
- Modify: `config/kai_source_registry.json`
- Modify: `tools/kai_control_plane.py`
- Modify: `skills/kai-control-plane/SKILL.md`
- Test: `tests/test_kai_federation_bootstrap.py`
- Test: `tests/test_kai_control_plane_cli.py`

**Interfaces:**
- Produces: `build_adapter(source: dict)`, `run_federation_cycle(...)`.
- Adds CLI command `federation-cycle` and conversational alias `/ciclo-unificacion`.
- Uses explicit adapter kinds; unknown kinds fail closed.

- [ ] **Step 1: Write RED test for explicit adapter factory**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from tools.kai_federation_bootstrap import build_adapter
from tools.kai_source_adapters import KaiMasterInventoryAdapter

class FederationBootstrapTests(unittest.TestCase):
    def test_factory_builds_known_adapter_and_rejects_unknown(self):
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "inventory.sqlite3"
            source = {
                "source_id": "pc:kai-master",
                "kind": "KAI_MASTER_INVENTORY",
                "adapter": "kai_master_inventory",
                "path": str(db),
            }
            self.assertIsInstance(build_adapter(source), KaiMasterInventoryAdapter)
            with self.assertRaisesRegex(ValueError, "unsupported adapter"):
                build_adapter({"source_id": "bad", "adapter": "arbitrary_python"})
```
- [ ] **Step 2: Run factory test and verify RED**

Run:
```powershell
python -m unittest tests.test_kai_federation_bootstrap.FederationBootstrapTests.test_factory_builds_known_adapter_and_rejects_unknown -v
```
Expected: missing `tools.kai_federation_bootstrap`.

- [ ] **Step 3: Implement explicit adapter factory**

Create `tools/kai_federation_bootstrap.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.kai_federation_cycle import FederationCycleConfig, FederationCycleRunner
from tools.kai_source_adapters import (
    AdbTreeAdapter,
    BackupManifestAdapter,
    ConnectorSnapshotAdapter,
    FileIndexDatabaseAdapter,
    KaiMasterInventoryAdapter,
    LocalGitAdapter,
    PathListAdapter,
    PowerShellCsvInventoryAdapter,
)
from tools.kai_source_federation import FederationLedger


def build_adapter(source: dict[str, Any]):
    adapter = source.get("adapter")
    source_id = str(source.get("source_id") or "")
    if adapter == "kai_master_inventory":
        return KaiMasterInventoryAdapter(source_id, Path(source["path"]))
    if adapter == "powershell_csv":
        return PowerShellCsvInventoryAdapter(source_id, Path(source["path"]))
    if adapter == "path_list":
        return PathListAdapter(source_id, source["kind"], Path(source["path"]), source["logical_root"])
    if adapter == "backup_manifest":
        return BackupManifestAdapter(source_id, Path(source["path"]))
    if adapter == "file_index":
        return FileIndexDatabaseAdapter(source_id, Path(source["path"]))
    if adapter == "connector_snapshot":
        return ConnectorSnapshotAdapter(source_id, source["kind"], Path(source["path"]))
    if adapter == "local_git":
        return LocalGitAdapter(source_id, [Path(item) for item in source["roots"]])
    if adapter == "adb_tree":
        return AdbTreeAdapter(source_id, Path(source["adb_executable"]), source["serial"], source["remote_root"])
    raise ValueError(f"unsupported adapter: {adapter!r}")
```
Add runtime cycle orchestration:

```python
def run_federation_cycle(
    *,
    federation_home: Path,
    source_registry_path: Path,
    cycle_id: str,
    max_items_per_source: int,
) -> dict[str, Any]:
    registry = SourceRegistry.from_json(source_registry_path)
    sources = registry.enabled()
    ledger = FederationLedger(federation_home / "ledger")
    runner = FederationCycleRunner(
        federation_home / "cycles",
        ledger,
        sources,
        build_adapter,
    )
    return runner.run(FederationCycleConfig(cycle_id, max_items_per_source))
```

For `local_git`, allow either inline `roots` or a JSON `roots_path` containing `{"roots": ["..."]}`. Never execute arbitrary code from the registry.

- [ ] **Step 4: Extend source registry with current evidence roots**

Add entries for the existing reproducible evidence:

```json
{"source_id":"pc:kai-master-inventory","kind":"KAI_MASTER_INVENTORY","enabled":true,"adapter":"kai_master_inventory","path":"C:/Users/ASIER/OneDrive/Desktop/KAI/mobile-audit/kai_master_inventory.sqlite3"},
{"source_id":"pc:c-drive-20260711","kind":"PC","enabled":true,"adapter":"powershell_csv","path":"C:/Users/ASIER/OneDrive/Desktop/KAI/mobile-audit/full-inventory-2026-07-11/pc_C_files_full.csv"},
{"source_id":"pc:d-drive-20260711","kind":"PC","enabled":true,"adapter":"powershell_csv","path":"C:/Users/ASIER/OneDrive/Desktop/KAI/mobile-audit/full-inventory-2026-07-11/pc_D_files_full.csv"},
{"source_id":"pc:e-drive-20260711","kind":"PC","enabled":true,"adapter":"powershell_csv","path":"C:/Users/ASIER/OneDrive/Desktop/KAI/mobile-audit/full-inventory-2026-07-11/pc_E_files_full.csv"},
{"source_id":"pc:g-drive-20260711","kind":"PC","enabled":true,"adapter":"powershell_csv","path":"C:/Users/ASIER/OneDrive/Desktop/KAI/mobile-audit/full-inventory-2026-07-11/pc_G_files_full.csv"},
{"source_id":"s24:shared-storage-20260711","kind":"S24_ADB","enabled":true,"adapter":"path_list","path":"C:/Users/ASIER/OneDrive/Desktop/KAI/mobile-audit/full-inventory-2026-07-11/android_shared_storage_paths_full.txt","logical_root":"/sdcard"},
{"source_id":"s24:root-accessible-20260711","kind":"S24_ADB","enabled":true,"adapter":"path_list","path":"C:/Users/ASIER/OneDrive/Desktop/KAI/mobile-audit/full-inventory-2026-07-11/android_root_accessible_paths_full.txt","logical_root":"/"}
```
- [ ] **Step 5: Add live Git roots and connector snapshots**

Generate `C:\Users\ASIER\.kai_federation\snapshots\local_git_roots_20260712.json` from the currently discovered `.git` directories under the KAI scope. The snapshot must contain sorted unique repository roots and the observation timestamp.

Create connector snapshots with this schema:

```json
{
  "schema_version": 1,
  "source_id": "github:bashull",
  "observed_at": "2026-07-12T00:00:00Z",
  "complete": true,
  "items": [
    {
      "external_id": "1069592908",
      "name": "Kai",
      "url": "https://github.com/Bashull/Kai",
      "size_bytes": 55880,
      "metadata": {"default_branch": "main", "visibility": "public"}
    }
  ]
}
```

Save GitHub and Drive snapshots under:

```text
C:\Users\ASIER\.kai_federation\snapshots\github_bashull_20260712.json
C:\Users\ASIER\.kai_federation\snapshots\drive_kai_20260712.json
```

The GitHub snapshot must include all 7 currently accessible repositories returned by the connected GitHub app. Drive snapshot completeness must reflect real pagination or permission limits instead of claiming full coverage.

- [ ] **Step 6: Add federation cycle command to Control Plane**

Add CLI command:

```text
federation-cycle --cycle-id <id> --max-items-per-source <n>
```

Add alias:

```python
"/ciclo-unificacion": "federation-cycle"
```

The command calls `run_federation_cycle()` and prints deterministic JSON.
- [ ] **Step 7: Add RED/green tests for `federation-cycle`**

Add CLI test:

```python
def test_federation_cycle_cli_returns_cycle_report(self):
    result = self.run_cli(
        "federation-cycle",
        "--cycle-id", "test-cycle",
        "--max-items-per-source", "2",
    )
    self.assertIn(result.returncode, {0, 2})
    payload = json.loads(result.stdout)
    self.assertEqual(payload["cycle_id"], "test-cycle")
    self.assertIn("sources", payload)
```

Run RED before implementation, then GREEN after dispatch is added.

- [ ] **Step 8: Run the full source suite**

Run:
```powershell
python -m unittest \
  tests.test_kai_source_federation \
  tests.test_kai_source_adapters \
  tests.test_kai_federation_cycle \
  tests.test_kai_federation_bootstrap \
  tests.test_kai_control_plane \
  tests.test_kai_control_plane_cli -v
```
Expected: all tests pass.

- [ ] **Step 9: Commit Task 8 source implementation**

```powershell
git add tools/kai_federation_bootstrap.py tools/kai_control_plane.py config/kai_source_registry.json skills/kai-control-plane/SKILL.md tests/test_kai_federation_bootstrap.py tests/test_kai_control_plane_cli.py
git commit -m "feat: add runnable source federation cycles"
```
- [ ] **Step 10: Run bounded real baseline cycles**

Use a private runtime home:

```text
C:\Users\ASIER\.kai_federation
```

Start with:

```powershell
python tools/kai_control_plane.py `
  --policy C:\Users\ASIER\OneDrive\Desktop\KAI\_KAI_BRIDGE\config\kai_location_policy.json `
  --repo-root C:\Users\ASIER\OneDrive\Desktop\KAI\_KAI_BRIDGE\worktrees\kai-memory-forge `
  --bridge-root C:\Users\ASIER\OneDrive\Desktop\KAI\_KAI_BRIDGE `
  --state-root C:\Users\ASIER\.kai_capabilities\control-plane-state `
  --memory-home C:\Users\ASIER\.kai_memory `
  --capability-home C:\Users\ASIER\.kai_capabilities `
  --federation-home C:\Users\ASIER\.kai_federation `
  --source-registry config\kai_source_registry.json `
  federation-cycle --cycle-id baseline-001 --max-items-per-source 25000
```

Repeat bounded cycles with incrementing IDs until cursor-backed sources complete or a source reports an explicit blocker. Do not use an unbounded loop. After each cycle run `source-doctor` and preserve `coverage_current.json` plus `federation_events.jsonl`.

Expected baseline evidence includes, without treating old counts as permanent truth:
- existing KAI master inventory database: 275,009 indexed records before federation import;
- prior PC-specific inventory: 149,341 files across its declared roots;
- prior Android shared storage evidence: 195,738 paths;
- prior Android accessible root evidence: 209,779 paths;
- local Git scope: 66 repositories in the current discovery;
- connected GitHub: 7 accessible repositories in the current snapshot;
- current S24 Kai_Nido direct count observed separately around 117,090 files, which must be treated as drift against older evidence rather than silently reconciled.

- [ ] **Step 11: Verify no false completion claims**

Run:
```powershell
python tools/kai_control_plane.py ... source-doctor
```

Expected:
- every source has a status;
- truncated or cursor-pending sources are not complete;
- blocked Drive/Android/Termux scopes show reasons;
- no inaccessible source is marked `HEALTHY` merely because it was skipped.
### Task 9: Full Verification, Governed Deployment, Promotion and Continuity

**Files:**
- Modify: `tools/kai_control_plane.py`
- Modify: `skills/kai-control-plane/SKILL.md`
- Create evidence under: `C:\Users\ASIER\.kai_capabilities\evidence\`
- Update memory under: `C:\Users\ASIER\.kai_memory\`
- Update CURRENT Drive documents only after local verification succeeds.

- [ ] **Step 1: Run complete fresh test suite**

Run:
```powershell
python -m unittest discover -s tests -v
```
Expected: all existing and new tests pass with zero failures.

- [ ] **Step 2: Inspect Git diff and confirm scope**

Run:
```powershell
git status --short
git diff --stat
git diff -- tools/kai_source_federation.py tools/kai_source_adapters.py tools/kai_federation_cycle.py tools/kai_federation_bootstrap.py tools/kai_control_plane.py config/kai_source_registry.json skills/kai-control-plane/SKILL.md tests
```
Expected: only source-federation work and its documentation/tests are present.

- [ ] **Step 3: Commit final source state**

```powershell
git add tools config/kai_source_registry.json skills/kai-control-plane/SKILL.md tests
git commit -m "feat: add global source federation and inventory ledger"
```

Do not stage unrelated worktree changes.

- [ ] **Step 4: Snapshot runtime before replacement**

Create a timestamped snapshot under:

```text
C:\Users\ASIER\.kai_capabilities\snapshots\kai-source-federation\<timestamp>\
```

Copy the previous runtime versions of changed Control Plane files before deployment.
- [ ] **Step 5: Deploy verified runtime bundle**

Deploy these files together:

```text
_KAI_BRIDGE/agent_tools/kai_control_plane/kai_control_plane.py
_KAI_BRIDGE/agent_tools/kai_control_plane/kai_location_policy.py
_KAI_BRIDGE/agent_tools/kai_control_plane/kai_capability_integrations.py
_KAI_BRIDGE/agent_tools/kai_control_plane/kai_source_federation.py
_KAI_BRIDGE/agent_tools/kai_control_plane/kai_source_adapters.py
_KAI_BRIDGE/agent_tools/kai_control_plane/kai_federation_cycle.py
_KAI_BRIDGE/agent_tools/kai_control_plane/kai_federation_bootstrap.py
_KAI_BRIDGE/config/kai_source_registry.json
_KAI_BRIDGE/skills/kai-control-plane/SKILL.md
```

Compute SHA-256 for every source/runtime pair and require exact parity.

- [ ] **Step 6: Run runtime regression and doctors**

Run from the deployed runtime:

```powershell
python C:\Users\ASIER\OneDrive\Desktop\KAI\_KAI_BRIDGE\agent_tools\kai_control_plane\kai_control_plane.py --help
python C:\Users\ASIER\OneDrive\Desktop\KAI\_KAI_BRIDGE\agent_tools\kai_control_plane\kai_control_plane.py ... source-doctor
python C:\Users\ASIER\OneDrive\Desktop\KAI\_KAI_BRIDGE\agent_tools\kai_control_plane\kai_control_plane.py ... doctor
```

Expected:
- import regression passes in isolated runtime layout;
- federation ledger doctor is healthy or explicitly degraded by real source blockers;
- core doctor remains healthy;
- no source is silently omitted.

- [ ] **Step 7: Static scanner and capability registry governance**

Scan changed/new implementation artifacts with `kai_capability_scanner.py`. Require:

```text
0 exact duplicate collisions unless intentionally superseding
0 exposed secret values
0 unreviewed quarantine signals
```

Register new versions and move them through:

```text
DISCOVERED â†’ CLASSIFIED â†’ CANDIDATE â†’ TESTING â†’ VALIDATED â†’ PROMOTED
```

Only after new versions reach `PROMOTED` may previous corresponding versions become `SUPERSEDED`. Do not grant `CANONICAL` automatically.
- [ ] **Step 8: Record memory and immutable session snapshot**

Create an evidenced improvement memory containing:

```text
objective
verified baseline sources
new files and capability IDs
full test count
runtime deployment parity
source coverage counts
blocked scopes with reasons
known drift between old and current source counts
next subproject
```

Regenerate the boot packet and run memory doctor.

Close the session with a snapshot under:

```text
C:\Users\ASIER\.kai_memory\sessions\<cycle-id>.json
```

- [ ] **Step 9: Update Drive CURRENT surfaces**

After all local verification succeeds, update:

```text
KAI_LONG_TERM_MEMORY_BOOT_PACKET_CURRENT
07_KAI_COMMANDS_AND_STORAGE_CONTRACT_CURRENT_v1.0.0
20260711_KAI_CONTROL_PLANE_COMMANDS_STORAGE_POLICY_STATUS_v1.0.0
05_KAI_DRIVE_MASTER_INDEX_CURRENT_v1.0.0
```

Add a new section describing Source Federation + Global Inventory, source completeness, current counts, blockers and next phase.

Preserve prior incident history; update current status without deleting historical evidence.

- [ ] **Step 10: Final verification before completion claim**

Repeat:

```powershell
python -m unittest discover -s tests -v
git status --short
```

Recompute deployment hashes from disk, rerun federation doctor, global doctor, memory doctor and capability registry doctor, then read back the four Drive CURRENT documents.

Completion is allowed only when evidence agrees across tests, hashes, doctors, Git and Drive readback.

---

## Plan Exit Condition

Subproject A is complete when KAI has a working federated inventory database, cursor-resumable bounded ingestion, explicit coverage status for every known source, global query commands in Control Plane, reproducible source evidence, promoted runtime components and persistent memory of the result.

The next implementation plan is Subproject B: content-addressed evidence, extraction, knowledge database and provenance graph.
