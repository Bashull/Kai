'use strict';

const { PROTOCOL_VERSION, ACTIONS, CAPABILITIES } = require('./constants');
const { ProtocolError } = require('./errors');

const REQUIRED_REQUEST_FIELDS = [
  'protocol',
  'request_id',
  'session_id',
  'device_id',
  'timestamp',
  'action',
  'params',
  'capability',
  'nonce',
  'signature',
];

function createRequestEnvelope(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new ProtocolError('INVALID_ENVELOPE', 'Request envelope input must be an object');
  }

  return { protocol: PROTOCOL_VERSION, ...input };
}

function validateRequestEnvelope(envelope, options = {}) {
  const maxClockSkewMs = options.maxClockSkewMs ?? 120_000;
  const nowMs = options.nowMs ?? Date.now();

  if (!envelope || typeof envelope !== 'object' || Array.isArray(envelope)) {
    throw new ProtocolError('INVALID_ENVELOPE', 'Request envelope must be an object');
  }

  for (const field of REQUIRED_REQUEST_FIELDS) {
    if (!(field in envelope)) {
      throw new ProtocolError('MISSING_FIELD', `Missing required field: ${field}`, { field });
    }
  }

  if (envelope.protocol !== PROTOCOL_VERSION) {
    throw new ProtocolError('UNSUPPORTED_PROTOCOL', `Unsupported protocol: ${envelope.protocol}`);
  }

  if (!ACTIONS.includes(envelope.action)) {
    throw new ProtocolError('UNKNOWN_ACTION', `Unknown action: ${envelope.action}`);
  }

  if (!CAPABILITIES.includes(envelope.capability)) {
    throw new ProtocolError('UNKNOWN_CAPABILITY', `Unknown capability: ${envelope.capability}`);
  }

  const timestampMs = Date.parse(envelope.timestamp);
  if (!Number.isFinite(timestampMs)) {
    throw new ProtocolError('INVALID_TIMESTAMP', 'timestamp must be RFC3339-compatible');
  }

  if (Math.abs(nowMs - timestampMs) > maxClockSkewMs) {
    throw new ProtocolError(
      'STALE_TIMESTAMP',
      'Request timestamp is outside the allowed clock skew'
    );
  }

  if (typeof envelope.nonce !== 'string' || envelope.nonce.length < 12) {
    throw new ProtocolError('INVALID_NONCE', 'nonce must be at least 12 characters');
  }

  if (!envelope.params || typeof envelope.params !== 'object' || Array.isArray(envelope.params)) {
    throw new ProtocolError('INVALID_PARAMS', 'params must be an object');
  }

  return { ok: true };
}

function createResponseEnvelope(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new ProtocolError('INVALID_RESPONSE', 'Response input must be an object');
  }

  return {
    protocol: PROTOCOL_VERSION,
    request_id: input.request_id,
    status: input.status,
    started_at: input.started_at,
    finished_at: input.finished_at,
    result: input.result ?? null,
    error: input.error ?? null,
    audit_id: input.audit_id,
  };
}

module.exports = {
  createRequestEnvelope,
  createResponseEnvelope,
  validateRequestEnvelope,
};
