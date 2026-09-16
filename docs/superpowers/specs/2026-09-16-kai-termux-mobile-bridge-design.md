# Kai Termux Mobile Bridge v0.1 — Design

Date: 2026-09-16
Status: APPROVED_BY_USER_DIRECTION
Branch: `feat/kai-termux-mobile-bridge-v0.1`

## Purpose

Turn Termux on Asier's S24 Ultra into a durable local recovery and control surface for Kai without replacing MobileNode or merging it with the Windows Relay. Termux is the local recovery substrate; MobileNode remains the Android UI/control app; the Windows Mobile Relay remains a separate transport/control component.

## Goals

1. Upgrade the Termux package environment safely.
2. Install a small, useful toolchain for recovery, diagnostics, development and Android control.
3. Create a local `Kai Mobile Bridge` with typed, allowlisted actions such as `health`, `open-whatsapp`, `home`, `open-app`, `wake`, and local diagnostics.
4. Make the bridge restartable and boot-friendly without relying on a fragile PID file.
5. Prepare ADB-over-Wireless-Debugging and SSH-over-Tailscale as recovery paths, while keeping them disabled or non-authoritative until verified.
6. Preserve secrets only on-device and never commit them to GitHub or ordinary Drive documents.
7. Produce effect evidence: command accepted is not enough; app foreground/state must be checked when Android permits it.

## Non-goals

- No unrestricted remote shell exposed to the Internet.
- No public HTTP control endpoint.
- No WhatsApp message reading, sending, chat inspection, call control, contacts or private UI capture.
- No silent APK replacement across signing sources.
- No root requirement.
- No replacement of MobileNode, Tailscale or the Windows Relay.

## Upgrade policy

The bootstrap first records `termux-info`, package state, Android version, architecture, free space and the installed Termux package-manager family. It then runs the supported package refresh/upgrade path. Official Termux guidance recommends upgrading all packages with `pkg upgrade`; if repositories are broken, the bootstrap stops and reports the mirror problem instead of rewriting sources blindly.

The bootstrap does not assume that upgrading Termux packages upgrades the Android Termux APK itself. If the app version is below the supported baseline, it reports that separately. Termux and add-ons such as Termux:API and Termux:Boot must come from compatible signing sources; the bootstrap will not silently install or replace mismatched APKs.

## Package set

Required packages are intentionally small and capability-driven:

- `termux-tools`
- `git`
- `curl`
- `jq`
- `openssh`
- `python`
- `nodejs-lts`
- `termux-api`
- `termux-services`
- `android-tools`
- `tmux`
- `rsync`
- `ripgrep`

Installation is idempotent. Optional or unavailable packages do not cause partial state to be mislabeled healthy.

## Filesystem layout

```text
$HOME/.kai/mobile-bridge/
  bin/
  lib/
  config/
  state/
  logs/
  private/
  STOP
```

`private/` is mode 700 and secret files are mode 600. Logs must not include tokens, pairing codes, auth URLs, private UI dumps, notification contents or message data.

## Command model

The local command entry point is `kai-mobile`.

Initial typed actions:

- `kai-mobile health`
- `kai-mobile open-whatsapp`
- `kai-mobile open-app <allowlisted-package>`
- `kai-mobile home`
- `kai-mobile wake`
- `kai-mobile status`
- `kai-mobile adb-status`
- `kai-mobile doctor`

`open-app` uses an explicit local allowlist. WhatsApp is represented only as package/component metadata. No action reads or manipulates WhatsApp content.

The bridge tries the least-privileged local Android mechanism first. If direct `am` invocation is denied by Android, it records the failure and can use a separately verified local ADB-self path after Wireless Debugging has been paired by the user. It never weakens Android security settings automatically.

## Process ownership and persistence

The bridge avoids the Windows Relay failure pattern discovered earlier:

- no pidfile is treated as a lock;
- one service instance is enforced by the service manager / lock primitive;
- health and readiness are separate;
- a stale state file never authorizes spawning another daemon;
- restart loops use bounded backoff;
- a local `STOP` file is a persistent kill switch.

`termux-services` is preferred for long-running local services. If Termux:Boot is present, the bootstrap creates `~/.termux/boot/10-kai-mobile-bridge` to acquire a wake lock and start the service framework. Termux:Boot still requires its Android app to be installed from a compatible source and launched once.

## Recovery transports

### Local-first

All Android actions remain local. No listener is published merely because the bridge is installed.

### SSH recovery

OpenSSH is installed, but remote login is not considered configured until public-key authentication is explicitly provisioned and verified. Password-only remote administration is not promoted as a Kai recovery path.

### Tailscale

The already-installed Android Tailscale app remains the preferred private network transport. The bridge may later be reached through Tailscale only after an authenticated service is deliberately configured and tested. No Funnel/public exposure.

### Remote Desktop Commander

If the Desktop Commander remote agent proves compatible with Termux, it may be used as a temporary recovery connector. It is not the canonical protocol and its absence must not make the bridge unusable locally.

## Android control escalation ladder

1. Direct Termux `/system/bin/am` for harmless app launch/navigation where Android permits it.
2. Termux:API for supported Android API functions.
3. Local ADB self-connection via Wireless Debugging for commands requiring shell identity, after explicit Android pairing.
4. MobileNode Accessibility for UI actions already covered by the Mobile Control Spine.

The bridge records which layer produced an effect. It does not claim success merely because a command returned exit code 0.

## Verification gates

Gate T0 — Environment
- `termux-info` captured and sanitized.
- package upgrade completes or a specific blocker is recorded.
- required packages are present.

Gate T1 — Local bridge
- `kai-mobile health` passes.
- kill switch blocks actions.
- duplicate service startup does not create duplicate instances.

Gate T2 — Android effect
- `open-whatsapp` launches `com.whatsapp` or records a precise permission blocker.
- effect is verified without inspecting chat contents.
- `home` returns to launcher.

Gate T3 — Persistence
- service survives shell exit.
- Termux:Boot path is installed when the companion app is available.
- post-reboot verification remains a separate evidence gate.

Gate T4 — Recovery transport
- a private authenticated transport reaches the bridge from outside the phone.
- no public unauthenticated listener exists.

## Evidence model

Every material observation is one of `OBSERVED`, `INFERRED`, `UNRESOLVED`, or `BLOCKED`. Runtime reports live under `$HOME/.kai/mobile-bridge/state/` and only sanitized summaries are written back to GitHub/Drive.

## Immediate implementation order

1. Build an idempotent bootstrap script and shell tests.
2. Build `kai-mobile` typed dispatcher and allowlist.
3. Add state/logging/kill-switch and duplicate-instance protection.
4. Add Termux:Boot/service integration.
5. Add direct Android launch tests and ADB fallback probes.
6. Run on the S24 when an execution surface is available; until then runtime gates remain `BLOCKED_EXECUTION_SURFACE`.
