const test = require('node:test');
const assert = require('node:assert/strict');
const { runRecoveryPlaybook } = require('../pc-agent/recoveryPlaybook');

function makePolicy(overrides = {}) {
  return {
    recovery: {
      playbooks: {
        echo: {
          executable: process.execPath,
          argv: ['-e', 'process.stdout.write("ok")'],
        },
        loud: {
          executable: process.execPath,
          argv: ['-e', 'process.stdout.write("x".repeat(1000)); process.stderr.write("y".repeat(1000))'],
        },
        slow: {
          executable: process.execPath,
          argv: ['-e', 'setTimeout(()=>{}, 5000)'],
          timeout_ms: 5000,
        },
      },
    },
    limits: {
      max_command_ms: 150,
      max_output_bytes: 64,
    },
    ...overrides,
  };
}

test('executes only the exact policy-defined recovery playbook', async () => {
  const result = await runRecoveryPlaybook({ playbook_id: 'echo' }, makePolicy());
  assert.equal(result.exit_code, 0);
  assert.equal(result.stdout, 'ok');
  assert.equal(result.stderr, '');
  assert.equal(result.playbook_id, 'echo');
});

test('rejects an unknown recovery playbook id', async () => {
  await assert.rejects(
    () => runRecoveryPlaybook({ playbook_id: 'missing' }, makePolicy()),
    /not configured|unknown/i
  );
});

test('rejects malformed recovery playbook ids', async () => {
  for (const playbook_id of ['', '../escape', 'has space', 'UPPER', 'x'.repeat(65)]) {
    await assert.rejects(
      () => runRecoveryPlaybook({ playbook_id }, makePolicy()),
      /playbook.*id|invalid/i
    );
  }
});

test('rejects remote argument or environment injection instead of ignoring it', async () => {
  await assert.rejects(
    () => runRecoveryPlaybook({ playbook_id: 'echo', args: ['-e', 'process.exit(9)'] }, makePolicy()),
    /only.*playbook_id|unexpected.*param/i
  );
  await assert.rejects(
    () => runRecoveryPlaybook({ playbook_id: 'echo', env: { PWNED: '1' } }, makePolicy()),
    /only.*playbook_id|unexpected.*param/i
  );
});

test('clamps a playbook timeout to the global command timeout', async () => {
  const started = Date.now();
  await assert.rejects(
    () => runRecoveryPlaybook({ playbook_id: 'slow' }, makePolicy()),
    /timed out/i
  );
  assert.ok(Date.now() - started < 1500);
});

test('bounds stdout and stderr using the global output limit', async () => {
  const result = await runRecoveryPlaybook({ playbook_id: 'loud' }, makePolicy());
  assert.equal(result.exit_code, 0);
  assert.equal(result.truncated, true);
  assert.ok(Buffer.byteLength(result.stdout) <= 64);
  assert.ok(Buffer.byteLength(result.stderr) <= 64);
});

test('rejects unsafe playbook configuration shapes', async () => {
  const policy = makePolicy();
  policy.recovery.playbooks.badShell = {
    executable: process.execPath,
    argv: ['--version'],
    shell: true,
  };
  policy.recovery.playbooks.badEnv = {
    executable: process.execPath,
    argv: ['--version'],
    env: { PWNED: '1' },
  };

  await assert.rejects(
    () => runRecoveryPlaybook({ playbook_id: 'badShell' }, policy),
    /unsupported.*config|shell/i
  );
  await assert.rejects(
    () => runRecoveryPlaybook({ playbook_id: 'badEnv' }, policy),
    /unsupported.*config|env/i
  );
});
