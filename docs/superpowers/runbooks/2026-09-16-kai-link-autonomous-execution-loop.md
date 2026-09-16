# KAI Link Autonomous Execution Loop

**Status:** ACTIVE PROJECT RUNBOOK · approved operating mode for the `feat/kai-nervous-link-v0.1` branch.

**Scope:** Kai Link / Kai Nervous Link only. This runbook governs how work continues when the operator is unavailable or has explicitly delegated routine technical decisions. It does not override irreversible, destructive, billing, security-weakening, or external-consent gates.

## 1. Default decision rule

When several technically valid next steps exist, choose the recommended path and execute it. Do not present an option menu merely to transfer an ordinary engineering decision back to the operator.

Use this ordering:

`REUSE -> ADAPT -> COMPOSE -> ACQUIRE -> BUILD`

Prefer the smallest reversible step that increases verified capability or removes a verified blocker.

## 2. Continuous engineering loop

For each cell of work:

`OBSERVE -> EVIDENCE -> CLASSIFY -> ROOT CAUSE -> MINIMAL REVERSIBLE CHANGE -> COMMAND PROOF -> EFFECT PROOF -> REGRESSION -> WRITEBACK -> RESUME`

For source changes, insert:

`RED -> VERIFY RED -> GREEN -> VERIFY GREEN -> REFACTOR`

A command that returned success is not effect proof. A process that exists is not service health. A historical checkpoint is not a fresh runtime observation.

## 3. Evidence classes

Every material datum must be classified as one of:

- `OBSERVED`: fresh direct evidence from the relevant system or immutable source.
- `INFERRED`: conclusion supported by observed evidence but not directly measured.
- `UNRESOLVED`: evidence is insufficient or conflicting.
- `BLOCKED`: the next required observation/action cannot currently be performed; record the exact blocker and resume condition.

Never silently promote `INFERRED` or `UNRESOLVED` to `OBSERVED`.

## 4. Authority ladder

Keep authority dimensions separate:

- live runtime evidence: what is actually running now;
- local source + hashes: what code the runtime appears to use;
- GitHub approved branch: preserved source/design/plan authority once material is actually committed there;
- Drive CURRENT/wiki: durable project memory, decisions, checkpoints and recovery context;
- protected local/provider vaults: secret values;
- Secret Pointer Registry: non-secret metadata pointing to where secrets live.

`ONLINE != VERIFIED != DOCUMENTED != CANONICAL`

`SOURCE_AUTHORITY != RUNTIME_AUTHORITY`

## 5. Two-spine invariant

Never collapse the two Relay lineages:

1. **Mobile Control Spine:** `KAI Node -> Python/SQLite Mobile Relay -> Android MobileNode`.
2. **PC Remote Spine:** Node.js/Socket.IO Relay + PC Agent + CLI under `nervous-link/`.

Shared policy, evidence formats, recovery concepts and transport strategy may be federated. Code is shared only after differential analysis proves it safe and useful.

## 6. Blocker protocol

A blocker in one lane does not stop the project.

When a live-control lane is blocked:

1. record the tool/channel and exact failure classification;
2. preserve all fresh evidence already obtained;
3. move to unblocked lanes such as source archaeology, protocol comparison, test design, rollback design, official documentation research, Drive/GitHub writeback, or recovery-surface preparation;
4. do not invent runtime success while blocked;
5. resume the blocked lane automatically when a valid execution surface becomes available.

Do not ask the operator to choose between equivalent technical routes when one route is clearly preferred.

## 7. Human stop gates

Stop and require the operator only for:

- irreversible or destructive actions with material data-loss risk;
- deliberate weakening of security boundaries or broad sensitive privilege grants;
- provider OAuth/consent/system dialogs that technically require the operator;
- paid resources, domains, subscriptions or non-trivial recurring cost;
- publication/merge outside the already approved feature branch;
- actions involving private messages, chats, calls or other sensitive UI content outside explicit scope;
- architecture that remains genuinely underdetermined after evidence gathering and where choosing would be guesswork rather than engineering judgment.

Routine reversible repair, tests, source preservation, documentation, branch-local commits, health checks, and project-scoped configuration work do not require an option menu.

## 8. Mobile Relay single-owner incident doctrine

Current incident evidence must be interpreted carefully:

- Task 2 already observed the current Relay-related process population with start times around `02:14` and `02:19` on 2026-09-16.
- A later `Get-NetTCPConnection` probe surfaced two listener owners, while `netstat -ano` later surfaced seven simultaneous listeners on `127.0.0.1:8788`.
- Therefore it is **not proven** that five new servers were created between those two probes. The correct fact is that seven Relay process pairs already existed by approximately `02:19`, and seven simultaneous listeners were directly observed later.
- The six-process start cluster around `02:19` is consistent with a concurrent-start race or another fan-out path, but the exact caller remains `UNRESOLVED` until logs/process ancestry/callers prove it.
- `.runtime/relay.pid` is observed as an empty zero-byte file.
- `start-relay.ps1` performs non-atomic pidfile check/start/write/cleanup operations and is null-unsafe on an empty pidfile read.
- the Python Relay uses `ThreadingHTTPServer` with `allow_reuse_address=True`.
- on Windows, address reuse can allow multiple server sockets on the same address/port and make connection ownership non-deterministic; production Relay must enforce a single-owner bind invariant.
- `/health` currently reaches `store.healthcheck()`, so storage contention can masquerade as process-health failure.

Leading hypothesis: `CONCURRENT_START_RACE + NON_EXCLUSIVE_BIND + LOST_OWNERSHIP_STATE`.

Status: `HIGH_CONFIDENCE_HYPOTHESIS`, not `ROOT_CAUSE_SUPPORTED`, until the exact launch chronology/caller is evidenced.

## 9. Single-owner remediation invariant

Before Tailscale Serve is enabled, the Mobile Relay must satisfy all of the following:

- exactly one production listener owns `127.0.0.1:8788`;
- production socket binding fails closed if another owner exists;
- starter ownership is serialized using an OS-level primitive or equivalent atomic mechanism, not a naked pidfile race;
- pidfile/state is null-safe, atomic and includes enough process identity to resist PID reuse ambiguity;
- listener ambiguity never triggers another spawn;
- foreign listeners are never killed;
- watchdog restart attempts are bounded with threshold, cooldown/backoff and circuit breaking;
- liveness is separated from dependency/readiness health sufficiently to prevent SQLite stalls from causing spawn storms;
- source and rollback evidence exist before runtime repair;
- tests prove concurrency and recovery invariants before controlled cleanup.

On Windows, prefer an exclusive socket ownership mechanism (`SO_EXCLUSIVEADDRUSE` or an equivalent tested implementation) and do not deliberately enable production-port reuse.

## 10. Transport promotion order

After `RELAY_SINGLE_OWNER_HEALTH_VERIFIED`:

1. re-observe PC and S24 Tailscale state;
2. configure **Tailscale Serve**, never Funnel, for the private Mobile Control route;
3. verify HTTPS reverse proxy to loopback Relay;
4. provision MobileNode runtime endpoint only after Serve works;
5. verify fresh heartbeat and a neutral read-only command;
6. verify one harmless visible effect plus post-state;
7. repeat with S24 Wi-Fi disabled and cellular enabled;
8. repeat on unrelated Wi-Fi when practical;
9. only then promote `HOME_LAN_INDEPENDENT_VERIFIED`;
10. harden tailnet grants after proof, not before.

## 11. Sensitive UI boundary

For unattended technical proof, use neutral state and harmless navigation only. Do not read, send, alter or persist private WhatsApp/chat/message/call content. Do not persist screenshots or private UI trees unless the operator explicitly asks for that content and the task requires it.

## 12. Context-budget discipline

Do not re-read the entire archive on every step. Start with:

`CURRENT -> exact relevant runbook/plan -> fresh runtime evidence -> action -> proof -> writeback`

Deep-read only the files needed by the active hypothesis. When prior work exists, continue incrementally from the last verified checkpoint instead of rediscovering the system from scratch.

## 13. Promotion of this runbook into a reusable skill

This document is intentionally a project runbook, not a global skill. Promote its stable, general parts into a reusable skill only after the loop has been exercised on multiple real incidents and evaluated through the skill-lab/evaluation workflow. Avoid duplicating existing systematic-debugging, TDD, verification, worktree, or planning skills.

## 14. Completion rule

Do not claim the complete Kai Link objective achieved until fresh evidence shows:

- one healthy canonical Mobile Relay owner;
- bounded self-recovery and reboot recovery;
- source authority + rollback;
- private Tailscale Serve path;
- MobileNode heartbeat and neutral command over the private route;
- visible harmless Android effect over real cellular data;
- regression/chaos evidence recorded;
- durable Drive/GitHub writeback complete.
