const test = require('node:test');
const assert = require('node:assert/strict');

test('tool engine resolves the backend database module', () => {
  assert.doesNotThrow(() => require('../backend/toolEngine'));
});

test('learning engine resolves the backend database module', () => {
  assert.doesNotThrow(() => require('../backend/learningEngine'));
});
