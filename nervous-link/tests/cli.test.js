const test = require('node:test');
const assert = require('node:assert/strict');
const { parseArgs } = require('../clients/cli/kai-link');

test('parseArgs converts command and option pairs', () => {
  const parsed = parseArgs([
    'call',
    '--relay', 'https://relay.example',
    '--device', 'pc-asier-main',
    '--action', 'device_info',
  ]);

  assert.deepEqual(parsed, {
    command: 'call',
    relay: 'https://relay.example',
    device: 'pc-asier-main',
    action: 'device_info',
  });
});

test('parseArgs rejects option missing a value', () => {
  assert.throws(() => parseArgs(['call', '--relay']), /missing value/i);
});
