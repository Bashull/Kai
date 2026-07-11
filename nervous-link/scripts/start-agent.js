'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { createPcAgent } = require('../pc-agent/agent');
const { loadPolicy } = require('../pc-agent/policy');

function expandHome(value) {
  if (typeof value !== 'string') return value;
  return value
    .replace('%USERPROFILE%', os.homedir())
    .replace(/^~(?=$|[\\/])/, os.homedir());
}

const projectRoot = path.join(__dirname, '..');
const configPath = process.env.KAI_NERVOUS_LINK_AGENT_CONFIG
  ?? path.join(projectRoot, 'config', 'agent.local.json');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const credentials = JSON.parse(
  fs.readFileSync(expandHome(config.credential_path), 'utf8')
);
const policy = loadPolicy(path.resolve(projectRoot, config.policy_path));

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
