# KAI Phone Control 0.1.0

On-demand control and discovery for Asier's Samsung SM-S928B. Reuses authorized
wireless ADB, the existing scrcpy/live service on loopback 7190 and the existing
Nexus SQLite catalogue. It creates no server, bridge or background scanner.

Code authority: Bashull/Kai, relay/phone-control. Runtime: Termux KAI_TOOLS.
Documentation authority: Drive Node/MobileNode wiki and Phone Control runbook.
The source package is independent of the original phone-control experiment logs.

## Dependencies and scope

Python 3.10+ syntax, standard library, adb and one authorized loopback device of
model SM-S928B. Actual runtime verified on Python 3.14.6 / Android API 36.
ADB selects the current serial; yesterday's port is not configuration.
Termux app UID and ADB shell UID are different. ADB shell UID 2000 is not root.
Private app databases, Android protected surfaces and other user profiles are
not made accessible by this tool. GPS state can be inspected; no location fixes
are collected and the global location switch is not changed.

Existing secret pointer: ~/.kai_mobile/kai-live-token. The value is read only in
memory for authenticated loopback calls. No token values belong in logs or Git.
Screenshots and UI XML are created exclusively below private Termux home, mode
0600, with no overwrite. Audit records contain command name, time, exit code and
version, not text input, search queries or screen contents.

## Use

```sh
kai-phone status
kai-phone apps kai
kai-phone apps --user
kai-phone roots
kai-phone search mcpack
kai-phone find KAI_Factory --root Download --budget 10
kai-phone browse AndroidData --relative com.mojang.minecraftpe
kai-phone launch com.kai.controlprobe
kai-phone ui
kai-phone screen
kai-phone tap 540 644 --expect-package com.kai.controlprobe --transport live
```

Coordinates in examples came from the lab screen and must be reobserved before
use. `tap`, `swipe`, `key` and `text` require the expected foreground package.
This is a guard against a changed app, not an atomic guarantee against a user
switching apps between the final check and injection. Read a fresh UI/frame,
perform the requested action, then verify the effect.

`text` takes stdin, so text is absent from the command line and audit. Direct
ADB text accepts a deliberately small ASCII set; the existing live channel can
accept Unicode, but Unicode input has not yet been validated in this release.
Preflight subprocesses use DEVNULL so they cannot consume the text input.

Use `--transport adb` (default) or `--transport live` explicitly. The existing
live bridge may report an internal ADB fallback; the receipt exposes what it
used. Neither an exit code nor a `sent` receipt proves the intended UI effect.

`search` reads the existing Nexus catalogue and reports its PARTIAL scope.
`find` traverses one selected public root, names and metadata only, with a time
budget and result cap. It excludes hidden files, symlinks and archive contents.
`browse` uses ADB for one directory, including Android/data if Android permits
it; listing a parent is not proof that every descendant is readable. No index
is silently replaced and no files are deleted, deduplicated or uploaded.

## Installation and recovery

Runtime source: ~/KAI_TOOLS/kai-phone-v0.1.0/kai_phone.py.
Wrapper: /data/data/com.termux/files/usr/bin/kai-phone.
Original experiment and evidence: ~/KAI_RUNTIME_LAB/PHONE_CONTROL_20261012.

If ADB is unavailable, use the existing kai-adb-recover and Android's normal
wireless debugging authorization. Do not invent a port, disable Android
protections, install root tools or reset the ADB server by default.
If the live route fails, inspect the existing kai-minecraft-live service and
its authenticated /status; use explicit direct ADB control when appropriate.

MobileNode accessibility recovery in this session restored a service already
enabled by the owner. The original enabled-service list was preserved, the Kai
entry was temporarily removed, and the exact original list was restored.
The service subsequently bound with a live PID. This does not prove the remote
Relay transport or receipt of a command through MobileNode.

The CLI installs no scheduled work. To retire it, preserve its audit/evidence,
remove only its wrapper and retain the version directory as an ancestor.
The lab APK is separately removable through Android app settings under
"KAI Control Lab"; its package is com.kai.controlprobe. It does not replace
MobileNode or Image Forge. Minecraft/Reflex configuration is untouched.

## APK laboratory

The permission-free native Java app exposes a tap counter, editable field,
echo button and scroll marker. It has no network, service or accessibility
permission. It is a visible test instrument, not a backdoor or permission broker.

`android/build.sh` reuses the existing Termux Factory Stage02 SDK 36 and D8,
then AAPT2, javac, D8, zipalign and apksigner. No dependency download is needed.
The local signing key and password file stay under android/build/private and
are excluded from source/versioning. This is a test signature, not a production
signing identity. Override KAI_FACTORY_ROOT to select a verified factory root.

The first signing attempt exposed apksigner's sequential password-file reads
when one file was supplied separately for store and key passwords. The final
script supplies the keystore password once and uses the same PKCS12 key
password. The failed build was preserved locally for genealogy.

## Verification

12 unit tests cover device ambiguity, remote-shell quoting, package guards,
private evidence paths, traversal, index query literals, scan limits and stdin.
Live tests observed counter increments via ADB and scrcpy, ASCII text and its
echo, a valid screenshot, scroll completion and return to ChatGPT with BACK.
A foreground change caused an earlier attempt to abort without tapping the
wrong app. All tests are scoped evidence, not a promise of control over every
Android app or continuous autonomous operation.

Genealogy: Termux NERVE 0.4.1 existing live transport; Nexus private_visual
catalogue; Termux App Factory Stage02/Fresh01 build recipe; Android official
ADB/storage/accessibility documentation. No donor installation scripts or
third-party APK code were copied into this tool.
