# KAI Mobile Relay Single-Owner Recovery Implementation Plan

> **For KAI:** REQUIRED: execute with systematic-debugging + test-driven-development + verification-before-completion. Do not mutate Tailscale Serve until this plan reaches the local Relay health gate.

**Goal:** Restore the Python/SQLite Mobile Relay to exactly one canonical healthy owner on `127.0.0.1:8788`, make watchdog recovery bounded and non-proliferating, preserve source authority, and produce the prerequisite evidence for Tailscale Serve Gate A.

**Architecture boundary:** This plan applies only to the **Mobile Control Spine** (`KAI Node -> Python/SQLite Mobile Relay -> Android MobileNode`). It MUST NOT modify or replace the Node.js/Socket.IO Relay of the PC Remote Spine.

**Current evidence:** `/health` times out; listener count grew from 2 to 7; `.runtime/relay.pid` is an empty zero-byte file; watchdog runs at boot and invokes recovery on health failure; starter launches `python -m kai_relay.server`; Python server uses `allow_reuse_address=True`; `/health` calls `store.healthcheck()`; `C:\Kai\Relay` is not itself a Git worktree.

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

**Step 2: Capture listener chronology**

For every current `127.0.0.1:8788` listener, record PID, PPID, creation time, executable and sanitized entrypoint. Do not kill anything yet.

**Step 3: Correlate logs to process creation times**

Search watchdog/runtime logs for `Recovery attempted`, `UNHEALTHY_FOREIGN_LISTENER`, starts, PID writes/removals, health failures and exceptions. Build a monotonic timeline.

**Step 4: Inspect pidfile lifecycle**

Record zero-byte state, mtime and ACL. Determine whether the starter truncates the file before writing, whether concurrent starters race, or whether cleanup removes/truncates it.

**Step 5: Inspect storage pressure without modifying the DB**

Record database/WAL/SHM metadata, open-handle/process ownership where available, and low-cost read-only timing. Do not checkpoint, vacuum or delete WAL/SHM.

**Gate 1:** Promote the proliferation hypothesis to `ROOT_CAUSE_SUPPORTED` only if process creation/recovery chronology demonstrates the causal sequence. Otherwise branch into the next falsifiable hypothesis.

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
2. an empty/stale pidfile cannot authorize an unbounded second launch;
3. watchdog does not launch another server when listener ownership is ambiguous;
4. repeated health failures consume a bounded retry budget rather than spawning indefinitely;
5. startup grace prevents immediate recovery loops during initialization;
6. exactly one canonical owner remains after a controlled recovery;
7. health/readiness behavior remains compatible with existing MobileNode protocol.

Run tests and capture the expected RED evidence.

---

## Task 4 — Make process ownership fail closed

**Files likely modified:**
- `kai_relay/server.py`
- `start-relay.ps1`
- `Watchdog-KaiRelay.ps1`
- tests

**Step 1: Remove accidental multi-owner socket behavior**

For the production server, do not permit address reuse to create multiple simultaneous TCP owners on Windows. Prefer a single-owner bind invariant. Preserve test isolation using ephemeral ports rather than production-port sharing.

**Step 2: Make pidfile handling atomic and null-safe**

- never call `.Trim()` on a null read;
- distinguish `missing`, `empty`, `stale`, `live-owned`, and `foreign` PID states;
- write PID atomically via temporary file + replace/rename where practical;
- only remove a pidfile proven stale or belonging to the controlled process;
- store process-start identity metadata if needed to prevent PID reuse ambiguity.

**Step 3: Validate actual process identity**

A PID is owned only if its executable/entrypoint/runtime root match the expected Relay process. Do not kill a process based solely on port ownership or numeric PID.

Run targeted tests until GREEN.

---

## Task 5 — Split liveness from readiness/storage health

**Problem:** current `/health` invokes `store.healthcheck()`. A storage stall therefore looks like process death and can trigger restart storms.

**Step 1: Preserve protocol compatibility**

Determine which callers rely on `/health` semantics before changing it.

**Step 2: Introduce two health classes if compatible**

- cheap liveness: proves the HTTP process/thread can answer without expensive storage work;
- readiness/dependency health: verifies SQLite/store availability and can report degraded state without immediately forcing process replacement.

If endpoint compatibility prevents a new path, keep `/health` response shape but decouple restart eligibility from a single dependency timeout.

**Step 3: Add timing and timeout tests**

Simulate storage contention/slow health and verify watchdog does not proliferate servers.

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
- task remains `IgnoreNew`.

Tests must demonstrate a retry storm cannot exceed the configured budget.

---

## Task 7 — Controlled runtime recovery

Only after Tasks 1-6 are verified on source/tests:

1. capture pre-recovery listener/process/storage evidence;
2. stop the watchdog recovery loop or place it in an explicit maintenance mode without disabling security controls;
3. terminate only processes proven to be Mobile Relay instances;
4. clear only the proven stale/empty pidfile state;
5. start one Relay instance through the canonical starter;
6. verify exactly one listener owner;
7. verify cheap liveness;
8. verify storage/readiness;
9. verify heartbeat/replay regression;
10. re-enable normal watchdog supervision;
11. deliberately kill the canonical Relay once and prove bounded single-owner auto-recovery;
12. observe long enough to prove listener count remains exactly one.

**Gate 3:** `RELAY_SINGLE_OWNER_HEALTH_VERIFIED` requires command + effect evidence, not process presence alone.

---

## Task 8 — Physical reboot resilience

Reboot is a human-impacting operation; execute only when the operator context allows it and rollback/evidence is prepared.

After reboot verify:

- scheduled watchdog starts once;
- exactly one Relay owner;
- pidfile valid;
- liveness and readiness healthy;
- no proliferation after multiple probe intervals;
- Tailscale remains Running;
- no unrelated startup regression.

**Gate 4:** `PC_BOOT_RECOVERY_VERIFIED`.

---

## Task 9 — Resume Mobile Control Gate A

Only after Gate 3 (and preferably Gate 4):

1. verify PC and S24 live Tailscale identities again;
2. verify Tailnet Lock state again rather than assuming the prior snapshot;
3. configure **Tailscale Serve**, not Funnel, to the loopback Mobile Relay;
4. verify HTTPS health via the PC MagicDNS name;
5. provision the MobileNode runtime endpoint to the private Serve URL only after it is proven;
6. verify fresh heartbeat;
7. run `screen_state` or equivalent neutral read-only command;
8. run one harmless visible action and verify post-state;
9. repeat with S24 Wi-Fi disabled and cellular enabled;
10. repeat on unrelated Wi-Fi when available;
11. then classify `HOME_LAN_INDEPENDENT_VERIFIED`.

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
- valid canonical process ownership state;
- watchdog recovery is bounded/non-proliferating;
- full Relay tests pass;
- heartbeat/replay regression passes;
- private Tailscale Serve path works;
- neutral Android effect proof works over real cellular data;
- source authority/rollback are explicit;
- Drive CURRENT/wiki and GitHub branch contain sanitized final evidence.
