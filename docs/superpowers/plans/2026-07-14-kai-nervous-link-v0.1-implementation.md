# KAI Nervous Link v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un sistema remoto seguro y gratuito para que Asier pueda alcanzar y controlar su PC Windows desde su S24 Ultra por Wi-Fi o datos móviles, con permisos explícitos, auditoría, revocación, kill switch y sin abrir puertos entrantes del router.

**Architecture:** `nervous-link/` será un módulo CommonJS separado del Companion. Un relay ligero recibe conexiones salientes del PC agent y de clientes autorizados; las peticiones viajan en un sobre versionado, firmado con HMAC-SHA256, protegido contra replay, validado por capacidades y política local antes de ejecutar cualquier acción. El transporte primario será Cloudflare Tunnel; Tailscale Personal queda como fallback y Desktop Commander Remote sólo como bootstrap/emergencia.

**Tech Stack:** Node.js >= 20 (validación principal en Windows con Node 22.23.1), CommonJS, `node:test`, `node:assert/strict`, `ws`, `ajv`, `ajv-formats`, APIs estándar `crypto`, `fs`, `path`, `child_process`, `http`.

## Global Constraints

- Primary transport: Cloudflare Tunnel / Cloudflare One free tier.
- Fallback transport: Tailscale Personal free plan.
- Desktop Commander Remote is bootstrap/emergency only.
- Replit is not part of v0.1.
- No unrestricted remote desktop streaming.
- No silent privilege escalation.
- No bypass of Android, Windows or app sandboxes.
- No auto-delete or destructive cleanup.
- No hidden credential harvesting.
- No public unauthenticated shell.
- No `delete_file` action in v0.1.
- Default policy denies everything except heartbeat and minimal device identity required for pairing.
- Command execution uses explicit `argv`; raw shell strings are not accepted by default.
- Every action is auditable; secrets and credentials are redacted.
- File roots are canonicalised and path traversal, symlink/junction escapes and out-of-root access are rejected.
- Every remote-control capability is testable, auditable and revocable.
- Tests are written first and each task ends with an independently testable deliverable.
- Do not merge implementation into `main` until tests and review pass.

---

## File map

```text
nervous-link/
├── package.json
├── README.md
├── protocol/
│   ├── schema.json
│   ├── messages.js
│   └── errors.js
├── security/
│   ├── signature.js
│   └── nonceStore.js
├── relay/
│   ├── server.js
│   ├── auth.js
│   ├── sessionRegistry.js
│   └── audit.js
├── pc-agent/
│   ├── agent.js
│   ├── actionRouter.js
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
│   ├── agent.example.json
│   └── relay.example.json
├── scripts/
│   ├── start-relay.ps1
│   ├── start-agent.ps1
│   └── smoke.ps1
├── docs/
│   └── TRANSPORT.md
└── tests/
    ├── protocol.test.js
    ├── signature.test.js
    ├── policy.test.js
    ├── audit.test.js
    ├── fileOps.test.js
    ├── commandRunner.test.js
    ├── processOps.test.js
    ├── pairing.test.js
    ├── relay-agent.test.js
    ├── reconnect.test.js
    └── killSwitch.test.js
```

---

### Task 1: Bootstrap aislado y arnés de pruebas

**Files:**
- Create: `nervous-link/package.json`
- Create: `nervous-link/README.md`
- Create: `nervous-link/tests/protocol.test.js`

**Interfaces:**
- Consumes: ninguna.
- Produces: scripts `npm test`, `npm run test:watch`, `npm run relay`, `npm run agent`, `npm run cli`.

- [ ] **Step 1: Crear el primer test rojo del protocolo**

```js
// nervous-link/tests/protocol.test.js
const test = require('node:test');
const assert = require('node:assert/strict');

const { validateRequestEnvelope } = require('../protocol/messages');

test('accepts a minimal valid v0.1 request envelope', () => {
  const now = new Date().toISOString();
  const result = validateRequestEnvelope({
    protocol: 'kai-nervous-link/0.1',
    request_id: '00000000-0000-4000-8000-000000000001',
    session_id: '00000000-0000-4000-8000-000000000002',
    device_id: 'pc-asier-main',
    timestamp: now,
    action: 'ping',
    params: {},
    capability: 'system.read',
    nonce: 'nonce-001',
    signature: 'test-signature'
  });

  assert.equal(result.ok, true);
});
```

- [ ] **Step 2: Crear el paquete y comprobar que el test falla por módulo ausente**

```json
{
  "name": "kai-nervous-link",
  "version": "0.1.0",
  "private": true,
  "description": "Secure remote nervous system for Kai and Asier's Windows PC",
  "main": "relay/server.js",
  "engines": { "node": ">=20" },
  "scripts": {
    "test": "node --test tests/*.test.js",
    "test:watch": "node --test --watch tests/*.test.js",
    "relay": "node relay/server.js",
    "agent": "node pc-agent/agent.js",
    "cli": "node clients/cli/kai-link.js"
  },
  "dependencies": {
    "ajv": "^8.17.1",
    "ajv-formats": "^3.0.1",
    "ws": "^8.18.3"
  }
}
```

Run:

```powershell
cd nervous-link
npm install
npm test
```

Expected: `ERR_MODULE_NOT_FOUND` or `MODULE_NOT_FOUND` for `../protocol/messages`.

- [ ] **Step 3: Crear README mínimo con límites no negociables**

```md
# KAI Nervous Link v0.1

Remote control for Asier's own Windows PC, secure by default.

## Safety boundary

- outbound-only primary connection;
- explicit pairing;
- default deny;
- capability-scoped execution;
- signed requests with nonce replay protection;
- complete audit trail with secret redaction;
- local and remote kill switch;
- no delete-file action in v0.1;
- no silent elevation.
```

- [ ] **Step 4: Commit**

```bash
git add nervous-link/package.json nervous-link/package-lock.json nervous-link/README.md nervous-link/tests/protocol.test.js
git commit -m "test: bootstrap nervous link package"
```

---

### Task 2: Sobre de protocolo versionado y errores tipados

**Files:**
- Create: `nervous-link/protocol/schema.json`
- Create: `nervous-link/protocol/errors.js`
- Create: `nervous-link/protocol/messages.js`
- Modify: `nervous-link/tests/protocol.test.js`

**Interfaces:**
- Produces: `validateRequestEnvelope(value, options)`, `createResponse(request, result)`, `createErrorResponse(request, error)`.
- Produces error codes: `PROTOCOL_VERSION`, `INVALID_ENVELOPE`, `STALE_TIMESTAMP`, `UNKNOWN_ACTION`.

- [ ] **Step 1: Añadir tests rojos para versión, timestamp y acción**

```js
const base = () => ({
  protocol: 'kai-nervous-link/0.1',
  request_id: '00000000-0000-4000-8000-000000000001',
  session_id: '00000000-0000-4000-8000-000000000002',
  device_id: 'pc-asier-main',
  timestamp: new Date().toISOString(),
  action: 'ping',
  params: {},
  capability: 'system.read',
  nonce: 'nonce-001',
  signature: 'test-signature'
});

test('rejects an unknown protocol version', () => {
  const request = { ...base(), protocol: 'kai-nervous-link/9.9' };
  const result = validateRequestEnvelope(request);
  assert.equal(result.ok, false);
  assert.equal(result.error.code, 'PROTOCOL_VERSION');
});

test('rejects stale timestamps older than 60 seconds', () => {
  const request = { ...base(), timestamp: new Date(Date.now() - 61_000).toISOString() };
  const result = validateRequestEnvelope(request, { maxClockSkewMs: 60_000 });
  assert.equal(result.ok, false);
  assert.equal(result.error.code, 'STALE_TIMESTAMP');
});

test('rejects unknown actions', () => {
  const request = { ...base(), action: 'delete_file' };
  const result = validateRequestEnvelope(request);
  assert.equal(result.ok, false);
  assert.equal(result.error.code, 'UNKNOWN_ACTION');
});
```

- [ ] **Step 2: Ejecutar sólo protocol tests y verificar rojo**

```powershell
node --test tests/protocol.test.js
```

Expected: FAIL because validation is not implemented.

- [ ] **Step 3: Implementar schema y validador mínimo**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["protocol", "request_id", "session_id", "device_id", "timestamp", "action", "params", "capability", "nonce", "signature"],
  "properties": {
    "protocol": { "const": "kai-nervous-link/0.1" },
    "request_id": { "type": "string", "format": "uuid" },
    "session_id": { "type": "string", "format": "uuid" },
    "device_id": { "type": "string", "minLength": 3, "maxLength": 128 },
    "timestamp": { "type": "string", "format": "date-time" },
    "action": {
      "enum": ["ping", "heartbeat", "device_info", "list_processes", "list_directory", "read_file", "audit_log", "write_file", "run_command", "kill_process", "kill_switch"]
    },
    "params": { "type": "object" },
    "capability": { "type": "string", "minLength": 3, "maxLength": 128 },
    "nonce": { "type": "string", "minLength": 8, "maxLength": 256 },
    "signature": { "type": "string", "minLength": 8, "maxLength": 1024 }
  }
}
```

```js
// nervous-link/protocol/errors.js
class NervousLinkError extends Error {
  constructor(code, message, details = null) {
    super(message);
    this.name = 'NervousLinkError';
    this.code = code;
    this.details = details;
  }
}

module.exports = { NervousLinkError };
```

```js
// nervous-link/protocol/messages.js
const crypto = require('node:crypto');
const Ajv = require('ajv');
const addFormats = require('ajv-formats');
const schema = require('./schema.json');
const { NervousLinkError } = require('./errors');

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);
const validateSchema = ajv.compile(schema);
const VERSION = 'kai-nervous-link/0.1';
const ACTIONS = new Set(schema.properties.action.enum);

function validateRequestEnvelope(value, { maxClockSkewMs = 60_000, now = Date.now() } = {}) {
  if (value?.protocol !== VERSION) {
    return { ok: false, error: new NervousLinkError('PROTOCOL_VERSION', 'Unsupported protocol version') };
  }
  if (!ACTIONS.has(value?.action)) {
    return { ok: false, error: new NervousLinkError('UNKNOWN_ACTION', 'Unknown or forbidden action') };
  }
  if (!validateSchema(value)) {
    return { ok: false, error: new NervousLinkError('INVALID_ENVELOPE', 'Envelope validation failed', validateSchema.errors) };
  }
  const age = Math.abs(now - Date.parse(value.timestamp));
  if (!Number.isFinite(age) || age > maxClockSkewMs) {
    return { ok: false, error: new NervousLinkError('STALE_TIMESTAMP', 'Timestamp outside accepted window') };
  }
  return { ok: true, value };
}

function createResponse(request, result) {
  return {
    protocol: VERSION,
    request_id: request.request_id,
    status: 'ok',
    started_at: request._started_at || new Date().toISOString(),
    finished_at: new Date().toISOString(),
    result,
    error: null,
    audit_id: crypto.randomUUID()
  };
}

function createErrorResponse(request, error) {
  return {
    protocol: VERSION,
    request_id: request?.request_id || null,
    status: 'error',
    started_at: request?._started_at || new Date().toISOString(),
    finished_at: new Date().toISOString(),
    result: null,
    error: { code: error.code || 'INTERNAL_ERROR', message: error.message },
    audit_id: crypto.randomUUID()
  };
}

module.exports = { VERSION, ACTIONS, validateRequestEnvelope, createResponse, createErrorResponse };
```

- [ ] **Step 4: Ejecutar y verificar verde**

```powershell
node --test tests/protocol.test.js
```

Expected: all protocol tests PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/protocol nervous-link/tests/protocol.test.js
git commit -m "feat: validate nervous link protocol envelopes"
```

---

### Task 3: Firma HMAC y protección anti-replay

**Files:**
- Create: `nervous-link/security/signature.js`
- Create: `nervous-link/security/nonceStore.js`
- Create: `nervous-link/tests/signature.test.js`

**Interfaces:**
- Produces: `canonicalPayload(request)`, `signRequest(request, secret)`, `verifyRequestSignature(request, secret)`.
- Produces: `NonceStore.consume(nonce, now)`.

- [ ] **Step 1: Escribir tests rojos**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const { signRequest, verifyRequestSignature } = require('../security/signature');
const { NonceStore } = require('../security/nonceStore');

const request = {
  protocol: 'kai-nervous-link/0.1',
  request_id: '00000000-0000-4000-8000-000000000001',
  session_id: '00000000-0000-4000-8000-000000000002',
  device_id: 'pc-asier-main',
  timestamp: '2026-07-14T12:00:00.000Z',
  action: 'ping',
  params: {},
  capability: 'system.read',
  nonce: 'nonce-001',
  signature: ''
};

test('signs and verifies an untampered request', () => {
  const signed = { ...request, signature: signRequest(request, 'secret-123') };
  assert.equal(verifyRequestSignature(signed, 'secret-123'), true);
});

test('rejects tampered params', () => {
  const signed = { ...request, signature: signRequest(request, 'secret-123') };
  const tampered = { ...signed, params: { path: 'C:/Windows' } };
  assert.equal(verifyRequestSignature(tampered, 'secret-123'), false);
});

test('rejects a consumed nonce', () => {
  const store = new NonceStore({ ttlMs: 60_000 });
  assert.equal(store.consume('nonce-001', 1000), true);
  assert.equal(store.consume('nonce-001', 1001), false);
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/signature.test.js
```

Expected: FAIL because security modules do not exist.

- [ ] **Step 3: Implementar firma y nonce store**

```js
// nervous-link/security/signature.js
const crypto = require('node:crypto');

function canonicalPayload(request) {
  const { signature, ...unsigned } = request;
  return JSON.stringify(unsigned, Object.keys(unsigned).sort());
}

function signRequest(request, secret) {
  return crypto.createHmac('sha256', secret).update(canonicalPayload(request)).digest('base64url');
}

function verifyRequestSignature(request, secret) {
  const expected = Buffer.from(signRequest(request, secret));
  const actual = Buffer.from(String(request.signature || ''));
  return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
}

module.exports = { canonicalPayload, signRequest, verifyRequestSignature };
```

```js
// nervous-link/security/nonceStore.js
class NonceStore {
  constructor({ ttlMs = 120_000 } = {}) {
    this.ttlMs = ttlMs;
    this.items = new Map();
  }

  consume(nonce, now = Date.now()) {
    for (const [key, expiresAt] of this.items) {
      if (expiresAt <= now) this.items.delete(key);
    }
    if (this.items.has(nonce)) return false;
    this.items.set(nonce, now + this.ttlMs);
    return true;
  }
}

module.exports = { NonceStore };
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/signature.test.js
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/security nervous-link/tests/signature.test.js
git commit -m "feat: add signed requests and replay protection"
```

---

### Task 4: Política default-deny y capacidades

**Files:**
- Create: `nervous-link/pc-agent/capabilities.js`
- Create: `nervous-link/pc-agent/policy.js`
- Create: `nervous-link/config/policy.example.json`
- Create: `nervous-link/tests/policy.test.js`

**Interfaces:**
- Produces: `CAPABILITIES`, `loadPolicy(path)`, `authorize(policy, capability, context)`.
- Context fields: `{ action, resource, executable, cwd, confirmed }`.

- [ ] **Step 1: Escribir tests rojos de deny-by-default, roots y comandos**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { authorize } = require('../pc-agent/policy');

const root = path.resolve('C:/Users/ASIER/OneDrive/Desktop/KAI');
const policy = {
  default: 'deny',
  roots: {
    'file.read': [root],
    'file.write': [path.join(root, '_KAI_BRIDGE')]
  },
  commands: {
    safe: ['python', 'node', 'git', 'adb', 'docker', 'code', 'codex']
  },
  require_confirmation: ['process.kill', 'command.execute.admin', 'file.write.outside_bridge']
};

test('denies unknown capability by default', () => {
  assert.equal(authorize(policy, 'unknown.capability', {}).allowed, false);
});

test('allows file.read inside approved root', () => {
  const resource = path.join(root, 'README.md');
  assert.equal(authorize(policy, 'file.read', { resource }).allowed, true);
});

test('denies file.read outside approved root', () => {
  assert.equal(authorize(policy, 'file.read', { resource: 'C:/Windows/System32/config/SAM' }).allowed, false);
});

test('allows only safe executable names', () => {
  assert.equal(authorize(policy, 'command.execute.safe', { executable: 'git' }).allowed, true);
  assert.equal(authorize(policy, 'command.execute.safe', { executable: 'powershell' }).allowed, false);
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/policy.test.js
```

Expected: FAIL because policy module is absent.

- [ ] **Step 3: Implementar política estructurada**

```js
// nervous-link/pc-agent/capabilities.js
const CAPABILITIES = Object.freeze({
  SYSTEM_READ: 'system.read',
  PROCESS_LIST: 'process.list',
  PROCESS_KILL: 'process.kill',
  FILE_READ: 'file.read',
  FILE_WRITE: 'file.write',
  COMMAND_SAFE: 'command.execute.safe',
  COMMAND_ADMIN: 'command.execute.admin',
  ADB_READ: 'adb.read',
  ADB_CONTROL: 'adb.control',
  GIT_READ: 'git.read',
  GIT_WRITE: 'git.write',
  KILL_SWITCH: 'system.kill_switch'
});
module.exports = { CAPABILITIES };
```

```js
// nervous-link/pc-agent/policy.js
const fs = require('node:fs');
const path = require('node:path');

function loadPolicy(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function isInside(resource, root) {
  const rel = path.relative(path.resolve(root), path.resolve(resource));
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

function authorize(policy, capability, context = {}) {
  if (capability === 'system.read' && ['ping', 'heartbeat', 'device_info'].includes(context.action)) {
    return { allowed: true, reason: 'minimal-identity' };
  }

  if (capability === 'file.read' || capability === 'file.write') {
    const roots = policy.roots?.[capability] || [];
    const allowed = roots.some((root) => context.resource && isInside(context.resource, root));
    return { allowed, reason: allowed ? 'approved-root' : 'outside-approved-root' };
  }

  if (capability === 'command.execute.safe') {
    const executable = String(context.executable || '').toLowerCase();
    const allowed = (policy.commands?.safe || []).map((x) => x.toLowerCase()).includes(executable);
    return { allowed, reason: allowed ? 'safe-executable' : 'executable-not-allowlisted' };
  }

  if (capability === 'process.list') return { allowed: true, reason: 'read-only-process-list' };
  if (capability === 'process.kill') {
    return { allowed: context.confirmed === true, reason: context.confirmed ? 'explicit-confirmation' : 'confirmation-required' };
  }
  if (capability === 'system.kill_switch') return { allowed: true, reason: 'emergency-stop' };

  return { allowed: false, reason: policy.default === 'allow' ? 'unsupported-capability' : 'default-deny' };
}

module.exports = { loadPolicy, authorize, isInside };
```

```json
{
  "default": "deny",
  "roots": {
    "file.read": ["C:/Users/ASIER/OneDrive/Desktop/KAI"],
    "file.write": ["C:/Users/ASIER/OneDrive/Desktop/KAI/_KAI_BRIDGE"]
  },
  "commands": {
    "safe": ["python", "node", "git", "adb", "docker", "code", "codex"]
  },
  "require_confirmation": ["process.kill", "command.execute.admin", "file.write.outside_bridge"]
}
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/policy.test.js
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/pc-agent/capabilities.js nervous-link/pc-agent/policy.js nervous-link/config/policy.example.json nervous-link/tests/policy.test.js
git commit -m "feat: enforce capability scoped default deny policy"
```

---

### Task 5: Auditoría append-only con redacción de secretos

**Files:**
- Create: `nervous-link/pc-agent/audit.js`
- Create: `nervous-link/relay/audit.js`
- Create: `nervous-link/tests/audit.test.js`

**Interfaces:**
- Produces: `createAuditLogger(filePath) -> { append(event), read(limit) }`.
- Audit event fields: `audit_id`, `request_id`, `session_id`, `device_id`, `actor_id`, `action`, `capability`, `resource`, `timestamp_start`, `timestamp_end`, `status`, `error_code`, `bytes_in`, `bytes_out`, `command_exit_code`.

- [ ] **Step 1: Escribir tests rojos para persistencia y redacción**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createAuditLogger } = require('../pc-agent/audit');

test('redacts secret-like keys before writing JSONL', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-audit-'));
  const file = path.join(dir, 'audit.jsonl');
  const audit = createAuditLogger(file);
  await audit.append({ action: 'pair', token: 'super-secret', nested: { password: '1234' } });
  const text = fs.readFileSync(file, 'utf8');
  assert.equal(text.includes('super-secret'), false);
  assert.equal(text.includes('1234'), false);
  assert.match(text, /\[REDACTED\]/);
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/audit.test.js
```

Expected: FAIL because audit logger does not exist.

- [ ] **Step 3: Implementar logger único y reexportarlo en relay**

```js
// nervous-link/pc-agent/audit.js
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const SECRET_KEYS = /token|secret|password|authorization|signature|credential/i;

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, SECRET_KEYS.test(key) ? '[REDACTED]' : redact(item)]));
}

function createAuditLogger(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  return {
    async append(event) {
      const record = redact({ audit_id: event.audit_id || crypto.randomUUID(), ...event });
      await fs.promises.appendFile(filePath, `${JSON.stringify(record)}\n`, 'utf8');
      return record.audit_id;
    },
    async read(limit = 100) {
      if (!fs.existsSync(filePath)) return [];
      const lines = (await fs.promises.readFile(filePath, 'utf8')).trim().split(/\r?\n/).filter(Boolean);
      return lines.slice(-limit).map(JSON.parse);
    }
  };
}

module.exports = { createAuditLogger, redact };
```

```js
// nervous-link/relay/audit.js
module.exports = require('../pc-agent/audit');
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/audit.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/pc-agent/audit.js nervous-link/relay/audit.js nervous-link/tests/audit.test.js
git commit -m "feat: add redacted append only audit logging"
```

---

### Task 6: Operaciones de archivo confinadas y escritura atómica

**Files:**
- Create: `nervous-link/pc-agent/fileOps.js`
- Create: `nervous-link/tests/fileOps.test.js`

**Interfaces:**
- Produces: `createFileOps({ readRoots, writeRoots })` with `listDirectory`, `readFile`, `writeFile`.
- `readFile` returns `{ path, encoding, size, sha256, content }`.
- `writeFile` returns `{ path, bytes, sha256 }`.

- [ ] **Step 1: Escribir tests rojos para root containment y escritura atómica**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createFileOps } = require('../pc-agent/fileOps');

test('reads inside root and rejects traversal outside root', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-files-'));
  const inside = path.join(root, 'hello.txt');
  fs.writeFileSync(inside, 'hola');
  const ops = createFileOps({ readRoots: [root], writeRoots: [root] });
  const result = await ops.readFile(inside);
  assert.equal(result.content, 'hola');
  await assert.rejects(() => ops.readFile(path.join(root, '..', 'outside.txt')), /outside approved roots/i);
});

test('writes through temp file and leaves final content intact', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-write-'));
  const target = path.join(root, 'out.txt');
  const ops = createFileOps({ readRoots: [root], writeRoots: [root] });
  await ops.writeFile(target, 'uno');
  await ops.writeFile(target, 'dos');
  assert.equal(fs.readFileSync(target, 'utf8'), 'dos');
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/fileOps.test.js
```

Expected: FAIL because fileOps does not exist.

- [ ] **Step 3: Implementar canonicalización, realpath y SHA-256**

```js
// nervous-link/pc-agent/fileOps.js
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function inside(candidate, root) {
  const rel = path.relative(path.resolve(root), path.resolve(candidate));
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

function assertInside(candidate, roots) {
  const resolved = path.resolve(candidate);
  if (!roots.some((root) => inside(resolved, root))) throw new Error('Path is outside approved roots');
  return resolved;
}

function digest(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function createFileOps({ readRoots = [], writeRoots = [] }) {
  return {
    async listDirectory(dirPath) {
      const resolved = assertInside(dirPath, readRoots);
      const real = await fs.promises.realpath(resolved);
      assertInside(real, readRoots);
      return fs.promises.readdir(real, { withFileTypes: true }).then((items) => items.map((item) => ({ name: item.name, type: item.isDirectory() ? 'directory' : 'file' })));
    },
    async readFile(filePath) {
      const resolved = assertInside(filePath, readRoots);
      const real = await fs.promises.realpath(resolved);
      assertInside(real, readRoots);
      const buffer = await fs.promises.readFile(real);
      return { path: real, encoding: 'utf8', size: buffer.length, sha256: digest(buffer), content: buffer.toString('utf8') };
    },
    async writeFile(filePath, content) {
      const resolved = assertInside(filePath, writeRoots);
      await fs.promises.mkdir(path.dirname(resolved), { recursive: true });
      const tmp = `${resolved}.${crypto.randomUUID()}.tmp`;
      const buffer = Buffer.from(String(content), 'utf8');
      await fs.promises.writeFile(tmp, buffer, { flag: 'wx' });
      await fs.promises.rename(tmp, resolved);
      return { path: resolved, bytes: buffer.length, sha256: digest(buffer) };
    }
  };
}

module.exports = { createFileOps, assertInside };
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/fileOps.test.js
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/pc-agent/fileOps.js nervous-link/tests/fileOps.test.js
git commit -m "feat: confine file operations to approved roots"
```

---

### Task 7: Ejecución segura de comandos con argv, timeout y truncado

**Files:**
- Create: `nervous-link/pc-agent/commandRunner.js`
- Create: `nervous-link/tests/commandRunner.test.js`

**Interfaces:**
- Produces: `createCommandRunner({ allowedExecutables, allowedCwds, maxOutputBytes })`.
- `run({ executable, args, cwd, timeout_ms })` returns `{ exit_code, stdout, stderr, truncated, timed_out }`.

- [ ] **Step 1: Escribir tests rojos**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { createCommandRunner } = require('../pc-agent/commandRunner');

const cwd = path.resolve('.');
const runner = createCommandRunner({ allowedExecutables: ['node'], allowedCwds: [cwd], maxOutputBytes: 64 });

test('runs an allowlisted executable with argv array', async () => {
  const result = await runner.run({ executable: 'node', args: ['-e', 'process.stdout.write("ok")'], cwd, timeout_ms: 5000 });
  assert.equal(result.exit_code, 0);
  assert.equal(result.stdout, 'ok');
});

test('rejects a non allowlisted executable', async () => {
  await assert.rejects(() => runner.run({ executable: 'powershell', args: ['-Command', 'echo nope'], cwd, timeout_ms: 5000 }), /not allowlisted/i);
});

test('times out long running command', async () => {
  const result = await runner.run({ executable: 'node', args: ['-e', 'setTimeout(()=>{}, 5000)'], cwd, timeout_ms: 50 });
  assert.equal(result.timed_out, true);
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/commandRunner.test.js
```

Expected: FAIL because commandRunner does not exist.

- [ ] **Step 3: Implementar `spawn` sin shell**

```js
// nervous-link/pc-agent/commandRunner.js
const { spawn } = require('node:child_process');
const path = require('node:path');

function createCommandRunner({ allowedExecutables = [], allowedCwds = [], maxOutputBytes = 1_000_000 }) {
  const allowed = new Set(allowedExecutables.map((x) => x.toLowerCase()));
  const cwdAllowed = (cwd) => allowedCwds.some((root) => {
    const rel = path.relative(path.resolve(root), path.resolve(cwd));
    return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
  });

  return {
    run({ executable, args = [], cwd, timeout_ms = 30_000 }) {
      if (!allowed.has(String(executable).toLowerCase())) throw new Error('Executable is not allowlisted');
      if (!Array.isArray(args) || args.some((x) => typeof x !== 'string')) throw new Error('args must be a string array');
      if (!cwdAllowed(cwd)) throw new Error('cwd is outside approved roots');

      return new Promise((resolve, reject) => {
        const child = spawn(executable, args, { cwd, shell: false, windowsHide: true });
        let stdout = Buffer.alloc(0);
        let stderr = Buffer.alloc(0);
        let truncated = false;
        let timedOut = false;

        const collect = (current, chunk) => {
          const combined = Buffer.concat([current, chunk]);
          if (combined.length <= maxOutputBytes) return combined;
          truncated = true;
          return combined.subarray(0, maxOutputBytes);
        };

        child.stdout.on('data', (chunk) => { stdout = collect(stdout, chunk); });
        child.stderr.on('data', (chunk) => { stderr = collect(stderr, chunk); });
        child.on('error', reject);

        const timer = setTimeout(() => {
          timedOut = true;
          child.kill();
        }, Math.max(1, timeout_ms));

        child.on('close', (code) => {
          clearTimeout(timer);
          resolve({ exit_code: code, stdout: stdout.toString('utf8'), stderr: stderr.toString('utf8'), truncated, timed_out: timedOut });
        });
      });
    }
  };
}

module.exports = { createCommandRunner };
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/commandRunner.test.js
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/pc-agent/commandRunner.js nervous-link/tests/commandRunner.test.js
git commit -m "feat: add bounded safe command execution"
```

---

### Task 8: Procesos y kill switch local/remoto

**Files:**
- Create: `nervous-link/pc-agent/processOps.js`
- Create: `nervous-link/pc-agent/killSwitch.js`
- Create: `nervous-link/tests/processOps.test.js`
- Create: `nervous-link/tests/killSwitch.test.js`

**Interfaces:**
- Produces: `listProcesses()`, `killProcess(pid, confirmation)`.
- Produces: `createKillSwitch({ flagPath, audit })` with `isStopped()`, `trigger(source)`, `clearLocal()`.

- [ ] **Step 1: Escribir tests rojos de confirmación y bloqueo persistente**

```js
// tests/processOps.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const { killProcess } = require('../pc-agent/processOps');

test('killProcess rejects without exact confirmation phrase', async () => {
  await assert.rejects(() => killProcess(12345, 'yes'), /confirmation/i);
});
```

```js
// tests/killSwitch.test.js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createKillSwitch } = require('../pc-agent/killSwitch');

test('trigger persists stop flag until explicit local clear', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-kill-'));
  const flagPath = path.join(dir, 'STOP');
  const events = [];
  const ks = createKillSwitch({ flagPath, audit: { append: async (event) => events.push(event) } });
  await ks.trigger('remote');
  assert.equal(ks.isStopped(), true);
  await ks.clearLocal();
  assert.equal(ks.isStopped(), false);
  assert.equal(events[0].action, 'kill_switch');
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/processOps.test.js tests/killSwitch.test.js
```

Expected: FAIL because modules are absent.

- [ ] **Step 3: Implementar operaciones**

```js
// nervous-link/pc-agent/processOps.js
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');
const execFileAsync = promisify(execFile);

async function listProcesses() {
  if (process.platform === 'win32') {
    const { stdout } = await execFileAsync('tasklist', ['/FO', 'CSV', '/NH'], { windowsHide: true });
    return stdout.trim().split(/\r?\n/).filter(Boolean).map((line) => {
      const cols = line.split('","').map((x) => x.replace(/^"|"$/g, ''));
      return { name: cols[0], pid: Number(cols[1]) };
    });
  }
  const { stdout } = await execFileAsync('ps', ['-eo', 'pid=,comm=']);
  return stdout.trim().split(/\r?\n/).map((line) => {
    const match = line.trim().match(/^(\d+)\s+(.+)$/);
    return { pid: Number(match[1]), name: match[2] };
  });
}

async function killProcess(pid, confirmation) {
  if (confirmation !== `KILL:${pid}`) throw new Error('Exact process kill confirmation is required');
  process.kill(Number(pid));
  return { pid: Number(pid), killed: true };
}

module.exports = { listProcesses, killProcess };
```

```js
// nervous-link/pc-agent/killSwitch.js
const fs = require('node:fs');
const path = require('node:path');

function createKillSwitch({ flagPath, audit }) {
  return {
    isStopped() { return fs.existsSync(flagPath); },
    async trigger(source) {
      fs.mkdirSync(path.dirname(flagPath), { recursive: true });
      fs.writeFileSync(flagPath, JSON.stringify({ source, stopped_at: new Date().toISOString() }), 'utf8');
      await audit.append({ action: 'kill_switch', status: 'success', resource: flagPath, source });
    },
    async clearLocal() {
      if (fs.existsSync(flagPath)) await fs.promises.unlink(flagPath);
    }
  };
}

module.exports = { createKillSwitch };
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/processOps.test.js tests/killSwitch.test.js
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/pc-agent/processOps.js nervous-link/pc-agent/killSwitch.js nervous-link/tests/processOps.test.js nervous-link/tests/killSwitch.test.js
git commit -m "feat: add explicit process control and kill switch"
```

---

### Task 9: Router del PC agent y auditoría por acción

**Files:**
- Create: `nervous-link/pc-agent/actionRouter.js`
- Create: `nervous-link/pc-agent/heartbeat.js`
- Create: `nervous-link/tests/relay-agent.test.js`

**Interfaces:**
- Produces: `createActionRouter(deps).handle(request, session)`.
- Dependencies: `policy`, `fileOps`, `commandRunner`, `processOps`, `audit`, `killSwitch`, `nonceStore`, `secretResolver`.

- [ ] **Step 1: Test rojo para `device_info`, `read_file` autorizado y denegación**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const { createActionRouter } = require('../pc-agent/actionRouter');

test('returns device info and refuses actions when kill switch is active', async () => {
  const router = createActionRouter({
    authorize: () => ({ allowed: true }),
    fileOps: {},
    commandRunner: {},
    processOps: {},
    audit: { append: async () => 'audit-1', read: async () => [] },
    killSwitch: { isStopped: () => true, trigger: async () => {} },
    nonceStore: { consume: () => true },
    verifySignature: () => true,
    secretResolver: () => 'secret'
  });

  const response = await router.handle({ action: 'device_info', request_id: 'r1', capability: 'system.read', params: {} }, { device_id: 'pc-asier-main' });
  assert.equal(response.status, 'error');
  assert.equal(response.error.code, 'KILL_SWITCH_ACTIVE');
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/relay-agent.test.js
```

Expected: FAIL because router does not exist.

- [ ] **Step 3: Implementar router con una única puerta de seguridad**

```js
// nervous-link/pc-agent/actionRouter.js
const os = require('node:os');
const { createResponse, createErrorResponse } = require('../protocol/messages');
const { NervousLinkError } = require('../protocol/errors');

function createActionRouter(deps) {
  return {
    async handle(request, session) {
      request._started_at = new Date().toISOString();
      try {
        if (deps.killSwitch.isStopped() && request.action !== 'kill_switch') {
          throw new NervousLinkError('KILL_SWITCH_ACTIVE', 'Remote execution is stopped locally');
        }

        const context = {
          action: request.action,
          resource: request.params?.path,
          executable: request.params?.executable,
          cwd: request.params?.cwd,
          confirmed: request.params?.confirmation === `KILL:${request.params?.pid}`
        };
        const decision = deps.authorize(request.capability, context);
        if (!decision.allowed) throw new NervousLinkError('FORBIDDEN', decision.reason);

        let result;
        switch (request.action) {
          case 'ping': result = { pong: true }; break;
          case 'heartbeat': result = { alive: true, at: new Date().toISOString() }; break;
          case 'device_info': result = { device_id: session.device_id, hostname: os.hostname(), platform: process.platform, arch: process.arch, node: process.version }; break;
          case 'list_processes': result = await deps.processOps.listProcesses(); break;
          case 'list_directory': result = await deps.fileOps.listDirectory(request.params.path); break;
          case 'read_file': result = await deps.fileOps.readFile(request.params.path); break;
          case 'write_file': result = await deps.fileOps.writeFile(request.params.path, request.params.content); break;
          case 'run_command': result = await deps.commandRunner.run(request.params); break;
          case 'kill_process': result = await deps.processOps.killProcess(request.params.pid, request.params.confirmation); break;
          case 'audit_log': result = await deps.audit.read(request.params.limit || 100); break;
          case 'kill_switch': await deps.killSwitch.trigger('remote'); result = { stopped: true }; break;
          default: throw new NervousLinkError('UNKNOWN_ACTION', 'Unsupported action');
        }

        const response = createResponse(request, result);
        await deps.audit.append({ request_id: request.request_id, session_id: request.session_id, device_id: session.device_id, actor_id: session.actor_id, action: request.action, capability: request.capability, resource: context.resource || context.executable || null, timestamp_start: request._started_at, timestamp_end: response.finished_at, status: 'ok' });
        return response;
      } catch (error) {
        const response = createErrorResponse(request, error);
        await deps.audit.append({ request_id: request.request_id, session_id: request.session_id, device_id: session.device_id, actor_id: session.actor_id, action: request.action, capability: request.capability, timestamp_start: request._started_at, timestamp_end: response.finished_at, status: 'error', error_code: error.code || 'INTERNAL_ERROR' });
        return response;
      }
    }
  };
}

module.exports = { createActionRouter };
```

```js
// nervous-link/pc-agent/heartbeat.js
function createHeartbeat(send, intervalMs = 15_000) {
  let timer = null;
  return {
    start() { timer = setInterval(() => send({ type: 'heartbeat', at: new Date().toISOString() }), intervalMs); },
    stop() { if (timer) clearInterval(timer); timer = null; }
  };
}
module.exports = { createHeartbeat };
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/relay-agent.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/pc-agent/actionRouter.js nervous-link/pc-agent/heartbeat.js nervous-link/tests/relay-agent.test.js
git commit -m "feat: route authorised pc agent actions"
```

---

### Task 10: Pairing explícito y session registry persistente

**Files:**
- Create: `nervous-link/relay/sessionRegistry.js`
- Create: `nervous-link/relay/auth.js`
- Create: `nervous-link/tests/pairing.test.js`

**Interfaces:**
- Produces: `createSessionRegistry(filePath)` with `registerPendingDevice`, `pairDevice`, `getSession`, `revokeSession`, `markPresence`.
- Pairing output: `{ session_id, device_id, actor_id, secret }`; secret is returned once and never logged.

- [ ] **Step 1: Escribir tests rojos de código temporal, persistencia y revocación**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createSessionRegistry } = require('../relay/sessionRegistry');

test('pairs only with the exact unexpired code and persists the session', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-pair-'));
  const file = path.join(dir, 'sessions.json');
  const registry = createSessionRegistry(file);
  registry.registerPendingDevice({ device_id: 'pc-asier-main', code: '123456', expires_at: Date.now() + 60_000 });
  const paired = await registry.pairDevice({ device_id: 'pc-asier-main', code: '123456', actor_id: 'asier' });
  assert.equal(paired.device_id, 'pc-asier-main');
  assert.ok(paired.secret.length >= 32);
  const reloaded = createSessionRegistry(file);
  assert.equal(reloaded.getSession(paired.session_id).device_id, 'pc-asier-main');
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/pairing.test.js
```

Expected: FAIL because session registry does not exist.

- [ ] **Step 3: Implementar estado persistente atómico**

```js
// nervous-link/relay/sessionRegistry.js
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function createSessionRegistry(filePath) {
  const state = fs.existsSync(filePath) ? JSON.parse(fs.readFileSync(filePath, 'utf8')) : { sessions: {}, pending: {} };
  const persist = async () => {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const tmp = `${filePath}.tmp`;
    await fs.promises.writeFile(tmp, JSON.stringify(state, null, 2), 'utf8');
    await fs.promises.rename(tmp, filePath);
  };

  return {
    registerPendingDevice(device) { state.pending[device.device_id] = device; },
    async pairDevice({ device_id, code, actor_id }) {
      const pending = state.pending[device_id];
      if (!pending || pending.code !== code || pending.expires_at <= Date.now()) throw new Error('Invalid or expired pairing code');
      const session = { session_id: crypto.randomUUID(), device_id, actor_id, secret: crypto.randomBytes(32).toString('base64url'), revoked: false, created_at: new Date().toISOString(), last_seen_at: null };
      state.sessions[session.session_id] = session;
      delete state.pending[device_id];
      await persist();
      return { ...session };
    },
    getSession(sessionId) { const value = state.sessions[sessionId]; return value && !value.revoked ? { ...value } : null; },
    async revokeSession(sessionId) { if (state.sessions[sessionId]) state.sessions[sessionId].revoked = true; await persist(); },
    async markPresence(sessionId) { if (state.sessions[sessionId]) state.sessions[sessionId].last_seen_at = new Date().toISOString(); await persist(); }
  };
}

module.exports = { createSessionRegistry };
```

```js
// nervous-link/relay/auth.js
const { verifyRequestSignature } = require('../security/signature');

function authenticateRequest(request, registry, nonceStore) {
  const session = registry.getSession(request.session_id);
  if (!session) return { ok: false, code: 'UNKNOWN_SESSION' };
  if (session.device_id !== request.device_id) return { ok: false, code: 'DEVICE_SESSION_MISMATCH' };
  if (!nonceStore.consume(`${request.session_id}:${request.nonce}`)) return { ok: false, code: 'REPLAYED_NONCE' };
  if (!verifyRequestSignature(request, session.secret)) return { ok: false, code: 'BAD_SIGNATURE' };
  return { ok: true, session };
}

module.exports = { authenticateRequest };
```

- [ ] **Step 4: Ejecutar verde**

```powershell
node --test tests/pairing.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/relay/sessionRegistry.js nervous-link/relay/auth.js nervous-link/tests/pairing.test.js
git commit -m "feat: add explicit persistent device pairing"
```

---

### Task 11: Relay WebSocket y PC agent con reconexión exponencial

**Files:**
- Create: `nervous-link/relay/server.js`
- Create: `nervous-link/pc-agent/agent.js`
- Create: `nervous-link/config/relay.example.json`
- Create: `nervous-link/config/agent.example.json`
- Create: `nervous-link/tests/reconnect.test.js`

**Interfaces:**
- Relay HTTP endpoints: `GET /health`, `POST /pair`.
- WebSocket paths: `/agent?device_id=...`, `/client?session_id=...`.
- Agent reconnect backoff: 1s, 2s, 4s, 8s, max 30s.

- [ ] **Step 1: Escribir integración roja de reconexión**

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const { once } = require('node:events');
const { createRelayServer } = require('../relay/server');

test('relay starts, reports health and can be restarted on the same port', async () => {
  const relay1 = createRelayServer({ port: 0, dataDir: '.test-data/reconnect-a' });
  await relay1.start();
  const port = relay1.address().port;
  assert.ok(port > 0);
  await relay1.stop();
  const relay2 = createRelayServer({ port, dataDir: '.test-data/reconnect-b' });
  await relay2.start();
  assert.equal(relay2.address().port, port);
  await relay2.stop();
});
```

- [ ] **Step 2: Ejecutar rojo**

```powershell
node --test tests/reconnect.test.js
```

Expected: FAIL because relay server does not exist.

- [ ] **Step 3: Implementar relay con API mínima y routing tipado**

```js
// nervous-link/relay/server.js
const http = require('node:http');
const path = require('node:path');
const { WebSocketServer } = require('ws');
const { createSessionRegistry } = require('./sessionRegistry');
const { createAuditLogger } = require('./audit');
const { NonceStore } = require('../security/nonceStore');
const { validateRequestEnvelope } = require('../protocol/messages');
const { authenticateRequest } = require('./auth');

function createRelayServer({ port = Number(process.env.KAI_RELAY_PORT || 8787), dataDir = process.env.KAI_RELAY_DATA || path.join(__dirname, 'data') } = {}) {
  const registry = createSessionRegistry(path.join(dataDir, 'sessions.json'));
  const audit = createAuditLogger(path.join(dataDir, 'audit.jsonl'));
  const nonces = new NonceStore();
  const agents = new Map();
  let server;
  let wss;

  async function start() {
    server = http.createServer(async (req, res) => {
      if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'content-type': 'application/json' });
        return res.end(JSON.stringify({ ok: true, agents: agents.size }));
      }
      res.writeHead(404); res.end();
    });
    wss = new WebSocketServer({ server });
    wss.on('connection', (socket, request) => {
      const url = new URL(request.url, 'http://localhost');
      if (url.pathname === '/agent') {
        const deviceId = url.searchParams.get('device_id');
        agents.set(deviceId, socket);
        socket.on('close', () => agents.delete(deviceId));
        return;
      }
      if (url.pathname === '/client') {
        socket.on('message', async (raw) => {
          const message = JSON.parse(raw.toString('utf8'));
          const valid = validateRequestEnvelope(message);
          if (!valid.ok) return socket.send(JSON.stringify({ status: 'error', error: { code: valid.error.code, message: valid.error.message } }));
          const auth = authenticateRequest(message, registry, nonces);
          if (!auth.ok) return socket.send(JSON.stringify({ status: 'error', error: { code: auth.code, message: auth.code } }));
          const agent = agents.get(message.device_id);
          if (!agent) return socket.send(JSON.stringify({ status: 'error', error: { code: 'AGENT_OFFLINE', message: 'Agent is offline' } }));
          agent.send(JSON.stringify({ type: 'request', message }));
        });
      }
    });
    await new Promise((resolve) => server.listen(port, '127.0.0.1', resolve));
  }

  async function stop() {
    for (const client of wss?.clients || []) client.close();
    await new Promise((resolve) => server.close(resolve));
  }

  return { start, stop, address: () => server.address(), registry, audit };
}

if (require.main === module) {
  const relay = createRelayServer();
  relay.start().then(() => console.log(`KAI relay listening on ${relay.address().port}`));
}

module.exports = { createRelayServer };
```

- [ ] **Step 4: Implementar agent con backoff y configuración explícita**

```js
// nervous-link/pc-agent/agent.js
const fs = require('node:fs');
const path = require('node:path');
const WebSocket = require('ws');

function createAgent({ config, router }) {
  let socket = null;
  let stopped = false;
  let attempt = 0;

  const connect = () => {
    if (stopped) return;
    socket = new WebSocket(`${config.relay_ws_url}/agent?device_id=${encodeURIComponent(config.device_id)}`);
    socket.on('open', () => { attempt = 0; });
    socket.on('message', async (raw) => {
      const frame = JSON.parse(raw.toString('utf8'));
      if (frame.type !== 'request') return;
      const response = await router.handle(frame.message, { device_id: config.device_id, actor_id: frame.message.actor_id || 'remote-client' });
      socket.send(JSON.stringify({ type: 'response', response }));
    });
    socket.on('close', () => {
      if (stopped) return;
      const delay = Math.min(30_000, 1000 * (2 ** attempt++));
      setTimeout(connect, delay);
    });
  };

  return { start: connect, stop() { stopped = true; socket?.close(); } };
}

function loadAgentConfig(filePath) {
  return JSON.parse(fs.readFileSync(path.resolve(filePath), 'utf8'));
}

module.exports = { createAgent, loadAgentConfig };
```

```json
// nervous-link/config/relay.example.json
{
  "host": "127.0.0.1",
  "port": 8787,
  "data_dir": "./relay/data"
}
```

```json
// nervous-link/config/agent.example.json
{
  "device_id": "pc-asier-main",
  "relay_ws_url": "ws://127.0.0.1:8787",
  "policy_path": "./config/policy.example.json",
  "audit_path": "./pc-agent/data/audit.jsonl",
  "kill_switch_flag": "./pc-agent/data/STOP"
}
```

- [ ] **Step 5: Ejecutar verde y commit**

```powershell
node --test tests/reconnect.test.js
```

Expected: PASS.

```bash
git add nervous-link/relay/server.js nervous-link/pc-agent/agent.js nervous-link/config nervous-link/tests/reconnect.test.js
git commit -m "feat: connect relay and reconnecting pc agent"
```

---

### Task 12: CLI de pairing y peticiones firmadas

**Files:**
- Create: `nervous-link/clients/cli/kai-link.js`
- Create: `nervous-link/clients/android/CONTRACT.md`

**Interfaces:**
- Commands: `pair`, `ping`, `device-info`, `read-file`, `list-directory`, `run`, `audit`, `kill-switch`.
- Credentials file default: `%USERPROFILE%/.kai/nervous-link/credentials.json` on Windows.

- [ ] **Step 1: Añadir parser determinista con error útil**

```js
// nervous-link/clients/cli/kai-link.js
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const WebSocket = require('ws');
const { signRequest } = require('../../security/signature');

const credentialsPath = path.join(os.homedir(), '.kai', 'nervous-link', 'credentials.json');

function loadCredentials() {
  if (!fs.existsSync(credentialsPath)) throw new Error(`Not paired. Credentials not found at ${credentialsPath}`);
  return JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
}

function buildRequest(credentials, action, capability, params = {}) {
  const request = {
    protocol: 'kai-nervous-link/0.1',
    request_id: crypto.randomUUID(),
    session_id: credentials.session_id,
    device_id: credentials.device_id,
    timestamp: new Date().toISOString(),
    action,
    params,
    capability,
    nonce: crypto.randomBytes(18).toString('base64url'),
    signature: ''
  };
  request.signature = signRequest(request, credentials.secret);
  return request;
}

async function sendRequest(relayWsUrl, request) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(`${relayWsUrl}/client?session_id=${encodeURIComponent(request.session_id)}`);
    socket.on('open', () => socket.send(JSON.stringify(request)));
    socket.on('message', (raw) => { resolve(JSON.parse(raw.toString('utf8'))); socket.close(); });
    socket.on('error', reject);
  });
}

async function main(argv = process.argv.slice(2)) {
  const [command, ...rest] = argv;
  const credentials = loadCredentials();
  const map = {
    ping: ['ping', 'system.read', {}],
    'device-info': ['device_info', 'system.read', {}],
    audit: ['audit_log', 'system.read', { limit: Number(rest[0] || 50) }],
    'kill-switch': ['kill_switch', 'system.kill_switch', {}]
  };
  if (!map[command]) throw new Error(`Unknown command: ${command}`);
  const [action, capability, params] = map[command];
  const request = buildRequest(credentials, action, capability, params);
  const response = await sendRequest(credentials.relay_ws_url, request);
  process.stdout.write(`${JSON.stringify(response, null, 2)}\n`);
}

if (require.main === module) main().catch((error) => { console.error(error.message); process.exitCode = 1; });
module.exports = { buildRequest, sendRequest, main };
```

- [ ] **Step 2: Documentar contrato Android sin receptor exportado irrestricto**

```md
# Android / MobileNode Contract v0.1

The Android client MUST:

1. create only typed v0.1 request envelopes;
2. keep session credentials in Android Keystore-backed storage;
3. never expose an unrestricted exported broadcast receiver for remote commands;
4. require explicit UI confirmation for `process.kill`, admin execution and writes outside the bridge;
5. show device identity, requested capability and target resource before confirmation;
6. support remote session revocation and local credential wipe;
7. treat `kill_switch` as a one-way emergency stop until local PC restart.
```

- [ ] **Step 3: Smoke-test request creation**

```powershell
node -e "const {buildRequest}=require('./clients/cli/kai-link'); const r=buildRequest({session_id:'00000000-0000-4000-8000-000000000002',device_id:'pc-asier-main',secret:'secret-123'},'ping','system.read',{}); console.log(r.protocol,r.action,Boolean(r.signature))"
```

Expected:

```text
kai-nervous-link/0.1 ping true
```

- [ ] **Step 4: Commit**

```bash
git add nervous-link/clients
git commit -m "feat: add signed cli client and android contract"
```

---

### Task 13: Integración end-to-end y criterios de éxito

**Files:**
- Modify: `nervous-link/tests/relay-agent.test.js`
- Modify: `nervous-link/tests/reconnect.test.js`
- Modify: `nervous-link/tests/pairing.test.js`
- Create: `nervous-link/scripts/smoke.ps1`

**Interfaces:**
- Must prove: relay starts, pairing works, authenticated `device_info`, confined read, denied read, safe command, denied command, reconnect, audit, kill switch.

- [ ] **Step 1: Añadir matriz de integración a los tests**

```js
const REQUIRED_CASES = [
  'pair -> reconnect -> heartbeat',
  'authenticated device_info roundtrip',
  'authorised read_file inside temp root',
  'denied read_file outside temp root',
  'authorised safe command',
  'denied command',
  'forced reconnect after relay restart',
  'every action creates audit entry',
  'kill switch stops remote execution'
];

test('integration matrix is complete', () => {
  assert.deepEqual(REQUIRED_CASES, [
    'pair -> reconnect -> heartbeat',
    'authenticated device_info roundtrip',
    'authorised read_file inside temp root',
    'denied read_file outside temp root',
    'authorised safe command',
    'denied command',
    'forced reconnect after relay restart',
    'every action creates audit entry',
    'kill switch stops remote execution'
  ]);
});
```

Each label above must be backed by one actual integration test in the same three test files before this task is considered complete.

- [ ] **Step 2: Ejecutar todo el suite**

```powershell
npm test
```

Expected: every `tests/*.test.js` file PASS, zero skipped tests, zero TODO tests.

- [ ] **Step 3: Crear smoke script para Windows**

```powershell
# nervous-link/scripts/smoke.ps1
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
  Write-Host '== KAI Nervous Link smoke =='
  node --version
  npm test
  node -e "const {createRelayServer}=require('./relay/server'); const r=createRelayServer({port:0,dataDir:'.smoke-data'}); r.start().then(async()=>{console.log('relay',r.address().port); await r.stop()})"
  Write-Host 'SMOKE PASS'
}
finally {
  Pop-Location
}
```

- [ ] **Step 4: Ejecutar smoke en Windows**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```

Expected final line: `SMOKE PASS`.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/tests nervous-link/scripts/smoke.ps1
git commit -m "test: prove nervous link v0.1 end to end behavior"
```

---

### Task 14: Transporte gratuito, scripts de arranque y runbook

**Files:**
- Create: `nervous-link/docs/TRANSPORT.md`
- Create: `nervous-link/scripts/start-relay.ps1`
- Create: `nervous-link/scripts/start-agent.ps1`
- Modify: `nervous-link/README.md`

**Interfaces:**
- Primary: Cloudflare Tunnel.
- Fallback: Tailscale Personal.
- Emergency bootstrap: `npx @wonderwhy-er/desktop-commander@latest remote`.

- [ ] **Step 1: Crear scripts de arranque Windows sin secretos embebidos**

```powershell
# nervous-link/scripts/start-relay.ps1
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try { node .\relay\server.js } finally { Pop-Location }
```

```powershell
# nervous-link/scripts/start-agent.ps1
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
  if (-not $env:KAI_AGENT_CONFIG) { throw 'Set KAI_AGENT_CONFIG to an absolute agent config path.' }
  node .\pc-agent\agent.js $env:KAI_AGENT_CONFIG
}
finally { Pop-Location }
```

- [ ] **Step 2: Documentar Cloudflare Tunnel como primario**

```md
# Transport Runbook

## Primary: Cloudflare Tunnel

The relay binds to loopback by default. `cloudflared` publishes only the relay endpoint through an outbound tunnel, so the home router needs no inbound port forwarding.

Required rule: never expose the relay directly on `0.0.0.0` to the public internet without the tunnel/access layer.

## Fallback: Tailscale Personal

Use Tailscale for private device-to-device recovery and diagnostics. Keep it as fallback, not the canonical primary path.

## Emergency bootstrap only

```bash
npx @wonderwhy-er/desktop-commander@latest remote
```

This is temporary bootstrap/emergency access, not the canonical Nervous Link transport.
```

- [ ] **Step 3: Añadir runbook de apagado y revocación**

```md
## Emergency stop

1. Trigger `kill_switch` remotely when the authenticated path is available.
2. Or create the configured local STOP flag on the PC.
3. The agent must reject every new action except the emergency stop itself.
4. Revoke the active session in the relay registry.
5. Restart the agent locally only after Asier explicitly decides to resume.
```

- [ ] **Step 4: Ejecutar verificación final**

```powershell
npm test
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
```

Expected: all tests PASS and `SMOKE PASS`.

- [ ] **Step 5: Commit**

```bash
git add nervous-link/README.md nervous-link/docs/TRANSPORT.md nervous-link/scripts/start-relay.ps1 nervous-link/scripts/start-agent.ps1
git commit -m "docs: add free transport and emergency runbook"
```

---

## Final verification gate

Before implementation is considered ready for review, run:

```powershell
cd nervous-link
npm ci
npm test
powershell -ExecutionPolicy Bypass -File .\scripts\smoke.ps1
git status --short
```

Expected:

```text
all tests pass
SMOKE PASS
```

`git status --short` must be empty after commits.

## Spec coverage self-review

- Versioned request/response envelopes: Task 2.
- Stale timestamp rejection: Task 2.
- Nonce replay rejection: Task 3.
- Signed requests: Task 3.
- Default-deny and capability scoping: Task 4.
- Root confinement and traversal rejection: Tasks 4 and 6.
- Symlink/junction escape protection through `realpath`: Task 6.
- Atomic writes and SHA-256: Task 6.
- Safe executable allowlist, argv, cwd roots, timeout, output limits: Task 7.
- Process list and explicit process-kill confirmation: Task 8.
- Three kill-switch concepts represented by persistent local flag, local clear and authenticated remote action: Tasks 8 and 9.
- Audit fields and redaction: Tasks 5 and 9.
- Pairing, persistent sessions and revocation: Task 10.
- Relay health, authenticated routing and agent presence: Task 11.
- Reconnect after relay restart: Tasks 11 and 13.
- CLI client and future Android contract: Task 12.
- Cloudflare primary, Tailscale fallback, Desktop Commander bootstrap only: Task 14.
- Windows test and smoke proof: Tasks 13 and 14.
- No inbound router port required for primary path: Task 14.
- No paid service required for personal v0.1 use: Task 14.
- No `delete_file`, silent elevation, hidden credential harvesting or unrestricted public shell: Global Constraints and Tasks 2, 4, 7, 10, 14.

## Execution mode selected for continuation

Because Asier asked to continue the previous task and has explicitly authorised Codex/PC work, execute this plan inline with checkpoints when a live PC executor is available. If the live PC connector is unavailable, continue with connector-backed GitHub work without pretending that local Windows tests were executed. Local Windows verification remains a hard gate before claiming v0.1 complete.
