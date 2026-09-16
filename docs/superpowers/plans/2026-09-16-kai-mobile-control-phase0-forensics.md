# Kai Mobile Control Phase 0 Forensics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a fresh, sanitized, reproducible Phase 0 evidence package for the Mobile Control Spine so the next Gate A plan can be written from observed runtime/source facts instead of assumptions.

**Architecture:** This plan is intentionally read-mostly. It does not change Tailscale policy, start Tailscale Serve, modify MobileNode endpoint configuration, rotate credentials, restart Relay, or alter Android UI. It gathers PC/S24/Tailscale/Mobile Relay/MobileNode/source-authority evidence, classifies each datum as `OBSERVED`, `INFERRED`, `UNRESOLVED`, or `BLOCKED`, and writes one sanitized runtime report. The separate PC Remote Spine remains distinct and is recorded only as an external recovery candidate/baseline.

**Tech Stack:** Windows PowerShell 7/5.1, Tailscale CLI 1.102.x or current installed version, Android ADB when available, Git, Python/Gradle metadata discovery, Google Drive runtime documentation, GitHub branch `feat/kai-nervous-link-v0.1`.

**Spec:** `docs/superpowers/specs/2026-09-16-kai-nervous-link-autonomous-control-plane-design.md`

## Global Constraints

- `TRUTH OVER BRILLIANCE`: no state is promoted without fresh evidence.
- `COMMAND_ACCEPTED != EFFECT_OBSERVED != USER_SUCCESS_CRITERION`.
- `SAME_NAME != SAME_COMPONENT`: Mobile Relay and PC Remote Relay remain separate lineages.
- `SOURCE_AUTHORITY != RUNTIME_AUTHORITY`.
- No public router forwarding of Relay port `8788`.
- No Tailscale Funnel for the Mobile Control private path.
- Secret values never enter GitHub, Drive documentation, CI logs, runtime reports, or normal chat writeback.
- Phase 0 is read-mostly: no `tailscale up`, `tailscale serve`, policy edit, service restart, package install, endpoint rewrite, credential migration, or Tailnet Lock signing in this plan.
- Private Android UI-tree content is not persisted. For accessibility state, retain only package/service/status metadata required for verification.
- Existing working DPAPI/Keystore/private files are not migrated or printed.
- If a required observation cannot be made, record `BLOCKED` with the exact blocked surface and continue with independent observations.

---

## File / Evidence Map

Runtime evidence created by this plan:

- `C:\Kai\Relay\state\KAI_LINK_PHASE0_PC_CURRENT.json` — sanitized Windows/Tailscale/Relay/source snapshot.
- `C:\Kai\Relay\state\KAI_LINK_PHASE0_S24_CURRENT.json` — sanitized S24/ADB/MobileNode snapshot when ADB is reachable.
- `C:\Kai\Relay\state\KAI_LINK_PHASE0_CURRENT.json` — final merged classification report.
- Drive `KAI/00_KAI_CORE/KAI_LINK_RUNTIME_REPORTS/KAI_LINK_PHASE0_CURRENT.json` — copy only if that local synced path is observed and writable; otherwise Drive writeback is performed through the Google Drive connector after evidence review.

Repository files read by this plan:

- `docs/superpowers/specs/2026-09-16-kai-nervous-link-autonomous-control-plane-design.md`
- `nervous-link/scripts/bootstrap-tailscale-serve.ps1` — inspect only; do not execute during Phase 0.
- `nervous-link/clients/android/STATUS.md`
- `nervous-link/clients/android/CONTRACT.md`

No application source is modified in Phase 0.

---

### Task 1: Establish the execution channel and immutable baseline

**Files:**
- Read: `docs/superpowers/specs/2026-09-16-kai-nervous-link-autonomous-control-plane-design.md`
- Read: `nervous-link/scripts/bootstrap-tailscale-serve.ps1`
- Produce: execution note inside `KAI_LINK_PHASE0_CURRENT.json`

**Interfaces:**
- Consumes: an available Windows command surface: RDC if functional, otherwise local PowerShell supplied by Asier, otherwise another already-authorized host-management surface.
- Produces: `execution.channel`, `execution.timestamp`, `execution.blockers`, and a verified GitHub baseline SHA.

- [ ] **Step 1: Reconfirm the repository baseline without touching the PC runtime**

Expected repository baseline:

```text
branch: feat/kai-nervous-link-v0.1
spec commit: d0511dbddca81a8ad12e20e6c97919d92335dea0
KAI Nervous Link CI run #10: completed / success
```

If HEAD has advanced, record the new HEAD separately; do not rewrite the historical spec commit.

- [ ] **Step 2: Probe the preferred Windows command surface once**

Use the available management connector to execute only:

```powershell
Get-Date -Format o
$env:COMPUTERNAME
$PSVersionTable.PSVersion.ToString()
```

Expected: a timestamp, computer name, and PowerShell version.

If the connector itself fails before process execution, classify:

```json
{
  "execution_channel": "RDC",
  "status": "BLOCKED",
  "reason": "TOOL_BLOCKED"
}
```

Do not infer PC/Tailscale/Relay failure from a connector-layer failure.

- [ ] **Step 3: Select the next available execution surface without changing system state**

Priority:

```text
1. RDC, if the probe actually executed.
2. Existing local PowerShell session operated by Asier.
3. Already-provisioned alternate management surface.
```

SentinelX is not considered provisioned until a host appears in its host list. Do not install/enrol it inside Phase 0 merely to avoid recording a blocker.

- [ ] **Step 4: Record the chosen channel and continue**

A blocked preferred channel does not stop the rest of Phase 0 if another channel can provide the same read-only evidence.

---

### Task 2: Capture the Windows host and network snapshot

**Files:**
- Create: `C:\Kai\Relay\state\KAI_LINK_PHASE0_PC_CURRENT.json`

**Interfaces:**
- Consumes: read-only PowerShell/WMI/CIM/network state.
- Produces: `host`, `network`, and `process_surface` sections in the PC report.

- [ ] **Step 1: Create the report directory if it does not exist**

This filesystem mutation is evidence-only and does not affect service configuration:

```powershell
$stateDir = 'C:\Kai\Relay\state'
if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
}
```

- [ ] **Step 2: Collect host identity and boot state**

```powershell
$os = Get-CimInstance Win32_OperatingSystem
$hostSnapshot = [ordered]@{
    timestamp = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    windows_caption = $os.Caption
    windows_version = $os.Version
    last_boot = $os.LastBootUpTime.ToString('o')
    powershell = $PSVersionTable.PSVersion.ToString()
}
$hostSnapshot | ConvertTo-Json -Depth 6
```

Expected: real current OS/boot values. Do not reuse the values from prior documentation.

- [ ] **Step 3: Collect active IP/interface metadata without dumping credentials**

```powershell
$net = Get-NetIPConfiguration |
    Where-Object { $_.NetAdapter.Status -eq 'Up' } |
    ForEach-Object {
        [ordered]@{
            alias = $_.InterfaceAlias
            ipv4 = @($_.IPv4Address | ForEach-Object IPAddress)
            gateway = @($_.IPv4DefaultGateway | ForEach-Object NextHop)
            dns = @($_.DNSServer.ServerAddresses)
        }
    }
$net | ConvertTo-Json -Depth 8
```

Expected: only active interface/address metadata; no Wi-Fi password/profile export.

- [ ] **Step 4: Record relevant process presence without treating it as health**

```powershell
Get-Process tailscale,cloudflared,python,python3,node -ErrorAction SilentlyContinue |
    Select-Object Id,ProcessName,StartTime,Path |
    ConvertTo-Json -Depth 4
```

Process existence is `OBSERVED_PROCESS`, not proof of service health.

---

### Task 3: Capture Tailscale identity, peer, Tailnet Lock and Serve state — no mutation

**Files:**
- Modify evidence only: `C:\Kai\Relay\state\KAI_LINK_PHASE0_PC_CURRENT.json`

**Interfaces:**
- Consumes: installed `tailscale.exe` and daemon state.
- Produces: sanitized `tailscale` section containing version/backend/self IP/DNS, peer summaries, Tailnet Lock state, and current Serve configuration.

- [ ] **Step 1: Locate Tailscale and record its version**

```powershell
$ts = "$env:ProgramFiles\Tailscale\tailscale.exe"
if (-not (Test-Path $ts)) { throw 'tailscale.exe not found at Program Files path' }
& $ts version
```

Expected: installed client version. If the executable is absent, classify `BLOCKED_TAILSCALE_NOT_INSTALLED` and do not substitute a guessed path silently.

- [ ] **Step 2: Read daemon/self/peer state**

```powershell
$tsState = (& $ts status --json | Out-String) | ConvertFrom-Json
[ordered]@{
    backend_state = $tsState.BackendState
    self = [ordered]@{
        host_name = $tsState.Self.HostName
        dns_name = ([string]$tsState.Self.DNSName).TrimEnd('.')
        ips = @($tsState.Self.TailscaleIPs)
        online = $tsState.Self.Online
        active = $tsState.Self.Active
    }
    peers = @(
        $tsState.Peer.PSObject.Properties.Value | ForEach-Object {
            [ordered]@{
                host_name = $_.HostName
                dns_name = ([string]$_.DNSName).TrimEnd('.')
                ips = @($_.TailscaleIPs)
                online = $_.Online
                active = $_.Active
            }
        }
    )
} | ConvertTo-Json -Depth 10
```

Do not persist `User`/account profile metadata from the raw JSON.

- [ ] **Step 3: Read Tailnet Lock state in machine-readable form**

```powershell
& $ts lock status --json
```

Expected: JSON indicating whether Tailnet Lock is enabled and whether this node is accessible/locked out. Do not run `lock init`, `lock sign`, `lock add`, `lock remove`, or `lock disable` in Phase 0.

- [ ] **Step 4: Read current Serve configuration without changing it**

```powershell
& $ts serve status
```

Expected outcomes:

```text
configured Serve state -> OBSERVED
no Serve config -> OBSERVED_NOT_CONFIGURED
CLI error -> BLOCKED with exact sanitized error
```

Do not run `tailscale serve`, `serve reset`, or `serve set-config` in Phase 0.

- [ ] **Step 5: Identify the S24 peer by observed device metadata only**

Use the peer list to locate the Android device by its actual current hostname/DNS/IP. Do not infer that an Android VPN icon means same-tailnet membership.

---

### Task 4: Resolve the exact Mobile Relay runtime genealogy

**Files:**
- Read only under: `C:\Kai\Relay\`
- Modify evidence only: `KAI_LINK_PHASE0_PC_CURRENT.json`

**Interfaces:**
- Consumes: filesystem metadata, listener/process ownership, `/health`, source hashes, optional Git metadata.
- Produces: `mobile_relay` section proving what program currently owns the Mobile Relay runtime and where its source/provenance lives.

- [ ] **Step 1: Probe the real health endpoint**

```powershell
try {
    Invoke-RestMethod -Uri 'http://127.0.0.1:8788/health' -TimeoutSec 5 | ConvertTo-Json -Depth 6
} catch {
    [ordered]@{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json
}
```

Expected healthy shape from prior evidence was service-specific JSON such as `ok=true` plus service/version fields. Record the actual fresh response; do not require historical version strings.

- [ ] **Step 2: Resolve the TCP listener and owning process**

```powershell
$conn = Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue
$conn | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json
if ($conn) {
    Get-Process -Id $conn.OwningProcess -ErrorAction Stop |
        Select-Object Id,ProcessName,Path,StartTime |
        ConvertTo-Json -Depth 4
}
```

Classification rule:

```text
/health true + listener/process -> runtime healthy
listener only -> liveness only, health unresolved/failed
/health true without resolved process -> health observed, ownership unresolved
```

- [ ] **Step 3: Inventory the Relay source root without reading secret file contents**

```powershell
Get-ChildItem 'C:\Kai\Relay' -Force |
    Select-Object Name,Mode,Length,LastWriteTime |
    Sort-Object Name |
    ConvertTo-Json -Depth 4

Get-ChildItem 'C:\Kai\Relay' -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '\\(secrets?|private|\.venv|venv|__pycache__|node_modules)\\' -and
        $_.Name -match '\.(py|ps1|toml|json|md|txt)$|^requirements.*\.txt$|^pyproject\.toml$'
    } |
    Select-Object FullName,Length,LastWriteTime |
    Sort-Object FullName |
    ConvertTo-Json -Depth 5
```

Do not print file contents from directories/files whose names indicate secret/private material.

- [ ] **Step 4: Capture source hashes for non-secret implementation files**

```powershell
Get-ChildItem 'C:\Kai\Relay' -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch '\\(secrets?|private|state|logs?|\.venv|venv|__pycache__|node_modules)\\' -and
        $_.Extension -in '.py','.ps1','.toml','.md'
    } |
    ForEach-Object {
        [ordered]@{
            path = $_.FullName
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    } | ConvertTo-Json -Depth 5
```

Hashes establish provenance candidates without exposing source or keys.

- [ ] **Step 5: Determine Git provenance if present**

```powershell
if (Test-Path 'C:\Kai\Relay\.git') {
    git -C 'C:\Kai\Relay' rev-parse --show-toplevel
    git -C 'C:\Kai\Relay' branch --show-current
    git -C 'C:\Kai\Relay' rev-parse HEAD
    git -C 'C:\Kai\Relay' status --short
} else {
    'NO_LOCAL_GIT_METADATA'
}
```

Do not initialize Git here. `NO_LOCAL_GIT_METADATA` is evidence, not a failure to fix during Phase 0.

---

### Task 5: Capture Relay watchdog/startup recovery state without testing recovery yet

**Files:**
- Read: `C:\Kai\Relay\Watchdog-KaiRelay.ps1`
- Read: `C:\Kai\Relay\start-relay.ps1`
- Read: `C:\Kai\Relay\state\*` metadata
- Modify evidence only.

**Interfaces:**
- Consumes: Windows Scheduled Tasks and existing watchdog state.
- Produces: `recovery` section describing configured startup/restart behavior and current watchdog evidence.

- [ ] **Step 1: Read matching scheduled tasks**

```powershell
Get-ScheduledTask |
    Where-Object { $_.TaskName -like '*Kai Relay*' } |
    ForEach-Object {
        $info = Get-ScheduledTaskInfo -TaskName $_.TaskName -TaskPath $_.TaskPath
        [ordered]@{
            task_name = $_.TaskName
            task_path = $_.TaskPath
            state = $_.State.ToString()
            user_id = $_.Principal.UserId
            logon_type = $_.Principal.LogonType.ToString()
            run_level = $_.Principal.RunLevel.ToString()
            last_run = $info.LastRunTime.ToString('o')
            last_result = $info.LastTaskResult
            next_run = if ($info.NextRunTime) { $info.NextRunTime.ToString('o') } else { $null }
        }
    } | ConvertTo-Json -Depth 6
```

- [ ] **Step 2: Read watchdog state file if present**

```powershell
$watchdogState = 'C:\Kai\Relay\state\watchdog-state.json'
if (Test-Path $watchdogState) {
    Get-Content -LiteralPath $watchdogState -Raw
} else {
    'WATCHDOG_STATE_NOT_FOUND'
}
```

If the actual state filename differs, discover it from the `state` directory listing and record the exact name. Do not start/stop the task in Phase 0.

- [ ] **Step 3: Inspect script hashes and version markers without editing**

```powershell
'C:\Kai\Relay\Watchdog-KaiRelay.ps1','C:\Kai\Relay\start-relay.ps1' |
    Where-Object { Test-Path $_ } |
    ForEach-Object {
        [ordered]@{
            path = $_
            sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash
        }
    } | ConvertTo-Json -Depth 4
```

Do not kill Relay or reboot the PC in Phase 0. Recovery-effect testing belongs to Gate C.

---

### Task 6: Resolve the exact MobileNode 0.5.1 source/runtime state

**Files:**
- Read only under: `C:\Kai\MobileNode\`
- Create: `C:\Kai\Relay\state\KAI_LINK_PHASE0_S24_CURRENT.json` when ADB is reachable.

**Interfaces:**
- Consumes: local Android project metadata and ADB read-only queries.
- Produces: `mobilenode_source` and `s24` evidence sections.

- [ ] **Step 1: Inventory local MobileNode source without build/generated/private files**

```powershell
$mobileRoot = 'C:\Kai\MobileNode'
if (Test-Path $mobileRoot) {
    Get-ChildItem $mobileRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch '\\(build|\.gradle|\.idea|local\.properties|secrets?)\\' -and
            $_.Name -ne 'local.properties'
        } |
        Select-Object FullName,Length,LastWriteTime |
        Sort-Object FullName |
        ConvertTo-Json -Depth 5
} else {
    'MOBILENODE_SOURCE_ROOT_NOT_FOUND'
}
```

- [ ] **Step 2: Hash Kotlin/Gradle/manifest/test source**

```powershell
if (Test-Path $mobileRoot) {
    Get-ChildItem $mobileRoot -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch '\\(build|\.gradle|\.idea|secrets?)\\' -and
            ($_.Extension -in '.kt','.kts','.xml' -or $_.Name -in 'gradle.properties','settings.gradle','settings.gradle.kts')
        } |
        ForEach-Object {
            [ordered]@{
                path = $_.FullName
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            }
        } | ConvertTo-Json -Depth 5
}
```

- [ ] **Step 3: Record Git provenance if present**

```powershell
if (Test-Path 'C:\Kai\MobileNode\.git') {
    git -C 'C:\Kai\MobileNode' branch --show-current
    git -C 'C:\Kai\MobileNode' rev-parse HEAD
    git -C 'C:\Kai\MobileNode' status --short
} else {
    'NO_LOCAL_GIT_METADATA'
}
```

Do not initialize, commit, clean, reset, or copy source yet. Source preservation is Gate F after this inventory is reviewed.

- [ ] **Step 4: Check ADB device reachability**

```powershell
adb devices -l
```

Classification:

```text
one authorized S24 -> OBSERVED_REACHABLE
unauthorized -> BLOCKED_ADB_AUTH
no device -> BLOCKED_ADB_UNREACHABLE
multiple devices -> UNRESOLVED_TARGET until exact serial is selected
```

- [ ] **Step 5: If one S24 is authorized, capture package/runtime basics only**

Use the exact serial from `adb devices -l` as `$serial`.

```powershell
adb -s $serial shell getprop ro.product.manufacturer
adb -s $serial shell getprop ro.product.model
adb -s $serial shell getprop ro.build.version.release
adb -s $serial shell getprop ro.build.version.sdk
adb -s $serial shell dumpsys package com.kai.mobilenode | Select-String 'versionName=|versionCode='
adb -s $serial shell pidof com.kai.mobilenode
adb -s $serial shell settings get secure enabled_accessibility_services
adb -s $serial shell dumpsys deviceidle whitelist | Select-String 'com.kai.mobilenode'
adb -s $serial shell dumpsys package com.tailscale.ipn | Select-String 'versionName=|versionCode='
```

Do not run `uiautomator dump`, screenshot, clipboard, notification dump, contact query, or accessibility-tree export.

- [ ] **Step 6: Read the MobileNode runtime endpoint value without exposing app secrets**

The endpoint file itself is not a credential, but app-private storage is high-trust. Read only this known file:

```powershell
adb -s $serial shell run-as com.kai.mobilenode cat files/relay-base-url.txt
```

Expected: one URL. Do not recursively list or dump app-private files.

- [ ] **Step 7: Discover declared service component names without starting them**

```powershell
adb -s $serial shell dumpsys package com.kai.mobilenode | Select-String 'Service|service|KaiLink|Accessibility' -Context 1,2
```

Record the exact component names needed for the next Gate A plan. Do not force-stop/start anything here.

---

### Task 7: Record the PC Remote Spine baseline separately

**Files:**
- Read: GitHub `nervous-link/**`
- Modify evidence only.

**Interfaces:**
- Consumes: GitHub branch metadata and CI state.
- Produces: `pc_remote_spine` evidence section that cannot be mistaken for the Mobile Relay runtime.

- [ ] **Step 1: Record source authority**

```text
repository: Bashull/Kai
branch: feat/kai-nervous-link-v0.1
approved delta spec commit: d0511dbddca81a8ad12e20e6c97919d92335dea0
module: nervous-link/
relay implementation: Node.js + Socket.IO
agent: nervous-link/pc-agent
```

- [ ] **Step 2: Record CI evidence for the spec commit**

```text
workflow: KAI Nervous Link CI
run: #10
head_sha: d0511dbddca81a8ad12e20e6c97919d92335dea0
status: completed
conclusion: success
```

This proves repository tests for that commit only. It does not prove PC Remote Agent deployment or Mobile Control runtime health.

- [ ] **Step 3: Record recovery-candidate status**

Unless fresh runtime evidence shows the PC Agent is installed/running, classify:

```text
PC_REMOTE_SPINE_SOURCE = OBSERVED
PC_REMOTE_SPINE_CI = OBSERVED_SUCCESS
PC_REMOTE_AGENT_RUNTIME = UNRESOLVED
```

---

### Task 8: Merge evidence, classify every required datum, and perform durable writeback

**Files:**
- Create/replace: `C:\Kai\Relay\state\KAI_LINK_PHASE0_CURRENT.json`
- Update: Drive Boot Packet CURRENT
- Update: Drive Node Map CURRENT
- Update: Drive `KAI_NODE_RELAY_MOBILENODE_WIKI_CURRENT_v1.0.0`
- Update: Drive Secret Pointer Registry only for pointer/status metadata discovered during Phase 0; never secret values.

**Interfaces:**
- Consumes: Tasks 1-7 evidence.
- Produces: one sanitized Phase 0 report and a precise list of blockers/observed facts that the Gate A implementation plan can rely on.

- [ ] **Step 1: Build the merged report with explicit evidence classes**

Required top-level shape:

```json
{
  "schema": "kai-mobile-control-phase0-v1",
  "timestamp": "RFC3339",
  "overall": "OBSERVED|PARTIAL|BLOCKED",
  "execution": {},
  "host": {},
  "network": {},
  "tailscale": {},
  "mobile_relay": {},
  "recovery": {},
  "mobilenode_source": {},
  "s24": {},
  "pc_remote_spine": {},
  "source_authority": {},
  "blockers": [],
  "promotion_readiness": {
    "gate_a_plan_ready": false,
    "reason": ""
  }
}
```

Every leaf that matters operationally must be traceable to one of:

```text
OBSERVED
INFERRED
UNRESOLVED
BLOCKED
```

- [ ] **Step 2: Apply the Gate A planning readiness rule**

Set `gate_a_plan_ready=true` only if all of these are known freshly:

```text
1. actual Mobile Relay health endpoint behavior
2. actual Mobile Relay source/runtime lineage or enough source evidence to invoke its existing command API safely
3. PC Tailscale backend/self identity
4. S24 Tailscale peer identity or explicit blocker
5. current Serve state
6. MobileNode installed version
7. MobileNode exact private endpoint file path confirmed
8. exact MobileNode service component names or exact existing wake/start mechanism
9. ADB state classified
```

If any item is unknown, keep Gate A plan readiness false and name the missing item precisely.

- [ ] **Step 3: Secret-scan the report before persistence**

Reject persistence if the JSON contains patterns matching any of:

```text
login.tailscale.com/
 tskey-
 CF_API_TOKEN
 cloudflared tunnel token
 disablement-secret:
 owner_token
 device_token
 payload_key
 hmac_key
```

Public DNS/IP names and public `tlpub:`/`nodekey:` identifiers may be retained only when operationally useful; omit them if not needed.

- [ ] **Step 4: Persist the local report atomically**

```powershell
$target = 'C:\Kai\Relay\state\KAI_LINK_PHASE0_CURRENT.json'
$tmp = "$target.tmp"
$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tmp -Encoding utf8
Move-Item -LiteralPath $tmp -Destination $target -Force
Get-FileHash -LiteralPath $target -Algorithm SHA256
```

Record the SHA-256 as evidence of the exact Phase 0 snapshot.

- [ ] **Step 5: Write sanitized conclusions to Drive authorities**

Write only the conclusions needed by future Kai sessions:

```text
- exact observation date/time
- Mobile Control Spine runtime identity and health classification
- Tailscale PC/S24/Serve/Tailnet Lock classifications
- MobileNode version/source-authority classification
- watchdog/startup classification
- PC Remote Spine kept separate
- exact blockers
- whether Gate A planning is ready
- local report path + SHA-256
```

Never paste raw Tailscale status JSON, private app data, UI trees, auth URLs, or secret values into Drive.

- [ ] **Step 6: Self-review Phase 0 before declaring completion**

Completion requires:

```text
[ ] no runtime mutation beyond evidence files
[ ] no secret values persisted
[ ] no UI/private-content capture
[ ] no historical state presented as current
[ ] Mobile Relay and PC Remote Relay remain distinctly named
[ ] every required unknown is explicitly UNRESOLVED/BLOCKED
[ ] report hash captured
[ ] Drive writeback completed/read back
```

- [ ] **Step 7: Commit only documentation produced by the execution, if any**

If execution requires a repository-side status note, it must contain sanitized conclusions only. Do not commit local runtime JSON, source dumps, user identifiers, IP inventories, or credential material by default.

---

## Phase 0 Exit Criteria

Phase 0 is complete when the fresh evidence can answer, without inference:

1. Which program/runtime currently owns `127.0.0.1:8788` and whether its real `/health` succeeds.
2. Where the current Mobile Relay source/provenance lives and whether it has Git source authority.
3. Where the exact MobileNode 0.5.1 source lives and whether it has Git source authority.
4. Whether PC Tailscale is Running, its current private identity, and whether the S24 is a peer.
5. Whether Tailnet Lock admits or blocks either relevant node, to the extent observable from the PC/S24 surfaces.
6. Whether Tailscale Serve is currently configured, without changing it.
7. Whether the S24 is ADB-reachable and whether `com.kai.mobilenode` 0.5.1/code 7 is actually installed.
8. The exact MobileNode private runtime endpoint file and service component names.
9. Which recovery/startup mechanisms are configured on Windows.
10. Which observations are blocked and by what surface.

Only after these are answered or precisely classified may the next plan mutate transport/runtime state for **Gate A: private Tailscale Serve path + real mobile-data effect proof**.

## Explicitly Deferred to Later Plans

- Gate A transport activation and MobileNode endpoint switch.
- Gate B least-privilege Tailscale policy hardening.
- Gate C PC/S24 reboot/background resilience.
- Gate D MobileNode multipath and Cloudflare named-tunnel failover.
- Gate E PC Remote Agent recovery path.
- Gate F exact MobileNode/Mobile Relay source preservation and canonicalization.
- Hybrid external broker/control plane.
