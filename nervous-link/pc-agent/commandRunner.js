'use strict';

const path = require('node:path');
const { spawn } = require('node:child_process');
const { assertPathAllowed } = require('./policy');

function truncateUtf8(text, maxBytes) {
  const buffer = Buffer.from(text, 'utf8');
  if (buffer.length <= maxBytes) {
    return { text, truncated: false };
  }

  return {
    text: buffer.subarray(0, maxBytes).toString('utf8'),
    truncated: true,
  };
}

function validateExecutableName(executable) {
  if (typeof executable !== 'string' || executable.length === 0) {
    throw new Error('Executable must be a non-empty string');
  }
  if (path.isAbsolute(executable) || executable !== path.basename(executable)) {
    throw new Error('Executable must be a bare allowlisted command name');
  }
}

function runCommand(input, policy) {
  validateExecutableName(input.executable);
  const allowed = new Set(policy.commands?.safe ?? []);
  if (!allowed.has(input.executable)) {
    return Promise.reject(new Error(`Executable is not allowlisted: ${input.executable}`));
  }

  const args = Array.isArray(input.args) ? input.args.map(String) : [];
  const joined = `${input.executable} ${args.join(' ')}`.toLowerCase();
  for (const pattern of policy.commands?.blocked_patterns ?? []) {
    if (joined.includes(String(pattern).toLowerCase())) {
      return Promise.reject(new Error(`Command matches blocked pattern: ${pattern}`));
    }
  }

  if (policy.commands?.require_arg_rules === true) {
    const allowedArgv = policy.commands?.rules?.[input.executable]?.allowed_argv ?? [];
    const approved = allowedArgv.some(candidate =>
      Array.isArray(candidate) &&
      candidate.length === args.length &&
      candidate.every((value, index) => String(value) === args[index])
    );

    if (!approved) {
      return Promise.reject(new Error(`Arguments are not approved for: ${input.executable}`));
    }
  }

  let cwd;
  if (input.cwd) {
    cwd = assertPathAllowed(policy, 'file.read', input.cwd);
  }

  const policyMaxMs = policy.limits?.max_command_ms ?? 30000;
  const requestedMs = input.timeout_ms ?? policyMaxMs;
  const timeoutMs = Math.max(1, Math.min(requestedMs, policyMaxMs));
  const maxOutput = policy.limits?.max_output_bytes ?? 1048576;

  return new Promise((resolve, reject) => {
    const child = spawn(input.executable, args, {
      cwd,
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
      const bounded = truncateUtf8(combined, maxOutput);
      truncated = truncated || bounded.truncated;
      return bounded.text;
    };

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill('SIGTERM');
      reject(new Error(`Command timed out after ${timeoutMs} ms`));
    }, timeoutMs);

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
        exit_code: code,
        stdout,
        stderr,
        truncated,
      });
    });
  });
}

module.exports = { runCommand, truncateUtf8 };
