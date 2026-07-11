const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { readFile, writeFileAtomic, listDirectory } = require('../pc-agent/fileOps');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-files-'));
const policy = {
  roots: { 'file.read': [root], 'file.write': [root] },
  limits: { max_read_bytes: 1024, max_write_bytes: 1024 },
};

test('writes atomically and reads text with sha256', async () => {
  const target = path.join(root, 'hello.txt');
  await writeFileAtomic({ path: target, text: 'hola' }, policy);
  const result = await readFile({ path: target, encoding: 'utf8', sha256: true }, policy);
  assert.equal(result.text, 'hola');
  assert.equal(result.sha256.length, 64);
});

test('lists directory entries', async () => {
  const result = await listDirectory({ path: root }, policy);
  assert.ok(result.entries.some(entry => entry.name === 'hello.txt'));
});
