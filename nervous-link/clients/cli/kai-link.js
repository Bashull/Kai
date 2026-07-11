#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const { io } = require('socket.io-client');
const { createRequestEnvelope } = require('../../protocol/envelope');

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const args = { command };

  for (let index = 0; index < rest.length; index += 2) {
    const key = rest[index];
    const value = rest[index + 1];
    if (!key?.startsWith('--')) {
      throw new Error(`Invalid option: ${key}`);
    }
    if (value === undefined || value.startsWith('--')) {
      throw new Error(`Missing value for option: ${key}`);
    }
    args[key.replace(/^--/, '')] = value;
  }

  return args;
}

function requireOption(args, key) {
  if (!args[key]) throw new Error(`Missing required option: --${key}`);
  return args[key];
}

async function pair(args) {
  const relay = requireOption(args, 'relay');
  const pairingId = requireOption(args, 'pairing-id');
  const code = requireOption(args, 'code');
  const ownerToken = process.env.KAI_NERVOUS_LINK_OWNER_TOKEN;
  if (!ownerToken) {
    throw new Error('KAI_NERVOUS_LINK_OWNER_TOKEN is required');
  }

  const response = await fetch(`${relay}/pair/approve`, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${ownerToken}`,
    },
    body: JSON.stringify({ pairing_id: pairingId, code }),
  });

  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error ?? `HTTP ${response.status}`);
  }

  const printable = { ...body };
  if (printable.device_token) printable.device_token = '<REDACTED>';
  console.log(JSON.stringify(printable, null, 2));
  return body;
}

async function call(args) {
  const relay = requireOption(args, 'relay');
  const device = requireOption(args, 'device');
  const action = requireOption(args, 'action');
  const capability = requireOption(args, 'capability');
  const ownerToken = process.env.KAI_NERVOUS_LINK_OWNER_TOKEN;
  if (!ownerToken) {
    throw new Error('KAI_NERVOUS_LINK_OWNER_TOKEN is required');
  }

  const requestId = crypto.randomUUID();
  const envelope = createRequestEnvelope({
    request_id: requestId,
    session_id: crypto.randomUUID(),
    device_id: device,
    timestamp: new Date().toISOString(),
    action,
    params: JSON.parse(args.params ?? '{}'),
    capability,
    nonce: crypto.randomBytes(18).toString('base64url'),
    signature: 'relay-owner-token-auth',
    owner_token: ownerToken,
    actor_id: 'asier-cli',
  });

  const socket = io(relay, { autoConnect: false, timeout: 5000 });
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Relay connect timeout')), 5000);
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

    const response = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Request timeout')), 30000);
      socket.once(`client:response:${requestId}`, payload => {
        clearTimeout(timer);
        resolve(payload);
      });
      socket.emit('client:request', envelope);
    });

    console.log(JSON.stringify(response, null, 2));
    return response;
  } finally {
    socket.disconnect();
  }
}

async function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.command === 'pair') return pair(args);
  if (args.command === 'call') return call(args);
  throw new Error('Usage: kai-link.js pair|call [options]');
}

if (require.main === module) {
  main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = {
  parseArgs,
  pair,
  call,
  main,
};
