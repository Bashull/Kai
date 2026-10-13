# KAI Master Unified v0.5 — CONTROL-PLANE STAGING CANDIDATE

**Status: STAGING ONLY. This package does not grant remote admin, execute
commands, collect screens or control a device.** It is the policy/route layer
for existing *separately verified* KAI paths, not a sixth gateway or server.

## What is real, as of the October 13 audit

- Windows Asier: user-session KAI GUI RC3 worker (SentinelX authenticated file queue);
  `pc.gui.observe` and `pc.agent.health` have actual `COMPLETED` receipts, with no
  extra TCP listener. PC Agent local `/v1/health` returned HTTP 200.
- Galaxy S24 Ultra: Termux `kai-phone status` can read ADB and loopback live
  capture/status; Galaxy→Windows `kai-master-pc status` over SSH returned
  a `COMPLETED` digest-bearing receipt. Android ADB UID 2000 is *not* root.
- RC4 `kai_eyes` source is bundled unchanged as source + synthetic tests:
  **no physical Win32 execution from this bundle**. Staged catalog and screenshot
  approval contract are not production capabilities.

## Design

`ChatGPT -> connected SentinelX -> KAI Inbox -> RC3 Gateway/Policy/SQLite Ledger -> Windows read-only adapters`,
plus independent `Galaxy Termux -> authorized SSH -> Windows gateway` and
`Galaxy Termux -> scoped ADB/scrcpy -> Android UI`.

The unified *logical* catalog (`kai_master/control_plane.py`) classifies:
- VERIFIED_SCOPE read paths, only with fresh matching proof;
- STAGING/LOCAL_ONLY sensitivity that cannot be remotely dispatched;
- UNAVAILABLE full admin/root paths that must remain denied.

`make_action` constructs **only** an existing KAI Windows manifest. It neither
sends it nor signs it. `verify_receipt` checks exact identity and SHA-256 digest
binding; SHA-256 alone is **not** a signature or authenticated transport.

## Offline reproducible tests

```sh
cd KAI_MASTER_UNIFIED_V05_CANDIDATE_20261013
PYTHONWARNINGS=error python -m unittest discover -s tests -v
python -m kai_master.doctor
```

## Promotion gates (NOT completed)

1. Preserve a valid CURRENT/restore capsule and verify runtime hashes.
2. Independently execute RC4 *read-only* probe on Windows, user interactive session,
   process-isolated under 5 seconds; reject unknown processes and stale frames.
3. Import the catalog into the existing RC3 Gateway **staging lab**, never a
   second port; run receipt/expiry/replay/kill-switch tests.
4. Optional screenshot of a dummy window only after local owner authorization,
   **not** an unattended image of the personal desktop.
5. Allowlisted Notepad click/type after on-PC confirmation; no logged text.
6. Verify logon, recovery, mobile SSH and independent backups and revoke tests;
   retire each ancient bridge only after proven recovery.

Do not install an all-powerful MCP server, scrape protected Android app data,
upgrade Termux's 79 native packages or kill live tunnels automatically.

## Donor lineage

- Existing KAI vNEXT `bridge/master-vnext/` Gateway contract and ledger.
- `relay/phone-control/` and Termux `kai-phone` 0.1.0; no donor code copied.
- `kai_eyes` from RC4 isolated lab; local pure tests only.
- pywinauto BSD-3, Win32 API and Windows-MCP UIA concepts under separate
  license/security review. No third-party code copy or additional runtime service.

See `evidence/VERIFIED_SCOPE.md` and `inventory.json` for current inventory and
unknowns. No passwords, enrollment tokens or private screenshots included.