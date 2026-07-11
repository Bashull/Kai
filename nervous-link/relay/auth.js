'use strict';

const crypto = require('node:crypto');

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`;
  }

  if (value && typeof value === 'object') {
    const pairs = Object.keys(value)
      .sort()
      .map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`);
    return `{${pairs.join(',')}}`;
  }

  return JSON.stringify(value);
}

function createHmacProof(secret, payload) {
  return crypto
    .createHmac('sha256', secret)
    .update(stableStringify(payload))
    .digest('base64url');
}

function verifyHmacProof(secret, payload, proof) {
  try {
    const expected = Buffer.from(createHmacProof(secret, payload), 'base64url');
    const actual = Buffer.from(String(proof ?? ''), 'base64url');
    return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
  } catch {
    return false;
  }
}

module.exports = {
  stableStringify,
  createHmacProof,
  verifyHmacProof,
};
