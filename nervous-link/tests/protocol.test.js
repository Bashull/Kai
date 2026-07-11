const test = require('node:test');
const assert = require('node:assert/strict');
const {
  createRequestEnvelope,
  createResponseEnvelope,
  validateRequestEnvelope,
} = require('../protocol/envelope');
const { ProtocolError } = require('../protocol/errors');

const base = () => ({
  request_id: 'req-1',
  session_id: 'sess-1',
  device_id: 'pc-asier-main',
  timestamp: new Date().toISOString(),
  action: 'device_info',
  params: {},
  capability: 'system.read',
  nonce: 'nonce-1234567890',
  signature: 'proof',
});

test('creates and validates a v0.1 request envelope', () => {
  const envelope = createRequestEnvelope(base());
  assert.equal(validateRequestEnvelope(envelope).ok, true);
});

test('rejects unknown protocol version', () => {
  const envelope = { ...createRequestEnvelope(base()), protocol: 'kai-nervous-link/9.9' };
  assert.throws(() => validateRequestEnvelope(envelope), ProtocolError);
});

test('rejects stale timestamps', () => {
  const envelope = createRequestEnvelope({
    ...base(),
    timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
  });
  assert.throws(
    () => validateRequestEnvelope(envelope, { maxClockSkewMs: 60_000 }),
    error => error.code === 'STALE_TIMESTAMP'
  );
});

test('creates a correlated response envelope', () => {
  const response = createResponseEnvelope({
    request_id: 'req-1',
    status: 'ok',
    started_at: '2026-07-11T00:00:00.000Z',
    finished_at: '2026-07-11T00:00:01.000Z',
    result: { online: true },
    audit_id: 'audit-1',
  });
  assert.equal(response.request_id, 'req-1');
  assert.equal(response.error, null);
});
