# Kai S24 Termux SuperStack

Status: **ACTIVE FOUNDATION / CONTROL LAB / CODEX GATED / ACCEL LAB / DESKTOP DEFERRED**  
Authority branch: `feat/codex-minecraft-pc-20261010`  
Target device: Samsung S24 Ultra, Android 16, aarch64

## Purpose

This document merges the Termux, Android-control, Codex, scrcpy, Shizuku, Snapdragon acceleration and desktop/runtime research into one implementation path. The design goal is not "install everything": it is to promote only measured components into a small, compatible, supervised stack.

## Non-negotiable design rules

1. **One primary video encoder.** `kai-minecraft-live` owns the high-rate Minecraft vision stream. Any control experiment may use only a tiny mapper stream unless it replaces the primary stream after measurement.
2. **One owner per privilege channel.** ADB, scrcpy control, Shizuku/rish and Accessibility are separate capabilities, not competing copies of the same daemon.
3. **Local by default.** Kai control APIs bind to localhost and use explicit authentication tokens where applicable.
4. **Persistent work runs under runit.** Long-lived processes are supervised with `termux-services`; experiments are not promoted until restart/recovery behavior is proven.
5. **No hard-coded Wireless Debugging port.** The Android ADB endpoint may change. Services resolve the sole authorized device at startup.
6. **Benchmark before promotion.** CPU, memory, latency, frame freshness, restart behavior and battery/thermal cost are measured on the real S24.
7. **Experimental repositories never become authority by accident.** Licenses and donor policy are recorded before source transfer.
8. **Android 16 background CPU restrictions are treated as a platform constraint.** Do not assume all eight cores are available to a background Termux process.

## Layer model

### L0 · CORE — ACTIVE

Responsibilities: package/runtime health, snapshots, runit, rollback.

Verified baseline after 2026-10-11 maintenance:

- `proot-distro 5.9.0`
- `ffmpeg 8.1.3`
- `ImageMagick 7.1.2.33`
- `tmux 3.8`
- Python 3.14.x, Node 26.x, Rust 1.98.x
- `termux-services` already running `kai-mobile` and `kai-minecraft-live`

Pre-upgrade package/service evidence is stored locally under:
`~/.kai_mobile/baselines/termux-2026-10-11-pre-stack`.

### L1 · VISION — ACTIVE

Authority: `relay/kai_minecraft_live.py`.

Path:

```
Android display
  -> official scrcpy H.264 server/client
  -> one S24 hardware encoder
  -> MKV FIFO
  -> FFmpeg
  -> in-memory JPEG
  -> token-protected localhost API
```

Verified behavior:

- landscape Minecraft frames: 960×442
- portrait frames: 442×960
- automatic capture-only restart on portrait/landscape mismatch
- no ADB/Minecraft restart required for orientation recovery
- `GET /frame`, `GET /next`, `POST /act`, `POST /minecraft`
- service supervised by `runsv`

### L2 · CONTROL — ACTIVE FALLBACK + LAB FAST PATH

Current fallback:
`ADB shell input` through `kai_minecraft_live.py`.

This path is reliable but command dispatch is materially slower than the frame loop.

Fast-path target:
**scrcpy binary control socket** using donor knowledge from `scrcpy-mcp`.

Important protocol fact discovered during integration:

- scrcpy touch input needs a valid `PositionMapper`.
- the mapper is created with the video capture.
- therefore a pure `video=false` control server is not sufficient for reliable touch mapping on the current scrcpy server.
- the first lab implementation must use either:
  1. the existing primary scrcpy session as combined vision+control owner, or
  2. a tiny mapper stream (very low resolution/FPS/bitrate) solely to establish mapping.

Promotion gate for fast control:

- no disruption of the primary vision stream
- touch/swipe effect proof inside Minecraft
- lower median input dispatch than ADB
- negligible incremental CPU/memory
- orientation mapping remains correct
- automatic fallback to ADB if control socket fails

Accessibility/MobileNode remains a separate fallback/semantic-control path.

### L3 · ANDROID SYSTEM PRIVILEGE — BLOCKED_USER_ACTION

Target: Shizuku/rish persistent shell and, later, a narrow UserService.

Current device state: Shizuku application is **not installed**.

Design:

- Shizuku must not expose a general shell to agents.
- Kai will expose a small allowlisted service surface only.
- intended uses: persistent Android-level operations that are expensive through repeated ADB process startup.
- Minecraft touch remains scrcpy-control-first; Shizuku is not a substitute for the high-rate input path unless benchmarks prove otherwise.

Promotion requires explicit user installation/approval in Android plus effect tests.

### L4 · AGENTS / CODEX — INSTALLED, EXECUTION GATED

Installed:
`codex-cli 0.162.1` from the native Termux repository.

Workspace:
`~/kai-workspaces/Kai`

Isolated Codex home:
`~/.kai_codex`

Wrapper:
`~/bin/kai-codex`

Critical compatibility correction:

- `codex doctor` reports Android/aarch64 correctly.
- however `codex sandbox` explicitly reports that the host sandbox is **not supported on Android**.
- therefore Codex is installed but intentionally **not authenticated/enabled as an executing agent**.
- the wrapper is gated by `~/.kai_mobile/flags/enable-codex-agent`.

Do not create that flag until an external sandbox such as abwrap (or an equivalent verified boundary) is available, or the user explicitly approves operation without that boundary.

abwrap is therefore a **security dependency for autonomous Codex**, not a performance dependency.

### L5 · ACCELERATION — LAB

Goal: compare real S24 performance, not internet claims.

Planned matrix:

```
CPU baseline
  vs Adreno OpenCL
  vs Adreno Vulkan
  vs Hexagon v75 HTP/NPU
```

Candidates:

- official Termux `llama-cpp`
- `llama-cpp-backend-vulkan`
- Freedreno/Turnip Vulkan ICD
- official llama.cpp Snapdragon backend
- audited MIT donor `llama.cpp-android` for Adreno/Hexagon packaging ideas

Rules:

- start with small models/tasks useful to Kai: embeddings, UI classification, visual state summaries, routing/decision helpers.
- do not upgrade the current Ollama runtime until CPU/GPU/NPU baselines are captured.
- keep model files and backend libraries outside Core.
- record prompt-processing and token-generation separately.
- record temperature, memory pressure and battery/thermal behavior.

Current Ollama is intentionally held at `0.31.1` until the acceleration lab is ready.

### L6 · UI / DESKTOP / VIRTUAL DISPLAYS — READY_FOR_LAB, NOT CORE

Priority order:

1. Termux:GUI for a lightweight native Android Kai Control Center/HUD.
2. MagicDesk/Shroot in isolation for virtual displays, Shizuku-backed shell runtime and OCI experiments.
3. Termux:X11 + Mesa/Turnip/Freedreno for a full Linux desktop.
4. WayLandIE/other DMA-BUF or SurfaceControl experiments only after license/audit review.

Termux:X11 open work such as AHardwareBuffer/DRI3 and lower drag latency is radar, not production authority.

### L7 · HEAVY EXPERIMENTS — DEFERRED

- Hangover/Wine
- QEMU full VMs
- broad TUR adoption
- Docker/container stacks requiring stronger kernel/root assumptions

These are interesting but currently offer less leverage for Kai/Minecraft than fast input, Shizuku, Codex isolation and Snapdragon acceleration.

## Android 16 / Samsung constraint

Observed on the real device while Termux is backgrounded:

`Cpus_allowed_list: 0-1,5-6`

All eight CPUs are online, but Kai background processes are not allowed to schedule on all of them. Do not "fix" this with undocumented cpuset hacks in Core.

Mitigation order:

1. reduce unnecessary processes/copies
2. keep long-lived work supervised and consolidated
3. use hardware encoder/GPU/NPU when it measurably helps
4. test Shizuku/UserService placement
5. evaluate foreground/virtual-display strategies only in LAB

## Health authority

Run:

```sh
~/kai-stack/core/kai_stack_health.py
```

It reports:

- ADB authorization
- Shizuku presence
- core package versions
- runit services
- live vision freshness
- Codex install/login/sandbox status
- acceleration backend presence
- current background CPU allowance

A module is not "ACTIVE" merely because its package is installed.

## Promotion states

- **ACTIVE** — effect-tested on the S24 and supervised if persistent.
- **READY** — installed/configured, but not yet effect-tested.
- **LAB** — isolated experiment; not a dependency of Core.
- **BLOCKED_USER_ACTION** — requires Android UI approval/install/permission.
- **DEFERRED** — intentionally postponed.
- **STUDY_ONLY** — donor/source may inform architecture but source is not copied into Kai.

## Implementation sequence

### Phase A · Foundation — DONE

- snapshot package/service baseline
- update low-risk Core packages
- verify `kai-minecraft-live` after FFmpeg upgrade
- install native Codex
- create clean Kai workspace
- create health authority

### Phase B · Fast hands — IN PROGRESS

- build persistent scrcpy binary-control prototype
- use low-cost mapper strategy or merge control into the primary scrcpy owner
- measure tap/swipe latency vs ADB
- add automatic ADB fallback
- only then wire Minecraft movement/camera to fast control

### Phase C · Android shell — BLOCKED_USER_ACTION

- install/approve Shizuku
- validate `rish`
- prototype narrow UserService
- forbid general-agent shell exposure

### Phase D · Agent isolation

- track/evaluate abwrap or equivalent external sandbox
- validate workspace RW / outside-workspace denied
- only then authenticate/enable `kai-codex`
- add Kai-specific MCP tools after least-privilege review

### Phase E · Snapdragon acceleration

- install lab-only Vulkan/OpenCL/llama components
- CPU baseline
- Adreno benchmark
- Hexagon v75 benchmark
- promote only workloads with clear latency/energy win

### Phase F · Kai UI / virtual display

- Termux:GUI Control Center
- MagicDesk/Shroot isolated experiment
- X11/Wayland only if it provides a measured workflow advantage

## Success KPIs

Minecraft/control:

- frame freshness p50/p95
- input dispatch p50/p95
- action-complete -> next-frame latency
- orientation recovery time
- stream/control restart count
- CPU/RSS for each daemon

Acceleration:

- prompt processing tokens/s
- generation tokens/s
- peak RSS
- sustained temperature/throttling behavior
- energy/battery delta over fixed workload

Reliability:

- runit recovery after process failure
- recovery after Android app foreground/background transitions
- recovery after Wireless Debugging endpoint changes
- no persistent secrets in repo
- exact deployed-source hash parity for promoted services

## Rollback policy

Core upgrades require:

1. package manifest snapshot
2. service/run-script copy
3. source SHA record
4. post-change healthcheck

If a promoted change degrades vision/control reliability, revert the affected layer only. Do not roll back unrelated layers.
