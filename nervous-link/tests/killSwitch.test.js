const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('node:os');
const path = require('node:path');
const fs = require('node:fs');
const { KillSwitch } = require('../pc-agent/killSwitch');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-kill-'));
const flag = path.join(dir, 'STOP');

test('trigger persists stop state and assertActive rejects', async () => {
  const kill = new KillSwitch(flag);
  await kill.trigger('test');
  assert.equal(await kill.isTriggered(), true);
  await assert.rejects(() => kill.assertActive(), /kill switch/i);

  const persisted = JSON.parse(fs.readFileSync(flag, 'utf8'));
  assert.equal(persisted.reason, 'test');
  assert.equal(typeof persisted.timestamp, 'string');
});
