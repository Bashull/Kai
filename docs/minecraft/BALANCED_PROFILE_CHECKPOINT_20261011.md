# Balanced profile implementation checkpoint — 2026-10-11

Scope: Samsung S24 Ultra / Termux; authorized remote read-only preflight, no Minecraft actions.

## Confirmed
- `~/.kai_mobile/profiles/active.env` symlinks to `balanced.env`, already configured.
- Balanced values: max-size 960, target max FPS 20, bitrate 3,000,000, 15s startup timeout, 3 attempts, localhost port 7190, scrcpy forward port 27185. Hardware override: Qualcomm `c2.qti.avc.encoder`.
- Native Codex 0.162.1 installed and responds to `codex --help` and `codex --version`.
- scrcpy 5.0.1 and FFmpeg 8.1.3 installed; bridge source compiles.
- `runsv` reports `kai-minecraft-live` RUNNING (process 804), but its `/status` reports `ok:false`, `frame_age_ms:null`, frame dimensions 0x0, scrcpy_alive false, ffmpeg_alive false. **Supervisor process health != functional video health.**
- `adb devices -l` lists NO devices. Previously saved wireless debugging endpoint 192.168.1.11:46599 refused connections; port is ephemeral.
- Earlier logs show `device offline` and `first frame timeout`; not enough evidence to claim one definitive root cause.
- `~/.kai_mobile/tests/balanced_preflight.py` created on the S24. It reads profile, checks installed tools and service, compiles bridge source and queries authenticated localhost status; it does not move or launch Minecraft. First run confirmed the above.

## Blocking gate
Re-establish Android Wireless Debugging authorization on the phone; do not guess/persist new pairing code or disclose credentials. Once ADB shows exactly one authorized device, repeat preflight, confirm scrcpy/FFmpeg alive and nonstale frame, then 10-minute soak. If encoder startup still fails, inspect logs and scrcpy server protocol before restarting services.

## Acceptance gates
1. ADB device authorized; no phantom offline entries.
2. Stream `ok:true`, fresh nonzero-size frame, video pipeline alive, localhost auth rejects anonymous requests.
3. 10-minute continuous capture with no runaway restarts.
4. Non-destructive touch and orientation tests only after explicit foreground/permission checks.
5. Codex isolated fixture tests; never grant blanket Termux filesystem write.

## Safety
No package upgrade, repository main modification, Android pairing reset, Minecraft world action, or privilege change was performed. The observed service is running without functional capture; do not label the profile fully deployed.


## Recovery update — 08:45 CEST
- Wireless debugging was confirmed active by the user. The advertised Wi-Fi endpoint was not reachable from the Termux process namespace, but the same TLS ADB endpoint accepted loopback.
- Established authorized ADB over `127.0.0.1:35981`, then verified one device only.
- Restarted `kai-minecraft-live`; read-only preflight passed: stream `ok:true`, scrcpy/FFmpeg alive, frame 442x960, fresh frame age observed at 24.3 ms.
- Verified bearer protection: anonymous `/status` returned HTTP 401.
- Verified a real JPEG frame was fetchable from the bridge.
- Tested ADB serial migration without restarting the bridge process: disconnected `127.0.0.1:35981`, reconnected as `localhost:35981`; the same service process recovered automatically. Status showed `restart_count:1`, serial changed to `localhost:35981`, control alive, preferred input `scrcpy`.
- Hardened bridge: session startup now re-resolves the single authorized ADB serial; supervisor catches failed restart attempts and uses bounded exponential backoff instead of dying silently. Commit: `65aabea8`.
- Added read-only test harnesses: `relay/tests/balanced_preflight.py` and `relay/tests/balanced_soak.py`.
- Codex doctor: native Android/aarch64 runtime is consistent; authentication is not configured, and WebSocket diagnostics warned that HTTPS fallback may be required. No credentials were requested or changed.
- Resource snapshot while capture was healthy: bridge RSS about 30 MiB, 6 threads, Android cpuset `0-1,5-6`; Thermal Status 0. These are point-in-time observations, not sustained-load results.

## Remaining acceptance work
- The 10-minute soak harness is prepared but was intentionally not left running after this turn. Run it interactively when final acceptance testing is desired.
- Gameplay-load latency/thermal testing and non-destructive scrcpy input calibration remain pending.
- Do not hardcode the wireless-debugging port; it is ephemeral. Loopback works on this device while the session is active.
