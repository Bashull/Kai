# KAI Mobile Relay Single-Owner Recovery Implementation Plan

> **For KAI:** REQUIRED: execute with systematic-debugging + test-driven-development + verification-before-completion. Do not mutate Tailscale Serve until this plan reaches the local Relay health gate.

**Goal:** Restore the Python/SQLite Mobile Relay to exactly one canonical healthy owner on `127.0.0.1:8788`, make watchdog recovery bounded and non-proliferating, preserve source authority, and produce the prerequisite evidence for Tailscale Serve Gate A.

**Architecture boundary:** This plan applies only to the **Mobile Control Spine** (`KAI Node -> Python/SQLite Mobile Relay -> Android MobileNode`). It MUST NOT modify or replace the Node.js/Socket.IO Relay of the PC Remote Spine.

**Current evidence, corrected:** `/health` times out; `.runtime/relay.pid` is an empty zero-byte file; watchdog runs at boot and invokes recovery on health failure; starter launches `python -m kai_relay.server`; Python server uses `allow_reuse_address=True`; `/health` calls `store.healthcheck()`; `C:\Kai\Relay` is not itself a Git worktree. Seven distinct Relay-related process pairs were already present by approximately `02:19` on 2026-09-16. A later `Get-NetTCPConnection` probe surfaced two listener owners, while `netstat -ano` later directly observed seven simultaneous listeners on `127.0.0.1:8788`. This discrepancy does **not** prove that five servers were created between the probes. The six-process start cluster around `02:19` supports a concurrent-start/fan-out hypothesis, but the exact caller remains unresolved.

**External platform facts used by this plan:** Windows documents that `SO_REUSEADDR` can permit another socket to bind an address/port already in use and that behavior among same-port TCP sockets can be non-deterministic; `SO_EXCLUSIVEADDRUSE` prevents forced rebinding. Windows Task Scheduler `IgnoreNew` does not start a new scheduled-task instance while one is already running, so the scheduler policy alone does not explain the rapid fan-out; manual watchdog invocations or other callers remain possible.

---

## Task 1 — Freeze the diagnosis before recovery mutation

**Files:**
- Read: `C:\Kai\Relay\Watchdog-KaiRelay.ps1`
- Read: `C:\Kai\Relay\start-relay.ps1`
- Read: `C:\Kai\Relay\kai_relay\server.py`
- Read: `C:\Kai\Relay\kai_relay\store.py`
- Read: `C:\Kai\Relay\.runtime\*`
- Read: `C:\Kai\Relay\state\*`
- Read: Relay/watchdog logs if present

**Step 1: Capture exact recovery implementation**

Read the complete `Invoke-RelayRecovery` function and exact listener/PID ownership logic, not keyword excerpts.

**Step 2: Capture process/listener chronology without assuming probe deltas equal process creation**

For every current `127.0.0.1:8788` listener, record PID, PPID, creation time, executable and sanitized entrypoint. Reconcile this with the already observed process start times. Treat listener-count differences between Windows APIs/probes as evidence to explain, not automatically as newly spawned processes.

**Step 3: Identify every possible launcher**

Correlate watchdog/runtime logs with process creation times. Search for `Recovery attempted`, `UNHEALTHY_FOREIGN_LISTENER`, starts, PID writes/removals, health failures and exceptions. Enumerate active/historical PowerShell watchdog instances where possible, scheduled-task history, manual/tool launch surfaces, and any script that invokes `start-relay.ps1` or `python -m kai_relay.server`.

**Step 4: Inspect pidfile lifecycle**

Record zero-byte state, mtime and ACL. Determine whether the starter truncates the file before writing, concurrent starters race through the check/write window, or cleanup removes/truncates ownership state.

**Step 5: Inspect storage pressure without modifying the DB**

Record database/WAL/SHM metadata, open-handle/process ownership where available, and low-cost read-only timing. Do not checkpoint, vacuum or delete WAL/SHM.

**Gate 1:** Promote `CONCURRENT_START_RACE + NON_EXCLUSIVE_BIND + LOST_OWNERSHIP_STATE` to `ROOT_CAUSE_SUPPORTED` only when chronology/caller evidence demonstrates the causal sequence. Otherwise branch into the next falsifiable hypothesis. Until then the hypothesis may be `HIGH_CONFIDENCE`, but not `OBSERVED` root cause.

**Writeback:** sanitized Phase 0 evidence to Drive/wiki.

---

## Task 2 — Preserve exact current source authority before editing

**Step 1: Snapshot source with hashes**

Create a dated local evidence capsule outside runtime directories containing source/scripts/tests only; exclude `.venv`, runtime DB, credentials, private configuration and logs containing sensitive data.

**Step 2: Compare against known historical source**

Compare current `server.py`, `store.py`, watchdog and starter hashes against preserved August evidence and any recoverable Git/Drive copies. Do not overwrite current source with an older capsule.

**Step 3: Establish source authority**

If current source is not represented in GitHub, add a sanitized Mobile Relay source subtree to the approved feature branch only after verifying no secrets/private endpoints are embedded. Record provenance and source hashes.

**Gate 2:** Exact current source has rollback evidence and a declared authority before source edits.

---

## Task 3 — Write failing tests for single-instance invariants

**Target tests:** local Relay test suite / PowerShell harness.

Create failing tests before implementation for:

1. a second Relay instance cannot successfully own the production bind while the first is alive;
2. five or more concurrent starter invocations yield exactly one canonical server owner;
3. an empty/stale pidfile cannot authorize an unbounded second launch;
4. watchdog does not launch another server when listener ownership is ambiguous;
5. repeated health failures consume a bounded retry budget rather than spawning indefinitely;
6. startup grace prevents immediate recovery loops during initialization;
7. exactly one canonical owner remains after a controlled recovery;
8. health/readiness behavior remains compatible with existing MobileNode protocol;
9. a foreign listener is never killed by Relay recovery.

Run tests and capture the expected RED evidence.

---

## Task 4 — Make process and socket ownership fail closed

**Files likely modified:**
- `kai_relay/server.py`
- `start-relay.ps1`
- `Watchdog-KaiRelay.ps1`
- tests

**Step 1: Remove accidental multi-owner socket behavior**

For the production server, do not permit address reuse to create multiple simultaneous TCP owners on Windows. Prefer a tested exclusive bind invariant. On Windows, use `SO_EXCLUSIVEADDRUSE` or an equivalent implementation set before bind; do not deliberately enable production-port reuse. Preserve test isolation with ephemeral ports rather than production-port sharing.

**Step 2: Serialize starter ownership with an OS-level primitive**

Use a Windows named mutex or another tested machine-local single-instance primitive around the entire inspect/start/establish-ownership sequence. The pidfile is evidence/state, not the concurrency primitive.

**Step 3: Make pidfile handling atomic and null-safe**

- never call `.Trim()` on a null read;
- distinguish `missing`, `empty`, `stale`, `live-owned`, and `foreign` states;
- write ownership metadata through a temporary file + atomic replacement/rename where practical;
- include PID plus process creation identity/executable/entrypoint fingerprint as needed to prevent PID reuse ambiguity;
- only remove ownership state proven stale or belonging to the controlled process;
- if state is malformed while a listener exists, fail closed and preserve evidence rather than spawning.

**Step 4: Validate actual process identity and all listeners**

A PID is owned only if executable, entrypoint and runtime root match the expected Relay. Enumerate all listeners, not one arbitrary `Get-NetTCPConnection` result. Do not kill a process based solely on port ownership or numeric PID.

Run targeted tests until GREEN.

---

## Task 5 — Split liveness from readiness/storage health

**Problem:** current `/health` invokes `store.healthcheck()`. A storage stall therefore looks like process death and can trigger recovery even when the HTTP process itself is alive.

**Step 1: Preserve protocol compatibility**

Determine which callers rely on `/health` semantics before changing it.

**Step 2: Introduce two health classes if compatible**

- cheap liveness: proves the HTTP process/thread can answer without SQLite dependency work;
- readiness/dependency health: verifies SQLite/store availability and can report degraded state without immediately forcing process replacement.

If endpoint compatibility prevents a new path, keep `/health` response shape but decouple restart eligibility from a single dependency timeout.

**Step 3: Add timing and timeout tests**

Simulate storage contention/slow readiness and prove the watchdog does not fan out servers.

Run full Relay test suite.

---

## Task 6 — Bound watchdog recovery

Implement one recovery owner and a finite state machine:

`STARTUP -> READY -> DEGRADED -> RECOVERING -> COOLDOWN -> READY | BLOCKED`

Required properties:

- consecutive failure threshold before restart;
- startup grace/cooldown;
- bounded attempts per time window;
- exponential backoff + jitter;
- no nested/redundant restart layer;
- listener ambiguity => block and preserve evidence, not spawn;
- foreign listener => never kill;
- sanitized persistent state/logging;
- Task Scheduler remains `IgnoreNew`;
- recovery mutex/lease ensures one active recovery actor even when the script is invoked outside Task Scheduler.

Tests must demonstrate a retry storm or concurrent manual invocations cannot exceed the configured budget or create a second owner.

---

## Task 7 — Controlled runtime recovery

Only after Tasks 1-6 are verified on source/tests:

1. capture pre-recovery listener/process/storage evidence;
2. place watchdog recovery into explicit maintenance/quiesced state without weakening unrelated security controls;
3. terminate only processes proven to be Mobile Relay instances;
4. clear only proven stale/empty ownership state;
5. wait until `127.0.0.1:8788` is fully unowned;
6. start one Relay through the canonical serialized starter;
7. verify exactly one listener owner and valid ownership state;
8. verify cheap liveness;
9. verify storage/readiness;
10. verify heartbeat/replay regression;
11. restore normal watchdog supervision;
12. deliberately kill the canonical Relay once and prove bounded single-owner auto-recovery;
13. observe enough probe intervals to prove listener count remains exactly one.

**Gate 3:** `RELAY_SINGLE_OWNER_HEALTH_VERIFIED` requires command + effect evidence, not process presence alone.

---

## Task 8 — Physical reboot resilience

Reboot is a human-impacting operation; execute only when the operator context allows it and rollback/evidence is prepared.

After reboot verify:

- scheduled watchdog starts once;
- exactly one Relay owner;
- ownership state valid;
- liveness and readiness healthy;
- no fan-out after multiple probe intervals;
- Tailscale remains Running;
- no unrelated startup regression.

**Gate 4:** `PC_BOOT_RECOVERY_VERIFIED`.

---

## Task 9 — Resume Mobile Control Gate A

Only after Gate 3 (and preferably Gate 4):

1. verify PC and S24 live Tailscale identities again;
2. verify Tailnet Lock state again rather than assuming the prior snapshot;
3. configure **Tailscale Serve**, not Funnel, to the loopback Mobile Relay;
4. if Tailscale requires an interactive HTTPS/consent step, stop only at that external-consent gate;
5. verify HTTPS health via the PC MagicDNS name;
6. provision the MobileNode runtime endpoint to the private Serve URL only after it is proven;
7. verify fresh heartbeat;
8. run `screen_state` or equivalent neutral read-only command;
9. run one harmless visible action and verify post-state;
10. repeat with S24 Wi-Fi disabled and cellular enabled;
11. repeat on unrelated Wi-Fi when available;
12. then classify `HOME_LAN_INDEPENDENT_VERIFIED`.

Do not use WhatsApp/chats/calls/private UI as the visible proof.

---

## Task 10 — Hardening and chaos regression

After Gate A:

- narrow tailnet policy atomically with tests;
- verify `S24 -> PC Serve` allowed and unintended administrative/direct Relay ports denied as intended;
- exercise controlled Relay death, Tailscale stop/recovery, MobileNode death, network change and endpoint failure;
- record recovery time and effect proof;
- continue separate PC Remote Spine recovery-profile gap analysis without merging the two Relay implementations.

---

## Completion evidence

This incident is complete only when all of the following are fresh and evidenced:

- one Mobile Relay listener owner;
- valid canonical process/socket ownership state;
- watchdog recovery is bounded/non-proliferating even under concurrent invocations;
- full Relay tests pass;
- heartbeat/replay regression passes;
- private Tailscale Serve path works;
- neutral Android effect proof works over real cellular data;
- source authority/rollback are explicit;
- Drive CURRENT/wiki and GitHub branch contain sanitized final evidence.
