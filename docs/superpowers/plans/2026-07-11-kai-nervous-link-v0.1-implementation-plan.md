# KAI Nervous Link v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a free-first, secure, auditable remote nervous system that lets Asier reach and control the Windows PC from the S24 Ultra over Wi-Fi or mobile data without permanently depending on Desktop Commander Remote.

**Architecture:** A separate `nervous-link/` module inside `Bashull/Kai` contains a Cloudflare-Tunnel-friendly relay, an outbound Windows PC agent, a CLI client, versioned protocol helpers, capability policy enforcement, local JSONL audit, explicit pairing, replay protection, bounded command execution and an independent kill switch. The relay routes authenticated envelopes but does not become a general file store; the PC agent remains the final policy enforcement point.

**Tech Stack:** Node.js 22, CommonJS, built-in `node:test`, built-in `crypto`, `fs/promises`, `child_process`, Express 4, Socket.IO 4, Socket.IO Client 4, Cloudflare Tunnel free tier as primary transport, Tailscale Personal as fallback.

## Global Constraints

- Work only on branch `feat/kai-nervous-link-v0.1`; do not touch `main` directly.
- Primary operation must remain free for Asier's personal v0.1 usage.
- No inbound router port may be required for the Cloudflare path.
- Default policy is deny.
- No unrestricted public shell.
- No silent privilege escalation.
- No sandbox bypass.
- No `delete_file` action in v0.1.
- No secrets in Git, logs or test fixtures.
- Same-size files are never considered exact duplicates without full matching hash; this doctrine applies to all future file-transfer work.
- Every mutating capability must be explicit, auditable and revocable.
- All implementation is test-first.
- Reuse useful Kai concepts, but keep Nervous Link independent from avatar/chat UI concerns.

---

## Repository structure to create

```text
nervous-link/
├── README.md
├── package.json
├── protocol/
│   ├── constants.js
│   ├── envelope.js
│   └── errors.js
├── relay/
│   ├── server.js
│   ├── auth.js
│   ├── sessionRegistry.js
│   ├── replayGuard.js
│   └── audit.js
├── pc-agent/
│   ├── agent.js
│   ├── capabilities.js
│   ├── policy.js
│   ├── commandRunner.js
│   ├── fileOps.js
│   ├── processOps.js
│   ├── heartbeat.js
│   ├── audit.js
│   └── killSwitch.js
├── clients/
│   ├── cli/
│   │   └── kai-link.js
│   └── android/
│       └── CONTRACT.md
├── config/
│   ├── policy.example.json
│   └── agent.example.json
├── scripts/
│   ├── start-relay.js
│   ├── start-agent.js
│   └── install-windows-startup.ps1
└── tests/
    ├── protocol.test.js
    ├── policy.test.js
    ├── commandRunner.test.js
    ├── fileOps.test.js
    ├── pairing.test.js
    ├── relay-agent.integration.test.js
    ├── audit.test.js
    └── killSwitch.test.js
```

---

## Task 1: Scaffold package and versioned protocol envelope

**Files:**
- Create: `nervous-link/package.json`
- Create: `nervous-link/protocol/constants.js`
- Create: `nervous-link/protocol/errors.js`
- Create: `nervous-link/protocol/envelope.js`
- Test: `nervous-link/tests/protocol.test.js`

**Interfaces:**
- Produces `PROTOCOL_VERSION`, `ACTIONS`, `CAPABILITIES`.
- Produces `createRequestEnvelope(input)`, `validateRequestEnvelope(envelope, options)`, `createResponseEnvelope(input)`.
- Later tasks consume these exact exports.

- [ ] **Step 1: Create the package manifest**

```json
{
  "name": "kai-nervous-link",
  "version": "0.1.0",
  "private": true,
  "description": "Secure remote nervous system for Kai",
  "main": "relay/server.js",
  "scripts": {
    "test": "node --test tests/*.test.js",
    "test:unit": "node --test tests/protocol.test.js tests/policy.test.js tests/commandRunner.test.js tests/fileOps.test.js tests/audit.test.js tests/killSwitch.test.js",
    "test:integration": "node --test tests/pairing.test.js tests/relay-agent.integration.test.js",
    "relay": "node scripts/start-relay.js",
    "agent": "node scripts/start-agent.js"
  },
  "engines": {
    "node": ">=22"
  },
  "dependencies": {
    "express": "^4.21.2",
    "socket.io": "^4.8.1",
    "socket.io-client": "^4.8.1"
  }
}
```

- [ ] **Step 2: Write the failing protocol tests**

Create `nervous-link/tests/protocol.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  createRequestEnvelope,
  createResponseEnvelope,
  validateRequestEnvelope,
} = require('../protocol/envelope');
const { ProtocolError } = require('../protocol/errors');

const base = () => ({
  request_id: 'req-1',
  session_id: 'sess-1',
  device_id: 'pc-asier-main',
  timestamp: new Date().toISOString(),
  action: 'device_info',
  params: {},
  capability: 'system.read',
  nonce: 'nonce-1234567890',
  signature: 'proof',
});

test('creates and validates a v0.1 request envelope', () => {
  const envelope = createRequestEnvelope(base());
  assert.equal(validateRequestEnvelope(envelope).ok, true);
});

test('rejects unknown protocol version', () => {
  const envelope = { ...createRequestEnvelope(base()), protocol: 'kai-nervous-link/9.9' };
  assert.throws(() => validateRequestEnvelope(envelope), ProtocolError);
});

test('rejects stale timestamps', () => {
  const envelope = createRequestEnvelope({
    ...base(),
    timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
  });
  assert.throws(
    () => validateRequestEnvelope(envelope, { maxClockSkewMs: 60_000 }),
    error => error.code === 'STALE_TIMESTAMP'
  );
});

test('creates a correlated response envelope', () => {
  const response = createResponseEnvelope({
    request_id: 'req-1',
    status: 'ok',
    started_at: '2026-07-11T00:00:00.000Z',
    finished_at: '2026-07-11T00:00:01.000Z',
    result: { online: true },
    audit_id: 'audit-1',
  });
  assert.equal(response.request_id, 'req-1');
  assert.equal(response.error, null);
});
```

- [ ] **Step 3: Run the protocol test and verify RED**

Run:

```bash
cd nervous-link
node --test tests/protocol.test.js
```

Expected: FAIL because `../protocol/envelope` does not exist.

- [ ] **Step 4: Implement protocol constants and errors**

Create `nervous-link/protocol/constants.js`:

```js
const PROTOCOL_VERSION = 'kai-nervous-link/0.1';

const ACTIONS = Object.freeze([
  'ping',
  'heartbeat',
  'device_info',
  'list_processes',
  'list_directory',
  'read_file',
  'audit_log',
  'write_file',
  'run_command',
  'kill_process',
  'kill_switch',
]);

const CAPABILITIES = Object.freeze([
  'system.read',
  'process.list',
  'process.kill',
  'file.read',
  'file.write',
  'command.execute.safe',
  'adb.read',
  'adb.control',
  'git.read',
  'git.write',
  'emergency.kill',
]);

module.exports = { PROTOCOL_VERSION, ACTIONS, CAPABILITIES };
```

Create `nervous-link/protocol/errors.js`:

```js
class ProtocolError extends Error {
  constructor(code, message, details = null) {
    super(message);
    this.name = 'ProtocolError';
    this.code = code;
    this.details = details;
  }
}

module.exports = { ProtocolError };
```

- [ ] **Step 5: Implement request/response envelope validation**

Create `nervous-link/protocol/envelope.js`:

```js
const { PROTOCOL_VERSION, ACTIONS, CAPABILITIES } = require('./constants');
const { ProtocolError } = require('./errors');

const REQUIRED_REQUEST_FIELDS = [
  'protocol', 'request_id', 'session_id', 'device_id', 'timestamp',
  'action', 'params', 'capability', 'nonce', 'signature',
];

function createRequestEnvelope(input) {
  return { protocol: PROTOCOL_VERSION, ...input };
}

function validateRequestEnvelope(envelope, options = {}) {
  const maxClockSkewMs = options.maxClockSkewMs ?? 120_000;
  if (!envelope || typeof envelope !== 'object' || Array.isArray(envelope)) {
    throw new ProtocolError('INVALID_ENVELOPE', 'Request envelope must be an object');
  }
  for (const field of REQUIRED_REQUEST_FIELDS) {
    if (!(field in envelope)) {
      throw new ProtocolError('MISSING_FIELD', `Missing required field: ${field}`);
    }
  }
  if (envelope.protocol !== PROTOCOL_VERSION) {
    throw new ProtocolError('UNSUPPORTED_PROTOCOL', `Unsupported protocol: ${envelope.protocol}`);
  }
  if (!ACTIONS.includes(envelope.action)) {
    throw new ProtocolError('UNKNOWN_ACTION', `Unknown action: ${envelope.action}`);
  }
  if (!CAPABILITIES.includes(envelope.capability)) {
    throw new ProtocolError('UNKNOWN_CAPABILITY', `Unknown capability: ${envelope.capability}`);
  }
  const timestampMs = Date.parse(envelope.timestamp);
  if (!Number.isFinite(timestampMs)) {
    throw new ProtocolError('INVALID_TIMESTAMP', 'timestamp must be RFC3339-compatible');
  }
  if (Math.abs(Date.now() - timestampMs) > maxClockSkewMs) {
    throw new ProtocolError('STALE_TIMESTAMP', 'Request timestamp is outside the allowed clock skew');
  }
  if (typeof envelope.nonce !== 'string' || envelope.nonce.length < 12) {
    throw new ProtocolError('INVALID_NONCE', 'nonce must be at least 12 characters');
  }
  return { ok: true };
}

function createResponseEnvelope(input) {
  return {
    protocol: PROTOCOL_VERSION,
    request_id: input.request_id,
    status: input.status,
    started_at: input.started_at,
    finished_at: input.finished_at,
    result: input.result ?? null,
    error: input.error ?? null,
    audit_id: input.audit_id,
  };
}

module.exports = {
  createRequestEnvelope,
  createResponseEnvelope,
  validateRequestEnvelope,
};
```

- [ ] **Step 6: Run tests and verify GREEN**

Run:

```bash
npm test -- --test-name-pattern="protocol|timestamp|response"
```

Expected: all tests in `protocol.test.js` pass.

- [ ] **Step 7: Commit**

```bash
git add nervous-link/package.json nervous-link/protocol nervous-link/tests/protocol.test.js
git commit -m "feat(nervous-link): add versioned protocol envelope"
```

---

## Task 2: Default-deny capability policy and path containment

**Files:**
- Create: `nervous-link/pc-agent/capabilities.js`
- Create: `nervous-link/pc-agent/policy.js`
- Create: `nervous-link/config/policy.example.json`
- Test: `nervous-link/tests/policy.test.js`

**Interfaces:**
- Produces `ACTION_CAPABILITY` mapping.
- Produces `loadPolicy(path)`, `authorizeAction(policy, request)`, `assertPathAllowed(policy, capability, candidatePath)`.
- Consumed by command/file/process execution and the agent dispatcher.

- [ ] **Step 1: Write the failing policy tests**

Create `nervous-link/tests/policy.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { authorizeAction, assertPathAllowed } = require('../pc-agent/policy');

const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-policy-'));
const policy = {
  default: 'deny',
  capabilities: {
    'system.read': true,
    'file.read': true,
    'file.write': false,
    'command.execute.safe': true,
  },
  roots: {
    'file.read': [tempRoot],
    'file.write': [],
  },
  commands: {
    safe: ['node'],
    blocked_patterns: ['diskpart', 'format'],
  },
};

test('default deny rejects unknown capability', () => {
  assert.equal(authorizeAction(policy, { capability: 'git.write' }).allowed, false);
});

test('explicit capability allow succeeds', () => {
  assert.equal(authorizeAction(policy, { capability: 'system.read' }).allowed, true);
});

test('allows path inside approved root', () => {
  const target = path.join(tempRoot, 'hello.txt');
  assert.equal(assertPathAllowed(policy, 'file.read', target), path.resolve(target));
});

test('rejects traversal outside approved root', () => {
  const target = path.resolve(tempRoot, '..', 'outside.txt');
  assert.throws(() => assertPathAllowed(policy, 'file.read', target), /outside approved roots/);
});
```

- [ ] **Step 2: Run policy tests and verify RED**

```bash
node --test tests/policy.test.js
```

Expected: FAIL because policy module does not exist.

- [ ] **Step 3: Implement action-to-capability mapping**

Create `nervous-link/pc-agent/capabilities.js`:

```js
const ACTION_CAPABILITY = Object.freeze({
  ping: 'system.read',
  heartbeat: 'system.read',
  device_info: 'system.read',
  list_processes: 'process.list',
  list_directory: 'file.read',
  read_file: 'file.read',
  audit_log: 'system.read',
  write_file: 'file.write',
  run_command: 'command.execute.safe',
  kill_process: 'process.kill',
  kill_switch: 'emergency.kill',
});

module.exports = { ACTION_CAPABILITY };
```

- [ ] **Step 4: Implement the policy engine**

Create `nervous-link/pc-agent/policy.js`:

```js
const fs = require('node:fs');
const path = require('node:path');
const { ACTION_CAPABILITY } = require('./capabilities');

function loadPolicy(policyPath) {
  return JSON.parse(fs.readFileSync(policyPath, 'utf8'));
}

function authorizeAction(policy, request) {
  const expected = ACTION_CAPABILITY[request.action] ?? request.capability;
  if (expected !== request.capability) {
    return { allowed: false, reason: 'CAPABILITY_ACTION_MISMATCH' };
  }
  const allowed = policy.capabilities?.[request.capability] === true;
  return { allowed, reason: allowed ? null : 'DEFAULT_DENY' };
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function assertPathAllowed(policy, capability, candidatePath) {
  const candidate = path.resolve(candidatePath);
  const roots = (policy.roots?.[capability] ?? []).map(root => path.resolve(root));
  if (!roots.some(root => isWithin(root, candidate))) {
    throw new Error(`Path is outside approved roots for ${capability}`);
  }
  return candidate;
}

module.exports = { loadPolicy, authorizeAction, assertPathAllowed, isWithin };
```

- [ ] **Step 5: Create the safe example policy**

Create `nervous-link/config/policy.example.json`:

```json
{
  "default": "deny",
  "capabilities": {
    "system.read": true,
    "process.list": true,
    "process.kill": false,
    "file.read": true,
    "file.write": true,
    "command.execute.safe": true,
    "emergency.kill": true
  },
  "roots": {
    "file.read": [
      "C:/Users/ASIER/OneDrive/Desktop/KAI"
    ],
    "file.write": [
      "C:/Users/ASIER/OneDrive/Desktop/KAI/_KAI_BRIDGE"
    ]
  },
  "commands": {
    "safe": ["python", "node", "git", "adb", "docker", "code", "codex"],
    "blocked_patterns": ["diskpart", "format", "cipher /w", "remove-item -recurse c:/"]
  },
  "limits": {
    "max_command_ms": 30000,
    "max_output_bytes": 1048576,
    "max_read_bytes": 10485760,
    "max_write_bytes": 10485760
  }
}
```

- [ ] **Step 6: Add symlink/junction escape test on supported platforms**

Append to `policy.test.js`:

```js
test('rejects symlink escape when symlink creation is available', (t) => {
  const inside = path.join(tempRoot, 'link');
  const outsideRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-outside-'));
  try {
    fs.symlinkSync(outsideRoot, inside, 'junction');
  } catch (error) {
    t.skip(`symlink/junction creation unavailable: ${error.code}`);
    return;
  }
  const resolved = fs.realpathSync(inside);
  assert.throws(() => assertPathAllowed(policy, 'file.read', resolved), /outside approved roots/);
});
```

- [ ] **Step 7: Run tests and verify GREEN**

```bash
node --test tests/policy.test.js
```

Expected: all mandatory tests pass; symlink test may be explicitly skipped only when the OS refuses test fixture creation.

- [ ] **Step 8: Commit**

```bash
git add nervous-link/pc-agent/capabilities.js nervous-link/pc-agent/policy.js nervous-link/config/policy.example.json nervous-link/tests/policy.test.js
git commit -m "feat(nervous-link): add default deny policy engine"
```

---

## Task 3: Bounded command execution, file operations and process operations

**Files:**
- Create: `nervous-link/pc-agent/commandRunner.js`
- Create: `nervous-link/pc-agent/fileOps.js`
- Create: `nervous-link/pc-agent/processOps.js`
- Test: `nervous-link/tests/commandRunner.test.js`
- Test: `nervous-link/tests/fileOps.test.js`

**Interfaces:**
- Produces `runCommand({ executable, args, cwd, timeout_ms }, policy)`.
- Produces `listDirectory`, `readFile`, `writeFileAtomic`.
- Produces `listProcesses`, `killProcess`.

- [ ] **Step 1: Write failing command-runner tests**

Create `nervous-link/tests/commandRunner.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const { runCommand } = require('../pc-agent/commandRunner');

const policy = {
  commands: { safe: ['node'], blocked_patterns: ['diskpart'] },
  limits: { max_command_ms: 500, max_output_bytes: 64 },
};

test('executes an allowlisted executable with argv', async () => {
  const result = await runCommand({ executable: 'node', args: ['-e', 'console.log("ok")'], timeout_ms: 500 }, policy);
  assert.equal(result.exit_code, 0);
  assert.match(result.stdout, /ok/);
});

test('rejects non-allowlisted executable', async () => {
  await assert.rejects(
    () => runCommand({ executable: 'definitely-not-allowed', args: [] }, policy),
    /not allowlisted/
  );
});

test('times out long running command', async () => {
  await assert.rejects(
    () => runCommand({ executable: 'node', args: ['-e', 'setTimeout(()=>{}, 5000)'], timeout_ms: 50 }, policy),
    /timed out/
  );
});

test('truncates oversized output', async () => {
  const result = await runCommand({ executable: 'node', args: ['-e', 'console.log("x".repeat(1000))'] }, policy);
  assert.equal(result.truncated, true);
  assert.ok(Buffer.byteLength(result.stdout) <= 64);
});
```

- [ ] **Step 2: Write failing file-operation tests**

Create `nervous-link/tests/fileOps.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { readFile, writeFileAtomic, listDirectory } = require('../pc-agent/fileOps');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-files-'));
const policy = {
  roots: { 'file.read': [root], 'file.write': [root] },
  limits: { max_read_bytes: 1024, max_write_bytes: 1024 },
};

test('writes atomically and reads text with sha256', async () => {
  const target = path.join(root, 'hello.txt');
  await writeFileAtomic({ path: target, text: 'hola' }, policy);
  const result = await readFile({ path: target, encoding: 'utf8', sha256: true }, policy);
  assert.equal(result.text, 'hola');
  assert.equal(result.sha256.length, 64);
});

test('lists directory entries', async () => {
  const result = await listDirectory({ path: root }, policy);
  assert.ok(result.entries.some(entry => entry.name === 'hello.txt'));
});
```

- [ ] **Step 3: Run tests and verify RED**

```bash
node --test tests/commandRunner.test.js tests/fileOps.test.js
```

Expected: FAIL because modules do not exist.

- [ ] **Step 4: Implement bounded command execution**

Create `nervous-link/pc-agent/commandRunner.js`:

```js
const { spawn } = require('node:child_process');

function truncateUtf8(text, maxBytes) {
  const buffer = Buffer.from(text, 'utf8');
  return buffer.length <= maxBytes ? { text, truncated: false } : {
    text: buffer.subarray(0, maxBytes).toString('utf8'),
    truncated: true,
  };
}

function runCommand(input, policy) {
  const allowed = new Set(policy.commands?.safe ?? []);
  if (!allowed.has(input.executable)) {
    return Promise.reject(new Error(`Executable is not allowlisted: ${input.executable}`));
  }
  const args = Array.isArray(input.args) ? input.args.map(String) : [];
  const joined = `${input.executable} ${args.join(' ')}`.toLowerCase();
  for (const pattern of policy.commands?.blocked_patterns ?? []) {
    if (joined.includes(pattern.toLowerCase())) {
      return Promise.reject(new Error(`Command matches blocked pattern: ${pattern}`));
    }
  }
  const timeoutMs = Math.min(input.timeout_ms ?? policy.limits?.max_command_ms ?? 30000, policy.limits?.max_command_ms ?? 30000);
  const maxOutput = policy.limits?.max_output_bytes ?? 1048576;

  return new Promise((resolve, reject) => {
    const child = spawn(input.executable, args, {
      cwd: input.cwd,
      shell: false,
      windowsHide: true,
      env: process.env,
    });
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error(`Command timed out after ${timeoutMs} ms`));
    }, timeoutMs);
    child.stdout.on('data', chunk => { stdout += chunk.toString('utf8'); });
    child.stderr.on('data', chunk => { stderr += chunk.toString('utf8'); });
    child.on('error', error => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', code => {
      clearTimeout(timer);
      const out = truncateUtf8(stdout, maxOutput);
      const err = truncateUtf8(stderr, maxOutput);
      resolve({
        exit_code: code,
        stdout: out.text,
        stderr: err.text,
        truncated: out.truncated || err.truncated,
      });
    });
  });
}

module.exports = { runCommand, truncateUtf8 };
```

- [ ] **Step 5: Implement safe file operations**

Create `nervous-link/pc-agent/fileOps.js`:

```js
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { assertPathAllowed } = require('./policy');

async function listDirectory(input, policy) {
  const target = assertPathAllowed(policy, 'file.read', input.path);
  const entries = await fs.readdir(target, { withFileTypes: true });
  return {
    path: target,
    entries: entries.map(entry => ({
      name: entry.name,
      type: entry.isDirectory() ? 'directory' : entry.isFile() ? 'file' : 'other',
    })),
  };
}

async function readFile(input, policy) {
  const target = assertPathAllowed(policy, 'file.read', input.path);
  const stat = await fs.stat(target);
  const max = policy.limits?.max_read_bytes ?? 10485760;
  if (stat.size > max) throw new Error(`File exceeds max_read_bytes: ${stat.size} > ${max}`);
  const bytes = await fs.readFile(target);
  const result = { path: target, bytes: bytes.length };
  if (input.encoding === 'base64') result.base64 = bytes.toString('base64');
  else result.text = bytes.toString(input.encoding ?? 'utf8');
  if (input.sha256 === true) result.sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  return result;
}

async function writeFileAtomic(input, policy) {
  const target = assertPathAllowed(policy, 'file.write', input.path);
  const bytes = input.base64 ? Buffer.from(input.base64, 'base64') : Buffer.from(input.text ?? '', 'utf8');
  const max = policy.limits?.max_write_bytes ?? 10485760;
  if (bytes.length > max) throw new Error(`Write exceeds max_write_bytes: ${bytes.length} > ${max}`);
  await fs.mkdir(path.dirname(target), { recursive: true });
  const temp = `${target}.kai-tmp-${process.pid}-${Date.now()}`;
  await fs.writeFile(temp, bytes, { flag: 'wx' });
  await fs.rename(temp, target);
  return { path: target, bytes: bytes.length };
}

module.exports = { listDirectory, readFile, writeFileAtomic };
```

- [ ] **Step 6: Implement process operations**

Create `nervous-link/pc-agent/processOps.js`:

```js
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const execFileAsync = promisify(execFile);

async function listProcesses() {
  if (process.platform === 'win32') {
    const { stdout } = await execFileAsync('powershell.exe', [
      '-NoProfile', '-NonInteractive', '-Command',
      'Get-Process | Select-Object Id,ProcessName,CPU,WorkingSet64 | ConvertTo-Json -Compress'
    ], { windowsHide: true, maxBuffer: 4 * 1024 * 1024 });
    const parsed = JSON.parse(stdout || '[]');
    return Array.isArray(parsed) ? parsed : [parsed];
  }
  const { stdout } = await execFileAsync('ps', ['-eo', 'pid,comm']);
  return stdout.trim().split('\n').slice(1).map(line => line.trim().split(/\s+/, 2)).map(([pid, name]) => ({ Id: Number(pid), ProcessName: name }));
}

function killProcess(pid) {
  if (!Number.isInteger(pid) || pid <= 0) throw new Error('pid must be a positive integer');
  process.kill(pid, 'SIGTERM');
  return { pid, signal: 'SIGTERM' };
}

module.exports = { listProcesses, killProcess };
```

- [ ] **Step 7: Run tests and verify GREEN**

```bash
node --test tests/commandRunner.test.js tests/fileOps.test.js
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add nervous-link/pc-agent/commandRunner.js nervous-link/pc-agent/fileOps.js nervous-link/pc-agent/processOps.js nervous-link/tests/commandRunner.test.js nervous-link/tests/fileOps.test.js
git commit -m "feat(nervous-link): add bounded local operations"
```

---

## Task 4: Append-only audit with secret redaction and kill switch

**Files:**
- Create: `nervous-link/pc-agent/audit.js`
- Create: `nervous-link/pc-agent/killSwitch.js`
- Test: `nervous-link/tests/audit.test.js`
- Test: `nervous-link/tests/killSwitch.test.js`

**Interfaces:**
- Produces `AuditLog` class with `append(entry)` and `read(limit)`.
- Produces `KillSwitch` class with `trigger(reason)`, `isTriggered()`, `assertActive()`.

- [ ] **Step 1: Write failing audit and kill-switch tests**

Create `nervous-link/tests/audit.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { AuditLog } = require('../pc-agent/audit');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-audit-'));
const file = path.join(dir, 'audit.jsonl');

test('redacts secret-like keys before append', async () => {
  const audit = new AuditLog(file);
  await audit.append({ action: 'test', params: { token: 'abc', safe: 'ok' } });
  const rows = await audit.read(10);
  assert.equal(rows[0].params.token, '<REDACTED>');
  assert.equal(rows[0].params.safe, 'ok');
});
```

Create `nervous-link/tests/killSwitch.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { KillSwitch } = require('../pc-agent/killSwitch');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-kill-'));
const flag = path.join(dir, 'STOP');

test('trigger persists stop state and assertActive rejects', async () => {
  const kill = new KillSwitch(flag);
  await kill.trigger('test');
  assert.equal(await kill.isTriggered(), true);
  await assert.rejects(() => kill.assertActive(), /kill switch/i);
});
```

- [ ] **Step 2: Run tests and verify RED**

```bash
node --test tests/audit.test.js tests/killSwitch.test.js
```

Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement append-only audit with recursive redaction**

Create `nervous-link/pc-agent/audit.js`:

```js
const fs = require('node:fs/promises');
const path = require('node:path');

const SECRET_KEY = /(token|secret|password|passwd|api[_-]?key|cookie|credential|private[_-]?key|authorization)/i;

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).map(([key, child]) => [
    key,
    SECRET_KEY.test(key) ? '<REDACTED>' : redact(child),
  ]));
}

class AuditLog {
  constructor(filePath) {
    this.filePath = filePath;
  }

  async append(entry) {
    await fs.mkdir(path.dirname(this.filePath), { recursive: true });
    const row = { timestamp: new Date().toISOString(), ...redact(entry) };
    await fs.appendFile(this.filePath, `${JSON.stringify(row)}\n`, 'utf8');
    return row;
  }

  async read(limit = 100) {
    try {
      const text = await fs.readFile(this.filePath, 'utf8');
      return text.trim().split('\n').filter(Boolean).slice(-limit).map(line => JSON.parse(line));
    } catch (error) {
      if (error.code === 'ENOENT') return [];
      throw error;
    }
  }
}

module.exports = { AuditLog, redact };
```

- [ ] **Step 4: Implement independent local kill switch**

Create `nervous-link/pc-agent/killSwitch.js`:

```js
const fs = require('node:fs/promises');
const path = require('node:path');

class KillSwitch {
  constructor(flagPath) {
    this.flagPath = flagPath;
  }

  async isTriggered() {
    try {
      await fs.access(this.flagPath);
      return true;
    } catch (error) {
      if (error.code === 'ENOENT') return false;
      throw error;
    }
  }

  async trigger(reason = 'manual') {
    await fs.mkdir(path.dirname(this.flagPath), { recursive: true });
    await fs.writeFile(this.flagPath, JSON.stringify({ reason, timestamp: new Date().toISOString() }), 'utf8');
  }

  async assertActive() {
    if (await this.isTriggered()) {
      throw new Error('Kai Nervous Link kill switch is triggered');
    }
  }
}

module.exports = { KillSwitch };
```

- [ ] **Step 5: Run tests and verify GREEN**

```bash
node --test tests/audit.test.js tests/killSwitch.test.js
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add nervous-link/pc-agent/audit.js nervous-link/pc-agent/killSwitch.js nervous-link/tests/audit.test.js nervous-link/tests/killSwitch.test.js
git commit -m "feat(nervous-link): add audit and kill switch"
```

---

## Task 5: Relay auth, replay protection, pairing and session registry

**Files:**
- Create: `nervous-link/relay/auth.js`
- Create: `nervous-link/relay/replayGuard.js`
- Create: `nervous-link/relay/sessionRegistry.js`
- Create: `nervous-link/relay/audit.js`
- Create: `nervous-link/relay/server.js`
- Test: `nervous-link/tests/pairing.test.js`

**Interfaces:**
- `createHmacProof(secret, payload)` and `verifyHmacProof(secret, payload, proof)`.
- `ReplayGuard.checkAndRemember(nonce, timestamp)`.
- `SessionRegistry.announcePairing`, `approvePairing`, `registerAgentSocket`, `getAgentSocket`.
- `createRelayServer(options)` returns `{ app, httpServer, io, start, stop, registry }`.

- [ ] **Step 1: Write failing pairing and replay tests**

Create `nervous-link/tests/pairing.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const { ReplayGuard } = require('../relay/replayGuard');
const { SessionRegistry } = require('../relay/sessionRegistry');


test('replay guard rejects same nonce twice', () => {
  const guard = new ReplayGuard({ ttlMs: 60_000 });
  guard.checkAndRemember('nonce-abcdefghijkl', Date.now());
  assert.throws(() => guard.checkAndRemember('nonce-abcdefghijkl', Date.now()), /replay/i);
});

test('pairing requires correct short-lived code and owner approval', () => {
  const registry = new SessionRegistry();
  const announced = registry.announcePairing({
    device_id: 'pc-asier-main',
    code: 'A7K9M2Q4',
    public_identity: 'ed25519-public-key-placeholder',
    ttl_ms: 60_000,
  });
  assert.throws(() => registry.approvePairing({ pairing_id: announced.pairing_id, code: 'WRONG' }), /invalid pairing code/i);
  const approved = registry.approvePairing({ pairing_id: announced.pairing_id, code: 'A7K9M2Q4' });
  assert.equal(approved.device_id, 'pc-asier-main');
  assert.equal(typeof approved.device_token, 'string');
  assert.ok(approved.device_token.length >= 32);
});
```

- [ ] **Step 2: Run tests and verify RED**

```bash
node --test tests/pairing.test.js
```

Expected: FAIL because relay modules do not exist.

- [ ] **Step 3: Implement HMAC helpers**

Create `nervous-link/relay/auth.js`:

```js
const crypto = require('node:crypto');

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function createHmacProof(secret, payload) {
  return crypto.createHmac('sha256', secret).update(stableStringify(payload)).digest('base64url');
}

function verifyHmacProof(secret, payload, proof) {
  const expected = Buffer.from(createHmacProof(secret, payload));
  const actual = Buffer.from(String(proof ?? ''));
  return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
}

module.exports = { stableStringify, createHmacProof, verifyHmacProof };
```

- [ ] **Step 4: Implement replay guard**

Create `nervous-link/relay/replayGuard.js`:

```js
class ReplayGuard {
  constructor({ ttlMs = 120_000 } = {}) {
    this.ttlMs = ttlMs;
    this.nonces = new Map();
  }

  checkAndRemember(nonce, timestampMs = Date.now()) {
    const now = Date.now();
    for (const [value, seenAt] of this.nonces) {
      if (now - seenAt > this.ttlMs) this.nonces.delete(value);
    }
    if (this.nonces.has(nonce)) throw new Error(`Replay detected for nonce: ${nonce}`);
    if (Math.abs(now - timestampMs) > this.ttlMs) throw new Error('Timestamp outside replay window');
    this.nonces.set(nonce, now);
  }
}

module.exports = { ReplayGuard };
```

- [ ] **Step 5: Implement session and pairing registry**

Create `nervous-link/relay/sessionRegistry.js`:

```js
const crypto = require('node:crypto');

class SessionRegistry {
  constructor() {
    this.pairings = new Map();
    this.devices = new Map();
    this.agentSockets = new Map();
  }

  announcePairing({ device_id, code, public_identity, ttl_ms = 10 * 60_000 }) {
    const pairing_id = crypto.randomUUID();
    const row = {
      pairing_id,
      device_id,
      code_hash: crypto.createHash('sha256').update(code).digest('hex'),
      public_identity,
      expires_at: Date.now() + ttl_ms,
    };
    this.pairings.set(pairing_id, row);
    return { pairing_id, device_id, expires_at: row.expires_at };
  }

  approvePairing({ pairing_id, code }) {
    const row = this.pairings.get(pairing_id);
    if (!row || row.expires_at < Date.now()) throw new Error('Pairing request missing or expired');
    const codeHash = crypto.createHash('sha256').update(code).digest('hex');
    if (codeHash !== row.code_hash) throw new Error('Invalid pairing code');
    const device_token = crypto.randomBytes(32).toString('base64url');
    const device = {
      device_id: row.device_id,
      public_identity: row.public_identity,
      device_token,
      paired_at: new Date().toISOString(),
    };
    this.devices.set(device.device_id, device);
    this.pairings.delete(pairing_id);
    return { ...device };
  }

  getDevice(device_id) {
    return this.devices.get(device_id) ?? null;
  }

  registerAgentSocket(device_id, socket) {
    this.agentSockets.set(device_id, socket);
  }

  removeAgentSocket(device_id, socketId) {
    const current = this.agentSockets.get(device_id);
    if (current?.id === socketId) this.agentSockets.delete(device_id);
  }

  getAgentSocket(device_id) {
    return this.agentSockets.get(device_id) ?? null;
  }
}

module.exports = { SessionRegistry };
```

- [ ] **Step 6: Implement relay audit and server**

Create `nervous-link/relay/audit.js`:

```js
const { AuditLog } = require('../pc-agent/audit');
module.exports = { RelayAuditLog: AuditLog };
```

Create `nervous-link/relay/server.js`:

```js
const http = require('node:http');
const express = require('express');
const { Server } = require('socket.io');
const { SessionRegistry } = require('./sessionRegistry');
const { ReplayGuard } = require('./replayGuard');
const { verifyHmacProof } = require('./auth');

function createRelayServer(options = {}) {
  const app = express();
  app.use(express.json({ limit: '1mb' }));
  const httpServer = http.createServer(app);
  const io = new Server(httpServer, { cors: { origin: false } });
  const registry = options.registry ?? new SessionRegistry();
  const replayGuard = options.replayGuard ?? new ReplayGuard();
  const ownerToken = options.ownerToken ?? process.env.KAI_NERVOUS_LINK_OWNER_TOKEN;
  if (!ownerToken) throw new Error('KAI_NERVOUS_LINK_OWNER_TOKEN is required');

  app.get('/health', (_req, res) => res.json({ ok: true, protocol: 'kai-nervous-link/0.1' }));
  app.post('/pair/approve', (req, res) => {
    if (req.get('authorization') !== `Bearer ${ownerToken}`) return res.status(401).json({ error: 'UNAUTHORIZED' });
    try {
      res.json(registry.approvePairing(req.body));
    } catch (error) {
      res.status(400).json({ error: error.message });
    }
  });

  io.on('connection', socket => {
    socket.on('agent:announce-pairing', payload => {
      try { socket.emit('agent:pairing-announced', registry.announcePairing(payload)); }
      catch (error) { socket.emit('agent:error', { error: error.message }); }
    });

    socket.on('agent:authenticate', payload => {
      const device = registry.getDevice(payload.device_id);
      if (!device || !verifyHmacProof(device.device_token, payload.proof_payload, payload.proof)) {
        socket.emit('agent:error', { error: 'AUTHENTICATION_FAILED' });
        return;
      }
      socket.data.device_id = payload.device_id;
      registry.registerAgentSocket(payload.device_id, socket);
      socket.emit('agent:authenticated', { device_id: payload.device_id });
    });

    socket.on('client:request', envelope => {
      try {
        if (envelope.owner_token !== ownerToken) throw new Error('UNAUTHORIZED');
        replayGuard.checkAndRemember(envelope.nonce, Date.parse(envelope.timestamp));
        const agent = registry.getAgentSocket(envelope.device_id);
        if (!agent) throw new Error('DEVICE_OFFLINE');
        agent.emit('agent:request', envelope);
      } catch (error) {
        socket.emit('client:response', { request_id: envelope.request_id, status: 'error', error: error.message });
      }
    });

    socket.on('agent:response', response => io.emit(`client:response:${response.request_id}`, response));
    socket.on('disconnect', () => {
      if (socket.data.device_id) registry.removeAgentSocket(socket.data.device_id, socket.id);
    });
  });

  return {
    app,
    httpServer,
    io,
    registry,
    start(port = 0) {
      return new Promise(resolve => httpServer.listen(port, '127.0.0.1', () => resolve(httpServer.address())));
    },
    stop() {
      return new Promise(resolve => io.close(() => httpServer.close(resolve)));
    },
  };
}

module.exports = { createRelayServer };
```

- [ ] **Step 7: Run pairing tests and verify GREEN**

```bash
node --test tests/pairing.test.js
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add nervous-link/relay nervous-link/tests/pairing.test.js
git commit -m "feat(nervous-link): add relay pairing and replay protection"
```

---

## Task 6: PC agent dispatcher, heartbeat, reconnect and persistent credential storage

**Files:**
- Create: `nervous-link/pc-agent/heartbeat.js`
- Create: `nervous-link/pc-agent/agent.js`
- Create: `nervous-link/config/agent.example.json`
- Create: `nervous-link/scripts/start-agent.js`
- Test: `nervous-link/tests/relay-agent.integration.test.js`

**Interfaces:**
- `createPcAgent(options)` returns `{ start, stop, dispatch, state }`.
- `dispatch(envelope)` performs protocol validation, kill-switch check, policy enforcement, action execution and audit.

- [ ] **Step 1: Write failing relay-agent integration test**

Create `nervous-link/tests/relay-agent.integration.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { io: createClient } = require('socket.io-client');
const { createRelayServer } = require('../relay/server');
const { createPcAgent } = require('../pc-agent/agent');

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-link-int-'));

test('agent connects outward and answers device_info after pre-pairing', async (t) => {
  const relay = createRelayServer({ ownerToken: 'owner-test-token' });
  const address = await relay.start(0);
  t.after(() => relay.stop());

  relay.registry.devices.set('pc-test', {
    device_id: 'pc-test',
    public_identity: 'test',
    device_token: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
  });

  const policy = {
    capabilities: { 'system.read': true },
    roots: {}, commands: { safe: [], blocked_patterns: [] }, limits: {},
  };

  const agent = createPcAgent({
    relayUrl: `http://127.0.0.1:${address.port}`,
    deviceId: 'pc-test',
    deviceToken: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
    policy,
    auditPath: path.join(temp, 'audit.jsonl'),
    killSwitchPath: path.join(temp, 'STOP'),
    reconnectBaseMs: 20,
  });
  await agent.start();
  t.after(() => agent.stop());

  await new Promise(resolve => setTimeout(resolve, 100));
  assert.equal(agent.state.connected, true);
  assert.equal(agent.state.authenticated, true);
});
```

- [ ] **Step 2: Run integration test and verify RED**

```bash
node --test tests/relay-agent.integration.test.js
```

Expected: FAIL because `pc-agent/agent.js` does not exist.

- [ ] **Step 3: Implement heartbeat helper**

Create `nervous-link/pc-agent/heartbeat.js`:

```js
function startHeartbeat({ intervalMs = 15000, send }) {
  const timer = setInterval(() => send({
    action: 'heartbeat',
    timestamp: new Date().toISOString(),
    pid: process.pid,
  }), intervalMs);
  timer.unref?.();
  return () => clearInterval(timer);
}

module.exports = { startHeartbeat };
```

- [ ] **Step 4: Implement the PC agent**

Create `nervous-link/pc-agent/agent.js`:

```js
const os = require('node:os');
const crypto = require('node:crypto');
const { io } = require('socket.io-client');
const { validateRequestEnvelope, createResponseEnvelope } = require('../protocol/envelope');
const { createHmacProof } = require('../relay/auth');
const { authorizeAction } = require('./policy');
const { runCommand } = require('./commandRunner');
const { listDirectory, readFile, writeFileAtomic } = require('./fileOps');
const { listProcesses, killProcess } = require('./processOps');
const { AuditLog } = require('./audit');
const { KillSwitch } = require('./killSwitch');
const { startHeartbeat } = require('./heartbeat');

function createPcAgent(options) {
  const state = { connected: false, authenticated: false, stopped: false };
  const audit = new AuditLog(options.auditPath);
  const killSwitch = new KillSwitch(options.killSwitchPath);
  let socket = null;
  let stopHeartbeat = null;

  async function dispatch(envelope) {
    const startedAt = new Date().toISOString();
    const auditId = crypto.randomUUID();
    let status = 'ok';
    let result = null;
    let error = null;
    try {
      validateRequestEnvelope(envelope);
      await killSwitch.assertActive();
      const authz = authorizeAction(options.policy, envelope);
      if (!authz.allowed) throw new Error(authz.reason);
      switch (envelope.action) {
        case 'ping': result = { pong: true }; break;
        case 'heartbeat': result = { alive: true }; break;
        case 'device_info': result = { hostname: os.hostname(), platform: process.platform, arch: process.arch, node: process.version, pid: process.pid }; break;
        case 'list_processes': result = await listProcesses(); break;
        case 'list_directory': result = await listDirectory(envelope.params, options.policy); break;
        case 'read_file': result = await readFile(envelope.params, options.policy); break;
        case 'write_file': result = await writeFileAtomic(envelope.params, options.policy); break;
        case 'run_command': result = await runCommand(envelope.params, options.policy); break;
        case 'kill_process': result = killProcess(envelope.params.pid); break;
        case 'audit_log': result = await audit.read(envelope.params.limit ?? 100); break;
        case 'kill_switch': await killSwitch.trigger('remote_authenticated'); state.stopped = true; result = { stopped: true }; break;
        default: throw new Error(`Unhandled action: ${envelope.action}`);
      }
    } catch (caught) {
      status = 'error';
      error = { code: caught.code ?? 'ACTION_FAILED', message: caught.message };
    }
    const finishedAt = new Date().toISOString();
    await audit.append({
      audit_id: auditId,
      request_id: envelope.request_id,
      session_id: envelope.session_id,
      device_id: options.deviceId,
      actor_id: envelope.actor_id ?? 'unknown',
      action: envelope.action,
      capability: envelope.capability,
      resource: envelope.params?.path ?? envelope.params?.executable ?? null,
      timestamp_start: startedAt,
      timestamp_end: finishedAt,
      status,
      error_code: error?.code ?? null,
    });
    return createResponseEnvelope({
      request_id: envelope.request_id,
      status,
      started_at: startedAt,
      finished_at: finishedAt,
      result,
      error,
      audit_id: auditId,
    });
  }

  async function start() {
    state.stopped = false;
    socket = io(options.relayUrl, { reconnection: true, reconnectionDelay: options.reconnectBaseMs ?? 500, reconnectionDelayMax: 30000 });
    socket.on('connect', () => {
      state.connected = true;
      const proofPayload = { device_id: options.deviceId, socket_id: socket.id };
      socket.emit('agent:authenticate', {
        device_id: options.deviceId,
        proof_payload: proofPayload,
        proof: createHmacProof(options.deviceToken, proofPayload),
      });
    });
    socket.on('disconnect', () => { state.connected = false; state.authenticated = false; });
    socket.on('agent:authenticated', () => {
      state.authenticated = true;
      stopHeartbeat?.();
      stopHeartbeat = startHeartbeat({ send: payload => socket.emit('agent:heartbeat', payload) });
    });
    socket.on('agent:request', async envelope => {
      const response = await dispatch(envelope);
      socket.emit('agent:response', response);
      if (state.stopped) await stop();
    });
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Agent connection timeout')), 5000);
      socket.once('connect', () => { clearTimeout(timer); resolve(); });
      socket.once('connect_error', error => { clearTimeout(timer); reject(error); });
    });
  }

  async function stop() {
    stopHeartbeat?.();
    socket?.disconnect();
    state.connected = false;
    state.authenticated = false;
  }

  return { start, stop, dispatch, state };
}

module.exports = { createPcAgent };
```

- [ ] **Step 5: Create example agent config and startup script**

Create `nervous-link/config/agent.example.json`:

```json
{
  "device_id": "pc-asier-main",
  "relay_url": "http://127.0.0.1:8787",
  "policy_path": "./config/policy.local.json",
  "credential_path": "%USERPROFILE%/.kai/nervous-link/device.json",
  "audit_path": "%USERPROFILE%/.kai/nervous-link/audit.jsonl",
  "kill_switch_path": "%USERPROFILE%/.kai/nervous-link/STOP"
}
```

Create `nervous-link/scripts/start-agent.js`:

```js
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { createPcAgent } = require('../pc-agent/agent');
const { loadPolicy } = require('../pc-agent/policy');

function expandHome(value) {
  return value.replace('%USERPROFILE%', os.homedir());
}

const configPath = process.env.KAI_NERVOUS_LINK_AGENT_CONFIG ?? path.join(__dirname, '..', 'config', 'agent.local.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const credentials = JSON.parse(fs.readFileSync(expandHome(config.credential_path), 'utf8'));
const policy = loadPolicy(path.resolve(path.dirname(configPath), config.policy_path));

const agent = createPcAgent({
  relayUrl: config.relay_url,
  deviceId: config.device_id,
  deviceToken: credentials.device_token,
  policy,
  auditPath: expandHome(config.audit_path),
  killSwitchPath: expandHome(config.kill_switch_path),
});

agent.start().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
```

- [ ] **Step 6: Run integration test and verify GREEN**

```bash
node --test tests/relay-agent.integration.test.js
```

Expected: PASS.

- [ ] **Step 7: Add reconnect-after-relay-restart test**

Append to `relay-agent.integration.test.js` a second integration case that:
- starts relay on an ephemeral port;
- starts agent;
- stops relay;
- restarts relay on the same port with the same registry fixture;
- waits up to 5 seconds;
- asserts `agent.state.connected === true` and `agent.state.authenticated === true`.

Use a bounded polling helper in the test:

```js
async function waitFor(predicate, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('Condition not met before timeout');
}
```

- [ ] **Step 8: Re-run integration tests**

```bash
node --test tests/relay-agent.integration.test.js
```

Expected: both connection and reconnect tests pass.

- [ ] **Step 9: Commit**

```bash
git add nervous-link/pc-agent/agent.js nervous-link/pc-agent/heartbeat.js nervous-link/config/agent.example.json nervous-link/scripts/start-agent.js nervous-link/tests/relay-agent.integration.test.js
git commit -m "feat(nervous-link): add outbound PC agent"
```

---

## Task 7: CLI client for pairing and typed remote calls

**Files:**
- Create: `nervous-link/clients/cli/kai-link.js`
- Create: `nervous-link/clients/android/CONTRACT.md`
- Create: `nervous-link/scripts/start-relay.js`
- Modify: `nervous-link/package.json`

**Interfaces:**
- CLI syntax:
  - `node clients/cli/kai-link.js pair --relay URL --pairing-id ID --code CODE`
  - `node clients/cli/kai-link.js call --relay URL --device DEVICE --action device_info --capability system.read --params '{}'`

- [ ] **Step 1: Implement relay startup script**

Create `nervous-link/scripts/start-relay.js`:

```js
const { createRelayServer } = require('../relay/server');

const port = Number(process.env.PORT ?? 8787);
const relay = createRelayServer({ ownerToken: process.env.KAI_NERVOUS_LINK_OWNER_TOKEN });
relay.start(port).then(address => {
  console.log(`KAI Nervous Link relay listening on http://127.0.0.1:${address.port}`);
});
```

- [ ] **Step 2: Implement CLI client**

Create `nervous-link/clients/cli/kai-link.js`:

```js
#!/usr/bin/env node
const crypto = require('node:crypto');
const { io } = require('socket.io-client');
const { createRequestEnvelope } = require('../../protocol/envelope');

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const args = { command };
  for (let index = 0; index < rest.length; index += 2) {
    args[rest[index].replace(/^--/, '')] = rest[index + 1];
  }
  return args;
}

async function pair(args) {
  const response = await fetch(`${args.relay}/pair/approve`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${process.env.KAI_NERVOUS_LINK_OWNER_TOKEN}` },
    body: JSON.stringify({ pairing_id: args['pairing-id'], code: args.code }),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  console.log(JSON.stringify(body, null, 2));
}

async function call(args) {
  const ownerToken = process.env.KAI_NERVOUS_LINK_OWNER_TOKEN;
  if (!ownerToken) throw new Error('KAI_NERVOUS_LINK_OWNER_TOKEN is required');
  const requestId = crypto.randomUUID();
  const envelope = createRequestEnvelope({
    request_id: requestId,
    session_id: crypto.randomUUID(),
    device_id: args.device,
    timestamp: new Date().toISOString(),
    action: args.action,
    params: JSON.parse(args.params ?? '{}'),
    capability: args.capability,
    nonce: crypto.randomBytes(18).toString('base64url'),
    signature: 'relay-owner-token-auth',
    owner_token: ownerToken,
    actor_id: 'asier-cli',
  });
  const socket = io(args.relay);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Relay connect timeout')), 5000);
    socket.once('connect', () => { clearTimeout(timer); resolve(); });
    socket.once('connect_error', reject);
  });
  const response = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Request timeout')), 30000);
    socket.once(`client:response:${requestId}`, payload => { clearTimeout(timer); resolve(payload); });
    socket.emit('client:request', envelope);
  });
  socket.disconnect();
  console.log(JSON.stringify(response, null, 2));
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  if (args.command === 'pair') await pair(args);
  else if (args.command === 'call') await call(args);
  else throw new Error('Usage: kai-link.js pair|call [options]');
})().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
```

- [ ] **Step 3: Document the future Android/MobileNode typed-command contract**

Create `nervous-link/clients/android/CONTRACT.md`:

```markdown
# KAI Nervous Link Android Client Contract

Android/MobileNode must send only typed protocol envelopes from `protocol/envelope.js`.

It must not expose an unrestricted exported broadcast receiver that accepts arbitrary shell text.

Required client responsibilities:

- hold only revocable client credentials;
- require explicit Asier approval for pairing;
- show connected device identity and last heartbeat;
- support typed actions only;
- display audit ID for every response;
- expose a local emergency disconnect action;
- never log raw long-lived credentials;
- preserve Android sandbox boundaries.

The first Android integration target is Kai MobileNode. The v0.1 relay/agent must remain usable without modifying MobileNode.
```

- [ ] **Step 4: Add CLI bin entry to package.json**

Add:

```json
"bin": {
  "kai-link": "clients/cli/kai-link.js"
}
```

- [ ] **Step 5: Run full unit suite**

```bash
npm test
```

Expected: all current unit and integration tests pass.

- [ ] **Step 6: Commit**

```bash
git add nervous-link/clients nervous-link/scripts/start-relay.js nervous-link/package.json
git commit -m "feat(nervous-link): add CLI client and Android contract"
```

---

## Task 8: End-to-end authorised roundtrips and denial tests

**Files:**
- Modify: `nervous-link/tests/relay-agent.integration.test.js`
- Modify: `nervous-link/relay/server.js`
- Modify: `nervous-link/pc-agent/agent.js`

**Interfaces:**
- Proves pair/reconnect/heartbeat.
- Proves authenticated `device_info`.
- Proves allowed `read_file` inside root.
- Proves denied `read_file` outside root.
- Proves allowed `node` command.
- Proves denied executable.

- [ ] **Step 1: Add an integration test helper that submits a typed request**

Add this helper to `relay-agent.integration.test.js`:

```js
const crypto = require('node:crypto');
const { createRequestEnvelope } = require('../protocol/envelope');

async function requestThroughRelay({ relayUrl, ownerToken, deviceId, action, capability, params = {} }) {
  const socket = createClient(relayUrl);
  await new Promise((resolve, reject) => {
    socket.once('connect', resolve);
    socket.once('connect_error', reject);
  });
  const requestId = crypto.randomUUID();
  const envelope = createRequestEnvelope({
    request_id: requestId,
    session_id: crypto.randomUUID(),
    device_id: deviceId,
    timestamp: new Date().toISOString(),
    action,
    params,
    capability,
    nonce: crypto.randomBytes(18).toString('base64url'),
    signature: 'test',
    owner_token: ownerToken,
    actor_id: 'integration-test',
  });
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Timed out waiting for response')), 3000);
    socket.once(`client:response:${requestId}`, response => {
      clearTimeout(timer);
      socket.disconnect();
      resolve(response);
    });
    socket.emit('client:request', envelope);
  });
}
```

- [ ] **Step 2: Add device-info roundtrip test**

```js
test('authenticated device_info roundtrip returns platform identity', async (t) => {
  // Reuse the same isolated relay/agent fixture pattern from the first integration test.
  const response = await requestThroughRelay({
    relayUrl,
    ownerToken: 'owner-test-token',
    deviceId: 'pc-test',
    action: 'device_info',
    capability: 'system.read',
  });
  assert.equal(response.status, 'ok');
  assert.equal(typeof response.result.platform, 'string');
  assert.equal(typeof response.audit_id, 'string');
});
```

- [ ] **Step 3: Add file allow/deny roundtrip tests**

```js
const allowedFile = path.join(temp, 'allowed.txt');
fs.writeFileSync(allowedFile, 'kai-ok', 'utf8');

const allowed = await requestThroughRelay({
  relayUrl,
  ownerToken: 'owner-test-token',
  deviceId: 'pc-test',
  action: 'read_file',
  capability: 'file.read',
  params: { path: allowedFile, encoding: 'utf8', sha256: true },
});
assert.equal(allowed.status, 'ok');
assert.equal(allowed.result.text, 'kai-ok');

const denied = await requestThroughRelay({
  relayUrl,
  ownerToken: 'owner-test-token',
  deviceId: 'pc-test',
  action: 'read_file',
  capability: 'file.read',
  params: { path: path.resolve(temp, '..', 'outside.txt'), encoding: 'utf8' },
});
assert.equal(denied.status, 'error');
```

- [ ] **Step 4: Add safe-command allow/deny roundtrip tests**

```js
const allowedCommand = await requestThroughRelay({
  relayUrl,
  ownerToken: 'owner-test-token',
  deviceId: 'pc-test',
  action: 'run_command',
  capability: 'command.execute.safe',
  params: { executable: 'node', args: ['-e', 'console.log("kai-command-ok")'], timeout_ms: 1000 },
});
assert.equal(allowedCommand.status, 'ok');
assert.match(allowedCommand.result.stdout, /kai-command-ok/);

const deniedCommand = await requestThroughRelay({
  relayUrl,
  ownerToken: 'owner-test-token',
  deviceId: 'pc-test',
  action: 'run_command',
  capability: 'command.execute.safe',
  params: { executable: 'definitely-not-allowed', args: [] },
});
assert.equal(deniedCommand.status, 'error');
```

- [ ] **Step 5: Run integration suite**

```bash
npm run test:integration
```

Expected: pairing, connection, reconnect, device-info, file allow/deny and command allow/deny all pass.

- [ ] **Step 6: Run the complete test suite**

```bash
npm test
```

Expected: zero failures.

- [ ] **Step 7: Commit**

```bash
git add nervous-link/tests/relay-agent.integration.test.js nervous-link/relay/server.js nervous-link/pc-agent/agent.js
git commit -m "test(nervous-link): prove authorised end to end roundtrips"
```

---

## Task 9: Free transport deployment, Windows startup and operator documentation

**Files:**
- Create: `nervous-link/README.md`
- Create: `nervous-link/scripts/install-windows-startup.ps1`
- Create: `nervous-link/config/.gitignore`
- Modify: root `.gitignore` only if needed to protect generated Nervous Link secrets.

**Interfaces:**
- Documents Cloudflare Tunnel primary path.
- Documents Tailscale fallback.
- Preserves Desktop Commander emergency command.
- Installs a user-level Windows Scheduled Task only when explicitly run locally by Asier.

- [ ] **Step 1: Create Windows user-level startup installer**

Create `nervous-link/scripts/install-windows-startup.ps1`:

```powershell
param(
  [Parameter(Mandatory=$true)]
  [string]$NodeExe,
  [Parameter(Mandatory=$true)]
  [string]$AgentScript,
  [Parameter(Mandatory=$true)]
  [string]$WorkingDirectory
)

$ErrorActionPreference = 'Stop'
$taskName = 'KAI Nervous Link PC Agent'
$action = New-ScheduledTaskAction -Execute $NodeExe -Argument ('"' + $AgentScript + '"') -WorkingDirectory $WorkingDirectory
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
Write-Host "Installed user-level task: $taskName"
```

This deliberately uses `RunLevel Limited`; v0.1 must not silently install itself as administrator.

- [ ] **Step 2: Protect local secret/config files**

Create `nervous-link/config/.gitignore`:

```gitignore
agent.local.json
policy.local.json
*.secret.json
```

Also ensure the repository ignores:

```gitignore
nervous-link/.env
nervous-link/data/
nervous-link/config/agent.local.json
nervous-link/config/policy.local.json
```

- [ ] **Step 3: Write operator README**

Create `nervous-link/README.md` with these exact operational sections:

```markdown
# KAI Nervous Link v0.1

KAI Nervous Link is Kai's free-first remote nervous system between Asier's S24 Ultra, cloud relay and Windows PC agent.

## Safety defaults

- default deny;
- no delete action;
- no administrator auto-elevation;
- no public unauthenticated shell;
- explicit allowlisted executables;
- explicit file roots;
- append-only local audit;
- independent local kill switch.

## Emergency bootstrap retained

```bash
npx @wonderwhy-er/desktop-commander@latest remote
```

Use this only as a temporary recovery bridge while Nervous Link is unavailable.

## Local install

```bash
cd nervous-link
npm install
npm test
```

## Start relay locally

```powershell
$env:KAI_NERVOUS_LINK_OWNER_TOKEN = '<set-locally-never-commit>'
npm run relay
```

The relay binds to localhost. Cloudflare Tunnel publishes the local relay through an outbound connection.

## Cloudflare Tunnel primary transport

Use a free Cloudflare Tunnel to publish the local relay without opening inbound router ports. Keep Cloudflare credentials outside Git. The exact tunnel command/config must be generated for Asier's Cloudflare account during deployment and must not be committed with credentials.

## Tailscale fallback

Tailscale Personal can provide private device-to-device recovery. It is a fallback, not the canonical relay protocol.

## Start PC agent

Copy the example policy and config to local ignored files, then set the device credential locally and run:

```bash
npm run agent
```

## Kill switch

The PC agent stops accepting remote actions when its configured STOP file exists. It remains stopped until the flag is removed locally and the agent is explicitly restarted.

## Verification gates

v0.1 is complete only after:

1. all `npm test` tests pass;
2. relay and agent reconnect after relay restart;
3. device info roundtrip works;
4. allowed file read succeeds;
5. outside-root file read is denied;
6. allowlisted command succeeds;
7. non-allowlisted command is denied;
8. audit entries are written and secrets redacted;
9. kill switch stops execution;
10. S24 reaches the relay over mobile data without opening a router port.
```

- [ ] **Step 4: Run full tests**

```bash
npm test
```

Expected: zero failures.

- [ ] **Step 5: Run a secret scan before commit**

Run:

```bash
git diff --cached -- nervous-link | grep -E -i "(api[_-]?key|token|password|secret)\s*[:=]\s*['\"][A-Za-z0-9_-]{12,}" && exit 1 || exit 0
```

Expected: exit 0 with no real credential values.

- [ ] **Step 6: Commit**

```bash
git add nervous-link/README.md nervous-link/scripts/install-windows-startup.ps1 nervous-link/config/.gitignore .gitignore
git commit -m "docs(nervous-link): add free transport and Windows operator guide"
```

---

## Task 10: Final verification, branch report and pull request

**Files:**
- Create: `nervous-link/VERIFICATION.md`
- No production source changes unless verification exposes a defect.

- [ ] **Step 1: Install clean dependencies**

```bash
cd nervous-link
rm -rf node_modules
npm ci
```

On Windows PowerShell use:

```powershell
Remove-Item node_modules -Recurse -Force -ErrorAction SilentlyContinue
npm ci
```

Expected: install completes without modifying source files.

- [ ] **Step 2: Run complete automated suite**

```bash
npm test
```

Expected: zero failures.

- [ ] **Step 3: Run a local relay-agent smoke test**

Terminal 1:

```powershell
$env:KAI_NERVOUS_LINK_OWNER_TOKEN = 'local-smoke-test-only'
npm run relay
```

Terminal 2:

```bash
npm run agent
```

Terminal 3:

```powershell
$env:KAI_NERVOUS_LINK_OWNER_TOKEN = 'local-smoke-test-only'
node clients/cli/kai-link.js call --relay http://127.0.0.1:8787 --device pc-asier-main --action device_info --capability system.read --params '{}'
```

Expected: an `ok` response containing hostname/platform/arch/node/pid and an `audit_id`.

- [ ] **Step 4: Test kill switch locally**

Create the configured STOP flag locally, then repeat the remote call.

Expected: remote action returns an error indicating the kill switch is triggered and the agent stops accepting new work.

- [ ] **Step 5: Create verification record**

Create `nervous-link/VERIFICATION.md` with actual observed evidence in this shape, replacing each `NOT_RUN` only with real command output after it has been run:

```markdown
# KAI Nervous Link v0.1 Verification

- Branch: feat/kai-nervous-link-v0.1
- Node version: NOT_RUN
- npm ci: NOT_RUN
- npm test: NOT_RUN
- Local relay health: NOT_RUN
- Agent outbound connection: NOT_RUN
- Agent reconnect after relay restart: NOT_RUN
- device_info roundtrip: NOT_RUN
- allowed read_file: NOT_RUN
- denied outside-root read_file: NOT_RUN
- allowlisted run_command: NOT_RUN
- denied run_command: NOT_RUN
- audit redaction: NOT_RUN
- kill switch: NOT_RUN
- Cloudflare Tunnel from mobile data: NOT_RUN
- Tailscale fallback: NOT_RUN

No item may be changed to PASS without fresh command/test evidence.
```

- [ ] **Step 6: Commit the verification record only after filling real evidence**

```bash
git add nervous-link/VERIFICATION.md
git commit -m "test(nervous-link): record v0.1 verification evidence"
```

- [ ] **Step 7: Open a pull request from the feature branch to main**

PR title:

```text
feat: add KAI Nervous Link v0.1 secure remote nervous system
```

PR body must include:

```markdown
## Summary
- add versioned remote-control protocol
- add default-deny policy engine
- add bounded file/process/command operations
- add explicit pairing, replay protection and authenticated relay
- add outbound Windows PC agent with reconnect and heartbeat
- add audit redaction and independent kill switch
- add CLI client and Android contract
- add Cloudflare Tunnel primary transport docs and Tailscale fallback

## Safety
- no delete action in v0.1
- no public unauthenticated shell
- no silent privilege escalation
- secrets excluded from Git/logs
- all mutating actions capability-gated and audited

## Verification
Paste exact final `npm test` output and smoke-test evidence here.
```

- [ ] **Step 8: Do not merge until review gate passes**

Required gates:

```text
npm test = PASS
secret scan = PASS
kill switch = PASS
file root denial = PASS
command denial = PASS
agent reconnect = PASS
mobile-data Cloudflare reachability = PASS
```

---

## Spec coverage self-review

The implementation tasks cover every v0.1 requirement from the approved design:

- Versioned envelope: Task 1.
- Unknown protocol/stale timestamps: Task 1.
- Default-deny capability policy: Task 2.
- Path containment and symlink/junction escape defence: Task 2.
- Bounded argv command execution, timeout and output truncation: Task 3.
- Safe file reads/writes and SHA-256 support: Task 3.
- Process listing/termination: Task 3.
- Audit redaction: Task 4.
- Kill switch: Task 4.
- Pairing, agent auth and replay protection: Task 5.
- Outbound PC connection, heartbeat and reconnect: Task 6.
- CLI client and Android contract: Task 7.
- End-to-end allowed/denied roundtrips: Task 8.
- Cloudflare/Tailscale/bootstrap documentation and Windows startup: Task 9.
- Final evidence and PR gate: Task 10.

No destructive delete capability is introduced. No production capability is promoted to verified without fresh test evidence.
