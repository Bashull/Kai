const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { authorizeAction, assertPathAllowed } = require('../pc-agent/policy');

const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-policy-'));
const policy = {
  default: 'deny',
  capabilities: {
    'system.read': true,
    'file.read': true,
    'file.write': false,
    'command.execute.safe': true,
  },
  roots: {
    'file.read': [tempRoot],
    'file.write': [],
  },
  commands: {
    safe: ['node'],
    blocked_patterns: ['diskpart', 'format'],
  },
};

test('default deny rejects unknown capability', () => {
  assert.equal(authorizeAction(policy, { capability: 'git.write' }).allowed, false);
});

test('explicit capability allow succeeds', () => {
  assert.equal(authorizeAction(policy, { capability: 'system.read' }).allowed, true);
});

test('allows path inside approved root', () => {
  const target = path.join(tempRoot, 'hello.txt');
  assert.equal(assertPathAllowed(policy, 'file.read', target), path.resolve(target));
});

test('rejects traversal outside approved root', () => {
  const target = path.resolve(tempRoot, '..', 'outside.txt');
  assert.throws(() => assertPathAllowed(policy, 'file.read', target), /outside approved roots/);
});

test('rejects symlink escape when symlink creation is available', (t) => {
  const inside = path.join(tempRoot, 'link');
  const outsideRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-outside-'));
  try {
    fs.symlinkSync(outsideRoot, inside, 'junction');
  } catch (error) {
    t.skip(`symlink/junction creation unavailable: ${error.code}`);
    return;
  }

  const escapedTarget = path.join(inside, 'escape.txt');
  assert.throws(() => assertPathAllowed(policy, 'file.read', escapedTarget), /outside approved roots/);
});
