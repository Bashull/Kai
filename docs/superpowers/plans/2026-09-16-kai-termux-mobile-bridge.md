# Kai Termux Mobile Bridge v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an idempotent Termux bootstrap and a typed local Android recovery/control CLI for Asier's S24 Ultra, with safe package upgrades, allowlisted app actions, local state/logging, kill switch, boot integration, and ADB-self fallback.

**Architecture:** `mobile/termux/bootstrap.sh` upgrades and installs the supported Termux toolchain, then installs a focused `kai-mobile` CLI plus libraries/config into `$HOME/.kai/mobile-bridge`. Android actions use a least-privilege ladder: direct `/system/bin/am`, then verified local ADB when available. No public listener or unrestricted shell is introduced.

**Tech Stack:** Bash/POSIX utilities, Termux `pkg`, Android `am`/`input`, optional `adb`, Termux:API client package, termux-services/runit, GitHub Actions Ubuntu shell tests.

**Spec:** `docs/superpowers/specs/2026-09-16-kai-termux-mobile-bridge-design.md`

## Global Constraints

- No unrestricted remote shell exposed to the Internet.
- No public HTTP control endpoint.
- No WhatsApp message reading, sending, chat inspection, call control, contacts or private UI capture.
- No silent APK replacement across signing sources.
- No root requirement.
- No replacement of MobileNode, Tailscale or the Windows Relay.
- Secrets remain on-device under `$HOME/.kai/mobile-bridge/private` with restrictive permissions.
- Runtime evidence uses `OBSERVED`, `INFERRED`, `UNRESOLVED`, or `BLOCKED` classifications.

---

## File Structure

- `mobile/termux/bootstrap.sh` — idempotent package/environment installer and filesystem setup.
- `mobile/termux/kai-mobile` — typed CLI entry point.
- `mobile/termux/lib/common.sh` — paths, atomic state/log helpers, STOP enforcement, command lookup.
- `mobile/termux/lib/android.sh` — direct Android action and ADB fallback functions.
- `mobile/termux/config/apps.tsv` — explicit package/component allowlist.
- `mobile/termux/boot/10-kai-mobile-bridge` — Termux:Boot integration template.
- `mobile/termux/tests/test_bootstrap.sh` — bootstrap behavior using command stubs.
- `mobile/termux/tests/test_kai_mobile.sh` — dispatcher, allowlist, STOP and Android fallback tests.
- `mobile/termux/tests/test_common.sh` — tiny shell assertion harness shared by tests.
- `.github/workflows/termux-mobile-bridge-ci.yml` — shell syntax and test workflow.
- `mobile/termux/README.md` — install, manual Android gates, verification and recovery.

---

### Task 1: Bootstrap and package upgrade contract

**Files:**
- Create: `mobile/termux/bootstrap.sh`
- Create: `mobile/termux/tests/test_common.sh`
- Create: `mobile/termux/tests/test_bootstrap.sh`

**Interfaces:**
- Consumes: Termux `pkg`, `termux-info`, `$HOME`, `$PREFIX`.
- Produces: `bootstrap_main()`, `$HOME/.kai/mobile-bridge/{bin,lib,config,state,logs,private}`, sanitized `state/bootstrap-current.json` when `jq` is available.

- [ ] **Step 1: Write the failing bootstrap tests**

Create a stub `pkg` in a temporary `PATH` that records arguments. Test that `bootstrap.sh --dry-run` plans `pkg update`, `pkg upgrade`, and installation of exactly: `termux-tools git curl jq openssh python nodejs-lts termux-api termux-services android-tools tmux rsync ripgrep`. Test that an existing bridge directory is preserved and that `private` is chmod 700.

```bash
assert_contains "$calls" "pkg update -y"
assert_contains "$calls" "pkg upgrade -y"
assert_contains "$calls" "pkg install -y termux-tools git curl jq openssh python nodejs-lts termux-api termux-services android-tools tmux rsync ripgrep"
[ "$(stat -c %a "$HOME/.kai/mobile-bridge/private")" = "700" ]
```

- [ ] **Step 2: Run the test and verify RED**

Run: `bash mobile/termux/tests/test_bootstrap.sh`
Expected: FAIL because `mobile/termux/bootstrap.sh` does not exist.

- [ ] **Step 3: Implement minimal idempotent bootstrap**

`bootstrap.sh` must use `set -euo pipefail`, support `--dry-run`, refuse to continue when `$PREFIX` is empty, record a sanitized preflight, run `pkg update -y`, `pkg upgrade -y`, install the exact package list above, create bridge directories, chmod `private` to 700, and copy repository bridge files only after tests introduce them. It must not edit Android APKs or repository sources automatically.

- [ ] **Step 4: Run bootstrap tests GREEN**

Run: `bash mobile/termux/tests/test_bootstrap.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/termux/bootstrap.sh mobile/termux/tests/test_common.sh mobile/termux/tests/test_bootstrap.sh
git commit -m "feat: add idempotent Termux bootstrap"
```

---

### Task 2: Typed `kai-mobile` dispatcher and Android allowlist

**Files:**
- Create: `mobile/termux/kai-mobile`
- Create: `mobile/termux/lib/common.sh`
- Create: `mobile/termux/lib/android.sh`
- Create: `mobile/termux/config/apps.tsv`
- Create: `mobile/termux/tests/test_kai_mobile.sh`

**Interfaces:**
- Consumes: `KAI_BRIDGE_ROOT`, `/system/bin/am`, optional `adb`, allowlist TSV.
- Produces: CLI actions `health`, `status`, `open-whatsapp`, `open-app PACKAGE`, `home`, `wake`, `adb-status`, `doctor`.

- [ ] **Step 1: Write failing dispatcher tests**

Use fake `am` and `adb` executables under a temporary `PATH`. Verify:

```bash
run_kai health
assert_status 0
assert_contains "$output" '"ok":true'

run_kai open-app com.example.notallowed
assert_status 64

run_kai open-whatsapp
assert_contains "$(cat "$CALL_LOG")" "am start -W -n com.whatsapp/.Main"
```

Also verify direct `am` failure plus `adb get-state=device` causes `adb shell am start -W -n com.whatsapp/.Main`, and that no arbitrary component supplied by the caller is executed.

- [ ] **Step 2: Run test and verify RED**

Run: `bash mobile/termux/tests/test_kai_mobile.sh`
Expected: FAIL because CLI/library files do not exist.

- [ ] **Step 3: Implement the minimal typed CLI**

`apps.tsv` starts with:

```text
whatsapp	com.whatsapp	com.whatsapp/.Main
settings	com.android.settings	com.android.settings/.Settings
```

`open-app` accepts the package field only when it appears exactly in the TSV. `open-whatsapp` resolves the WhatsApp row internally. Direct Android launch uses `/system/bin/am` when executable; fallback uses `adb shell am` only if `adb get-state` returns `device`. `home` uses direct `input keyevent KEYCODE_HOME` if available and the same verified ADB fallback otherwise. `wake` uses `KEYCODE_WAKEUP` without unlocking the phone.

- [ ] **Step 4: Run dispatcher tests GREEN**

Run: `bash mobile/termux/tests/test_kai_mobile.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/termux/kai-mobile mobile/termux/lib mobile/termux/config/apps.tsv mobile/termux/tests/test_kai_mobile.sh
git commit -m "feat: add typed Termux Android control CLI"
```

---

### Task 3: State, sanitized logging, STOP kill switch and concurrency guard

**Files:**
- Modify: `mobile/termux/lib/common.sh`
- Modify: `mobile/termux/kai-mobile`
- Modify: `mobile/termux/tests/test_kai_mobile.sh`

**Interfaces:**
- Consumes: bridge state/log directories.
- Produces: `bridge_log EVENT STATUS DETAIL`, `bridge_state_write KEY VALUE`, `assert_bridge_active`, `with_action_lock`.

- [ ] **Step 1: Add failing safety tests**

Verify that creating `$KAI_BRIDGE_ROOT/STOP` makes `open-whatsapp`, `open-app`, `home`, and `wake` return 75 without calling Android commands, while `health`, `status`, and `doctor` remain readable. Verify two concurrent action invocations cannot both enter the protected action section by using an atomic `mkdir` lock directory.

- [ ] **Step 2: Run test and verify RED**

Run: `bash mobile/termux/tests/test_kai_mobile.sh`
Expected: FAIL on STOP/concurrency assertions.

- [ ] **Step 3: Implement safety state**

Use `$KAI_BRIDGE_ROOT/state/action.lock` as an atomic `mkdir` lock with a trap that removes it. Do not use a PID file as a lock. Write JSONL events containing timestamp, action, status and non-sensitive detail only. Reject detail strings containing case-insensitive `token`, `secret`, `password`, `authorization`, `cookie`, or `pairing` by replacing the detail with `[REDACTED]`.

- [ ] **Step 4: Run tests GREEN**

Run: `bash mobile/termux/tests/test_kai_mobile.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/termux/lib/common.sh mobile/termux/kai-mobile mobile/termux/tests/test_kai_mobile.sh
git commit -m "feat: harden Termux bridge state and kill switch"
```

---

### Task 4: Termux:Boot and service-framework integration

**Files:**
- Create: `mobile/termux/boot/10-kai-mobile-bridge`
- Modify: `mobile/termux/bootstrap.sh`
- Modify: `mobile/termux/tests/test_bootstrap.sh`

**Interfaces:**
- Consumes: Termux:Boot companion app when installed; `termux-services` profile script.
- Produces: `~/.termux/boot/10-kai-mobile-bridge` template installed idempotently.

- [ ] **Step 1: Write failing boot integration tests**

Verify bootstrap installs an executable boot script containing only wake-lock acquisition when available, creation of bridge state directories, and sourcing `$PREFIX/etc/profile.d/start-services.sh` when that file exists. Verify it does not start `sshd` or expose a listener by default.

- [ ] **Step 2: Run RED**

Run: `bash mobile/termux/tests/test_bootstrap.sh`
Expected: FAIL on boot-script assertions.

- [ ] **Step 3: Implement boot template and installer**

The script must be POSIX shell, tolerate missing `termux-wake-lock`, and never fail boot merely because Termux:Boot or the services profile is absent. Bootstrap installs it at `$HOME/.termux/boot/10-kai-mobile-bridge` mode 700. README must state that the Termux:Boot APK must be from a signing-compatible source and launched once by the user before Android will execute boot scripts.

- [ ] **Step 4: Run GREEN**

Run: `bash mobile/termux/tests/test_bootstrap.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/termux/boot/10-kai-mobile-bridge mobile/termux/bootstrap.sh mobile/termux/tests/test_bootstrap.sh
git commit -m "feat: add safe Termux boot integration"
```

---

### Task 5: Doctor, runtime evidence and documentation

**Files:**
- Modify: `mobile/termux/kai-mobile`
- Modify: `mobile/termux/lib/android.sh`
- Create: `mobile/termux/README.md`
- Modify: `mobile/termux/tests/test_kai_mobile.sh`

**Interfaces:**
- Consumes: package/tool availability and Android action results.
- Produces: `kai-mobile doctor` JSON with `OBSERVED`/`BLOCKED` classifications and no private UI data.

- [ ] **Step 1: Write failing doctor tests**

Verify JSON includes bridge version, timestamp, Termux prefix presence, direct-am availability, adb availability, adb state, Termux:API client availability, STOP state and boot-script presence. It must not enumerate notifications, contacts, clipboard, chats, installed private-app data or UI hierarchy.

- [ ] **Step 2: Run RED**

Run: `bash mobile/termux/tests/test_kai_mobile.sh`
Expected: FAIL on doctor fields.

- [ ] **Step 3: Implement doctor and README**

README must include the single bootstrap command from a checked-out repo, the manual Android gates that cannot be automated safely (Termux APK/add-on signing-source compatibility, launching Termux:Boot once, Wireless Debugging pairing if direct `am` is blocked, battery-optimization exemption if persistence tests require it), and the verification sequence:

```bash
kai-mobile health
kai-mobile doctor
kai-mobile open-whatsapp
kai-mobile home
kai-mobile adb-status
```

Document that visible-effect verification is required before Gate T2 PASS.

- [ ] **Step 4: Run GREEN**

Run: `bash mobile/termux/tests/test_kai_mobile.sh && bash mobile/termux/tests/test_bootstrap.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mobile/termux/README.md mobile/termux/kai-mobile mobile/termux/lib/android.sh mobile/termux/tests/test_kai_mobile.sh
git commit -m "docs: add Termux bridge doctor and runbook"
```

---

### Task 6: Continuous integration and final static verification

**Files:**
- Create: `.github/workflows/termux-mobile-bridge-ci.yml`

**Interfaces:**
- Consumes: shell files and test scripts from Tasks 1-5.
- Produces: branch CI evidence for syntax and deterministic shell behavior; it does not claim Android runtime success.

- [ ] **Step 1: Add workflow**

Workflow triggers on changes under `mobile/termux/**` or itself, uses `ubuntu-latest`, installs `shellcheck`, runs:

```bash
bash -n mobile/termux/bootstrap.sh
bash -n mobile/termux/kai-mobile
find mobile/termux/lib mobile/termux/boot -type f -print0 | xargs -0 -n1 bash -n
shellcheck mobile/termux/bootstrap.sh mobile/termux/kai-mobile mobile/termux/lib/*.sh mobile/termux/boot/*
bash mobile/termux/tests/test_bootstrap.sh
bash mobile/termux/tests/test_kai_mobile.sh
```

- [ ] **Step 2: Push and verify GitHub Actions**

Expected: workflow completes `success`. Treat GitHub CI as static/unit evidence only; Gates T0-T4 remain runtime gates on the S24.

- [ ] **Step 3: Commit if workflow was created separately**

```bash
git add .github/workflows/termux-mobile-bridge-ci.yml
git commit -m "ci: verify Termux mobile bridge"
```

---

## Runtime Handoff After CI

When a Termux execution surface is available on the S24:

1. Record `termux-info` and `df -h "$HOME"` before mutation.
2. Run the reviewed bootstrap from the repository.
3. Run `kai-mobile health` and `kai-mobile doctor`.
4. Run `kai-mobile open-whatsapp`; verify only that WhatsApp becomes foreground, without reading any content.
5. Run `kai-mobile home`; verify launcher foreground.
6. If direct `am` is blocked, pair local ADB through Android Wireless Debugging and repeat.
7. Verify Termux:Boot only after the compatible companion app has been installed and launched once.
8. Record sanitized evidence and write back the gate results.

No runtime success claim is permitted until the S24 effect is observed.
