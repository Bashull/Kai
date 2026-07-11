const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { AuditLog } = require('../pc-agent/audit');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-audit-'));
const file = path.join(dir, 'audit.jsonl');

test('redacts secret-like keys before append', async () => {
  const audit = new AuditLog(file);
  await audit.append({
    action: 'test',
    params: {
      token: 'abc',
      safe: 'ok',
      nested: { api_key: 'xyz', visible: 'yes' },
    },
  });
  const rows = await audit.read(10);
  assert.equal(rows[0].params.token, '<REDACTED>');
  assert.equal(rows[0].params.nested.api_key, '<REDACTED>');
  assert.equal(rows[0].params.safe, 'ok');
});

test('append preserves multiple audit rows in order', async () => {
  const audit = new AuditLog(file);
  await audit.append({ action: 'second' });
  await audit.append({ action: 'third' });
  const rows = await audit.read(10);
  assert.deepEqual(rows.slice(-2).map(row => row.action), ['second', 'third']);
});
