const test = require('node:test');
const assert = require('node:assert/strict');
const { runCommand } = require('../pc-agent/commandRunner');

const policy = {
  commands: { safe: ['node'], blocked_patterns: ['diskpart', 'blocked-marker'] },
  limits: { max_command_ms: 500, max_output_bytes: 64 },
};

test('executes an allowlisted executable with argv', async () => {
  const result = await runCommand({
    executable: 'node',
    args: ['-e', 'console.log("ok")'],
    timeout_ms: 500,
  }, policy);
  assert.equal(result.exit_code, 0);
  assert.match(result.stdout, /ok/);
});

test('rejects non-allowlisted executable', async () => {
  await assert.rejects(
    () => runCommand({ executable: 'definitely-not-allowed', args: [] }, policy),
    /not allowlisted/
  );
});

test('times out long running command', async () => {
  await assert.rejects(
    () => runCommand({
      executable: 'node',
      args: ['-e', 'setTimeout(()=>{}, 5000)'],
      timeout_ms: 50,
    }, policy),
    /timed out/
  );
});

test('truncates oversized output', async () => {
  const result = await runCommand({
    executable: 'node',
    args: ['-e', 'console.log("x".repeat(1000))'],
  }, policy);
  assert.equal(result.truncated, true);
  assert.ok(Buffer.byteLength(result.stdout) <= 64);
});

test('rejects blocked pattern even for allowlisted executable', async () => {
  await assert.rejects(
    () => runCommand({ executable: 'node', args: ['-e', 'console.log("blocked-marker")'] }, policy),
    /blocked pattern/
  );
});
