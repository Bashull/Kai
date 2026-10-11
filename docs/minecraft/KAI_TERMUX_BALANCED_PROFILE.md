# Kai Termux — Balanced profile

Status: **IMPLEMENTED / STAGED / LONG-SOAK PENDING**
Date: 2026-10-11
Device evidence: Samsung S24 Ultra, Android 16, aarch64
Branch: `feat/codex-minecraft-pc-20261010`

## Goal

Keep Minecraft Bedrock vision/control responsive while avoiding unnecessary always-on AI, desktop or virtualization workloads. Balanced favors stable low-latency control, bounded recovery and reversible changes over peak synthetic throughput.

## Active runtime profile

Portable profile: `relay/profiles/balanced.env`

- live host: localhost only
- API port: 7190
- scrcpy forward: 27185
- max video dimension: 960 px
- target max capture: 20 fps
- H.264 bitrate: 3,000,000 bps
- first-frame timeout: 15 s
- bounded startup attempts: 3

Device-local hardware override on the verified S24:

```sh
KAI_LIVE_VIDEO_ENCODER=c2.qti.avc.encoder
```

The hardware override is intentionally not part of the portable profile.

## Service model

`termux-services/runit` sources an active profile symlink, then an optional local hardware override, then starts the reviewed `kai_minecraft_live.py`.

`relay/kai-profile` changes the active profile, restarts the service, waits for authenticated health, and rolls back the symlink if health does not recover in the bounded window.

## Minecraft service verification

The previously-down service was rechecked before profile work.

Verified after restart:

- ADB device state: `device`
- scrcpy direct-v2 active
- FFmpeg active
- scrcpy control socket active
- preferred input: `scrcpy`
- authenticated `/frame`: HTTP 200
- portrait stream recovered to Minecraft landscape automatically
- Minecraft main menu visually confirmed at 960×442
- reviewed GitHub source and deployed service source SHA-256 match exactly

Current reviewed/deployed balanced source SHA-256 at implementation checkpoint:

`98897f52d67462faa6796f412d0f0e067d7ea1f2da50da12edce9a2226efdddd`

## Startup resilience change

The former fixed 8-second first-frame failure now uses:

- configurable `KAI_LIVE_START_TIMEOUT` (Balanced: 15 s)
- bounded `KAI_LIVE_START_ATTEMPTS` (Balanced: 3)
- cleanup between attempts
- diagnostic data including received H.264 bytes and recent errors

The same bounded retry helper is used for initial startup and orientation/process recovery. Failed attempts clean up the partial scrcpy/FFmpeg session before retrying. This does not create an infinite retry loop inside the bridge; runit remains the outer supervisor.

## Initial 60-second smoke result

Profile: 960 px / target 20 fps / 3 Mbps.

- samples: 30
- failures: 0
- restart delta: 0
- frame age median: 38.3 ms
- frame age p95: 86.1 ms
- maximum observed frame age: 104.0 ms
- decoder delivery median: 15.99 fps
- final frame: 960×442
- control socket: alive
- battery temperature sample: 37.5 °C
- final result: PASS

One process snapshot showed FFmpeg at ~46% of one CPU in this workload. Treat process-level `ps %CPU` as a point sample, not device-wide power use.

## Rejected optimization

Removing FFmpeg's explicit `fps=20` filter increased the observed FFmpeg process sample from ~46% to ~54% CPU while providing no demonstrated control benefit. The experiment was reverted.

## Codex in Balanced

Native Codex 0.162.1 and `codex-code-mode-host` are installed and executable.

`codex doctor` found:

- native Android/aarch64 runtime: OK
- disk: OK
- Git/ripgrep present
- authentication: **not configured**
- Responses WebSocket: failed in doctor; HTTPS fallback may still work

Critical compatibility finding:

`codex sandbox` returns **"not supported on this operating system"** on Android.

Therefore Balanced **does not allow Codex agent execution yet**. `relay/kai-codex-balanced` only permits diagnostic/preflight commands until an external containment layer is effect-verified. The offline workspace fixture and Python unit test pass, but that is not a Codex-agent execution test.

## Components deliberately OFF in Balanced

- Ollama upgrade / daemon
- CPU↔Adreno↔Hexagon benchmark workload
- Termux:X11
- Termux:GUI
- MagicDesk/Shroot
- Wayland experiments
- Hangover/Wine
- QEMU
- TUR additions
- privileged Shizuku MCP shell

They remain later-stage labs so the Bedrock loop does not compete with unrelated workloads.

## Test harness

`relay/kai_balanced_probe.py` checks authenticated health repeatedly and records:

- frame age
- sequence progress
- delivery rate
- restarts
- scrcpy / FFmpeg / control socket state
- frame geometry
- battery temperature
- foreground Android activity
- relevant process snapshot

Results append locally to `~/.kai_mobile/benchmarks/balanced.jsonl`; tokens and secrets are never written to the repository.

## Acceptance gate still running

A final clean 10-minute soak is required by the master plan. Static screens are allowed to retain an older but still-current frame; active freshness is tested separately after actions. Orientation restarts are explained recovery events, while unexplained restarts remain failures. Do not mark Balanced fully accepted until the clean soak completes.
