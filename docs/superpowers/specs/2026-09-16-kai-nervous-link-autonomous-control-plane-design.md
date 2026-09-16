# Kai Nervous Link Autonomous Control Plane Design

**Status:** APPROVED DIRECTION / DELTA SPECIFICATION

**Date:** 2026-09-16

**Parent specification:** `docs/superpowers/specs/2026-07-11-kai-nervous-link-design.md`

**Branch:** `feat/kai-nervous-link-v0.1`

## 1. Purpose

This document is a delta specification for the existing Kai Nervous Link v0.1 implementation. It does not replace or rebuild the July design. It reconciles the implementation that now exists in the repository, the September 2026 runtime work on Relay/MobileNode, and the new autonomy/resilience requirements.

The immediate goal is to prove secure control of Asier's S24 MobileNode through Kai Relay independently of the home LAN, including a real mobile-data test. The longer-term goal is a hybrid control plane in which the Windows PC remains a high-capability edge node but is no longer the only point of continuity.

## 2. Binding principles

1. `TRUTH OVER BRILLIANCE`: no state is promoted without fresh evidence.
2. `COMMAND_ACCEPTED != EFFECT_OBSERVED != USER_SUCCESS_CRITERION`.
3. `MEMORY_PRESENT + MEMORY_NOT_RETRIEVED = OPERATIONAL_AMNESIA`.
4. Blockers use `REUSE -> ADAPT -> COMPOSE -> ACQUIRE -> BUILD`, followed by resumption of the original objective.
5. No public router forwarding of Relay port `8788`.
6. Secret values never enter GitHub, Drive documentation, CI logs, runtime reports, or chat writeback. Only pointers/aliases/status may be durable outside the private vault.
7. Public cryptographic identifiers such as Tailscale `nodekey:` and `tlpub:` values are not automatically secret-value credentials.
8. Existing working implementation is inherited. New work must reconcile and extend it, not duplicate it.

## 3. Current inherited implementation

The branch already contains substantial v0.1 implementation and tests under `nervous-link/`, including:

- protocol envelopes, crypto, credentials, pairing, replay guard and transport
- Relay server/store
- PC agent, policy and capabilities
- CLI client
- startup/install scripts
- Android contract/status documentation
- Tailscale bootstrap/signing helper scripts
- CI workflow and a broad Node test suite

The Android MobileNode 0.5.1 runtime source remains a preservation debt: the runtime implementation exists outside the canonical GitHub Android client directory and must not be considered source-authoritative until its exact source is recovered, compared and committed.

## 4. Four-plane architecture

### 4.1 Control Plane

Responsibilities:

- orchestration of typed operations
- admin/maintenance surfaces
- policy decisions and operation receipts
- workflow/loop coordination

Current surfaces may include ChatGPT/Kai and Remote Desktop Commander. Future surfaces may include a first-party Kai Ops Agent and independent recovery adapters. No individual admin connector is the continuity authority.

### 4.2 Transport/Data Plane

Responsibilities:

- authenticated command/result transport
- heartbeats and health probes
- route selection and failover
- Relay protocol traffic

Immediate private route:

`S24 MobileNode -> Tailscale/Tailnet Lock -> tailnet policy -> Tailscale Serve HTTPS -> 127.0.0.1:8788 -> Kai Relay`

Independent alternative route:

`S24 MobileNode -> stable Cloudflare named tunnel -> loopback Kai Relay`

The current Cloudflare Quick Tunnel is bootstrap-only and must not be treated as durable identity.

### 4.3 Recovery Plane

Responsibilities:

- Windows/Android boot recovery
- health watchdogs
- bounded restart/backoff
- alternate admin surfaces
- break-glass actions
- evidence required to resume after connector/session loss

Recovery must not depend on Remote Desktop Commander alone.

### 4.4 Authority Plane

Authorities remain deliberately separated:

- GitHub: source-code authority
- Google Drive CURRENT/wiki/runbooks: durable documentation and continuity authority
- local protected vaults/Keystore/DPAPI: secret-value authority
- runtime reports/logs: live evidence authority

A transport or connector cannot silently become source, memory, or secret authority.

## 5. Tailscale design

### 5.1 Serve, not Funnel

Tailscale Serve is the private tailnet publication mechanism for Relay. Funnel is explicitly out of scope for the private Kai Link path because it publishes resources to the broader Internet.

Relay should remain loopback-only where practical and be exposed to the tailnet through HTTPS Serve rather than binding Relay directly to every interface.

### 5.2 Identity model

The existing S24 and Windows PC are user-owned general-purpose devices. Do not automatically convert them to service-tag identities merely to model Kai roles. During v0.1, prefer their observed Tailscale identities/IPs and policy host aliases. Dedicated future server/broker nodes may use service tags intentionally.

### 5.3 Tailnet Lock and policy are separate layers

Tailnet Lock answers whether a node is cryptographically admitted. Tailnet Grants/ACLs answer what an admitted node may reach. Relay/MobileNode authentication answers whether an allowed network request is an authorized Kai operation. These layers must be verified independently.

### 5.4 Policy-hardening gate

The current permissive tailnet grant must not be tightened until the following are freshly observed:

- PC Tailscale identity/IP/DNS name
- S24 Tailscale identity/IP
- peer reachability
- Tailnet Lock status
- Serve HTTPS health
- MobileNode heartbeat/result through the Serve route
- real mobile-data E2E proof

The hardening change must include policy regression tests in the same operation. The target is least privilege, conceptually S24 -> PC HTTPS/443 only for the MobileNode/Relay route, with explicit negative assertions for unintended administrative/direct Relay ports where the final grammar supports them.

## 6. MobileNode multipath target

MobileNode must stop depending on one hard-coded or ephemeral Relay URL.

A future `EndpointManager` (or equivalent focused component) will maintain a set of configured transport candidates and expose one selected healthy endpoint to RelayClient.

Required behavior:

- Tailscale Serve private endpoint preferred when healthy
- stable Cloudflare named-tunnel endpoint available as independent alternative
- bounded exponential backoff
- jitter where useful to avoid synchronized reconnect storms
- hysteresis/cooldown to avoid route flapping
- network-change awareness
- explicit endpoint health state
- no APK rebuild required merely to change a runtime endpoint
- no secret values written to diagnostics

The exact class/file structure must follow the recovered MobileNode 0.5.1 source rather than being invented before source preservation.

## 7. PC autonomy target

The PC edge stack must recover without interactive Kai intervention after ordinary failures.

Required properties:

- Relay real `/health` probe, not process-only liveness
- owned PID/process semantics
- bounded restart/backoff and restart telemetry
- Tailscale health/state visibility
- cloudflared health/state visibility
- startup persistence
- sanitized logs and atomic runtime evidence
- physical reboot recovery test

The existing Relay watchdog work is inherited evidence but physical reboot remains unverified until a fresh reboot test is performed.

## 8. Independent recovery surfaces

Remote Desktop Commander remains useful but must not be the only recovery path.

Candidate recovery fabric:

1. RDC for broad interactive administration.
2. First-party Kai Ops Agent for typed allowlisted operations.
3. An independent third-party/alternate management surface when provisioned and verified.
4. Minimal break-glass actions for recovery of the control surfaces themselves.

A first-party Kai Ops Agent must not expose an arbitrary unauthenticated/public shell. Operations must be typed, allowlisted, auditable, revocable, timeout-bounded, output-bounded, idempotent where practical, and constrained to explicit roots/capabilities. Privilege must never be silently escalated.

## 9. Secrets and credential handling

Secret values remain local/protected. Documentation stores only pointer metadata.

Examples that are secret values:

- Tailscale auth/API/private signing/recovery material
- Cloudflare tunnel credentials/certificates/tokens
- Relay authentication/encryption keys

Examples not automatically secret:

- public node keys/rotation public keys
- public DNS names
- public-safe capability/status metadata

Candidate vault paths are not promoted to deployed authority until Phase 0 confirms actual provisioning and consumer loaders. Existing working DPAPI/Keystore material must not be migrated solely for cosmetic path uniformity.

## 10. Work-loop contract

Every operational cell follows:

`OBSERVE -> CAPTURE_EVIDENCE -> CLASSIFY -> ROOT_CAUSE -> SINGLE_HYPOTHESIS -> MINIMAL_CHANGE -> VERIFY_COMMAND -> VERIFY_EFFECT -> REGRESSION -> COMMIT/PROMOTE -> WRITEBACK -> NEXT_CELL`

If a test/change fails, return to root-cause investigation instead of stacking speculative fixes.

Source changes use strict red/green/refactor where behavior changes:

`RED -> VERIFY_EXPECTED_FAILURE -> GREEN_MINIMAL -> VERIFY_ALL_GREEN -> REFACTOR -> VERIFY_AGAIN`

No task is marked complete from connector acceptance, process existence, or a stale prior test alone.

## 11. Phase 0 forensic snapshot

Before configuration mutation, capture a sanitized current-state report for PC and S24.

PC evidence:

- Windows identity/version and boot time
- active network surfaces
- Tailscale version, backend state, self identity/IP/DNS, relevant peers, Tailnet Lock status and Serve status
- Relay `/health`, listener address/port, owned PID and watchdog state
- scheduled-task/service startup configuration
- cloudflared version/process/config identity state without secret content
- MobileNode source directory/version/git status if present on PC
- ADB reachability count/state
- canonical Git checkout/worktree/branch/status
- secret-vault provisioning metadata only

S24 evidence:

- device/OS basics
- Tailscale package/runtime and tailnet IP/peer state if observable
- MobileNode installed version/process/service/accessibility state
- Relay endpoint configuration metadata with secret redaction
- heartbeat/result-path state
- Termux/ADB reachability
- battery/background constraints relevant to persistence

Every datum is classified `OBSERVED`, `INFERRED`, `UNRESOLVED` or `BLOCKED`.

## 12. Promotion gates

### Gate A - Private remote path

Required fresh evidence:

1. Relay local health true.
2. Tailscale PC + S24 authenticated/admitted.
3. Serve HTTPS `/health` true from the tailnet path.
4. MobileNode heartbeat through that path.
5. `screen_state` completed through that path.
6. harmless visible action on neutral UI followed by post-state/effect proof.
7. repeat with S24 Wi-Fi disabled and mobile data active.

Only after step 7 may the state `HOME_LAN_INDEPENDENT_VERIFIED` be recorded.

### Gate B - Policy hardening

After Gate A, apply least-privilege policy and policy tests atomically, then repeat the private-path regression.

### Gate C - Reboot/background resilience

Demonstrate PC reboot recovery and S24 reboot/background/network-change recovery without manual reconstruction.

### Gate D - Multipath

Demonstrate controlled failure of the preferred transport, automatic fallback to the alternative, effect proof, and stable recovery without route flapping.

### Gate E - Independent recovery

Demonstrate loss of RDC while retaining at least one independently verified safe recovery path.

## 13. Chaos/resilience matrix

Before calling the autonomous path durable, test at least:

- Relay process killed
- Tailscale stopped/unavailable
- Cloudflare tunnel stopped/unavailable
- PC reboot
- S24 reboot
- MobileNode process death
- Wi-Fi -> 4G/5G
- 4G/5G -> unrelated Wi-Fi
- endpoint expiry/config change
- RDC loss
- credential rotation/revocation drill where safe

For each scenario capture trigger, expected behavior, observed behavior, recovery time, command/result evidence and user-visible effect where relevant.

## 14. Hybrid control-plane evolution

The external durable broker is Phase 2, not a prerequisite for proving v0.1.

It may be introduced only after current-path requirements are measured. Its purpose is to keep durable command/state/receipt continuity when the PC is temporarily offline, with outbound-only node connections and no home-router port forwarding.

Minimum future properties:

- durable queue/state
- device registry and revocation
- replay/nonce protection
- signed/audited receipts
- bounded retention
- outbound-only PC/mobile connectivity
- explicit offline/reconciliation semantics

Provider choice and any paid infrastructure require a separate measured design and cost/consent gate.

## 15. Non-goals for this delta

- publishing Relay through Tailscale Funnel
- router-forwarding Relay
- replacing the existing Nervous Link protocol wholesale
- making user-owned devices service-tag identities without demonstrated need
- implementing a general unrestricted remote shell
- declaring Cloudflare named tunnel, Tailnet Lock signing, reboot recovery or mobile-data independence without fresh proof
- buying domains/VPS/services without an explicit cost gate

## 16. Stop gates

Continuous execution is preferred for reversible in-scope work. Stop for human action only when required by one of these classes:

- irreversible/destructive operation
- deliberate security weakening or sensitive privilege change
- external consent/OAuth/VPN/system dialog that technically requires the user
- paid resource/domain/service creation
- publication/merge to a shared protected authority outside the approved feature branch
- architecture so underdetermined that every path would be a guess

Everything else should be decided, documented, verified and continued without unnecessary human stalls.

## 17. Definition of success

The immediate autonomous Nervous Link milestone is successful only when fresh evidence demonstrates:

- mobile-data operation independent of home Wi-Fi/LAN
- least-privilege private route after proof
- PC and MobileNode ordinary-failure recovery
- source authority includes the exact MobileNode implementation
- secret-value handling is verified, not merely designed
- at least one recovery route is independent of RDC
- evidence/writeback is sufficient for a future Kai to resume without asking Asier to reconstruct the state

Until those gates are passed, the project remains `IN_PROGRESS` with each proven sub-state recorded independently.