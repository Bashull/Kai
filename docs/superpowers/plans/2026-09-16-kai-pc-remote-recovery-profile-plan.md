# KAI PC Remote Spine Recovery Profile Implementation Plan

> **For KAI:** execute with test-driven-development + verification-before-completion. This plan strengthens the existing PC Remote Spine as an independent recovery surface; it does not merge it with the Python/SQLite Mobile Relay.

**Goal:** Add a narrow, policy-defined, typed recovery-playbook action to the existing Nervous Link PC Agent so a future authenticated remote client can invoke preconfigured recovery/status playbooks without gaining an arbitrary shell. Use it to recover/diagnose Kai services when RDC or another third-party admin surface is unavailable.

**Why reuse this agent:** the existing PC Agent already has outbound reconnection, HMAC authentication, replay protection, default-deny capabilities, local kill switch, append-only audit, bounded execution, file roots, and Windows startup support. Extending it is lower-risk than creating a second unrestricted agent.

**Security invariant:** the remote request chooses only a `playbook_id`. Executable, argv, cwd and limits come entirely from the trusted local policy. The request cannot supply or interpolate arbitrary command text/arguments/environment.

---

## Task 1 — RED: define fixed-playbook runner behavior

**Create:** `nervous-link/tests/recoveryPlaybook.test.js`

Write failing tests for:

1. configured playbook executes exact policy-defined executable/argv;
2. unknown playbook id is rejected;
3. malformed playbook id is rejected;
4. request-supplied extra keys/argv are rejected rather than ignored;
5. policy-defined timeout is bounded by the global limit;
6. stdout/stderr are bounded by the existing output limit semantics;
7. playbook config cannot request `shell: true` or arbitrary environment injection because those knobs do not exist in the runner contract.

Run CI and capture expected RED evidence before implementation.

---

## Task 2 — GREEN: implement `runRecoveryPlaybook`

**Create:** `nervous-link/pc-agent/recoveryPlaybook.js`

Contract:

```js
runRecoveryPlaybook({ playbook_id }, policy)
```

Rules:

- `playbook_id` must be a conservative identifier such as `^[a-z0-9][a-z0-9._-]{0,63}$`;
- params must contain exactly `playbook_id` and no arbitrary payload;
- resolve playbook from `policy.recovery.playbooks[playbook_id]`;
- executable and argv come only from policy;
- spawn with `shell: false`, hidden Windows window, inherited base environment only;
- no remote env injection;
- no string interpolation/substitution from request fields;
- optional cwd must pass existing path-root policy or a dedicated recovery cwd allowlist;
- clamp timeout/output to existing global limits;
- return `{exit_code, stdout, stderr, truncated, playbook_id}`.

Run targeted tests until GREEN.

---

## Task 3 — RED/GREEN: add typed protocol action/capability

**Modify:**
- `nervous-link/protocol/constants.js`
- `nervous-link/pc-agent/capabilities.js`
- `nervous-link/pc-agent/agent.js`
- protocol/policy/integration tests as needed

Add:

- action: `run_recovery_playbook`
- capability: `recovery.execute.safe`

Map the action to that capability. In `agent.js`, dispatch it only through `runRecoveryPlaybook`.

Audit resource should identify `playbook_id`, not executable command text. Existing kill switch and authentication/policy gates remain in force.

Test that:

- wrong capability fails with `CAPABILITY_ACTION_MISMATCH`;
- capability default-denies when absent/false;
- enabled capability + known playbook succeeds;
- arbitrary `run_command` permissions are not implicitly granted.

---

## Task 4 — Extend example policy safely

**Modify:** `nervous-link/config/policy.example.json`

Add `recovery.execute.safe: false` by default.

Add an illustrative disabled/local example structure under `recovery.playbooks`; do not embed secrets or private tunnel endpoints. The example should show an absolute/local trusted script path and exact argv, but leave the capability disabled until the operator deliberately enables a locally reviewed playbook.

Do not broaden `command.execute.safe` or add PowerShell to the generic safe command allowlist as part of this feature.

---

## Task 5 — Documentation and threat model

**Modify:** `nervous-link/README.md`

Document:

- recovery playbooks are locally configured, fixed and typed;
- remote caller selects only an id;
- no arbitrary argument/environment injection;
- local policy file remains ignored/private;
- write roots must not include the policy/playbook definition directory unless deliberately required;
- remote kill switch remains independent;
- this feature is a recovery lane, not Desktop Commander parity.

Explicitly warn that a recovery script itself is trusted code and must be reviewed/hash-pinned operationally before enabling it.

---

## Task 6 — Full regression + CI

Run `npm test` on Windows CI.

Required evidence:

- all existing Nervous Link tests remain green;
- new recovery-playbook tests green;
- no owner/device tokens in logs or committed config;
- capability remains default-deny in example policy;
- generic command runner semantics unchanged.

Commit with a focused message.

---

## Task 7 — Prepare Kai Link recovery playbooks, but do not deploy blind

Only after live PC source/runtime paths are revalidated, define reviewed local playbooks for narrow operations such as:

- `kai_link_status`: inspect Tailscale status/Serve status, Relay listener count, Relay health and watchdog state;
- `kai_relay_quiesce`: place Mobile Relay watchdog into an explicit maintenance/quiesced mode designed by the single-owner recovery plan;
- `kai_relay_recover_single_owner`: execute the already-tested controlled single-owner recovery workflow;
- `kai_tailscale_status`: read-only transport diagnostics;
- optionally `kai_link_resume`: restore normal supervised state after a verified maintenance operation.

Each playbook must be a dedicated reviewed local script with no request-derived command interpolation. The local policy should reference exact paths and operationally record expected hashes/versions.

Do not provision these playbooks until the exact Mobile Relay source/runtime authority is preserved and the single-owner tests are green.

---

## Promotion gate

Promote `PC_REMOTE_RECOVERY_PROFILE_READY` only when fresh evidence proves:

- agent connects/authenticates through its actual deployed Relay;
- read-only recovery status playbook round-trip works remotely;
- unknown/extra-argument attempts are denied;
- audit records the playbook id with secrets redacted;
- kill switch still blocks execution;
- recovery capability can be revoked by local policy;
- no unrestricted shell was introduced.

This gate does not claim Mobile Control Gate A or full remote desktop parity.
