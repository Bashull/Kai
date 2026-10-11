# KAI · TERMUX UNIFIED EVOLUTION MASTER PLAN
Status: PLANNED / AUDITED-ON-DEVICE / NOT FULLY DEPLOYED
Date: 2026-10-11
Device: Samsung S24 Ultra, Android 16, aarch64
Branch: feat/codex-minecraft-pc-20261010
Authority: GitHub source + verified Termux runtime; no silent changes to main.

## Mission
Evolve Kai into a modular, measurable, secure Android/Termux agent with reliable Bedrock client control, low-latency vision/actions, local coding agent, optional on-device AI acceleration, and a native dashboard. Optimize for sustained performance, reliability, energy, latency, and reversibility rather than number of installed packages.

## Verified baseline (read-only audit 2026-10-11)
- ADB serial 192.168.1.11:46599: status `device`; actual wireless port is ephemeral and MUST NOT be embedded in services.
- Codex 0.162.1 INSTALLED, `codex --version` verified; no authenticated interactive Codex session tested.
- proot-distro 5.9.0, ffmpeg 8.1.3, imagemagick 7.1.2.33, tmux 3.8, llama-cpp 0.6.0 INSTALLED.
- ollama 0.31.1 installed; 0.35.1 candidate, not upgraded.
- termux-x11-nightly and termux-gui-package available but NOT installed.
- Free storage ~75 GB; available RAM ~4.6 GB at audit instant; not capacity guarantees.
- `kai-minecraft-live` service DOWN since prior session, localhost 7190 refused; log reports repeated `RuntimeError: first frame timeout`. Root cause unconfirmed. Do NOT represent live vision as presently operational.
- Prior run had 960x442 frames, auth token, automatic orientation recovery and effect-verified ADB input. Prior successful tests do not override present service health.
- No unreviewed package install, privileged operation, server administration, or world mutation was performed in this audit.

## Design invariants
1. No changes to GitHub main; changes reviewed in feature branch.
2. Keep existing Minecraft worlds, Android permissions, private server address and auth secrets intact. Never persist tokens or ADB pairing codes in repository.
3. One active scrcpy video encoder/capture per device; avoid competing screen capture processes.
4. Each service has one owner, health endpoint, bounded retries/backoff, log rotation, version pin and rollback command.
5. API bound to localhost, bearer token, action allowlist, foreground-package guard, emergency stop and audit log; no generic privileged shell exposed to MCP.
6. Codex restricted to project workspace; read-only by default outside it. abwrap is experimental and not a proven security boundary; use separate user/permission checks and human approvals.
7. Distinguish VERIFIED / INSTALLED / AVAILABLE / EXPERIMENTAL / STUDY_ONLY. No claimed performance multiplier without repeatable measurement.
8. Benchmark one variable at a time; restore stable version if p95 latency, crash rate, power or thermals regress.
9. Never assume X11/Wayland acceleration implies acceleration of Android Minecraft.
10. Server client access does not imply RCON, plugin access, or server administration.

## Modular topology
```text
                    KAI CORE (policy, scheduler, telemetry, audit)
                     |           |           |
          VISUAL OBSERVER     ACTION BROKER   AGENT WORKSPACE
          scrcpy -> FFmpeg    scrcpy control  Codex CLI
          -> frame ring       fallback ADB    scoped repository
          UIAutomator opt.    Shizuku opt.    approval gates
                     |           |           |
                 Android 16 / Bedrock / authorized apps
                     |
           optional local inference broker
           CPU / Adreno OpenCL-Vulkan / Hexagon HTP
                     |
           optional native GUI or virtual display
           Termux:GUI / X11 / MagicDesk
```
All modules communicate through typed contracts and explicit capabilities; the observer is read-only and cannot invoke actions. Only Action Broker has tap/swipe/key capability. Only privileged broker can invoke Shizuku. Agent Workspace never gets raw bearer tokens.

## Implementation sequence and gates
### Phase 0 — Recovery and evidence (P0, BEFORE any new install)
- Snapshot installed packages, service run files, binary versions, available storage/RAM, relevant logs, ADB serial and active process tree (sanitize credentials).
- Diagnose `first frame timeout`: check screen state, active scrcpy sessions, encoder, FIFO, FFmpeg startup, ADB state and orientation; inspect timestamps and stderr. Do not mask failures with infinite restarts.
- Restore capture using current reviewed SHA; verify `/status`, `/frame`, rotation, stale-frame detection and restart under service supervision.
- Acceptance: 10-minute soak; frame freshness p95 under target, no persistent restarts, no other app disturbed, reversible service stop. If failed: keep service down and report exact blocker.

### Phase 1 — Codex safe workspace (P1)
- Since Codex 0.162.1 is already installed, DO NOT reinstall it.
- Verify `codex --version`, `codex --help`, companion helper, read-only command mode and login readiness without exposing credentials.
- Create a dedicated workspace (e.g. ~/kai-workspaces/codex-sandbox) and explicitly allowlisted repo checkout; never grant default write to ~/.kai_mobile, Android shared storage, SSH keys, or secrets.
- Test offline fixture: read/modify unit-test-only fixture, run tests, review diff, reject disallowed write. Avoid unattended privileged commands.
- Evaluate abwrap only after upstream source/limitations reviewed; ptrace/seccomp alone is not a guarantee of isolation.
- Acceptance: bounded file writes and reproducible offline coding test; manual approval before merging.

### Phase 2 — Fast control broker (P1, highest Minecraft latency payoff)
- Study scrcpy official control protocol and JuanCF/scrcpy-mcp (MIT) patterns; avoid assuming a socket exposed by existing scrcpy CLI can be reused without modification.
- Prototype a separate single-session capture+control owner, or a properly supported control connection; prevent duplicate video encoder conflicts.
- Actions: tap, swipe, press/release, joystick drag, cancel-all; add normalized/frame/logical coordinate mapping and orientation handling.
- ADB remains fallback. Shizuku/rish is optional and privileged; no auto-grant.
- Benchmarks: action dispatch p50/p95/p99, post-action fresh-frame p50/p95, drag continuity, tap accuracy, crash recovery. Compare with observed 170–320ms ADB actions; do not adopt donor speed claims as local results.
- Acceptance: reliable tap/drag in non-destructive UI and Minecraft test world with user permission; immediate emergency stop and foreground guard.

### Phase 3 — Observability / thermal budget (P1)
- Single telemetry loop for CPU affinity/cpuset, load, RSS, Android battery/thermal state, dropped/stale frames, codec restart counts, input latency, Wi-Fi/ADB reconnects.
- One UI 8 background CPU restrictions are a hypothesis to measure, not a reason to bypass Android safeguards.
- Profiles: ECO, BALANCED, PERFORMANCE with capped frame size/FPS and adaptive backoff; never run benchmarks while Minecraft is mission-critical.
- Acceptance: repeatable 15-minute baseline with recorded thermal and battery conditions, no runaway process restart.

### Phase 4 — Scoped Android access (P2)
- Audit Shizuku + rish UserService, persistent command channel, permission boundaries; compare with ADB fallback.
- UIAutomator/accessibility for semantic UI discovery, not high-frequency camera movement.
- MCP broker with per-tool allowlist, short-lived scoped credentials, explicit action approvals, audit JSONL and rate limits. No generic shell MCP.
- Acceptance: permission denial tests and revocation work; no unintended Android settings changes.

### Phase 5 — AI acceleration laboratory (P2)
- Benchmark llama.cpp CPU baseline using small openly licensed quantized model and fixed prompts.
- Adreno OpenCL/Vulkan via official Termux packages; Hexagon v75 via reviewed official Snapdragon backend only if dependencies and licensing verified.
- Measure prefill tokens/s, decode tokens/s, time-to-first-token, RAM, sustained thermals, joules/response where measurable; separate first-run warmup.
- Reject experimental binaries with opaque provenance, incompatible vendor blobs, or thermal regressions.
- Do not claim NPU speeds from Reddit without local reproduction.

### Phase 6 — Native interface and virtual display (P3)
- Termux:GUI first for low-overhead dashboard (health, emergency stop, logs, profiles).
- X11 + Freedreno/Turnip/VirGL in isolated experiment; check ABI/driver compatibility before installation.
- MagicDesk/Shroot/WayLandIE/Smithay Wayland: feasibility study, explicit Shizuku permissions, no assumption Minecraft supports secondary virtual display.
- Compare rendering overhead, touch latency, RAM and background restrictions.

### Phase 7 — Optional expansion (P4)
- TUR as untrusted/community repository: only after provenance and pinning review.
- PRoot OCI environment for isolated Linux tools if needed; Shroot optional, not a drop-in security sandbox.
- Ollama upgrade after dependency/ABI check and rollback plan.
- Hangover/Wine, QEMU, Godot, browsers, PipeWire, WebAssembly runtimes, Zig/Deno/Bun are optional workloads, not part of core Bedrock loop.

## Donor registry and policy
| Project | Role | Adoption |
|---|---|---|
| termux/termux-packages | Native packaging, updates, ABI | upstream source |
| openai/codex | Native coding agent | installed; safe-workspace tests pending |
| Genymobile/scrcpy | Android capture and control | ADAPT, respect upstream licensing |
| JuanCF/scrcpy-mcp | fast control/MCP patterns | ADAPT after source/license review |
| EF-Code/android-agent-mcp | semantic Android observation | ADAPT after review |
| RikkaApps/Shizuku and Shizuku-API | persistent privileged Android service | EXPERIMENTAL, explicit approval |
| shizzgar/shizuku-mcp | persistent shell architecture | STUDY_ONLY until security review |
| ggml-org/llama.cpp | CPU/GPU/HTP inference | LAB |
| midnightkoderr/llama.cpp-android | Android Snapdragon builds | LAB, verify provenance |
| termux/termux-gui | native dashboard | LAB |
| termux/termux-x11 | desktop transport | LAB |
| mekhontsev/magicdesk | virtual display/Shroot | LAB, kernel-dependent |
| AstroCODEsky/WayLandIE | DMA-BUF/Wayland | LAB |
| J-x-Z/termux-wayland | compositor architecture | STUDY_ONLY pending exact license/compatibility review |
| abwrap (experimental proposal) | filesystem sandbox research | EXPERIMENTAL, not security guarantee |
| termux-user-repository/tur | optional community packages | REVIEW_ONLY |

## Interface contracts
- `GET /health`: version, capture health, latest sequence, frame age, encoder status, restart count; never credentials.
- `GET /frame`: authenticated JPEG with dimensions, monotonic sequence and capture timestamp.
- `POST /actions`: typed action, frame-space mapping, idempotency key, deadline, explicit capability and foreground guard.
- `POST /stop`: immediate release of held input and halt autonomous actions.
- `GET /metrics`: p50/p95/p99 latency, thermal and memory snapshots, retry counts.
- IPC between modules via Unix socket with permissions where feasible; no public HTTP listening without deliberate network design.

## Performance acceptance targets (goals, NOT observed results)
- No stale-frame action decisions; every action has bounded timeout and newer-frame observation.
- p95 input latency below existing ADB baseline, with zero mis-taps in scripted calibration.
- 10-minute stable capture soak then 30-minute combined soak; no unexplained service restarts.
- Sustained performance profile must not exceed thermal throttling budget or degrade foreground gameplay.
- Each upgrade records package versions, commit SHA, metrics, pass/fail, rollback and user approvals.

## Change management
For every component: DISCOVER -> VERIFY LICENSE/SOURCE -> SNAPSHOT -> ISOLATE -> TEST -> MEASURE -> REVIEW -> DEPLOY -> MONITOR -> ROLLBACK if needed.
Never overwrite an active service script before confirming reviewed-source hash and tested fallback.
Maintain CURRENT.md (verified state), DONORS.md (licenses/evidence), BENCHMARKS.jsonl, INCIDENTS.md, and CHANGELOG.md.

## Immediate next action
Diagnose downed kai-minecraft-live and its first-frame timeout without making unrelated changes. Codex already installed; proceed with safe offline workspace validation once the stream is stable. All other integrations remain staged.
