# CELL-000 Runbook

## Authorities
- GitHub is authority for live code and commit history.
- SQLite is authority for runtime jobs, attempts, receipts, checkpoints, and evidence.
- Drive is documentary CURRENT/checkpoint writeback only; core execution does not depend on it.

## Fresh start
```bash
python -m core.loop_factory init --db .kai-loop/loopfactory.db
```

## Focused verification
```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
```

## Branch safety
Never execute a mutating cell on `main` or `master`. Branch detection is fail-closed: unknown or detached branch state is not treated as safe.

## Write-scope safety
Every mutating worker must expose its target sandbox. The target must equal or descend from a declared job write scope before any mutation occurs.

## Crash recovery
1. Re-open the same SQLite database.
2. Inspect the job with `show`.
3. Inspect the latest checkpoint.
4. Execute exactly one `run-once`.
5. Confirm an existing receipt prevents duplicate side effects.

Example:
```bash
python -m core.loop_factory show --db .kai-loop/loopfactory.db CELL-000-DEMO
python -m core.loop_factory checkpoint --db .kai-loop/loopfactory.db CELL-000-DEMO --format markdown
python -m core.loop_factory run-once --db .kai-loop/loopfactory.db CELL-000-DEMO --sandbox .kai-loop/sandboxes/CELL-000-DEMO --branch feat/loop-factory-cell-000
```

If a durable receipt already exists, the runner skips ACT and resumes from the recorded output. Post-receipt timeout, budget, or verification failures quarantine rather than blind-retry, because the external effect may already exist.

## Requeue and cancel
`requeue` schedules a fresh attempt; it never rewrites an old terminal attempt. `cancel` closes active work when legal and updates scheduling state without deleting history.

```bash
python -m core.loop_factory requeue --db .kai-loop/loopfactory.db CELL-000-DEMO --reason "retry after environment repair"
python -m core.loop_factory cancel --db .kai-loop/loopfactory.db CELL-000-DEMO --reason "operator cancelled"
```

## Capability routing
`workers` emits the static CELL-000 registry as JSON. Availability is intentionally `UNKNOWN` until a runtime probe verifies the current host/account state.

```bash
python -m core.loop_factory workers
```

FREE-FIRST ranking is deterministic: local/open/included options are preferred over paid options within the declared job cost ceiling. Provider identity belongs in adapters, not domain objects.

## Evidence and checkpoint writeback
```bash
python -m core.loop_factory checkpoint --db .kai-loop/loopfactory.db CELL-000-DEMO --format json
python -m core.loop_factory checkpoint --db .kai-loop/loopfactory.db CELL-000-DEMO --format markdown
```

These outputs are Drive-ready but require no Drive connection. Do not place plaintext secrets in manifests, evidence, SQLite payloads, logs, or checkpoint writeback.

## Promotion gate
Promotion is A4 and separate from implementation. Before promotion require fresh CI evidence, reviewed diff, expected head SHA, rollback path, and explicit A4 authorization. CELL-000 itself never auto-merges or deploys.

## Current CELL-000 limits
- no distributed lock service;
- no live provider probes;
- no UI;
- no automatic Drive write;
- no automatic merge;
- no background daemon;
- no generic hard-kill mechanism for arbitrary in-process workers.

## Recovery invariant
A job is never considered successful because a process disappeared. An expired lease is recoverable, not successful. An effect is never assumed absent merely because the worker died; receipts and output verification decide what happened.

## Local CI equivalent
```bash
python -m compileall -q core/loop_factory
python -m unittest discover -s tests/loop_factory -p 'test_*.py' -v
git diff --check
```

## Expected GitHub CI
`.github/workflows/test-loop-factory.yml` runs on GitHub-hosted Ubuntu with Python 3.11 and 3.12 and `contents: read` only. It compiles the package and executes the full CELL-000 test suite. It is evidence, not a promotion mechanism.

## Next exact action after CELL-000
Only after local verification, independent review, pushed branch, and remote CI evidence: write documentary checkpoint, then plan the next cell. The approved follow-on order begins with CELL-010 Fusion Studio source recovery.
