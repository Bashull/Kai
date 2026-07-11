'use strict';

const crypto = require('node:crypto');

function sha256Bytes(value) {
  return crypto.createHash('sha256').update(String(value)).digest();
}

class SessionRegistry {
  constructor() {
    this.pairings = new Map();
    this.devices = new Map();
    this.agentSockets = new Map();
  }

  announcePairing({ device_id, code, public_identity, ttl_ms = 10 * 60_000 }) {
    if (!device_id || !code || !public_identity) {
      throw new Error('device_id, code and public_identity are required');
    }
    if (!Number.isFinite(ttl_ms) || ttl_ms <= 0) {
      throw new Error('ttl_ms must be a positive number');
    }

    const pairing_id = crypto.randomUUID();
    const row = {
      pairing_id,
      device_id,
      code_hash: sha256Bytes(code),
      public_identity,
      expires_at: Date.now() + ttl_ms,
    };

    this.pairings.set(pairing_id, row);
    return { pairing_id, device_id, expires_at: row.expires_at };
  }

  approvePairing({ pairing_id, code }) {
    const row = this.pairings.get(pairing_id);
    if (!row || row.expires_at < Date.now()) {
      throw new Error('Pairing request missing or expired');
    }

    const expected = row.code_hash;
    const actual = sha256Bytes(code);
    if (expected.length !== actual.length || !crypto.timingSafeEqual(expected, actual)) {
      throw new Error('Invalid pairing code');
    }

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
    if (current?.id === socketId) {
      this.agentSockets.delete(device_id);
    }
  }

  getAgentSocket(device_id) {
    return this.agentSockets.get(device_id) ?? null;
  }
}

module.exports = { SessionRegistry };
