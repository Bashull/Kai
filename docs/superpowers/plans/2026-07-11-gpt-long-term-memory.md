# GPT Long-Term Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a durable, source-backed memory bridge that records what Kai did, where, why, what changed, what improved and what remains, then generates a compact boot packet for future chats.

**Architecture:** A Python standard-library core stores canonical records in SQLite, mirrors every mutation to an append-only JSONL event log, writes immutable session snapshots, and emits deterministic Markdown/JSON boot packets. A skill teaches future agents when to load and update that memory.

**Tech Stack:** Python 3.11+ stdlib (`sqlite3`, `json`, `hashlib`, `argparse`, `pathlib`, `datetime`, `re`), `unittest`, Markdown skills.

## Global Constraints

- No private memory content is committed to Git.
- Default runtime home is `%USERPROFILE%\.kai_memory` / `~/.kai_memory`; `KAI_MEMORY_HOME` overrides it.
- No credential values may appear in emitted boot packets, events or reports.
- Memory claims must carry confidence: `EXPLICIT`, `EVIDENCED`, `INFERRED` or `UNKNOWN`.
- Inferred narrative is never presented as fact.
- Exact duplicates are identified by stable SHA-256-derived IDs.
- Standard library only for the first version.

---

### Task 1: Persistent ledger core

**Files:**
- Create: `tools/kai_memory_ledger.py`
- Test: `tests/test_kai_memory_ledger.py`

**Interfaces:**
- Produces: `MemoryLedger(home: Path)`, `add_memory(record: dict) -> dict`, `search(query: str, limit: int = 20, scope: str | None = None) -> list[dict]`, `build_boot_packet(max_chars: int = 12000, project: str | None = None) -> dict`.

- [ ] **Step 1: Write failing tests for initialization, persistence and idempotency**

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from tools.kai_memory_ledger import MemoryLedger

class MemoryLedgerTests(unittest.TestCase):
    def test_persists_and_skips_exact_duplicate(self):
        with TemporaryDirectory() as tmp:
            ledger = MemoryLedger(Path(tmp))
            record = {"kind": "DECISION", "scope": "project:kai", "title": "Use SHA-256", "content": "Hashes decide exact duplicates.", "priority": 90, "confidence": "EXPLICIT", "tags": ["hash", "dedupe"], "provenance": []}
            first = ledger.add_memory(record)
            second = ledger.add_memory(record)
            self.assertEqual(first["decision"], "INSERTED")
            self.assertEqual(second["decision"], "SKIP_EXACT_DUPLICATE")
            self.assertEqual(len(ledger.search("SHA-256")), 1)
```

- [ ] **Step 2: Run test and verify RED**

Run: `python -m unittest -v tests.test_kai_memory_ledger.MemoryLedgerTests.test_persists_and_skips_exact_duplicate`
Expected: FAIL because `tools.kai_memory_ledger` does not exist.

- [ ] **Step 3: Implement minimal SQLite + JSONL core**

```python
class MemoryLedger:
    def __init__(self, home: Path):
        self.home = home
        self.db_path = home / "memory.sqlite3"
        self.events_path = home / "events.jsonl"
        self.sessions_dir = home / "sessions"
        self.init_storage()

    def add_memory(self, record: dict) -> dict:
        normalized = self._normalize_record(record)
        memory_id = self._stable_memory_id(normalized)
        if self._exists(memory_id):
            return {"decision": "SKIP_EXACT_DUPLICATE", "memory_id": memory_id}
        self._insert(memory_id, normalized)
        self._append_event("MEMORY_INSERTED", memory_id, normalized)
        return {"decision": "INSERTED", "memory_id": memory_id}
```

- [ ] **Step 4: Run targeted test and verify GREEN**

Run: `python -m unittest -v tests.test_kai_memory_ledger.MemoryLedgerTests.test_persists_and_skips_exact_duplicate`
Expected: PASS.

- [ ] **Step 5: Add tests for restart persistence and deterministic JSON export**

```python
def test_survives_new_process_object(self):
    with TemporaryDirectory() as tmp:
        home = Path(tmp)
        MemoryLedger(home).add_memory(self.sample_record())
        reopened = MemoryLedger(home)
        self.assertEqual(len(reopened.search("SHA-256")), 1)
```

- [ ] **Step 6: Commit Task 1**

```bash
git add tools/kai_memory_ledger.py tests/test_kai_memory_ledger.py
git commit -m "feat: add persistent Kai memory ledger core"
```

### Task 2: Redaction, supersession and search

**Files:**
- Modify: `tools/kai_memory_ledger.py`
- Modify: `tests/test_kai_memory_ledger.py`

**Interfaces:**
- Produces: `redact_sensitive(text: str) -> tuple[str, list[str]]`, `supersede(old_id: str, new_id: str) -> None`.

- [ ] **Step 1: Write failing tests for redaction and supersession**

```python
def test_redacts_sensitive_values_before_storage(self):
    text = "api_key=AIza" + "A" * 35
    result = self.ledger.add_memory({**self.sample_record(), "content": text})
    stored = self.ledger.get_memory(result["memory_id"])
    self.assertNotIn("AIza", stored["content"])
    self.assertIn("[REDACTED:GOOGLE_API_KEY]", stored["content"])

def test_superseded_record_is_not_in_default_search(self):
    old_id = self.add("Old path", "C:/old")
    new_id = self.add("New path", "C:/new")
    self.ledger.supersede(old_id, new_id)
    self.assertEqual([m["memory_id"] for m in self.ledger.search("path")], [new_id])
```

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m unittest -v tests.test_kai_memory_ledger.MemoryLedgerTests.test_redacts_sensitive_values_before_storage tests.test_kai_memory_ledger.MemoryLedgerTests.test_superseded_record_is_not_in_default_search`
Expected: FAIL because redaction and supersession are missing.

- [ ] **Step 3: Implement minimal redaction and supersession**

```python
SENSITIVE_PATTERNS = (
    ("OPENAI_KEY", re.compile(r"\\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\\b")),
    ("GITHUB_TOKEN", re.compile(r"\\bgh[pousr]_[A-Za-z0-9]{20,}\\b")),
    ("GOOGLE_API_KEY", re.compile(r"\\bAIza[0-9A-Za-z_-]{30,}\\b")),
)
```

- [ ] **Step 4: Run all ledger tests and verify GREEN**

Run: `python -m unittest -v tests.test_kai_memory_ledger`
Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add tools/kai_memory_ledger.py tests/test_kai_memory_ledger.py
git commit -m "feat: add memory redaction and supersession"
```

### Task 3: Session closure and boot packet

**Files:**
- Modify: `tools/kai_memory_ledger.py`
- Modify: `tests/test_kai_memory_ledger.py`

**Interfaces:**
- Produces: `close_session(summary: dict) -> dict`, `build_boot_packet(max_chars: int = 12000, project: str | None = None) -> dict`, `write_boot_packet(...) -> tuple[Path, Path]`.

- [ ] **Step 1: Write failing tests for session closure and boot generation**

The test creates a synthetic session with objective, actions, artifacts, decisions, improvements, pending work and next step; then asserts that an immutable session file exists and the generated boot packet contains the current objective and pending work.

- [ ] **Step 2: Run targeted tests and verify RED**

Run: `python -m unittest -v tests.test_kai_memory_ledger.MemoryLedgerTests.test_session_close_records_context tests.test_kai_memory_ledger.MemoryLedgerTests.test_boot_packet_is_deterministic_and_budgeted`
Expected: FAIL because session closure and boot generation are missing.

- [ ] **Step 3: Implement session closure and deterministic boot selection**

Use fixed section order: identity, preferences, project state, decisions, latest work, improvements, pending, health. Critical active records must be selected before score-based optional records.

- [ ] **Step 4: Run full ledger tests and verify GREEN**

Run: `python -m unittest -v tests.test_kai_memory_ledger`
Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add tools/kai_memory_ledger.py tests/test_kai_memory_ledger.py
git commit -m "feat: add session closure and boot packets"
```

### Task 4: CLI and health checks

**Files:**
- Modify: `tools/kai_memory_ledger.py`
- Modify: `tests/test_kai_memory_ledger.py`

**Interfaces:**
- CLI commands: `init`, `remember`, `search`, `boot`, `session-close`, `doctor`, `export`.

- [ ] **Step 1: Write failing CLI tests**

Use `subprocess.run([sys.executable, tool, ...], capture_output=True, text=True)` with a temporary `KAI_MEMORY_HOME`.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest -v tests.test_kai_memory_ledger.MemoryLedgerCliTests`
Expected: FAIL because CLI entrypoints are missing.

- [ ] **Step 3: Implement argparse CLI**

`remember` accepts `--json-file` or explicit fields; `session-close` accepts `--json-file`; `boot` writes both Markdown and JSON; `doctor` checks schema, event log, session directory and boot files.

- [ ] **Step 4: Verify GREEN**

Run: `python -m unittest -v tests.test_kai_memory_ledger`
Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add tools/kai_memory_ledger.py tests/test_kai_memory_ledger.py
git commit -m "feat: add Kai memory CLI and doctor"
```

### Task 5: GPT long-term-memory skill contract

**Files:**
- Create: `skills/gpt-long-term-memory/SKILL.md`
- Create: `tests/test_skill_contracts.py`

**Interfaces:**
- Produces a reusable skill triggered by cross-chat continuity, previous decisions, project state, artifact location, prior improvements, unresolved work or user preferences.

- [ ] **Step 1: Write failing contract test**

The test requires valid YAML frontmatter, a `description` starting with `Use when`, and sections: `Overview`, `When to use`, `Memory loading contract`, `Memory writing contract`, `Evidence and confidence`, `Safety contract`, `New-chat boot sequence`, `Decision labels`.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest -v tests.test_skill_contracts`
Expected: FAIL because the skill does not exist.

- [ ] **Step 3: Write the skill**

The skill must tell future agents to load the latest boot packet before making claims about prior work, search deeper when exact paths/versions/decisions matter, preserve explicit/evidenced/inferred distinctions, and write a session closure after material work.

- [ ] **Step 4: Verify GREEN**

Run: `python -m unittest -v tests.test_skill_contracts`
Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add skills/gpt-long-term-memory/SKILL.md tests/test_skill_contracts.py
git commit -m "feat: add GPT long-term memory skill"
```

### Task 6: Seed, deploy and create first boot packet

**Files:**
- Runtime only: `%USERPROFILE%\.kai_memory` or configured `KAI_MEMORY_HOME`
- Deploy validated files to: `_KAI_BRIDGE\skills\gpt-long-term-memory` and `_KAI_BRIDGE\agent_tools\kai_memory`

**Interfaces:**
- Consumes explicit/evidenced seed records from current work.
- Produces private `memory.sqlite3`, `events.jsonl`, `boot_packet.md`, `boot_packet.json`, session snapshot and doctor report.

- [ ] **Step 1: Run complete test suite**

Run: `python -m unittest -v tests.test_kai_memory_ledger tests.test_skill_contracts`
Expected: all tests pass.

- [ ] **Step 2: Initialize private runtime memory**

Run: `python tools/kai_memory_ledger.py init --home "C:\Users\ASIER\.kai_memory"`
Expected: storage initialized with no private data committed to Git.

- [ ] **Step 3: Seed only explicit/evidenced current-state memories**

Seed identity/directive pointers, current project state, verified OMNINET genealogy results, current tool/skill locations, this feature branch, and active pending work. Every seed must include provenance and confidence.

- [ ] **Step 4: Close the current implementation session**

Record objective, actions, artifacts, decisions, improvements, pending work and next step using `session-close`.

- [ ] **Step 5: Generate boot packet and doctor report**

Run: `python tools/kai_memory_ledger.py boot --home "C:\Users\ASIER\.kai_memory" --project kai --max-chars 12000`
Run: `python tools/kai_memory_ledger.py doctor --home "C:\Users\ASIER\.kai_memory"`
Expected: Markdown + JSON boot packets and healthy storage report.

- [ ] **Step 6: Promote validated runtime files**

Copy only validated code/skill files to `_KAI_BRIDGE` runtime directories; do not copy tests, fixtures or private database into public Git paths.

- [ ] **Step 7: Commit deployment metadata**

```bash
git add docs tools skills tests
git commit -m "chore: finalize Kai long-term memory deployment metadata"
```

## Verification checklist

- [ ] Existing legacy memory test is acknowledged as incomplete baseline evidence.
- [ ] New memory survives fresh `MemoryLedger` instances.
- [ ] Duplicate inserts are idempotent.
- [ ] Superseded memories disappear from default search.
- [ ] Sensitive values are redacted before storage.
- [ ] Session closure contains work/context/improvements/pending.
- [ ] Boot packet respects budget and preserves critical sections.
- [ ] Skill contract passes.
- [ ] Runtime doctor reports healthy state.
- [ ] Private memory data is absent from `git status`.
