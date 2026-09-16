# KAI Autonomous Engineering Loop

Date: 2026-09-16
Status: CURRENT CANDIDATE on `feat/kai-nervous-link-v0.1`
Scope: KAI Nervous Link / Mobile Control Spine / PC Remote Spine federation

## Purpose

This runbook defines how KAI should keep moving when one control surface is blocked, without inventing state, conflating similarly named components, or repeatedly asking the operator to choose a path that can be selected safely from evidence.

The governing distinction remains:

`SAME_NAME != SAME_COMPONENT`

The Mobile Control Spine (`KAI Node -> Python/SQLite Mobile Relay -> Android MobileNode`) and the PC Remote Spine (`Node.js/Socket.IO Relay -> PC Agent -> remote client`) are separate implementations and separate recovery domains.

## Default operating loop

Use this loop continuously for approved, reversible work:

1. **Recover continuity** — read CURRENT, relevant runbook/wiki, approved spec and latest execution plan.
2. **Observe fresh state** — prefer live runtime evidence over historical claims.
3. **Classify every datum** — `OBSERVED`, `INFERRED`, `UNRESOLVED`, or `BLOCKED`.
4. **Trace the failing boundary** — process -> socket -> HTTP health -> storage -> transport -> device -> visible effect.
5. **Form one falsifiable hypothesis** — never patch multiple guessed causes at once.
6. **Choose the smallest reversible test/change** — preserve rollback before mutation.
7. **Verify command outcome** — exit/status alone is insufficient.
8. **Verify effect** — `COMMAND_ACCEPTED != EFFECT_OBSERVED != USER_SUCCESS_CRITERION`.
9. **Run regression / resilience check** — prove the neighboring path was not damaged.
10. **Write back evidence** — Drive CURRENT/wiki plus GitHub branch where source authority exists.
11. **Resume the objective** — a recovered tool is not the objective; it is only a restored path.

When a blocker appears, use:

`REUSE -> ADAPT -> COMPOSE -> ACQUIRE -> BUILD -> VERIFY -> RESUME`

Do not ask the operator to choose between equivalent implementation paths unless a true human gate exists.

## Human stop gates

Stop and require the operator only for:

- irreversible or destructive changes;
- deliberate security weakening or sensitive privilege escalation;
- provider/OAuth/VPN/system consent that technically requires a human;
- paid resources, domains or services;
- publication or merge outside the approved feature branch;
- private/sensitive Android UI actions not explicitly requested;
- architecture so underdetermined that all remaining paths would be guesses.

Everything else should continue with the safest evidence-backed recommendation.

## Recovery-plane order

Use independent surfaces rather than waiting indefinitely on one:

1. existing live first-party control surface;
2. existing PC Remote Spine / PC Agent if deployed and healthy;
3. approved third-party recovery surface if already provisioned;
4. local operator-assisted command only when no independent path exists;
5. build a narrow recovery capability only after the previous options are disproven or unavailable.

A recovery agent must expose typed, allowlisted, audited and bounded actions. Do not create an unrestricted public shell.

## Health model

Separate three health concepts instead of one binary `healthy` flag:

- **Startup** — process initialized and owns the intended resources.
- **Liveness** — process can make forward progress and should only trigger restart after a bounded failure threshold.
- **Readiness** — process is safe to receive work, including required dependencies such as storage.

This follows the same reliability principle used by Kubernetes startup/liveness/readiness probes: aggressive liveness checks can cause cascading failures when the probe itself depends on a strained dependency.

Reference: https://kubernetes.io/docs/concepts/workloads/pods/probes/

## Retry and restart doctrine

Recovery must not become a retry storm.

- Restart/retry at one ownership layer only.
- Require consecutive failures before destructive recovery.
- Use a bounded retry budget.
- Apply exponential backoff with jitter for repeated recovery attempts.
- Add a cool-down after a successful start before liveness can kill/restart it.
- Record the trigger, attempted recovery, elapsed time and result.
- If the retry budget is exhausted, move to `DEGRADED/BLOCKED` and preserve evidence rather than spawning indefinitely.

References:
- https://docs.aws.amazon.com/wellarchitected/2023-04-10/framework/rel_mitigate_interaction_failure_limit_retries.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.html

## Socket ownership doctrine on Windows

A server expected to have a single owner must fail closed on a second bind. `SO_REUSEADDR`/address reuse is not a substitute for process supervision.

Microsoft documents that multiple TCP sockets forcibly bound to the same address/port via `SO_REUSEADDR` have non-deterministic request ownership; server applications should prefer exclusive address ownership where appropriate.

References:
- https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse
- https://learn.microsoft.com/en-us/windows/win32/winsock/so-exclusiveaddruse

For Python servers on Windows, any use of `allow_reuse_address=True` must therefore be reviewed against the intended single-instance invariant.

## Storage health doctrine

SQLite WAL improves reader/writer concurrency but does not make multiple uncontrolled server owners desirable. SQLite still serializes writers; a liveness endpoint that performs storage work can become slow or blocked under contention.

References:
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/faq.html

A preferred architecture is:

- cheap process liveness endpoint that does not perform heavy storage work;
- readiness/storage endpoint that can report dependency degradation;
- exactly one canonical Mobile Relay process owning the durable store.

## Tailscale transport doctrine

For Mobile Control Gate A, use Tailscale Serve, not Funnel. The backend remains loopback-only and Serve exposes it only inside the tailnet.

Reference: https://tailscale.com/docs/features/tailscale-serve

Required sequence:

1. prove local Relay healthy and single-owner;
2. prove PC and S24 are authenticated and online in the same tailnet;
3. configure private Serve to the loopback backend;
4. verify Serve HTTPS health;
5. provision MobileNode endpoint only after the private path is proven;
6. verify heartbeat and a neutral read-only command;
7. verify a harmless visible action plus post-state;
8. repeat with S24 Wi-Fi disabled / cellular enabled;
9. only then classify `HOME_LAN_INDEPENDENT_VERIFIED`.

Do not harden tailnet policy until the live path is effect-proven. Then reduce access atomically with positive/negative policy tests.

## Evidence ledger

Each material checkpoint should capture:

- timestamp and node;
- exact command or operation class, sanitized;
- expected outcome;
- observed outcome;
- classification;
- source/runtime authority;
- rollback pointer if a mutation occurred;
- next falsifiable question.

Recommended telemetry vocabulary:

- `service.name`
- `service.instance.id`
- component/spine identifier
- recovery attempt number
- health class (`startup`, `liveness`, `readiness`)
- observed owner PID
- transport path
- effect-proof status

Reference vocabulary inspiration: https://opentelemetry.io/docs/specs/semconv/resource/service/

## Current incident: Mobile Relay listener proliferation

Fresh Phase 0 evidence on 2026-09-16 established:

- PC and S24 are online in Tailscale;
- Tailnet Lock is disabled;
- Tailscale Serve is not configured;
- Mobile Relay `/health` times out while `127.0.0.1:8788` listens;
- listener count increased from two observed owners to seven;
- `.runtime/relay.pid` exists but is empty;
- boot watchdog continuously probes `/health` and invokes recovery on failure;
- `start-relay.ps1` launches `python -m kai_relay.server` and writes the pidfile;
- `RelayHTTPServer` uses `ThreadingHTTPServer` with `allow_reuse_address=True`;
- `/health` invokes `store.healthcheck()`;
- local Mobile Relay source exists but `C:\Kai\Relay` is not itself a Git worktree.

Leading hypothesis, not yet final root cause:

`storage/health stall -> watchdog recovery -> lost PID ownership -> additional server launch -> address reuse permits shared bind -> multiple Relay instances contend for SQLite -> health degrades further`

The next proof must capture the exact `Invoke-RelayRecovery` implementation, watchdog/runtime logs and listener process chronology before mutation.

## Completion rule

The work is not complete because a command succeeds, a process exists, or a tunnel is configured. Completion requires fresh effect evidence for the requested objective, including cellular independence and recovery behavior, followed by durable writeback and source authority.