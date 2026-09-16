const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');

const { ACTIONS, CAPABILITIES, PROTOCOL_VERSION } = require('../protocol/constants');
const { validateRequestEnvelope } = require('../protocol/envelope');
const { authorizeAction } = require('../pc-agent/policy');
const { createPcAgent } = require('../pc-agent/agent');

function recoveryEnvelope(overrides = {}) {
  return {
    protocol: PROTOCOL_VERSION,
    request_id: 'req-recovery-1',
    session_id: 'sess-recovery-1',
    device_id: 'pc-asier-main',
    actor_id: 'kai-control',
    timestamp: new Date().toISOString(),
    action: 'run_recovery_playbook',
    params: { playbook_id: 'status' },
    capability: 'recovery.execute.safe',
    nonce: 'nonce-recovery-12345',
    signature: 'proof',
    ...overrides,
  };
}

function recoveryPolicy(enabled = true) {
  return {
    default: 'deny',
    capabilities: {
      'system.read': true,
      'recovery.execute.safe': enabled,
    },
    recovery: {
      playbooks: {
        status: {
          executable: process.execPath,
          argv: ['-e', 'process.stdout.write("recovery-ok")'],
        },
      },
    },
    limits: {
      max_command_ms: 1000,
      max_output_bytes: 1024,
    },
  };
}

test('protocol declares the recovery action and capability', () => {
  assert.equal(ACTIONS.includes('run_recovery_playbook'), true);
  assert.equal(CAPABILITIES.includes('recovery.execute.safe'), true);
  assert.equal(validateRequestEnvelope(recoveryEnvelope()).ok, true);
});

test('recovery action rejects a mismatched capability even when that capability is otherwise enabled', () => {
  const policy = recoveryPolicy(true);
  const authz = authorizeAction(policy, recoveryEnvelope({ capability: 'system.read' }));
  assert.deepEqual(authz, { allowed: false, reason: 'CAPABILITY_ACTION_MISMATCH' });
});

test('recovery capability remains default-deny when disabled', () => {
  const authz = authorizeAction(recoveryPolicy(false), recoveryEnvelope());
  assert.deepEqual(authz, { allowed: false, reason: 'DEFAULT_DENY' });
});

test('agent dispatch executes a fixed recovery playbook and audits only its id', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'kai-recovery-agent-'));
  const auditPath = path.join(root, 'audit.jsonl');
  const killSwitchPath = path.join(root, 'STOP');

  const agent = createPcAgent({
    relayUrl: 'http://127.0.0.1:1',
    deviceId: 'pc-asier-main',
    policy: recoveryPolicy(true),
    auditPath,
    killSwitchPath,
  });

  const response = await agent.dispatch(recoveryEnvelope());
  assert.equal(response.status, 'ok');
  assert.equal(response.result.playbook_id, 'status');
  assert.equal(response.result.stdout, 'recovery-ok');

  const rows = (await fs.readFile(auditPath, 'utf8')).trim().split('\n').map(JSON.parse);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].action, 'run_recovery_playbook');
  assert.equal(rows[0].capability, 'recovery.execute.safe');
  assert.equal(rows[0].resource, 'status');
  assert.equal(JSON.stringify(rows[0]).includes(process.execPath), false);
});

test('agent dispatch denies the recovery playbook when capability is disabled', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'kai-recovery-deny-'));
  const agent = createPcAgent({
    relayUrl: 'http://127.0.0.1:1',
    deviceId: 'pc-asier-main',
    policy: recoveryPolicy(false),
    auditPath: path.join(root, 'audit.jsonl'),
    killSwitchPath: path.join(root, 'STOP'),
  });

  const response = await agent.dispatch(recoveryEnvelope());
  assert.equal(response.status, 'error');
  assert.match(response.error.message, /DEFAULT_DENY/);
});
