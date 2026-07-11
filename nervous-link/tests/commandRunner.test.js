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

const strictPolicy = {
  commands: {
    safe: ['node'],
    require_arg_rules: true,
    rules: {
      node: { allowed_argv: [['--version']] },
    },
    blocked_patterns: [],
  },
  limits: { max_command_ms: 2000, max_output_bytes: 256 },
};

test('strict argument rules allow only approved argv shape', async () => {
  const result = await runCommand({ executable: 'node', args: ['--version'] }, strictPolicy);
  assert.equal(result.exit_code, 0);
  assert.match(result.stdout, /^v\d+/);
});

test('strict argument rules reject arbitrary runtime eval', async () => {
  await assert.rejects(
    () => runCommand({ executable: 'node', args: ['-e', 'console.log("unsafe")'] }, strictPolicy),
    /arguments are not approved/i
  );
});
