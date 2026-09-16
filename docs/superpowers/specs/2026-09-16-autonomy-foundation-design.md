# KAI Autonomy Foundation Design

**Date:** 2026-09-16  
**Status:** APPROVED DESIGN / PRE-IMPLEMENTATION  
**Project:** KAI Loop Factory, transversal infrastructure for KAI Media Forge Omega and the wider KAI ecosystem  
**Repository:** `Bashull/Kai`  
**Authority model:** Drive for documentary CURRENT/checkpoints; GitHub for code; PC/Termux for local execution; Hugging Face and creative providers as capability workers.

## 1. Purpose

Build a durable, resumable, evidence-driven autonomy layer that can execute small, bounded work cells across recovery, coding, testing, media production, QA, promotion, and documentation without relying on one long-lived chat or one provider.

The system must remain understandable and recoverable by a human. Autonomy is permissioned by scope, not granted globally.

## 2. Core principles

1. `REUSE -> ADAPT -> COMPOSE -> ACQUIRE -> BUILD`.
2. One cell owns one clear objective and one write scope.
3. Fresh context per iteration; persistent state lives in durable artifacts.
4. No important result exists only in model memory.
5. Every external mutation is attributable to a run, a job, a worker, and evidence.
6. Work is restart-safe and idempotent where practical.
7. Generated media may be nondeterministic; orchestration, manifests, timelines, hashes, and promotion are deterministic.
8. `KNOWN != UNDERSTOOD`; `NOT READ != DOES NOT EXIST`.
9. Donors are preserved until Transfer x3 is complete: direct, transversal, emergent.
10. No loop is infinite. Every loop has max iterations, max retries, timeout, budget, and an explicit terminal state.

## 3. Non-goals for CELL-000

CELL-000 does not build the final Media Forge Workspace, generate a complete film, merge PR #33, recover all Fusion Studio source, or install a large orchestration platform.

CELL-000 establishes the contracts and guardrails required before autonomous implementation begins.

## 4. System architecture

KAI Loop Factory has seven logical components.

### 4.1 Supervisor

Owns the queue and dependency graph. It selects the next eligible cell but does not implement domain work itself.

Responsibilities:
- load durable job state;
- verify dependencies and gates;
- choose a worker through the capability router;
- enforce retry, iteration, cost, and permission limits;
- move jobs between states;
- record the next exact action.

### 4.2 Loop Engine

Executes exactly one bounded iteration of one cell.

Canonical iteration:

`RESTORE -> LOAD_MINIMUM_CONTEXT -> SELECT_CELL -> PLAN -> ACT -> VERIFY -> EVIDENCE -> CHECKPOINT -> LEARN -> EXIT_OR_REQUEUE`

### 4.3 Policy Engine

Answers whether an intended action is allowed without a new human approval.

Policy decisions are based on autonomy level, target, mutation type, reversibility, budget, secrets/security impact, and current project authority.

### 4.4 Capability Router

Matches task requirements to available workers/providers by capability, health, locality, license, cost, quota, privacy, latency, reproducibility, and required references.

The domain layer requests capabilities, not branded providers.

### 4.5 Workers

Initial worker families:
- GitHub Actions for clean CI and deterministic validation;
- Termux for always-near local scripts and FFmpeg;
- PC for worktrees, Python/Node, Blender or heavier local work;
- Hugging Face Jobs for optional burst CPU/GPU;
- Codex/agentic coding workers for implementation tasks;
- creative provider adapters for image/video/audio generation;
- deterministic renderers such as FFmpeg, Remotion, and Blender.

### 4.6 Evidence Store

Persists evidence for every completed or failed cell: inputs, hashes, outputs, logs, tests, commits, provider IDs, cost, retries, provenance, and QA findings.

### 4.7 Writeback Engine

Updates documentary authorities only after a cell reaches a terminal state. Writeback must be narrow and tied to the run that produced it.

## 5. Durable job contract

Every job must serialize at least:

```yaml
schema_version: 1
job_id: string
project: string
cell_type: string
goal: string
current_authority_refs: [string]
input_refs: [string]
input_hashes: {string: string}
dependencies: [string]
allowed_tools: [string]
write_scope: [string]
autonomy_level: A0|A1|A2|A3|A4|A5
budget:
  currency: EUR
  max_cost: number
  max_iterations: integer
  max_retries: integer
  timeout_seconds: integer
state: QUEUED|BLOCKED|READY|RUNNING|VERIFYING|CHECKPOINTED|REQUEUE|SUCCEEDED|FAILED|QUARANTINED|CANCELLED
worker: string|null
attempt: integer
evidence_refs: [string]
last_error_class: string|null
next_exact_action: string|null
created_at: datetime
updated_at: datetime
```

Job manifests must not contain plaintext secrets.

## 6. Autonomy levels

### A0 READ

Search, inspect, compare, inventory, fetch metadata, read logs, and calculate hashes. Fully autonomous.

### A1 SANDBOX

Create temporary files, extract archives, compile, render proxies, run tests, and generate disposable analysis artifacts. Fully autonomous inside approved sandbox paths.

### A2 ISOLATED WRITE

Create worktrees, feature branches, staging outputs, caches, draft manifests, and draft documents. Autonomous only inside explicit write scopes. Direct writes to `main` are forbidden.

### A3 REVERSIBLE EXTERNAL

Create draft PRs, trigger CI, retry failed jobs, upload candidate artifacts, run bounded provider jobs, and update noncanonical draft/checkpoint records. Autonomous only when the job declares the action and budget.

### A4 PROMOTION

Merge, mark CURRENT, publish release candidates, replace canonical artifacts, change deployment state, or promote a candidate to authority. Requires promotion gates. Default is human approval until policy explicitly delegates a narrower promotion class.

### A5 IRREVERSIBLE / MONEY / SECURITY

Delete unique originals, rotate or expose credentials, increase financial commitment beyond an approved budget, alter vault/security policy, remove repositories, or perform destructive deployment actions. Requires explicit human authorization for the exact action.

## 7. Repository safety requirements

Before autonomous code implementation:

1. No implementation worker may write directly to `main`.
2. All autonomous source changes occur in isolated branches/worktrees.
3. Candidate changes enter through PRs.
4. CI must report deterministic test results before promotion.
5. Promotion must verify expected head SHA to avoid race merges.
6. Force-push to protected/canonical branches is prohibited.
7. No self-hosted GitHub runner on an untrusted public-PR path.
8. Prefer short-lived/OIDC credentials where supported over long-lived secrets.
9. A preflight guard must fail closed when the current branch or write target is canonical.

At design time, `main` is observed as unprotected. CELL-000 must therefore include a software guard even before platform-level protection is configured.

## 8. Loop catalogue

### RESTORE LOOP
Reconstruct state from CURRENT, job manifest, evidence, and checkpoint. Terminates when one exact next action is known.

### DISCOVERY LOOP
Find existing code, donors, models, tools, or prior decisions. Terminates with scope-qualified inventory and provenance.

### RECOVERY LOOP
Recover superseded or displaced artifacts without destroying originals. Terminates with hash, location, genealogy, and classification.

### COMPARE LOOP
Compare donor capability against CURRENT. Terminates with `REUSE`, `ADAPT`, `COMPOSE`, `ACQUIRE`, `BUILD`, or `REJECT` plus evidence.

### BUILD LOOP
Implement one bounded unit with TDD. Terminates only when its acceptance tests pass or the cell is blocked/quarantined.

### TEST/REPAIR LOOP
Reproduce, diagnose, fix, rerun focused tests, then regression tests. Never edits `main` directly.

### MEDIA LOOP
Produce one bounded media unit from declared inputs and constraints. Terminates with provenance and candidate output, not automatic promotion.

### QA LOOP
Evaluate identity, continuity, technical validity, narrative intent, audio, and delivery requirements. Produces structured findings.

### REVIEW LOOP
Independent review of a candidate change or artifact. Reviewer must not silently mutate the candidate under review.

### PROMOTION LOOP
Checks required tests, reviews, evidence, expected SHAs, cost, provenance, and rollback path before promotion.

### WRITEBACK LOOP
Updates affected CURRENT/checkpoint/runbook records with the smallest necessary mutation.

### WATCHDOG LOOP
Detects stalled jobs, low disk, failed CI, auth expiry, quota exhaustion, provider outages, and orphaned RUNNING jobs.

### HEAL LOOP
Turns a detected deterministic regression into reproduce -> isolate -> repair -> verify -> review -> PR. No direct canonical write.

## 9. Worker routing

Routing is capability-first and FREE-FIRST.

Preference order is not globally fixed; the router scores candidates. The default economic policy is:

`existing local -> open source -> included/free hosted compute -> approved paid provider -> dedicated cloud fallback`

The router must never silently cross a job's `max_cost`.

Example request:

```yaml
capability: video.image_to_video
requirements:
  duration_seconds: 8
  character_reference: true
  camera_control: medium
  audio: false
  max_cost_eur: 0
```

Provider names belong in adapters, not in story/director domain objects.

## 10. Minimum-context policy

A loop loads only the context required for one cell:
- START_HERE/CURRENT for the project;
- the job manifest and latest checkpoint;
- affected contracts/specifications;
- a bounded set of relevant source files;
- recent focused test/evidence results.

A loop must not ingest the entire KAI corpus by default.

Learnings that should survive the iteration are written to code, tests, runbooks, CURRENT, or evidence; never entrusted only to conversation memory.

## 11. Parallelism policy

Parallel execution is allowed only for cells with disjoint write scopes or an explicit merge boundary.

Each coding worker receives a separate branch/worktree. Two autonomous workers may not concurrently edit the same owned file set.

An integration cell composes independently reviewed outputs.

## 12. Error taxonomy

Every operational failure must map to one of:

- `AUTH_REQUIRED`
- `ENV_MISSING`
- `DEPENDENCY_MISSING`
- `SOURCE_NOT_FOUND`
- `TEST_REGRESSION`
- `PROVIDER_QUOTA`
- `PROVIDER_DOWN`
- `BUDGET_EXCEEDED`
- `LICENSE_BLOCK`
- `NONDETERMINISTIC`
- `IDENTITY_FAIL`
- `CONTINUITY_FAIL`
- `WRITE_SCOPE_VIOLATION`
- `CANONICAL_BRANCH_GUARD`
- `CHECKPOINT_CORRUPT`
- `UNKNOWN`

`UNKNOWN` must not trigger an unbounded retry. It moves to `QUARANTINED` after the configured retry ceiling.

## 13. Observability contract

Each attempt records:

```text
run_id
job_id
parent_run_id
timestamp_start
timestamp_end
host
worker
model_or_provider
tool
input_hashes
output_hashes
branch
commit_sha
provider_job_id
cost_eur
duration_ms
retry_count
test_summary
result_state
error_class
next_exact_action
```

Logs may reference secret handles but may not print secret values.

## 14. CELL-000 implementation scope

CELL-000 will build the minimum autonomy substrate, not the final orchestration platform.

Required deliverables:

1. Typed job/state schema and serialization.
2. Permission/autonomy policy evaluator.
3. Canonical-branch/write-scope guard.
4. SQLite-backed job/checkpoint store.
5. One-iteration loop runner with bounded retry semantics.
6. Worker capability registry with local static entries for GitHub Actions, Termux, PC, and Hugging Face Jobs; creative providers may be represented as disabled/unverified adapters until capability probes exist.
7. Structured evidence records.
8. Failure taxonomy and deterministic state transitions.
9. CLI commands for create/show/run-once/checkpoint/requeue/cancel.
10. Tests proving restart/resume, branch guard, budget guard, retry ceiling, and idempotent completed-step behavior.
11. Documentation writeback format for Drive checkpoints.

## 15. Technology constraints

- Python-first implementation for the control plane.
- SQLite first; no Postgres/Redis/Kafka in CELL-000.
- Standard library where reasonable; dependencies require a concrete capability benefit.
- No new hosted service is a hard dependency.
- No plaintext credentials in repository, SQLite job payloads, or logs.
- GitHub Actions is preferred for public-repo CI.
- Termux is a valid worker and currently has Git, Python, Node, and FFmpeg.
- PC is a valid worker and currently has Git, Python, and Node; FFmpeg availability must be probed instead of assumed.
- Hugging Face Jobs is optional burst compute; authentication/write limitations must be probed at runtime.

## 16. State machine invariants

1. `SUCCEEDED`, `FAILED`, `QUARANTINED`, and `CANCELLED` are terminal for an attempt.
2. A job may be requeued through an explicit new attempt; history is immutable.
3. `RUNNING` requires an active lease/heartbeat timestamp.
4. An expired lease becomes recoverable, never silently successful.
5. Verification evidence is required before `SUCCEEDED` for BUILD/REPAIR/PROMOTION cells.
6. A write outside declared scope fails with `WRITE_SCOPE_VIOLATION` before mutation.
7. A direct canonical branch write fails with `CANONICAL_BRANCH_GUARD` before mutation.
8. Exceeding cost, iteration, retry, or timeout limits fails closed.
9. Promotion is a separate cell from implementation.

## 17. Security and authorization model

Tool/plugin permission settings are treated as upper bounds, not operating policy. Even when a connector is configured for full access, Loop Factory applies its own narrower job policy.

Secrets are referenced by opaque handles and resolved only inside the worker that needs them. The supervisor receives capability/availability metadata, not raw secrets.

No autonomous cell may broaden its own permissions.

## 18. Completion criteria for CELL-000

CELL-000 is complete only when a fresh clone can:

1. create a job manifest;
2. persist it to SQLite;
3. execute one deterministic demo cell in an isolated branch/sandbox;
4. checkpoint after each material step;
5. survive forced termination after a checkpoint;
6. resume without redoing an already committed/idempotent step;
7. refuse a direct `main` write;
8. refuse a write outside job scope;
9. stop at retry and budget ceilings;
10. emit structured evidence and an exact next action;
11. pass focused and regression tests in GitHub Actions;
12. produce a Drive-ready checkpoint payload without requiring Drive to be available for core execution.

## 19. Follow-on cells

After CELL-000 passes:

- CELL-010: Fusion Studio source recovery loop.
- CELL-020: Fusion <-> Omega capability comparison engine.
- CELL-030: engineering build/test/review factory.
- CELL-040: provider capability probes and FREE-FIRST router.
- CELL-050: Media Forge vertical slice orchestration.
- CELL-060: self-healing deterministic regression loop.
- CELL-070: convert mature runbooks into KAI skills and benchmark them.

Each follow-on cell receives its own spec/plan and independent promotion gate.

## 20. Immediate safety lesson from design setup

During specification setup, two accidental documentation writes reached `main` because the file-write connector defaults to the repository default branch when no valid branch is supplied. Both were immediately reverted.

This incident is design evidence, not noise: the first implementation milestone must include a fail-closed canonical-branch guard and must never rely solely on connector defaults or user-level GitHub permissions.
