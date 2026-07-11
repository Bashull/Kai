# KAI Nervous Link v0.1 Design

> Status: design approved in chat for a free-first implementation. This spec is the written gate before implementation planning.

## Goal

Build a secure remote nervous system for Kai so Asier can reach and control the Windows PC from the S24 Ultra over Wi-Fi or mobile data, without depending permanently on Desktop Commander Remote or another proprietary relay.

The first version must be free to operate for personal use, auditable, revocable, explicit about permissions, compatible with the current Kai ecosystem, and safe by default.

## Decision summary

Primary transport: Cloudflare Tunnel / Cloudflare One free tier, using outbound-only connectivity from the PC side so the home router does not need inbound port forwarding.

Fallback transport: Tailscale Personal free plan for direct device-to-device access and recovery.

Bootstrap/emergency fallback retained:

```bash
npx @wonderwhy-er/desktop-commander@latest remote
```

Replit is not part of v0.1. It may be reconsidered later only if it adds value without introducing cost or unnecessary dependency.

## Existing Kai context to reuse

The repository already contains `companion/backend` with Express, Socket.IO, SQLite, permissions and audit logging. Nervous Link must reuse the ideas and data contracts that are genuinely useful, while remaining a separate module so remote control does not become coupled to avatar, chat, file upload or Companion UI concerns.

Relevant existing concepts:

- `PermissionSystem` with READ, WRITE, DELETE, EXECUTE and CREATE actions.
- `audit_log` persistence.
- WebSocket/Socket.IO real-time messaging.
- `ToolEngine` and capability-style execution.
- Kai MobileNode with Accessibility and Termux `RUN_COMMAND` permission.
- Existing Kai capability registry, scrap-digestion doctrine and full-system inventory tooling.

## Non-goals for v0.1

- No unrestricted remote desktop streaming.
- No silent privilege escalation.
- No bypass of Android, Windows or app sandboxes.
- No auto-delete or destructive cleanup.
- No hidden credential harvesting.
- No public unauthenticated shell.
- No attempt to replace every MCP or connector at once.
- No commercial multi-tenant hosting.

## Architecture

```text
S24 / ChatGPT / future Kai app / MobileNode
                |
          4G / 5G / Wi-Fi
                |
                v
      +-----------------------+
      |   KAI CLOUD RELAY     |
      | auth + routing only   |
      +-----------+-----------+
                  |
        encrypted persistent link
                  |
                  v
      +-----------------------+
      |    KAI PC AGENT       |
      | Windows service/app   |
      +-----------+-----------+
                  |
      +-----------+-------------+-------------+
      |                         |             |
      v                         v             v
   Files                    Processes      Commands
      |                         |             |
      +---- ADB / Git / Docker / IDEs / Kai tools ----+
```

The PC agent initiates the connection outward. No inbound router port is required for the primary path.

## Repository layout

```text
nervous-link/
├── README.md
├── protocol/
│   ├── schema.json
│   ├── messages.js
│   └── errors.js
├── relay/
│   ├── server.js
│   ├── auth.js
│   ├── sessionRegistry.js
│   └── audit.js
├── pc-agent/
│   ├── agent.js
│   ├── capabilities.js
│   ├── policy.js
│   ├── commandRunner.js
│   ├── fileOps.js
│   ├── processOps.js
│   ├── heartbeat.js
│   └── killSwitch.js
├── clients/
│   ├── cli/
│   │   └── kai-link.js
│   └── android/
│       └── CONTRACT.md
├── config/
│   ├── policy.example.json
│   └── agent.example.json
└── tests/
    ├── protocol.test.js
    ├── policy.test.js
    ├── pairing.test.js
    ├── commandRunner.test.js
    ├── fileOps.test.js
    └── audit.test.js
```

## Protocol

Every request uses a versioned envelope:

```json
{
  "protocol": "kai-nervous-link/0.1",
  "request_id": "uuid",
  "session_id": "uuid",
  "device_id": "pc-asier-main",
  "timestamp": "RFC3339",
  "action": "device_info",
  "params": {},
  "capability": "system.read",
  "nonce": "random",
  "signature": "base64-or-token-proof"
}
```

Every response includes:

```json
{
  "protocol": "kai-nervous-link/0.1",
  "request_id": "uuid",
  "status": "ok",
  "started_at": "RFC3339",
  "finished_at": "RFC3339",
  "result": {},
  "error": null,
  "audit_id": "uuid"
}
```

Unknown protocol versions, replayed nonces, expired timestamps and unrecognised device/session IDs are rejected.

## v0.1 actions

Read-only actions:

- `ping`
- `heartbeat`
- `device_info`
- `list_processes`
- `list_directory`
- `read_file`
- `audit_log`

Mutating actions:

- `write_file`
- `run_command`
- `kill_process`

Emergency action:

- `kill_switch`

There is deliberately no `delete_file` action in v0.1.

## Capability model

Permissions are capability-scoped, not global.

Examples:

```text
system.read
process.list
process.kill
file.read
file.write
command.execute.safe
command.execute.admin
adb.read
adb.control
git.read
git.write
```

Default policy denies everything except heartbeat and minimal device identity required for pairing.

Example policy:

```json
{
  "default": "deny",
  "roots": {
    "file.read": ["C:/Users/ASIER/OneDrive/Desktop/KAI"],
    "file.write": ["C:/Users/ASIER/OneDrive/Desktop/KAI/_KAI_BRIDGE"]
  },
  "commands": {
    "safe": ["python", "node", "git", "adb", "docker", "code", "codex"],
    "blocked_patterns": ["format ", "diskpart", "cipher /w", "Remove-Item -Recurse C:\\"]
  },
  "require_confirmation": [
    "process.kill",
    "command.execute.admin",
    "file.write.outside_bridge"
  ]
}
```

The actual implementation must not rely only on string blocklists for safety. Structured argument validation and allowlisted executable resolution are required.

## Pairing

Pairing is explicit and revocable.

Flow:

```text
1. PC agent starts unpaired.
2. Agent generates short-lived pairing code + device public identity.
3. Asier approves pairing from authorised client.
4. Relay binds user identity, device ID and key material.
5. PC stores only the minimum long-lived credential required to reconnect.
6. Pairing can be revoked locally or remotely.
```

No long-lived secret is printed to logs or committed to Git.

## Transport strategy

### Primary: Cloudflare Tunnel

The PC side runs an outbound connector. The relay is exposed through Cloudflare without requiring inbound router configuration.

### Fallback: Tailscale Personal

Used for direct private device-to-device recovery, diagnostics and emergency access when appropriate.

### Emergency bootstrap

Desktop Commander Remote may remain documented as a temporary bootstrap:

```bash
npx @wonderwhy-er/desktop-commander@latest remote
```

It is not considered the canonical transport once Nervous Link is proven.

## Relay responsibilities

The relay does only what must be central:

- authenticate users/devices;
- pair sessions;
- route encrypted requests/responses;
- reject expired/replayed requests;
- maintain connection presence;
- expose minimal health state;
- append relay-side audit metadata.

The relay does not hold arbitrary PC filesystem contents or command history beyond configured audit retention.

## PC agent responsibilities

The agent:

- reconnects automatically with exponential backoff;
- authenticates relay and session;
- validates capability and policy before execution;
- executes one bounded action at a time;
- streams output for long-running commands;
- enforces timeout and output-size limits;
- records immutable local audit entries;
- supports immediate kill switch;
- never auto-elevates privileges.

## Command execution

`run_command` v0.1 is bounded by:

- allowlisted executable resolution;
- explicit argv array, not raw shell string by default;
- working-directory allowlist;
- timeout;
- maximum stdout/stderr size;
- optional interactive session ID only in a later milestone;
- no administrator elevation unless a separate future capability is explicitly designed and approved.

Example:

```json
{
  "action": "run_command",
  "params": {
    "executable": "git",
    "args": ["status", "--short"],
    "cwd": "C:/Users/ASIER/OneDrive/Desktop/KAI",
    "timeout_ms": 30000
  },
  "capability": "command.execute.safe"
}
```

## File access

File operations must:

- canonicalise paths;
- reject traversal outside approved roots;
- reject symlink/junction escapes;
- preserve binary/text distinction;
- optionally compute SHA-256;
- record path, operation, byte count and result in audit.

`write_file` uses atomic temporary-file replacement where possible.

## Audit

Every operation records:

```text
audit_id
request_id
session_id
device_id
actor_id
action
capability
resource
timestamp_start
timestamp_end
status
error_code
bytes_in
bytes_out
command_exit_code when applicable
```

Audit logs must redact credentials and secret values.

## Kill switch

Three independent kill paths:

1. Local file flag watched by the PC agent.
2. Local CLI command.
3. Remote authenticated emergency request.

When triggered:

- stop accepting new actions;
- cancel safe-to-cancel running tasks;
- close relay connection;
- write audit event;
- remain stopped until explicit local restart.

## Android/MobileNode integration

v0.1 does not require modifying the Android app immediately. The first client may be CLI/web. The Android contract is documented so MobileNode can later become a first-class client.

Future MobileNode integration should expose only explicit typed commands, not an unrestricted exported broadcast receiver.

## Compatibility with Kai doctrine

The system follows these binding Kai rules:

- SQUEEZE -> VERIFY -> INTEGRATE -> THEN DISCARD.
- No blocked zone is treated as omitted.
- No quick fingerprint proves exact duplication.
- No discovered code becomes canonical merely because it exists.
- No destructive action is added silently.
- Every capability must be testable, auditable and revocable.

## Testing strategy

All implementation is test-first.

Required unit tests:

- protocol envelope validation;
- stale timestamp rejection;
- nonce replay rejection;
- unknown device rejection;
- default-deny policy;
- root path containment;
- symlink/junction escape rejection where platform allows testing;
- safe command allowlist;
- blocked executable rejection;
- timeout handling;
- output truncation;
- audit redaction;
- kill-switch stop behaviour.

Required integration tests:

- relay + fake agent connection;
- pair -> reconnect -> heartbeat;
- authenticated `device_info` roundtrip;
- authorised `read_file` in temp root;
- denied `read_file` outside temp root;
- authorised safe command;
- denied command;
- forced reconnect after relay restart.

## Success criteria for v0.1

v0.1 is complete only when all of the following are proven:

1. A PC agent starts and connects outward.
2. A client can pair explicitly.
3. The relay routes authenticated messages.
4. The agent survives relay restart and reconnects.
5. The client can retrieve device info.
6. File reads are restricted to approved roots.
7. Safe command execution works with argv, timeout and output limits.
8. All actions create audit entries.
9. Kill switch stops remote execution.
10. Tests pass on Windows.
11. No inbound router port is required for the primary path.
12. No paid service is required for Asier's personal v0.1 use.

## Future milestones

Not part of v0.1 implementation plan:

- streaming terminal sessions;
- Android UI client;
- direct MobileNode adapter;
- desktop screen capture/remote desktop;
- resumable file transfer;
- GitHub/Hugging Face action adapters;
- Antigravity/VS Code structured automation;
- multi-PC fleet;
- end-to-end content encryption independent of transport provider;
- self-hosted relay.

## Security note

This project creates remote control capability over a personal computer. The safest interpretation wins when requirements conflict. Convenience never silently overrides authentication, authorization, audit, kill switch or explicit user control.

## Final design verdict

Build `nervous-link` as a separate module in `Bashull/Kai`, reuse proven permission/audit ideas from Companion, use Cloudflare Tunnel as the primary free transport, keep Tailscale Personal as fallback, retain Desktop Commander Remote only as emergency bootstrap, and do not merge implementation into `main` until tests and review pass.
