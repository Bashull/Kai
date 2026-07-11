const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { createRelayServer } = require('../relay/server');
const { SessionRegistry } = require('../relay/sessionRegistry');
const { createPcAgent } = require('../pc-agent/agent');

async function waitFor(predicate, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('Condition not met before timeout');
}

function createPolicy() {
  return {
    capabilities: { 'system.read': true },
    roots: {},
    commands: { safe: [], blocked_patterns: [] },
    limits: {},
  };
}

test('agent connects outward and answers device_info after pre-pairing', async (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-link-int-'));
  const relay = createRelayServer({ ownerToken: 'owner-test-token' });
  const address = await relay.start(0);

  relay.registry.devices.set('pc-test', {
    device_id: 'pc-test',
    public_identity: 'test',
    device_token: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
  });

  const agent = createPcAgent({
    relayUrl: `http://127.0.0.1:${address.port}`,
    deviceId: 'pc-test',
    deviceToken: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
    policy: createPolicy(),
    auditPath: path.join(temp, 'audit.jsonl'),
    killSwitchPath: path.join(temp, 'STOP'),
    reconnectBaseMs: 20,
  });

  t.after(async () => {
    await agent.stop();
    await relay.stop();
  });

  await agent.start();
  await waitFor(() => agent.state.authenticated === true);
  assert.equal(agent.state.connected, true);
  assert.equal(agent.state.authenticated, true);
});

test('agent reconnects after relay restart on same port', async (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-link-reconnect-'));
  const registry = new SessionRegistry();
  registry.devices.set('pc-test', {
    device_id: 'pc-test',
    public_identity: 'test',
    device_token: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
  });

  let relay = createRelayServer({
    ownerToken: 'owner-test-token',
    registry,
  });
  const firstAddress = await relay.start(0);
  const relayUrl = `http://127.0.0.1:${firstAddress.port}`;

  const agent = createPcAgent({
    relayUrl,
    deviceId: 'pc-test',
    deviceToken: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
    policy: createPolicy(),
    auditPath: path.join(temp, 'audit.jsonl'),
    killSwitchPath: path.join(temp, 'STOP'),
    reconnectBaseMs: 20,
  });

  t.after(async () => {
    await agent.stop();
    await relay.stop();
  });

  await agent.start();
  await waitFor(() => agent.state.authenticated === true);

  await relay.stop();
  await waitFor(() => agent.state.connected === false);

  relay = createRelayServer({
    ownerToken: 'owner-test-token',
    registry,
  });
  await relay.start(firstAddress.port);

  await waitFor(() => agent.state.connected === true && agent.state.authenticated === true);
  assert.equal(agent.state.connected, true);
  assert.equal(agent.state.authenticated, true);
});

const crypto = require('node:crypto');
const { io: createClient } = require('socket.io-client');
const { createRequestEnvelope } = require('../protocol/envelope');

async function requestThroughRelay({
  relayUrl,
  ownerToken,
  deviceId,
  action,
  capability,
  params = {},
}) {
  const socket = createClient(relayUrl, { autoConnect: false, timeout: 3000 });
  const requestId = crypto.randomUUID();

  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Relay connect timeout')), 3000);
      socket.once('connect', () => {
        clearTimeout(timer);
        resolve();
      });
      socket.once('connect_error', error => {
        clearTimeout(timer);
        reject(error);
      });
      socket.connect();
    });

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

    return await new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error('Timed out waiting for response')),
        3000
      );
      socket.once(`client:response:${requestId}`, response => {
        clearTimeout(timer);
        resolve(response);
      });
      socket.emit('client:request', envelope);
    });
  } finally {
    socket.disconnect();
  }
}

async function startRoundtripFixture(t) {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-link-e2e-'));
  const relay = createRelayServer({ ownerToken: 'owner-test-token' });
  const address = await relay.start(0);
  const relayUrl = `http://127.0.0.1:${address.port}`;

  relay.registry.devices.set('pc-test', {
    device_id: 'pc-test',
    public_identity: 'test',
    device_token: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
  });

  const policy = {
    capabilities: {
      'system.read': true,
      'file.read': true,
      'command.execute.safe': true,
    },
    roots: {
      'file.read': [temp],
      'file.write': [temp],
    },
    commands: {
      safe: ['node'],
      blocked_patterns: ['diskpart'],
    },
    limits: {
      max_command_ms: 1000,
      max_output_bytes: 4096,
      max_read_bytes: 4096,
      max_write_bytes: 4096,
    },
  };

  const agent = createPcAgent({
    relayUrl,
    deviceId: 'pc-test',
    deviceToken: 'device-test-token-abcdefghijklmnopqrstuvwxyz',
    policy,
    auditPath: path.join(temp, 'audit.jsonl'),
    killSwitchPath: path.join(temp, 'STOP'),
    reconnectBaseMs: 20,
  });

  t.after(async () => {
    await agent.stop();
    await relay.stop();
  });

  await agent.start();
  await waitFor(() => agent.state.authenticated === true);
  return { temp, relayUrl };
}

test('authenticated device_info roundtrip returns platform identity', async (t) => {
  const { relayUrl } = await startRoundtripFixture(t);
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

test('read_file allows inside root and denies outside root', async (t) => {
  const { temp, relayUrl } = await startRoundtripFixture(t);
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
  assert.equal(allowed.result.sha256.length, 64);

  const denied = await requestThroughRelay({
    relayUrl,
    ownerToken: 'owner-test-token',
    deviceId: 'pc-test',
    action: 'read_file',
    capability: 'file.read',
    params: { path: path.resolve(temp, '..', 'outside.txt'), encoding: 'utf8' },
  });

  assert.equal(denied.status, 'error');
  assert.match(denied.error.message, /outside approved roots/);
});

test('run_command allows allowlisted node and denies unknown executable', async (t) => {
  const { relayUrl } = await startRoundtripFixture(t);

  const allowed = await requestThroughRelay({
    relayUrl,
    ownerToken: 'owner-test-token',
    deviceId: 'pc-test',
    action: 'run_command',
    capability: 'command.execute.safe',
    params: {
      executable: 'node',
      args: ['-e', 'console.log("kai-command-ok")'],
      timeout_ms: 1000,
    },
  });

  assert.equal(allowed.status, 'ok');
  assert.match(allowed.result.stdout, /kai-command-ok/);
  assert.equal(typeof allowed.audit_id, 'string');

  const denied = await requestThroughRelay({
    relayUrl,
    ownerToken: 'owner-test-token',
    deviceId: 'pc-test',
    action: 'run_command',
    capability: 'command.execute.safe',
    params: { executable: 'definitely-not-allowed', args: [] },
  });

  assert.equal(denied.status, 'error');
  assert.match(denied.error.message, /not allowlisted/);
});
