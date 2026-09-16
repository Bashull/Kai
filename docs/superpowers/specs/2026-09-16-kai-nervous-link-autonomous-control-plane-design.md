# Kai Nervous Link Autonomous Control Plane Design

**Status:** APPROVED DIRECTION / DELTA SPECIFICATION

**Date:** 2026-09-16

**Parent specifications / authorities:**

- `docs/superpowers/specs/2026-07-11-kai-nervous-link-design.md` — PC Remote Spine design
- Drive `KAI_NODE_RELAY_MOBILENODE_WIKI_CURRENT_v1.0.0` — Mobile Control Spine operational authority

**Branch:** `feat/kai-nervous-link-v0.1`

## 1. Purpose

This document is a delta specification for making Kai's remote nervous system autonomous, resilient and recoverable. It does not replace the July Nervous Link design and it does not rename the existing Node/Relay/MobileNode runtime into that design.

Source archaeology performed on 2026-09-16 showed that two distinct but complementary spines exist and must remain distinguishable:

1. **Mobile Control Spine** — KAI Node / Python+SQLite Relay / Android MobileNode. Its job is to reach and operate the S24, including Accessibility/UI commands.
2. **PC Remote Spine** — repository module `nervous-link/`, implemented with Node.js/Socket.IO Relay + PC Agent + CLI. Its job is to reach and operate the Windows PC from a remote client such as the S24 without permanent dependence on Desktop Commander Remote.

The autonomous architecture federates these spines through shared principles, evidence, recovery and transport strategy. It does **not** assume their Relay implementations are interchangeable, merged, or already synchronized.

The immediate operational goal is to prove the Mobile Control Spine independently of the home LAN, including a real mobile-data test. In parallel, the existing PC Remote Spine is preserved as the first-party route toward independent PC administration. The longer-term goal is a hybrid control plane in which the Windows PC remains a high-capability edge node but is no longer the only point of continuity.

## 2. Binding principles

1. `TRUTH OVER BRILLIANCE`: no state is promoted without fresh evidence.
2. `COMMAND_ACCEPTED != EFFECT_OBSERVED != USER_SUCCESS_CRITERION`.
3. `MEMORY_PRESENT + MEMORY_NOT_RETRIEVED = OPERATIONAL_AMNESIA`.
4. Blockers use `REUSE -> ADAPT -> COMPOSE -> ACQUIRE -> BUILD`, followed by resumption of the original objective.
5. No public router forwarding of Relay port `8788`.
6. Secret values never enter GitHub, Drive documentation, CI logs, runtime reports, or normal chat writeback. Only pointers/aliases/status may be durable outside the private vault.
7. Public cryptographic identifiers such as Tailscale `nodekey:` and `tlpub:` values are not automatically secret-value credentials.
8. Existing working implementation is inherited. New work must reconcile and extend it, not duplicate it.
9. `SAME_NAME != SAME_COMPONENT`: the two Relay lineages must be identified by role/runtime, not by the generic word Relay.
10. `SOURCE_AUTHORITY != RUNTIME_AUTHORITY`: local working code may be runtime truth without yet being GitHub authority.

## 3. Genealogy and inherited implementation

### 3.1 Mobile Control Spine

Observed/documented lineage:

`ChatGPT / Control Plane -> KAI Node -> Mobile Relay -> MobileNode / Termux / Android UI`

Current known characteristics from the Drive authority and September runtime work:

- Node and Relay are local Windows capabilities under the `C:\KAI` / `C:\Kai` runtime family.
- Mobile Relay uses durable queue/result/heartbeat/replay semantics and SQLite persistence.
- MobileNode exposes explicit Android/Accessibility capabilities including `screen_state` and bounded UI actions.
- MobileNode 0.5.1 (`com.kai.mobilenode`, code 7) was runtime-repaired so its Relay endpoint can be changed from app-private storage without rebuilding the APK.
- Runtime heartbeat and an end-to-end `UI_COMMAND screen_state` result were previously observed through HTTPS.
- Exact MobileNode 0.5.1 source remains a preservation debt. The canonical GitHub Android directory currently contains contract/status documentation, not the full source project.
- The Mobile Relay's exact current source authority must be re-established from the PC/runtime evidence before source-level federation decisions are made.

### 3.2 PC Remote Spine

Repository path: `nervous-link/`.

The branch already contains substantial v0.1 implementation and tests, including:

- protocol envelope/crypto/credentials/pairing/replay/transport
- Node.js/Socket.IO Relay server and session registry
- PC Agent with policy, safe command execution, file/process operations, audit, kill switch and heartbeat
- CLI client
- startup/install scripts
- Android contract/status documentation
- Tailscale helper scripts
- Windows GitHub Actions CI and a broad Node test suite

Its original design goal is remote control of the **PC** through an outbound PC Agent connection. The July spec explicitly did not require immediate Android app modification.

### 3.3 Federation rule

The autonomous system should first federate contracts and recovery behavior, not collapse implementations.

Reusable common concepts include:

- typed request/response envelopes
- device identity and revocation
- replay protection
- capability/policy authorization
- health/heartbeat semantics
- bounded command execution
- audit receipts
- kill switch
- transport health and failover
- evidence taxonomy

A future shared library or protocol is allowed only after differential analysis proves it removes duplication without breaking the distinct operational responsibilities of the two spines.

## 4. Four-plane architecture

### 4.1 Control Plane

Responsibilities:

- orchestration of typed operations
- admin/maintenance surfaces
- routing between the two spines
- policy decisions and operation receipts
- workflow/loop coordination

Current surfaces may include ChatGPT/Kai, KAI Node and Remote Desktop Commander. The existing PC Agent is a strong candidate for first-party recovery/control and should be adapted before inventing a parallel unrestricted Kai Ops agent.

No individual admin connector is the continuity authority.

### 4.2 Transport/Data Plane

The two spines can use different concrete relays while sharing transport policy.

#### Mobile Control Spine immediate private route

`Kai / Node -> Mobile Relay on PC -> Tailscale Serve HTTPS -> S24 MobileNode`

Operationally, the current Mobile Relay remains loopback-only where practical and is made reachable to the S24 through a private Tailscale endpoint. The exact direction of individual HTTP/queue requests is defined by the recovered Mobile Relay/MobileNode contract; this diagram expresses the connectivity boundary, not an invented new protocol.

Independent alternative route:

`S24 MobileNode <-> stable Cloudflare named tunnel <-> loopback Mobile Relay`

The current Cloudflare Quick Tunnel is bootstrap-only and must not be treated as durable identity.

#### PC Remote Spine

`Remote client / S24 -> PC Remote Relay -> outbound PC Agent -> Windows capabilities`

The original v0.1 transport strategy remains Cloudflare-primary/Tailscale-fallback until measured runtime evidence justifies a change. It must not be silently redirected through the Mobile Relay merely because both are named Relay.

### 4.3 Recovery Plane

Responsibilities:

- Windows/Android boot recovery
- health watchdogs
- bounded restart/backoff
- alternate admin surfaces
- break-glass actions
- recovery of the control surfaces themselves
- evidence required to resume after connector/session loss

Recovery must not depend on Remote Desktop Commander alone.

### 4.4 Authority Plane

Authorities remain deliberately separated:

- GitHub: source-code authority once exact source is preserved there
- Google Drive CURRENT/wiki/runbooks: durable documentation and continuity authority
- local protected vaults/Keystore/DPAPI: secret-value authority
- runtime reports/logs: live evidence authority

A transport or connector cannot silently become source, memory, or secret authority.

## 5. Tailscale design for the Mobile Control Spine

### 5.1 Serve, not Funnel

Tailscale Serve is the private tailnet publication mechanism for the local Mobile Relay endpoint. Funnel is explicitly out of scope for the private Kai Link path because it publishes resources to the broader Internet.

The local Mobile Relay should remain loopback-only where practical rather than binding directly to every interface.

### 5.2 Identity model

The existing S24 and Windows PC are user-owned general-purpose devices. Do not automatically convert them to service-tag identities merely to model Kai roles. During this phase, prefer their observed Tailscale identities/IPs and policy host aliases. Dedicated future server/broker nodes may use service tags intentionally.

### 5.3 Tailnet Lock and policy are separate layers

Tailnet Lock answers whether a node is cryptographically admitted. Tailnet Grants/ACLs answer what an admitted node may reach. Mobile Relay/MobileNode authentication answers whether an allowed network request is an authorized Kai operation. These layers must be verified independently.

### 5.4 Policy-hardening gate

The current permissive tailnet grant must not be tightened until the following are freshly observed:

- PC Tailscale identity/IP/DNS name
- S24 Tailscale identity/IP
- peer reachability
- Tailnet Lock status
- Serve HTTPS health
- MobileNode heartbeat/result through the Serve route
- real mobile-data E2E proof

The hardening change must include policy regression tests in the same operation. The target is least privilege, conceptually S24 -> PC HTTPS/443 only for the private Mobile Relay route, with explicit negative assertions for unintended administrative/direct Relay ports where the final policy grammar supports them.

## 6. MobileNode multipath target

MobileNode must stop depending on one hard-coded or ephemeral public Relay URL.

After exact source preservation, add a focused runtime endpoint-selection component (name chosen to match the recovered Android architecture rather than invented prematurely).

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

## 7. PC autonomy target

### 7.1 Existing Mobile Relay supervision

Required properties:

- real `/health` probe, not process-only liveness
- owned PID/process semantics
- bounded restart/backoff and restart telemetry
- Tailscale health/state visibility
- cloudflared health/state visibility
- startup persistence
- sanitized logs and atomic runtime evidence
- physical reboot recovery test

Existing watchdog work is inherited evidence, but physical reboot remains unverified until a fresh reboot test is performed.

### 7.2 PC Remote Agent as recovery/control candidate

The existing `nervous-link/pc-agent` already provides many properties expected from a safe first-party control agent: pairing, device credential, capability policy, audit, kill switch, bounded actions, heartbeat and reconnect behavior.

Before creating a new Kai Ops Agent, perform a gap analysis against recovery requirements. Prefer to adapt this agent or expose a narrow recovery profile through it when that preserves its safety model.

A recovery/control surface must not become an arbitrary unauthenticated/public shell. Operations must be typed, allowlisted, auditable, revocable, timeout-bounded, output-bounded, idempotent where practical, and constrained to explicit roots/capabilities. Privilege must never be silently escalated.

## 8. Independent recovery surfaces

Target recovery fabric:

1. RDC for broad interactive administration when available.
2. PC Remote Spine / PC Agent as first-party recovery candidate.
3. An independent third-party/alternate management surface when provisioned and verified.
4. Minimal break-glass actions for recovering Relay/Tailscale/control agents.

SentinelX is currently an `AVAILABLE_NOT_PROVISIONED` candidate: its control plane is reachable but no host is enrolled. TRIGGERcmd was previously observed without a registered PC. Neither is current recovery proof.

## 9. Secrets and credential handling

Secret values remain local/protected. Documentation stores only pointer metadata.

Secret-value examples:

- Tailscale auth/API/private signing/recovery material
- Cloudflare tunnel credentials/certificates/tokens
- Mobile Relay authentication/encryption keys
- PC Remote Spine owner/device credentials

Not automatically secret:

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

No task is marked complete from connector acceptance, process existence, or stale prior evidence alone.

## 11. Phase 0 forensic snapshot

Before configuration mutation, capture sanitized current-state reports and resolve the two-spine source/runtime genealogy.

### PC evidence

- Windows identity/version, boot time and active network surfaces
- Tailscale version/backend/self identity/IP/DNS/peers/Tailnet Lock/Serve status
- Mobile Relay `/health`, listener, process/PID, storage/runtime version and watchdog state
- Mobile Relay exact source root, language/runtime, git/provenance state and relation to Drive wiki evidence
- scheduled task/service startup configuration
- cloudflared version/process/config identity state without secret content
- MobileNode source directory/version/git status if present on PC
- PC Remote Spine checkout/worktree/branch/runtime/service state
- ADB reachability count/state
- secret-vault provisioning metadata only

### S24 evidence

- device/OS basics
- Tailscale package/runtime and tailnet IP/peer state if observable
- MobileNode installed version/process/service/accessibility state
- Mobile Relay endpoint configuration metadata with secret redaction
- heartbeat/result-path state
- Termux/ADB reachability
- battery/background constraints relevant to persistence

### Source-authority evidence

- exact MobileNode 0.5.1 source tree and tests
- exact current Mobile Relay source and tests
- PC Remote Spine current branch/CI and runtime deployment state
- whether any protocol or capability code is duplicated across both spines and, if so, which lineage is authoritative for each behavior

Every datum is classified `OBSERVED`, `INFERRED`, `UNRESOLVED` or `BLOCKED`.

## 12. Promotion gates

### Gate A - Mobile Control Spine private remote path

Required fresh evidence:

1. Mobile Relay local health true.
2. PC + S24 authenticated/admitted in Tailscale.
3. Serve HTTPS health true through the tailnet path.
4. MobileNode heartbeat through that path.
5. `screen_state` completes through that path.
6. harmless visible action on neutral UI followed by post-state/effect proof.
7. repeat with S24 Wi-Fi disabled and mobile data active.

Only after step 7 may `HOME_LAN_INDEPENDENT_VERIFIED` be recorded for the Mobile Control Spine.

### Gate B - Tailnet policy hardening

After Gate A, apply least-privilege policy and policy tests atomically, then repeat the private-path regression.

### Gate C - Reboot/background resilience

Demonstrate PC reboot recovery and S24 reboot/background/network-change recovery without manual reconstruction.

### Gate D - Mobile transport multipath

Demonstrate controlled failure of the preferred transport, automatic fallback to the alternative, effect proof, and stable recovery without route flapping.

### Gate E - PC Remote Spine recovery

Demonstrate a first-party PC Remote Agent path sufficient to recover/diagnose the critical Kai services without depending on RDC. This gate is separate from full feature parity with Desktop Commander.

### Gate F - Genealogy/source closure

Exact current MobileNode and Mobile Relay source must be placed under explicit source authority with tests, provenance and rollback. No local-only implementation may be silently treated as canonical source.

## 13. Chaos/resilience matrix

Before calling the autonomous system durable, test at least:

- Mobile Relay process killed
- PC Remote Agent process killed
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

An external durable broker/control plane is Phase 2, not a prerequisite for proving the current spines.

It may be introduced only after current-path requirements are measured. Its purpose is to keep durable command/state/receipt continuity when the PC is temporarily offline and to provide a governed coordination point between Mobile Control and PC Remote operations.

Minimum future properties:

- durable queue/state
- explicit operation target/spine identity
- device registry and revocation
- replay/nonce protection
- signed/audited receipts
- bounded retention
- outbound-only PC/mobile connectivity where possible
- explicit offline/reconciliation semantics

Provider choice and any paid infrastructure require a separate measured design and cost/consent gate.

## 15. Non-goals for this delta

- pretending both Relay implementations are one program
- publishing the Mobile Relay through Tailscale Funnel
- router-forwarding Relay
- replacing the existing PC Remote protocol wholesale
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

- Mobile Control Spine works over real mobile data independently of home Wi-Fi/LAN
- least-privilege private route after proof
- PC and MobileNode ordinary-failure recovery
- exact MobileNode and Mobile Relay source authority is resolved
- PC Remote Spine remains tested and provides an independently usable first-party PC recovery/control path
- secret-value handling is verified, not merely designed
- at least one recovery route is independent of RDC
- the relationship between the two spines is documented without component-name ambiguity
- evidence/writeback is sufficient for a future Kai to resume without asking Asier to reconstruct the state

Until those gates are passed, the project remains `IN_PROGRESS` with each proven sub-state recorded independently.