'use strict';

class ReplayGuard {
  constructor({ ttlMs = 120_000 } = {}) {
    this.ttlMs = ttlMs;
    this.nonces = new Map();
  }

  checkAndRemember(nonce, timestampMs = Date.now()) {
    if (typeof nonce !== 'string' || nonce.length < 12) {
      throw new Error('Nonce must be at least 12 characters');
    }
    if (!Number.isFinite(timestampMs)) {
      throw new Error('Timestamp outside replay window');
    }

    const now = Date.now();
    for (const [value, seenAt] of this.nonces) {
      if (now - seenAt > this.ttlMs) {
        this.nonces.delete(value);
      }
    }

    if (this.nonces.has(nonce)) {
      throw new Error(`Replay detected for nonce: ${nonce}`);
    }

    if (Math.abs(now - timestampMs) > this.ttlMs) {
      throw new Error('Timestamp outside replay window');
    }

    this.nonces.set(nonce, now);
  }
}

module.exports = { ReplayGuard };
