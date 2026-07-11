const test = require('node:test');
const assert = require('node:assert/strict');
const { ReplayGuard } = require('../relay/replayGuard');
const { SessionRegistry } = require('../relay/sessionRegistry');
const { createHmacProof, verifyHmacProof } = require('../relay/auth');

test('replay guard rejects same nonce twice', () => {
  const guard = new ReplayGuard({ ttlMs: 60_000 });
  guard.checkAndRemember('nonce-abcdefghijkl', Date.now());
  assert.throws(
    () => guard.checkAndRemember('nonce-abcdefghijkl', Date.now()),
    /replay/i
  );
});

test('replay guard rejects timestamp outside window', () => {
  const guard = new ReplayGuard({ ttlMs: 1_000 });
  assert.throws(
    () => guard.checkAndRemember('nonce-abcdefghijkl', Date.now() - 10_000),
    /outside replay window/i
  );
});

test('pairing requires correct short-lived code and owner approval', () => {
  const registry = new SessionRegistry();
  const announced = registry.announcePairing({
    device_id: 'pc-asier-main',
    code: 'A7K9M2Q4',
    public_identity: 'ed25519-public-key-placeholder',
    ttl_ms: 60_000,
  });

  assert.throws(
    () => registry.approvePairing({ pairing_id: announced.pairing_id, code: 'WRONG' }),
    /invalid pairing code/i
  );

  const approved = registry.approvePairing({
    pairing_id: announced.pairing_id,
    code: 'A7K9M2Q4',
  });
  assert.equal(approved.device_id, 'pc-asier-main');
  assert.equal(typeof approved.device_token, 'string');
  assert.ok(approved.device_token.length >= 32);
});

test('HMAC proof is stable and rejects tampered payload', () => {
  const secret = 'device-secret-abcdefghijklmnopqrstuvwxyz';
  const payload = { z: 2, a: { y: true, x: 1 } };
  const proof = createHmacProof(secret, payload);

  assert.equal(verifyHmacProof(secret, payload, proof), true);
  assert.equal(verifyHmacProof(secret, { ...payload, z: 3 }, proof), false);
});
