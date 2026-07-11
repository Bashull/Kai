# KAI Nervous Link v0.1

KAI Nervous Link is Kai's free-first remote nervous system between Asier's S24 Ultra, a cloud-accessible relay and the Windows PC agent.

The PC agent connects outward to the relay. The primary design therefore avoids inbound router port forwarding.

## Current implementation status

Implemented and tested locally on Windows:

- versioned request/response protocol;
- default-deny capability policy;
- path-root containment with traversal and junction/symlink escape rejection;
- bounded command execution with argv, timeout and output limits;
- atomic file writes and optional SHA-256 reads;
- process listing;
- append-only audit with recursive secret redaction;
- persistent local kill switch;
- HMAC agent authentication;
- anti-replay nonce guard;
- pairing/session registry;
- outbound PC agent with heartbeat and reconnect;
- typed CLI client;
- Android/MobileNode client contract.

External mobile-data reachability is not yet claimed as verified until a real Cloudflare or Tailscale path is deployed and tested from the S24 on mobile data.

## Safety defaults

- default deny;
- no `delete_file` action in v0.1;
- no administrator auto-elevation;
- no public unauthenticated shell;
- explicit executable allowlist;
- explicit file roots;
- structured argv with `shell: false`;
- bounded command timeout and output size;
- append-only local audit;
- recursive secret redaction;
- independent persistent kill switch;
- HMAC-bound agent authentication;
- replay protection;
- owner credential removed before requests reach the PC agent.

## Important command-execution warning

A broadly capable runtime such as `node`, `python`, PowerShell or another interpreter can execute code that performs filesystem or network operations. Merely putting such a runtime in the executable allowlist does **not** make arbitrary arguments intrinsically safe.

For personal local testing, the example policy permits `node` because the integration suite needs a portable command fixture. Before treating `command.execute.safe` as production-safe over an Internet-facing transport, add executable-specific argument policies or classify broad runtimes under a higher-risk capability requiring explicit confirmation.

## Emergency bootstrap retained

```bash
npx @wonderwhy-er/desktop-commander@latest remote
```

Use this only as a temporary recovery bridge while Nervous Link is unavailable. It is not the canonical transport once Nervous Link is proven end to end.

## Local install

Requirements:

- Node.js 22 or newer;
- npm;
- Windows for the current primary PC-agent target.

```bash
cd nervous-link
npm ci
npm test
```

At the time this README was written on Asier's PC, neither `cloudflared` nor Tailscale was installed. Do not interpret the transport sections below as proof that external reachability has already been tested.

## Local configuration

Copy the examples to ignored local files:

```powershell
Copy-Item .\config\policy.example.json .\config\policy.local.json
Copy-Item .\config\agent.example.json .\config\agent.local.json
```

Never commit:

- `.env`;
- `data/`;
- `config/agent.local.json`;
- `config/policy.local.json`;
- `config/*.secret.json`;
- device tokens;
- owner tokens;
- Cloudflare or Tailscale credentials.

Store the paired device credential at the path configured by `credential_path`. The current startup script expects JSON containing a `device_token` field.

## Start relay locally

Set the owner token only in the local environment:

```powershell
$env:KAI_NERVOUS_LINK_OWNER_TOKEN = '<set-locally-never-commit>'
npm run relay
```

The relay starts on port `8787` by default and binds to localhost through the startup script.

Health endpoint:

```text
GET http://127.0.0.1:8787/health
```

Expected body:

```json
{"ok":true,"protocol":"kai-nervous-link/0.1"}
```

## Cloudflare Tunnel primary transport

Cloudflare Tunnel is the preferred free-first publication path for v0.1. `cloudflared` creates outbound-only connections from the origin to Cloudflare, so the design does not require an inbound router port or publicly routable origin IP.

Official references:

- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/
- https://www.cloudflare.com/plans/zero-trust-services/

Deployment rule:

1. install `cloudflared` from Cloudflare's official distribution;
2. create a tunnel in Asier's own Cloudflare account;
3. map only the local relay endpoint needed by Nervous Link;
4. keep tunnel credentials outside Git;
5. preserve owner-token authentication at the application layer;
6. test reachability from the S24 on mobile data before marking the gate PASS.

No specific tunnel credential, token or hostname belongs in this repository.

## Tailscale fallback

Tailscale Personal is the fallback recovery path for private device-to-device connectivity. The Personal plan is currently listed by Tailscale as free forever for personal use.

Official reference:

- https://tailscale.com/pricing

Tailscale is not the canonical Nervous Link protocol. It is a transport/recovery option underneath the same typed actions, policy, audit and kill-switch rules.

## Start PC agent

After creating the ignored local policy/config and storing a local paired device credential:

```powershell
npm run agent
```

The agent connects outward, authenticates with HMAC proof bound to its socket, starts heartbeat after authentication and reconnects automatically after relay interruption.

## CLI client

Pairing approval:

```powershell
$env:KAI_NERVOUS_LINK_OWNER_TOKEN = '<set-locally-never-commit>'
node .\clients\cli\kai-link.js pair --relay <URL> --pairing-id <ID> --code <CODE>
```

Typed remote call:

```powershell
node .\clients\cli\kai-link.js call --relay <URL> --device pc-asier-main --action device_info --capability system.read --params '{}'
```

The CLI reads the owner token from the environment. It does not accept a long-lived owner token as a command-line option. Pairing output redacts the device token from console output.

## Kill switch

The PC agent stops accepting remote actions when its configured STOP file exists.

The STOP file is persistent local state. Once triggered, the agent remains stopped until the flag is removed locally and the agent is explicitly restarted.

The remote `kill_switch` action is capability-gated and authenticated. There is deliberately no remote action to silently remove the STOP file.

## Install Windows user-level startup task

The installer creates a Scheduled Task at user logon with `RunLevel Limited`. It does not request administrator elevation.

Run it only after reviewing the paths:

```powershell
.\scripts\install-windows-startup.ps1 `
  -NodeExe (Get-Command node).Source `
  -AgentScript (Resolve-Path .\scripts\start-agent.js) `
  -WorkingDirectory (Resolve-Path .)
```

The script validates that all three paths exist before registering the task.

## Verification gates

v0.1 is complete only after fresh evidence proves:

1. `npm ci` succeeds from the lockfile;
2. all automated tests pass;
3. relay health responds locally;
4. PC agent connects outward and authenticates;
5. agent reconnects after relay restart;
6. `device_info` roundtrip works;
7. allowed `read_file` succeeds;
8. outside-root `read_file` is denied;
9. allowlisted command succeeds;
10. non-allowlisted command is denied;
11. audit entries are written with secrets redacted;
12. kill switch stops execution;
13. S24 reaches the relay over mobile data without opening a router port.

Cloudflare mobile-data reachability and Tailscale fallback must remain `NOT_RUN` until actually deployed and tested. Documentation alone is not evidence.

## Kai doctrine

`SQUEEZE -> VERIFY -> INTEGRATE -> THEN DISCARD.`

No discovery becomes canonical merely because it exists. No blocked zone counts as omitted. No quick fingerprint proves an exact duplicate. No destructive capability is added silently.
