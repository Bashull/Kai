'use strict';

const { spawn } = require('node:child_process');
const { assertPathAllowed } = require('./policy');
const { truncateUtf8 } = require('./commandRunner');

const PLAYBOOK_ID_RE = /^[a-z0-9][a-z0-9._-]{0,63}$/;
const REQUEST_KEYS = new Set(['playbook_id']);
const PLAYBOOK_KEYS = new Set(['executable', 'argv', 'cwd', 'timeout_ms']);

function assertPlainObject(value, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
}

function assertExactKeys(object, allowed, label) {
  for (const key of Object.keys(object)) {
    if (!allowed.has(key)) {
      throw new Error(`${label} contains unexpected parameter: ${key}`);
    }
  }
}

function normalizePlaybook(input, policy) {
  assertPlainObject(input, 'Recovery request');
  assertExactKeys(input, REQUEST_KEYS, 'Recovery request');

  const playbookId = input.playbook_id;
  if (typeof playbookId !== 'string' || !PLAYBOOK_ID_RE.test(playbookId)) {
    throw new Error('Invalid recovery playbook id');
  }

  const playbook = policy?.recovery?.playbooks?.[playbookId];
  if (!playbook) {
    throw new Error(`Recovery playbook is not configured: ${playbookId}`);
  }

  assertPlainObject(playbook, 'Recovery playbook');
  assertExactKeys(playbook, PLAYBOOK_KEYS, 'Recovery playbook');

  if (typeof playbook.executable !== 'string' || playbook.executable.length === 0) {
    throw new Error(`Recovery playbook executable is invalid: ${playbookId}`);
  }

  if (!Array.isArray(playbook.argv) || !playbook.argv.every(value => typeof value === 'string')) {
    throw new Error(`Recovery playbook argv is invalid: ${playbookId}`);
  }

  let cwd;
  if (playbook.cwd !== undefined) {
    if (typeof playbook.cwd !== 'string' || playbook.cwd.length === 0) {
      throw new Error(`Recovery playbook cwd is invalid: ${playbookId}`);
    }
    cwd = assertPathAllowed(policy, 'file.read', playbook.cwd);
  }

  const policyMaxMs = Number(policy?.limits?.max_command_ms ?? 30000);
  const configuredMs = Number(playbook.timeout_ms ?? policyMaxMs);
  if (!Number.isFinite(policyMaxMs) || policyMaxMs <= 0 || !Number.isFinite(configuredMs) || configuredMs <= 0) {
    throw new Error(`Recovery playbook timeout is invalid: ${playbookId}`);
  }
  const timeoutMs = Math.max(1, Math.min(configuredMs, policyMaxMs));

  const maxOutput = Number(policy?.limits?.max_output_bytes ?? 1048576);
  if (!Number.isFinite(maxOutput) || maxOutput <= 0) {
    throw new Error('Recovery playbook output limit is invalid');
  }

  return {
    playbookId,
    executable: playbook.executable,
    argv: playbook.argv,
    cwd,
    timeoutMs,
    maxOutput,
  };
}

function runRecoveryPlaybook(input, policy) {
  const spec = normalizePlaybook(input, policy);

  return new Promise((resolve, reject) => {
    const child = spawn(spec.executable, spec.argv, {
      cwd: spec.cwd,
      shell: false,
      windowsHide: true,
      env: process.env,
    });

    let stdout = '';
    let stderr = '';
    let truncated = false;
    let settled = false;

    const appendBounded = (current, chunk) => {
      const combined = `${current}${chunk.toString('utf8')}`;
      const bounded = truncateUtf8(combined, spec.maxOutput);
      truncated = truncated || bounded.truncated;
      return bounded.text;
    };

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill('SIGTERM');
      reject(new Error(`Recovery playbook timed out after ${spec.timeoutMs} ms`));
    }, spec.timeoutMs);

    child.stdout.on('data', chunk => {
      stdout = appendBounded(stdout, chunk);
    });

    child.stderr.on('data', chunk => {
      stderr = appendBounded(stderr, chunk);
    });

    child.on('error', error => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(error);
    });

    child.on('close', code => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({
        playbook_id: spec.playbookId,
        exit_code: code,
        stdout,
        stderr,
        truncated,
      });
    });
  });
}

module.exports = {
  runRecoveryPlaybook,
  normalizePlaybook,
  PLAYBOOK_ID_RE,
};
