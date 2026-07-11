# Kai Control Plane Parallel Capability Integration Design

## Goal

Integrate five already-promoted parallel capabilities into Kai Control Plane without duplicating their logic, weakening their guardrails, or allowing arbitrary code execution.

Target capabilities:
- `storage-commander`
- `termux-bridge-planner`
- `backup-manifest`
- `file-indexer`
- `local-knowledge-vault`

## Authority and precedence

The capability registry is authoritative for lifecycle state (`PROMOTED`, `DISCOVERED`, `SUPERSEDED`, etc.).
Package manifests are authoritative for functional contract, mutation policy, version and local runtime layout.
A package manifest claiming an older lifecycle state must not override the registry.
No capability becomes `CANONICAL` automatically.

## Recommended architecture

Add a focused module `tools/kai_capability_integrations.py`.
It owns a curated adapter catalogue for the five approved capability slugs.
It discovers actual runtime paths through registry provenance and the candidate runtime layout.
It never scans arbitrary Python files for execution.

## Adapter contract

Each adapter declares:
- slug;
- expected registry capability ID when known;
- Python module entry point;
- runtime package path;
- safe probe command;
- allowed operations;
- mutation class;
- whether live external connectivity is required.

The runtime adapter returns normalized records with:
- `slug`, `version`, `registry_state`, `capability_id`;
- `runtime_path`, `manifest_path`, `module`, `script_name`;
- `available`, `promoted`, `manifest_valid`, `probe_status`;
- `allowed_operations`, `mutation_policy`, `requires_live_transport`;
- `warnings` for lifecycle or contract drift.

## Safe execution boundary

Only operations explicitly present in an adapter allowlist may run.
Commands execute with `subprocess.run`, `shell=False`, bounded timeout and explicit `PYTHONPATH`.
No inherited secret values are added by the Control Plane.
`storage-commander execute` is not exposed by default.
Mutating operations require a future explicit elevation design and are out of scope for this phase.

## Control Plane commands

Add:
- `integrations`: list normalized integrated capability records;
- `integration-doctor`: run safe probes for all approved integrations;
- `integration-call`: invoke one allowlisted read-only/planning operation.

Conversational aliases:
- `/integraciones` ↔ `integrations`
- `/doctor-integraciones` ↔ `integration-doctor`
- `/usa-capacidad` ↔ `integration-call`

## Initial allowlist

- `storage-commander`: `plan` only; no `execute`.
- `termux-bridge-planner`: `plan`.
- `backup-manifest`: `verify` only for this phase.
- `file-indexer`: `stats`, `query`.
- `local-knowledge-vault`: `doctor`, `stats`, `search`.

Operations that write manifests, indexes, vault data or remote storage remain outside the first integration slice unless separately approved by an adapter policy.

## Doctor semantics

Core memory, registry and location policy remain mandatory.
Integrated capability status is reported separately.
A missing or broken promoted integration makes `integration_status=DEGRADED`.
Global `status` becomes `DEGRADED` only for approved required integrations, which in this phase are the five named targets.
A live-transport dependency may return `BLOCKED_EXTERNAL` without claiming the code itself is broken.

## Error handling

Return structured errors instead of raw tracebacks for:
- capability missing from registry;
- runtime path absent;
- manifest absent or malformed;
- unsupported operation;
- subprocess timeout;
- non-zero exit code;
- JSON output parse failure.

Each result preserves command, return code, stdout/stderr excerpts and timeout status without exposing secrets.

## Testing strategy

TDD order:
1. adapter discovery and registry precedence;
2. safe operation allowlist and mutation rejection;
3. subprocess probing in isolated fake runtimes;
4. Control Plane methods;
5. CLI commands;
6. deployed-runtime regression;
7. full suite;
8. source/runtime SHA-256 parity;
9. doctor on real promoted capability runtimes.

## Out of scope

- automatic `CANONICAL` promotion;
- arbitrary capability execution;
- `storage-commander execute`;
- deletion or destructive storage actions;
- automatic modification of historical package manifests;
- silent installation of dependencies;
- network secret discovery or propagation.

## Success criteria

The Control Plane lists all five targets from real registry/runtime evidence, safely probes them, invokes only allowlisted non-destructive operations, reports integration health, passes the complete test suite, deploys with exact source/runtime hashes and leaves a durable memory/session record.
