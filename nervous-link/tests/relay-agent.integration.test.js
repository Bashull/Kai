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
