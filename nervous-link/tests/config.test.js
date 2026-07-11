'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { loadJsonFile } = require('../pc-agent/jsonConfig');

test('loads UTF-8 JSON with BOM on Windows', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-json-bom-'));
  const file = path.join(dir, 'config.json');
  fs.writeFileSync(file, '\uFEFF{"ok":true}', 'utf8');

  const value = loadJsonFile(file);

  assert.deepEqual(value, { ok: true });
});
