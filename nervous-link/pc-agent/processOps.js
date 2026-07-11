'use strict';

const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const execFileAsync = promisify(execFile);

async function listProcesses() {
  if (process.platform === 'win32') {
    const { stdout } = await execFileAsync('powershell.exe', [
      '-NoProfile',
      '-NonInteractive',
      '-Command',
      'Get-Process | Select-Object Id,ProcessName,CPU,WorkingSet64 | ConvertTo-Json -Compress',
    ], {
      windowsHide: true,
      maxBuffer: 4 * 1024 * 1024,
    });

    const parsed = JSON.parse(stdout || '[]');
    return Array.isArray(parsed) ? parsed : [parsed];
  }

  const { stdout } = await execFileAsync('ps', ['-eo', 'pid,comm']);
  return stdout
    .trim()
    .split('\n')
    .slice(1)
    .filter(Boolean)
    .map(line => line.trim().split(/\s+/, 2))
    .map(([pid, name]) => ({ Id: Number(pid), ProcessName: name }));
}

function killProcess(pid) {
  if (!Number.isInteger(pid) || pid <= 0) {
    throw new Error('pid must be a positive integer');
  }

  process.kill(pid, 'SIGTERM');
  return { pid, signal: 'SIGTERM' };
}

module.exports = { listProcesses, killProcess };
