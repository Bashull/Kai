# KAI Autonomy Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build CELL-000, a dependency-light, restart-safe autonomy substrate that persists bounded jobs, enforces write/permission/budget guards, executes one idempotent iteration at a time, records evidence, and survives interruption without depending on Drive or a hosted orchestration service.

**Architecture:** Add an isolated Python package at `core/loop_factory/`, following the repository's existing dataclass/Path/JSON conventions. SQLite is the durable authority for jobs, attempts, checkpoints, step receipts, and evidence. External systems are represented through narrow worker/capability interfaces; Drive receives rendered checkpoint payloads only through an output adapter. CELL-000 uses standard-library orchestration rather than introducing LangGraph/Temporal/Redis/Postgres before evidence justifies them.

**Tech Stack:** Python 3.10+ standard library, `sqlite3`, `unittest`, Git, GitHub-hosted Actions runners. CI validates Python 3.11 and 3.12.

**Spec:** `docs/superpowers/specs/2026-09-16-autonomy-foundation-design.md`

## Global Constraints

- `REUSE -> ADAPT -> COMPOSE -> ACQUIRE -> BUILD`.
- One cell owns one objective and one declared write scope.
- No implementation worker writes directly to `main` or `master`.
- Source mutations happen in an isolated worktree/feature branch and enter canonical history through reviewable PRs.
- SQLite first; no Postgres, Redis, Kafka, Temporal, LangGraph, or new hosted runtime dependency in CELL-000.
- No plaintext credentials in source, manifests, SQLite payloads, checkpoints, evidence, or logs.
- Every loop has max cost, max iterations, max retries, timeout, and a terminal state.
- `SUCCEEDED`, `FAILED`, `QUARANTINED`, and `CANCELLED` are terminal for an attempt. Explicit requeue creates a new attempt; old terminal attempts are immutable.
- BUILD/REPAIR/PROMOTION cannot reach `SUCCEEDED` without verification evidence.
- Branch and write-scope guards run before mutation.
- Connector/plugin permission settings are upper bounds; Loop Factory policy remains narrower.
- GitHub-hosted runners only for public-repo CI; no self-hosted runner on an untrusted public-PR path.
- Drive is not required for execution. CELL-000 emits Drive-ready payloads but performs no Drive network call.
- Runtime state defaults under `.kai-loop/` and is ignored by Git.

## Mandatory Execution Preflight

Before Task 1, the executor must invoke `superpowers:using-git-worktrees` and create an isolated worktree from the approved design branch head. The intended implementation branch is `feat/loop-factory-cell-000`.

The worktree preflight must establish these invariants before any source write:

```bash
git fetch origin
git rev-parse --verify origin/docs/autonomy-foundation-20260916
git rev-parse --abbrev-ref HEAD
git status --short
```

The worktree's branch must be exactly `feat/loop-factory-cell-000`, its base must include the approved spec and this plan, and its working tree must be clean. If branch identity cannot be proven, implementation stops fail-closed.

---

## File Structure

### New package

- `core/loop_factory/__init__.py` — public CELL-000 API.
- `core/loop_factory/__main__.py` — `python -m core.loop_factory` entry point.
- `core/loop_factory/model.py` — canonical enums/dataclasses/serialization.
- `core/loop_factory/errors.py` — typed operational failure.
- `core/loop_factory/state_machine.py` — closed transition graph.
- `core/loop_factory/guards.py` — canonical-branch and write-scope guards.
- `core/loop_factory/policy.py` — autonomy, cost, security, and promotion policy.
- `core/loop_factory/store.py` — SQLite persistence and transactions.
- `core/loop_factory/evidence.py` — observability record + SHA-256 helpers.
- `core/loop_factory/capabilities.py` — FREE-FIRST worker registry/ranking.
- `core/loop_factory/workers.py` — worker protocol + deterministic demo worker.
- `core/loop_factory/runner.py` — one-iteration durable loop runner.
- `core/loop_factory/writeback.py` — Drive-ready checkpoint rendering.
- `core/loop_factory/cli.py` — governed CLI.

### Tests

- `tests/loop_factory/__init__.py`
- `tests/loop_factory/test_model.py`
- `tests/loop_factory/test_state_machine.py`
- `tests/loop_factory/test_policy_guards.py`
- `tests/loop_factory/test_store.py`
- `tests/loop_factory/test_capabilities.py`
- `tests/loop_factory/test_runner.py`
- `tests/loop_factory/test_cli.py`
- `tests/loop_factory/test_cell000_acceptance.py`

### CI/docs/config

- `.github/workflows/test-loop-factory.yml`
- `docs/loop_factory/CELL_000_RUNBOOK.md`
- `.gitignore` — add only `.kai-loop/`, `*.loopfactory.db`, `*.loopfactory.db-*`.

Do not modify the React UI, the Media Forge slices, or existing core modules during CELL-000. Do not export Loop Factory from `core/__init__.py` yet; use `core.loop_factory` explicitly.

---

### Task 1: Canonical Models, Error Taxonomy, and Serialization

**Files:**
- Create: `core/loop_factory/__init__.py`
- Create: `core/loop_factory/model.py`
- Create: `core/loop_factory/errors.py`
- Create: `tests/loop_factory/__init__.py`
- Create: `tests/loop_factory/test_model.py`

**Interfaces:**
- `AutonomyLevel(str, Enum)`: `A0` through `A5`.
- `JobState(str, Enum)`: exact spec state set.
- `ErrorClass(str, Enum)`: exact spec taxonomy.
- `Budget(currency: str = "EUR", max_cost_eur: float = 0.0, max_iterations: int = 1, max_retries: int = 0, timeout_seconds: int = 60)`.
- `JobManifest.new(...) -> JobManifest`.
- `JobManifest.to_dict() -> dict[str, object]`.
- `JobManifest.from_dict(data: Mapping[str, object]) -> JobManifest`.
- `JobManifest.to_json() -> str`.
- `JobManifest.from_json(payload: str) -> JobManifest`.
- `AttemptRecord` is a serializable dataclass for durable attempt metadata.
- `utc_now() -> str` returns timezone-aware UTC ISO-8601.
- `LoopFactoryError(error_class: ErrorClass, message: str, retryable: bool = False)`.

- [ ] **Step 1: Write failing model tests**

```python
# tests/loop_factory/test_model.py
import json
import unittest

from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState


class JobManifestTests(unittest.TestCase):
    def make_job(self) -> JobManifest:
        return JobManifest.new(
            job_id="CELL-000-DEMO",
            project="KAI_LOOP_FACTORY",
            cell_type="BUILD",
            goal="Create deterministic demo output",
            write_scope=[".kai-loop/sandboxes/CELL-000-DEMO"],
            autonomy_level=AutonomyLevel.A2,
            allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=0.0, max_iterations=3, max_retries=2, timeout_seconds=60),
        )

    def test_json_round_trip_preserves_contract(self):
        job = self.make_job()
        restored = JobManifest.from_json(job.to_json())
        self.assertEqual(restored, job)
        self.assertEqual(restored.state, JobState.QUEUED)
        self.assertEqual(restored.budget.currency, "EUR")

    def test_recursive_secret_key_is_rejected(self):
        payload = self.make_job().to_dict()
        payload["metadata"] = {"api_key": "sk-not-allowed"}
        with self.assertRaises(ValueError):
            JobManifest.from_dict(payload)

    def test_serialized_manifest_is_valid_json(self):
        parsed = json.loads(self.make_job().to_json())
        self.assertEqual(parsed["schema_version"], 1)
```

- [ ] **Step 2: Run to prove red state**

```bash
python -m unittest tests.loop_factory.test_model -v
```

Expected: import failure because the package does not exist.

- [ ] **Step 3: Implement minimal model/error contract**

Use `class X(str, Enum)`, not `StrEnum`, to retain Python 3.10 support. Define `JobState` exactly as:

```python
QUEUED, BLOCKED, READY, RUNNING, VERIFYING, CHECKPOINTED,
REQUEUE, SUCCEEDED, FAILED, QUARANTINED, CANCELLED
```

Define `ErrorClass` exactly as:

```python
AUTH_REQUIRED, ENV_MISSING, DEPENDENCY_MISSING, SOURCE_NOT_FOUND,
TEST_REGRESSION, PROVIDER_QUOTA, PROVIDER_DOWN, BUDGET_EXCEEDED,
LICENSE_BLOCK, NONDETERMINISTIC, IDENTITY_FAIL, CONTINUITY_FAIL,
WRITE_SCOPE_VIOLATION, CANONICAL_BRANCH_GUARD, CHECKPOINT_CORRUPT, UNKNOWN
```

`JobManifest.new()` initializes refs/hashes/dependencies/evidence empty, state `QUEUED`, attempt `0`, and UTC timestamps. Recursively inspect mapping keys before accepting a manifest; reject keys containing `secret`, `password`, `token`, `api_key`, `apikey`, or `credential`. Reject non-EUR currency and negative budget/limit values.

- [ ] **Step 4: Run focused tests**

```bash
python -m unittest tests.loop_factory.test_model -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory tests/loop_factory
git commit -m "feat(loop-factory): add CELL-000 job contract"
```

---

### Task 2: Deterministic State Machine

**Files:**
- Create: `core/loop_factory/state_machine.py`
- Create: `tests/loop_factory/test_state_machine.py`

**Interfaces:**
- `TERMINAL_STATES: frozenset[JobState]`.
- `is_terminal(state: JobState) -> bool`.
- `assert_transition(current: JobState, target: JobState) -> None`.
- `initial_state_for_new_attempt() -> JobState` returns `READY`.

- [ ] **Step 1: Write failing transition tests**

```python
import unittest
from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.model import JobState
from core.loop_factory.state_machine import assert_transition, is_terminal


class StateMachineTests(unittest.TestCase):
    def test_happy_path_is_legal(self):
        path = [JobState.QUEUED, JobState.READY, JobState.RUNNING,
                JobState.VERIFYING, JobState.CHECKPOINTED, JobState.SUCCEEDED]
        for current, target in zip(path, path[1:]):
            assert_transition(current, target)

    def test_terminal_attempt_has_no_outgoing_transition(self):
        self.assertTrue(is_terminal(JobState.SUCCEEDED))
        with self.assertRaises(LoopFactoryError):
            assert_transition(JobState.SUCCEEDED, JobState.RUNNING)

    def test_recoverable_attempt_can_request_requeue(self):
        assert_transition(JobState.RUNNING, JobState.REQUEUE)
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m unittest tests.loop_factory.test_state_machine -v
```

- [ ] **Step 3: Implement a closed transition map**

Legal transitions:

```text
QUEUED -> READY | BLOCKED | CANCELLED
BLOCKED -> READY | CANCELLED
READY -> RUNNING | CANCELLED
RUNNING -> VERIFYING | CHECKPOINTED | REQUEUE | FAILED | QUARANTINED | CANCELLED
VERIFYING -> CHECKPOINTED | REQUEUE | FAILED | QUARANTINED | CANCELLED
CHECKPOINTED -> RUNNING | VERIFYING | SUCCEEDED | REQUEUE | FAILED | QUARANTINED | CANCELLED
REQUEUE -> CANCELLED
```

`REQUEUE` terminates the current attempt. Starting a requeued job creates a new `AttemptRecord` in `READY`; do not mutate the old attempt back to READY.

- [ ] **Step 4: Run tests**

```bash
python -m unittest tests.loop_factory.test_state_machine -v
```

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/state_machine.py tests/loop_factory/test_state_machine.py
git commit -m "feat(loop-factory): enforce deterministic state transitions"
```

---

### Task 3: Fail-Closed Branch and Write-Scope Guards

**Files:**
- Create: `core/loop_factory/guards.py`
- Create: `tests/loop_factory/test_policy_guards.py`

**Interfaces:**
- `detect_git_branch(repo_root: Path) -> str`.
- `assert_noncanonical_branch(branch: str, canonical_branches: AbstractSet[str] = frozenset({"main", "master"})) -> None`.
- `assert_write_scope(target: Path, scopes: Sequence[Path]) -> None`.

- [ ] **Step 1: Write failing guard tests**

```python
import tempfile
import unittest
from pathlib import Path
from core.loop_factory.errors import LoopFactoryError
from core.loop_factory.model import ErrorClass
from core.loop_factory.guards import assert_noncanonical_branch, assert_write_scope


class GuardTests(unittest.TestCase):
    def test_main_and_master_fail_closed(self):
        for branch in ("main", "master"):
            with self.assertRaises(LoopFactoryError) as ctx:
                assert_noncanonical_branch(branch)
            self.assertEqual(ctx.exception.error_class, ErrorClass.CANONICAL_BRANCH_GUARD)

    def test_feature_branch_is_allowed(self):
        assert_noncanonical_branch("feat/loop-factory-cell-000")

    def test_out_of_scope_target_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "main.py"
            with self.assertRaises(LoopFactoryError) as ctx:
                assert_write_scope(outside, [root / "sandbox"])
            self.assertEqual(ctx.exception.error_class, ErrorClass.WRITE_SCOPE_VIOLATION)
            self.assertFalse(outside.exists())
```

- [ ] **Step 2: Run red test**

```bash
python -m unittest tests.loop_factory.test_policy_guards.GuardTests -v
```

- [ ] **Step 3: Implement path-safe guards**

Resolve targets/scopes with `Path.resolve(strict=False)`. A target is legal only when it equals an allowed scope or that scope is in `target.parents`. Empty scope rejects mutation. `detect_git_branch()` runs `git -C <root> rev-parse --abbrev-ref HEAD`; Git failure, blank output, or detached `HEAD` maps to `ENV_MISSING` and fails closed. No caller may substitute the repository default branch when branch detection fails.

- [ ] **Step 4: Run tests**

```bash
python -m unittest tests.loop_factory.test_policy_guards.GuardTests -v
```

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/guards.py tests/loop_factory/test_policy_guards.py
git commit -m "feat(loop-factory): fail closed on unsafe writes"
```

---

### Task 4: Autonomy, Security, Promotion, and Budget Policy

**Files:**
- Create: `core/loop_factory/policy.py`
- Modify: `tests/loop_factory/test_policy_guards.py`

**Interfaces:**
- `ActionRequest(name: str, required_level: AutonomyLevel = A0, mutation: bool = False, target_branch: str | None = None, target_path: Path | None = None, estimated_cost_eur: float = 0.0, destructive: bool = False, security_sensitive: bool = False, promotion: bool = False)`.
- `PolicyDecision(allowed: bool, error_class: ErrorClass | None, reason: str)`.
- `PolicyEngine.evaluate(job: JobManifest, action: ActionRequest, *, explicit_authorization: bool = False) -> PolicyDecision`.

- [ ] **Step 1: Add failing policy tests**

```python
from core.loop_factory.model import AutonomyLevel, Budget, ErrorClass, JobManifest
from core.loop_factory.policy import ActionRequest, PolicyEngine


class PolicyTests(unittest.TestCase):
    def make_job(self, level=AutonomyLevel.A2, max_cost=0.0):
        return JobManifest.new(
            job_id="policy-test", project="KAI_LOOP_FACTORY", cell_type="BUILD",
            goal="policy test", write_scope=["/tmp/kai-sandbox"],
            autonomy_level=level, allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=max_cost, max_iterations=2, max_retries=1, timeout_seconds=30),
        )

    def test_cost_above_budget_is_denied(self):
        decision = PolicyEngine().evaluate(
            self.make_job(max_cost=0.0),
            ActionRequest(name="gpu", estimated_cost_eur=0.01),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.error_class, ErrorClass.BUDGET_EXCEEDED)

    def test_promotion_requires_explicit_authorization(self):
        decision = PolicyEngine().evaluate(
            self.make_job(level=AutonomyLevel.A4),
            ActionRequest(name="merge", required_level=AutonomyLevel.A4, promotion=True, mutation=True,
                          target_branch="feat/candidate"),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.error_class, ErrorClass.AUTH_REQUIRED)

    def test_security_action_never_self_authorizes(self):
        job = self.make_job(level=AutonomyLevel.A5)
        action = ActionRequest(name="rotate-secret", required_level=AutonomyLevel.A5,
                               security_sensitive=True, mutation=True)
        self.assertFalse(PolicyEngine().evaluate(job, action).allowed)
        self.assertTrue(PolicyEngine().evaluate(job, action, explicit_authorization=True).allowed)
```

- [ ] **Step 2: Run red test**

```bash
python -m unittest tests.loop_factory.test_policy_guards.PolicyTests -v
```

- [ ] **Step 3: Implement evaluation order**

Evaluate: malformed/negative cost -> budget -> required autonomy level -> A5/destructive/security authorization -> A4 promotion authorization -> canonical branch guard -> write-scope guard -> allow. Never set `explicit_authorization=True` internally.

- [ ] **Step 4: Run full guard/policy module**

```bash
python -m unittest tests.loop_factory.test_policy_guards -v
```

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/policy.py tests/loop_factory/test_policy_guards.py
git commit -m "feat(loop-factory): add governed action policy"
```

---

### Task 5: SQLite Jobs, Attempts, Checkpoints, Receipts, and Evidence Storage

**Files:**
- Create: `core/loop_factory/store.py`
- Create: `tests/loop_factory/test_store.py`
- Modify: `.gitignore`

**Interfaces:**
- `LoopStore(path: Path)`; `initialize() -> None`; `close() -> None`.
- `create_job(job: JobManifest) -> None`; `get_job(job_id: str) -> JobManifest`; `update_job(job: JobManifest) -> None`.
- `start_attempt(job_id: str, worker: str, parent_run_id: str | None = None) -> AttemptRecord`.
- `get_latest_attempt(job_id: str) -> AttemptRecord | None`.
- `heartbeat(run_id: str, lease_until: str) -> None`.
- `mark_attempt_state(run_id: str, state: JobState, *, error_class: ErrorClass | None = None, next_exact_action: str | None = None, cost_eur: float | None = None) -> None`.
- `append_checkpoint(run_id: str, job_id: str, payload: Mapping[str, object]) -> str` returns checkpoint ID.
- `latest_checkpoint(job_id: str) -> dict[str, object] | None`.
- `record_step_receipt(job_id: str, attempt_no: int, step_key: str, input_hash: str, output_hash: str, evidence_ref: str) -> None`.
- `find_step_receipt(job_id: str, attempt_no: int, step_key: str, input_hash: str) -> dict[str, object] | None`.
- `commit_step(run_id: str, job_id: str, attempt_no: int, step_key: str, input_hash: str, output_hash: str, evidence_ref: str, checkpoint_payload: Mapping[str, object]) -> str` atomically inserts receipt + checkpoint.
- `append_evidence(record: EvidenceRecord) -> None`; `list_evidence(job_id: str) -> list[EvidenceRecord]`.

- [ ] **Step 1: Write failing persistence tests**

```python
import tempfile
import unittest
from pathlib import Path
from core.loop_factory.model import AutonomyLevel, Budget, JobManifest
from core.loop_factory.store import LoopStore


class LoopStoreTests(unittest.TestCase):
    def test_job_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.loopfactory.db"
            job = JobManifest.new(
                job_id="persist-me", project="KAI_LOOP_FACTORY", cell_type="BUILD", goal="persist",
                write_scope=[str(Path(tmp) / "sandbox")], autonomy_level=AutonomyLevel.A2,
                allowed_tools=["demo-file"],
                budget=Budget(max_cost_eur=0, max_iterations=2, max_retries=1, timeout_seconds=30),
            )
            store = LoopStore(db); store.initialize(); store.create_job(job); store.close()
            reopened = LoopStore(db); reopened.initialize()
            self.assertEqual(reopened.get_job("persist-me"), job)

    def test_duplicate_step_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LoopStore(Path(tmp) / "state.loopfactory.db"); store.initialize()
            store.record_step_receipt("job", 1, "demo/write", "abc", "def", "ev-1")
            with self.assertRaises(ValueError):
                store.record_step_receipt("job", 1, "demo/write", "abc", "def", "ev-2")
```

- [ ] **Step 2: Run red test**

```bash
python -m unittest tests.loop_factory.test_store -v
```

- [ ] **Step 3: Implement schema and transactions**

Use these tables:

```sql
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY, manifest_json TEXT NOT NULL, state TEXT NOT NULL,
  attempt INTEGER NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
  run_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, attempt_no INTEGER NOT NULL,
  parent_run_id TEXT, state TEXT NOT NULL, worker TEXT, lease_until TEXT,
  timestamp_start TEXT NOT NULL, timestamp_end TEXT, retry_count INTEGER NOT NULL DEFAULT 0,
  cost_eur REAL NOT NULL DEFAULT 0, error_class TEXT, next_exact_action TEXT,
  UNIQUE(job_id, attempt_no)
);
CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, job_id TEXT NOT NULL,
  sequence INTEGER NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL, UNIQUE(run_id, sequence)
);
CREATE TABLE IF NOT EXISTS step_receipts (
  job_id TEXT NOT NULL, attempt_no INTEGER NOT NULL, step_key TEXT NOT NULL,
  input_hash TEXT NOT NULL, output_hash TEXT NOT NULL, evidence_ref TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY(job_id, attempt_no, step_key, input_hash)
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, job_id TEXT NOT NULL,
  record_json TEXT NOT NULL, created_at TEXT NOT NULL
);
```

Use parameterized SQL and connection transactions. Canonicalize checkpoint JSON with `sort_keys=True` and compact separators before SHA-256. `commit_step()` must insert receipt and checkpoint within one SQLite transaction. Terminal attempt rows cannot be changed back to nonterminal states.

Append to `.gitignore`:

```text
.kai-loop/
*.loopfactory.db
*.loopfactory.db-*
```

- [ ] **Step 4: Run tests**

```bash
python -m unittest tests.loop_factory.test_store -v
```

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/store.py tests/loop_factory/test_store.py .gitignore
git commit -m "feat(loop-factory): persist durable loop state"
```

---

### Task 6: Evidence Contract and FREE-FIRST Capability Registry

**Files:**
- Create: `core/loop_factory/evidence.py`
- Create: `core/loop_factory/capabilities.py`
- Create: `tests/loop_factory/test_capabilities.py`

**Interfaces:**
- `sha256_bytes(data: bytes) -> str`; `sha256_text(text: str) -> str`; `sha256_file(path: Path) -> str`.
- `EvidenceRecord` contains all observability fields from the spec and `to_dict()/from_dict()`.
- `Availability(str, Enum)`: `UNKNOWN`, `AVAILABLE`, `UNAVAILABLE`.
- `CostClass(IntEnum)`: `LOCAL=0`, `OPEN=1`, `INCLUDED=2`, `PAID=3`.
- `WorkerCapability(worker_id: str, capabilities: frozenset[str], locality: str, cost_class: CostClass, availability: Availability, estimated_cost_eur: float, license_notes: str = "", metadata: Mapping[str, str] = ...)`.
- `CapabilityRegistry.register(worker: WorkerCapability) -> None`.
- `CapabilityRegistry.candidates(capability: str, max_cost_eur: float) -> list[WorkerCapability]`.
- `default_cell000_registry() -> CapabilityRegistry`.

- [ ] **Step 1: Write failing ranking/hash tests**

```python
import unittest
from core.loop_factory.capabilities import Availability, CapabilityRegistry, CostClass, WorkerCapability, default_cell000_registry
from core.loop_factory.evidence import sha256_text


class CapabilityTests(unittest.TestCase):
    def test_free_first_ranking_is_deterministic(self):
        registry = CapabilityRegistry()
        registry.register(WorkerCapability("paid", frozenset({"python.test"}), "cloud", CostClass.PAID, Availability.AVAILABLE, 0.10))
        registry.register(WorkerCapability("local", frozenset({"python.test"}), "local", CostClass.LOCAL, Availability.AVAILABLE, 0.0))
        self.assertEqual([x.worker_id for x in registry.candidates("python.test", 1.0)], ["local", "paid"])

    def test_unknown_hf_job_is_not_selected(self):
        ids = [x.worker_id for x in default_cell000_registry().candidates("gpu.burst", 100)]
        self.assertNotIn("hf-jobs", ids)

    def test_sha256_is_stable(self):
        self.assertEqual(sha256_text("kai"), sha256_text("kai"))
```

- [ ] **Step 2: Run red test**

```bash
python -m unittest tests.loop_factory.test_capabilities -v
```

- [ ] **Step 3: Implement deterministic registry/evidence**

Filter candidates to `AVAILABLE` and `estimated_cost_eur <= max_cost_eur`; sort by `(cost_class, estimated_cost_eur, worker_id)`. Seed static identities for `github-actions`, `termux`, `pc`, and `hf-jobs`, but mark live availability `UNKNOWN` until runtime probes confirm it. Do not fossilize today's machine/auth audit as permanent truth.

`EvidenceRecord` fields are: `run_id`, `job_id`, `parent_run_id`, `timestamp_start`, `timestamp_end`, `host`, `worker`, `model_or_provider`, `tool`, `input_hashes`, `output_hashes`, `branch`, `commit_sha`, `provider_job_id`, `cost_eur`, `duration_ms`, `retry_count`, `test_summary`, `result_state`, `error_class`, `next_exact_action`. No secret-value field exists.

- [ ] **Step 4: Run tests**

```bash
python -m unittest tests.loop_factory.test_capabilities -v
```

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/evidence.py core/loop_factory/capabilities.py tests/loop_factory/test_capabilities.py
git commit -m "feat(loop-factory): add evidence and capability routing"
```

---

### Task 7: Deterministic Worker and One-Iteration Runner

**Files:**
- Create: `core/loop_factory/workers.py`
- Create: `core/loop_factory/runner.py`
- Create: `tests/loop_factory/test_runner.py`

**Interfaces:**
- `StepContext(job: JobManifest, run_id: str, sandbox: Path, input_hash: str)`.
- `StepOutcome(output_hash: str, evidence_summary: str, cost_eur: float = 0.0, verified: bool = True)`.
- `Worker` protocol: `worker_id: str`; `run(context: StepContext) -> StepOutcome`.
- `DemoFileWorker(sandbox: Path, on_write: Callable[[], None] | None = None)`.
- `RunResult(run_id: str, state: JobState, evidence_ref: str | None, next_exact_action: str | None)`.
- `LoopRunner.run_once(job_id: str, *, branch: str, worker_id: str = "demo-file", after_checkpoint: Callable[[], None] | None = None) -> RunResult`.

- [ ] **Step 1: Write failing success and crash/resume tests**

```python
import tempfile
import unittest
from pathlib import Path
from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState
from core.loop_factory.runner import LoopRunner
from core.loop_factory.store import LoopStore
from core.loop_factory.workers import DemoFileWorker


class LoopRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); root = Path(self.tmp.name)
        self.sandbox = root / "sandbox"
        self.store = LoopStore(root / "state.loopfactory.db"); self.store.initialize()
        job = JobManifest.new(
            job_id="demo", project="KAI_LOOP_FACTORY", cell_type="BUILD",
            goal="write deterministic marker", write_scope=[str(self.sandbox)],
            autonomy_level=AutonomyLevel.A2, allowed_tools=["demo-file"],
            budget=Budget(max_cost_eur=0, max_iterations=3, max_retries=1, timeout_seconds=30),
        )
        self.store.create_job(job)

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def test_run_succeeds_on_feature_branch(self):
        runner = LoopRunner(self.store, {"demo-file": DemoFileWorker(self.sandbox)})
        result = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(result.state, JobState.SUCCEEDED)
        self.assertTrue((self.sandbox / "demo.txt").exists())

    def test_crash_after_checkpoint_resumes_without_duplicate_write(self):
        calls = {"count": 0}
        worker = DemoFileWorker(self.sandbox, on_write=lambda: calls.__setitem__("count", calls["count"] + 1))
        runner = LoopRunner(self.store, {"demo-file": worker})
        def crash():
            raise RuntimeError("simulated process death")
        with self.assertRaises(RuntimeError):
            runner.run_once("demo", branch="feat/loop-factory-cell-000", after_checkpoint=crash)
        self.assertEqual(calls["count"], 1)
        result = runner.run_once("demo", branch="feat/loop-factory-cell-000")
        self.assertEqual(result.state, JobState.SUCCEEDED)
        self.assertEqual(calls["count"], 1)
```

Add cases for `main` rejection, write-scope rejection, budget ceiling, iteration ceiling, retry ceiling, timeout accounting, expired lease recovery, and `UNKNOWN` quarantine after the retry ceiling.

- [ ] **Step 2: Run red test**

```bash
python -m unittest tests.loop_factory.test_runner -v
```

- [ ] **Step 3: Implement exactly one bounded iteration**

`DemoFileWorker` writes `demo.txt` via temporary sibling + `Path.replace()` and returns a SHA-256. Its deterministic content derives only from `job_id`, `goal`, and `input_hash`.

`run_once()` sequence:

```text
RESTORE job/attempt/checkpoint
validate dependency + cost/iteration/retry/timeout ceilings
policy + branch + write-scope preflight
create or recover attempt + lease
compute step_key/input_hash
if receipt exists: skip ACT
else ACT exactly once
atomically commit receipt + checkpoint
optional after_checkpoint hook
VERIFY output/evidence
append structured evidence
mark terminal state or REQUEUE
return exact next action
```

Use `uuid.uuid4().hex` for IDs and timezone-aware UTC timestamps. A stale `RUNNING` attempt is recoverable only after lease expiry and is never assumed successful. Arbitrary exceptions map to `UNKNOWN`; if retries remain, terminalize the attempt as `REQUEUE` and create a fresh attempt on the next `run_once`; at ceiling, `QUARANTINED`. Never use an unbounded loop.

Timeout enforcement in CELL-000 is fail-closed accounting around a single worker call: compare elapsed monotonic time before and after `ACT`; an overrun cannot be marked success and becomes `FAILED`/`REQUEUE` according to retry policy. Worker-level hard process preemption is deferred to worker adapters that execute external subprocesses; the deterministic demo worker is in-process and bounded.

BUILD cannot become `SUCCEEDED` unless `StepOutcome.verified` is true and a verification evidence record is persisted.

- [ ] **Step 4: Run twice**

```bash
python -m unittest tests.loop_factory.test_runner -v
python -m unittest tests.loop_factory.test_runner -v
```

Both runs must PASS.

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/workers.py core/loop_factory/runner.py tests/loop_factory/test_runner.py
git commit -m "feat(loop-factory): execute restart-safe single iterations"
```

---

### Task 8: Drive-Ready Writeback and CLI

**Files:**
- Create: `core/loop_factory/writeback.py`
- Create: `core/loop_factory/cli.py`
- Create: `core/loop_factory/__main__.py`
- Create: `tests/loop_factory/test_cli.py`

**Interfaces:**
- `build_drive_checkpoint_payload(job: JobManifest, attempt: AttemptRecord | None, evidence: Sequence[EvidenceRecord]) -> dict[str, object]`.
- `render_drive_checkpoint_markdown(payload: Mapping[str, object]) -> str`.
- `main(argv: Sequence[str] | None = None) -> int`.
- Commands: `init`, `create`, `show`, `run-once`, `checkpoint`, `requeue`, `cancel`, `workers`.

- [ ] **Step 1: Write failing CLI/writeback tests**

```python
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from core.loop_factory.cli import main
from core.loop_factory.writeback import render_drive_checkpoint_markdown


class CliTests(unittest.TestCase):
    def test_init_creates_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.loopfactory.db"
            self.assertEqual(main(["init", "--db", str(db)]), 0)
            self.assertTrue(db.exists())

    def test_workers_output_is_json(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(["workers"])
        self.assertEqual(code, 0)
        self.assertIsInstance(json.loads(stream.getvalue()), list)

    def test_checkpoint_markdown_has_next_action(self):
        text = render_drive_checkpoint_markdown({"job_id": "demo", "next_exact_action": "review evidence"})
        self.assertIn("demo", text)
        self.assertIn("review evidence", text)
```

- [ ] **Step 2: Run red test**

```bash
python -m unittest tests.loop_factory.test_cli -v
```

- [ ] **Step 3: Implement machine-readable CLI**

Required commands:

```bash
python -m core.loop_factory init --db .kai-loop/loopfactory.db
python -m core.loop_factory create --db .kai-loop/loopfactory.db --manifest job.json
python -m core.loop_factory show --db .kai-loop/loopfactory.db CELL-000-DEMO
python -m core.loop_factory run-once --db .kai-loop/loopfactory.db CELL-000-DEMO --sandbox .kai-loop/sandboxes/CELL-000-DEMO --branch feat/loop-factory-cell-000
python -m core.loop_factory checkpoint --db .kai-loop/loopfactory.db CELL-000-DEMO --format markdown
python -m core.loop_factory requeue --db .kai-loop/loopfactory.db CELL-000-DEMO --reason "retry after environment repair"
python -m core.loop_factory cancel --db .kai-loop/loopfactory.db CELL-000-DEMO --reason "operator cancelled"
python -m core.loop_factory workers
```

Every command except Markdown checkpoint output emits one JSON document. Operational errors emit one JSON error document to stderr and nonzero exit. If `--branch` is omitted, call `detect_git_branch(Path.cwd())`; never infer/default `main`.

`requeue` never mutates a terminal attempt. It updates job scheduling metadata and the next `run-once` creates a fresh attempt whose `parent_run_id` points to the prior attempt.

- [ ] **Step 4: Run tests/help smoke**

```bash
python -m unittest tests.loop_factory.test_cli -v
python -m core.loop_factory --help
```

- [ ] **Step 5: Commit**

```bash
git add core/loop_factory/writeback.py core/loop_factory/cli.py core/loop_factory/__main__.py tests/loop_factory/test_cli.py
git commit -m "feat(loop-factory): expose governed CLI and writeback"
```

---

### Task 9: CELL-000 Acceptance Gate and GitHub Actions

**Files:**
- Create: `tests/loop_factory/test_cell000_acceptance.py`
- Create: `.github/workflows/test-loop-factory.yml`

**Interfaces:**
- Acceptance tests are the executable definition of the 12 CELL-000 completion criteria.
- CI supplies promotion evidence only; it does not auto-merge or deploy.

- [ ] **Step 1: Write end-to-end crash/resume acceptance test**

```python
import tempfile
import unittest
from pathlib import Path
from core.loop_factory.model import AutonomyLevel, Budget, JobManifest, JobState
from core.loop_factory.runner import LoopRunner
from core.loop_factory.store import LoopStore
from core.loop_factory.writeback import build_drive_checkpoint_payload
from core.loop_factory.workers import DemoFileWorker


class Cell000AcceptanceTests(unittest.TestCase):
    def test_fresh_state_survives_checkpoint_crash_and_resumes_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "state.loopfactory.db"; sandbox = root / "sandbox"
            store = LoopStore(db); store.initialize()
            job = JobManifest.new(
                job_id="CELL-000-ACCEPTANCE", project="KAI_LOOP_FACTORY", cell_type="BUILD",
                goal="prove durable autonomy substrate", write_scope=[str(sandbox)],
                autonomy_level=AutonomyLevel.A2, allowed_tools=["demo-file"],
                budget=Budget(max_cost_eur=0, max_iterations=3, max_retries=1, timeout_seconds=30),
            )
            store.create_job(job)
            writes = {"count": 0}
            worker = DemoFileWorker(sandbox, on_write=lambda: writes.__setitem__("count", writes["count"] + 1))
            runner = LoopRunner(store, {"demo-file": worker})
            def crash():
                raise RuntimeError("kill after durable checkpoint")
            with self.assertRaises(RuntimeError):
                runner.run_once(job.job_id, branch="feat/loop-factory-cell-000", after_checkpoint=crash)
            store.close()

            reopened = LoopStore(db); reopened.initialize()
            result = LoopRunner(reopened, {"demo-file": worker}).run_once(
                job.job_id, branch="feat/loop-factory-cell-000")
            self.assertEqual(result.state, JobState.SUCCEEDED)
            self.assertEqual(writes["count"], 1)
            payload = build_drive_checkpoint_payload(
                reopened.get_job(job.job_id), reopened.get_latest_attempt(job.job_id), reopened.list_evidence(job.job_id))
            self.assertEqual(payload["job_id"], job.job_id)
            self.assertTrue(payload["next_exact_action"])
```

Add separate acceptance methods asserting: fresh manifest persistence; deterministic demo output; checkpoint creation; `main` rejection before mutation; out-of-scope rejection; budget ceiling; retry ceiling; iteration ceiling; timeout overrun cannot succeed; structured evidence exists; CLI create/show/checkpoint works; Drive-ready payload works without any network connection.

- [ ] **Step 2: Run complete suite before CI**

```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
```

Every one of the 12 completion criteria must map to an assertion before continuing.

- [ ] **Step 3: Add GitHub-hosted CI**

Create `.github/workflows/test-loop-factory.yml`:

```yaml
name: Test Loop Factory

on:
  pull_request:
    paths:
      - 'core/loop_factory/**'
      - 'tests/loop_factory/**'
      - 'docs/loop_factory/**'
      - 'docs/superpowers/specs/2026-09-16-autonomy-foundation-design.md'
      - 'docs/superpowers/plans/2026-09-16-autonomy-foundation.md'
      - '.github/workflows/test-loop-factory.yml'
      - '.gitignore'
  push:
    branches: ['feat/loop-factory-cell-000']
    paths:
      - 'core/loop_factory/**'
      - 'tests/loop_factory/**'
      - '.github/workflows/test-loop-factory.yml'

permissions:
  contents: read

jobs:
  unittest:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Compile Loop Factory
        run: python -m compileall -q core/loop_factory
      - name: Run CELL-000 tests
        run: python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
```

- [ ] **Step 4: Run local CI equivalent**

```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/loop_factory/test_cell000_acceptance.py .github/workflows/test-loop-factory.yml
git commit -m "test(loop-factory): gate CELL-000 end to end"
```

---

### Task 10: Runbook, Independent Review, Draft PR, and Documentary Writeback

**Files:**
- Create: `docs/loop_factory/CELL_000_RUNBOOK.md`
- Verify: spec and plan remain unchanged except separately reviewed documentation fixes.

**Interfaces:**
- Runbook documents human recovery and exact commands.
- Promotion remains a separate A4 action; this task does not merge to `main`.

- [ ] **Step 1: Write runbook from verified commands**

It must contain:

```markdown
# CELL-000 Runbook

## Authorities
- GitHub: live code and commits.
- SQLite: runtime job/attempt/checkpoint/evidence state.
- Drive: documentary CURRENT/checkpoint writeback only.

## Fresh start
python -m core.loop_factory init --db .kai-loop/loopfactory.db

## Focused verification
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v

## Branch safety
Never run a mutating cell on `main` or `master`.

## Crash recovery
1. Re-open the same SQLite database.
2. Inspect the job with `show`.
3. Inspect the latest checkpoint.
4. Execute exactly one `run-once`.
5. Confirm the existing receipt prevents duplicate side effects.

## Promotion gate
Promotion requires fresh CI evidence, reviewed diff, expected head SHA,
rollback path, and explicit A4 approval.
```

Document CELL-000 limits: no distributed lock service, no live provider probes, no UI, no automatic Drive write, no automatic merge, no background daemon, and no generic hard-kill mechanism for arbitrary in-process workers.

- [ ] **Step 2: Run verification and diff audit**

```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
git status --short
git diff --check
git diff --stat origin/docs/autonomy-foundation-20260916...HEAD
```

Expected: tests PASS, `git diff --check` silent, and only CELL-000 files differ from the approved design/plan base.

- [ ] **Step 3: Commit runbook**

```bash
git add docs/loop_factory/CELL_000_RUNBOOK.md
git commit -m "docs(loop-factory): add CELL-000 recovery runbook"
```

- [ ] **Step 4: Push isolated implementation branch**

```bash
git push -u origin feat/loop-factory-cell-000
```

Before pushing, verify:

```bash
test "$(git rev-parse --abbrev-ref HEAD)" = "feat/loop-factory-cell-000"
git merge-base --is-ancestor origin/docs/autonomy-foundation-20260916 HEAD
```

- [ ] **Step 5: Open a draft PR to `main`**

PR body records: spec path, plan path, exact focused test command/result count, CI run ID/URL when available, head SHA, confirmation of canonical-write guard, and rollback path. Keep PR draft; do not enable auto-merge.

- [ ] **Step 6: Independent review gate**

Review specifically for: implicit/direct canonical writes; path traversal/symlink escape; transaction gaps between receipt/checkpoint; retry paths without ceilings; serialized/logged secrets; terminal attempts mutated in place; missing verification evidence; frozen assumptions about PC/Termux/HF availability; non-hosted CI runners.

Any finding is repaired on the feature branch, then full tests rerun and a new commit produced. Review and merge are never the same operation.

- [ ] **Step 7: Produce documentary checkpoint after verified implementation**

```bash
python -m core.loop_factory checkpoint --db .kai-loop/loopfactory.db CELL-000-ACCEPTANCE --format markdown
```

Use the resulting payload to update the affected Drive CURRENT/checkpoint via the authorized Drive connector. Core execution remains valid if Drive is unavailable.

- [ ] **Step 8: Final candidate evidence**

```bash
git log --oneline --decorate -12
git status --short
git rev-parse HEAD
```

Expected: clean working tree and small CELL-000 commits. Merging/promoting to `main` is a later A4 action with explicit approval and expected-head verification.

---

## Plan-to-Spec Coverage Matrix

| Spec requirement | Plan coverage |
|---|---|
| Typed job/state schema + serialization | Task 1 |
| Error taxonomy | Tasks 1, 7 |
| Deterministic state transitions | Task 2 |
| Canonical branch/write-scope guard | Task 3 |
| Autonomy/budget/security policy | Task 4 |
| SQLite jobs/attempts/checkpoints | Task 5 |
| Atomic receipt + checkpoint | Task 5 |
| Structured evidence | Task 6 |
| FREE-FIRST capability registry | Task 6 |
| One bounded iteration | Task 7 |
| Restart/resume + idempotency | Tasks 5, 7, 9 |
| Lease recovery | Task 7 |
| Cost/iteration/retry/timeout ceilings | Tasks 4, 7, 9 |
| CLI create/show/run-once/checkpoint/requeue/cancel | Task 8 |
| Drive-ready writeback without Drive dependency | Tasks 8, 9, 10 |
| Fresh-state acceptance gate | Task 9 |
| GitHub-hosted CI | Task 9 |
| Human recovery runbook | Task 10 |
| Separate promotion gate | Tasks 4, 10 |
| Isolated worktree before implementation | Mandatory Execution Preflight |

## Execution Boundary

This plan stops at a reviewed **draft PR** and evidence-ready checkpoint. It does not merge to `main`, enable auto-merge, change repository protection settings, provision paid compute, rotate credentials, install a self-hosted GitHub runner, or start a long-running daemon. Those are separately governed actions.
