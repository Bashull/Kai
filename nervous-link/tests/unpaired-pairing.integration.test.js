const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { createRelayServer } = require('../relay/server');
const { createPcAgent } = require('../pc-agent/agent');

async function waitFor(predicate, timeoutMs = 5000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('Condition not met before timeout');
}

const policy = {
  capabilities: { 'system.read': true },
  roots: {},
  commands: { safe: [], blocked_patterns: [] },
  limits: {},
};

test('unpaired agent announces, receives approval, persists credential and authenticates', async (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-unpaired-'));
  const credentialPath = path.join(temp, 'device.json');
  const relay = createRelayServer({ ownerToken: 'owner-test-token' });
  const address = await relay.start(0);
  const relayUrl = `http://127.0.0.1:${address.port}`;

  const agent = createPcAgent({
    relayUrl,
    deviceId: 'pc-unpaired',
    policy,
    auditPath: path.join(temp, 'audit.jsonl'),
    killSwitchPath: path.join(temp, 'STOP'),
    credentialPath,
    pairingCode: 'A7K9M2Q4',
    publicIdentity: 'test-public-identity',
    reconnectBaseMs: 20,
  });

  t.after(async () => {
    await agent.stop();
    await relay.stop();
  });

  await agent.start();
  await waitFor(() => Boolean(agent.state.pairing?.pairing_id));

  const response = await fetch(`${relayUrl}/pair/approve`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: 'Bearer owner-test-token',
    },
    body: JSON.stringify({
      pairing_id: agent.state.pairing.pairing_id,
      code: 'A7K9M2Q4',
    }),
  });

  assert.equal(response.ok, true);
  await waitFor(() => agent.state.authenticated === true);

  const persisted = JSON.parse(fs.readFileSync(credentialPath, 'utf8'));
  assert.equal(persisted.device_id, 'pc-unpaired');
  assert.equal(typeof persisted.device_token, 'string');
  assert.ok(persisted.device_token.length >= 32);
  assert.equal(agent.state.authenticated, true);
});
