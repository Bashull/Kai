'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { createPcAgent } = require('../pc-agent/agent');
const { loadPolicy } = require('../pc-agent/policy');
const { readCredentials } = require('../pc-agent/credentials');

function expandHome(value) {
  if (typeof value !== 'string') return value;
  return value
    .replace('%USERPROFILE%', os.homedir())
    .replace(/^~(?=$|[\\/])/, os.homedir());
}

async function main() {
  const projectRoot = path.join(__dirname, '..');
  const configPath = process.env.KAI_NERVOUS_LINK_AGENT_CONFIG
    ?? path.join(projectRoot, 'config', 'agent.local.json');
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  const credentialPath = expandHome(config.credential_path);
  const credentials = await readCredentials(credentialPath);
  const policy = loadPolicy(path.resolve(projectRoot, config.policy_path));

  const agent = createPcAgent({
    relayUrl: config.relay_url,
    deviceId: config.device_id,
    deviceToken: credentials?.device_token ?? null,
    credentialPath,
    publicIdentity: config.public_identity,
    policy,
    auditPath: expandHome(config.audit_path),
    killSwitchPath: expandHome(config.kill_switch_path),
    onPairingAnnounced: pairing => {
      console.log('KAI Nervous Link pairing required.');
      console.log(`pairing_id=${pairing.pairing_id}`);
      console.log(`code=${pairing.code}`);
      console.log(`expires_at=${new Date(pairing.expires_at).toISOString()}`);
    },
  });

  await agent.start();
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
