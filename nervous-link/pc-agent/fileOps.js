'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const { assertPathAllowed } = require('./policy');

async function listDirectory(input, policy) {
  const target = assertPathAllowed(policy, 'file.read', input.path);
  const entries = await fs.readdir(target, { withFileTypes: true });
  return {
    path: target,
    entries: entries.map(entry => ({
      name: entry.name,
      type: entry.isDirectory() ? 'directory' : entry.isFile() ? 'file' : 'other',
    })),
  };
}

async function readFile(input, policy) {
  const target = assertPathAllowed(policy, 'file.read', input.path);
  const stat = await fs.stat(target);
  const max = policy.limits?.max_read_bytes ?? 10485760;
  if (stat.size > max) {
    throw new Error(`File exceeds max_read_bytes: ${stat.size} > ${max}`);
  }

  const bytes = await fs.readFile(target);
  const result = { path: target, bytes: bytes.length };
  if (input.encoding === 'base64') {
    result.base64 = bytes.toString('base64');
  } else {
    result.text = bytes.toString(input.encoding ?? 'utf8');
  }

  if (input.sha256 === true) {
    result.sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
  }

  return result;
}

async function writeFileAtomic(input, policy) {
  const target = assertPathAllowed(policy, 'file.write', input.path);
  const bytes = input.base64
    ? Buffer.from(input.base64, 'base64')
    : Buffer.from(input.text ?? '', 'utf8');
  const max = policy.limits?.max_write_bytes ?? 10485760;

  if (bytes.length > max) {
    throw new Error(`Write exceeds max_write_bytes: ${bytes.length} > ${max}`);
  }

  await fs.mkdir(path.dirname(target), { recursive: true });
  assertPathAllowed(policy, 'file.write', target);

  const temp = `${target}.kai-tmp-${process.pid}-${crypto.randomUUID()}`;
  let tempWritten = false;

  try {
    await fs.writeFile(temp, bytes, { flag: 'wx' });
    tempWritten = true;
    await fs.rename(temp, target);
    tempWritten = false;
  } finally {
    if (tempWritten) {
      await fs.unlink(temp).catch(() => {});
    }
  }

  return { path: target, bytes: bytes.length };
}

module.exports = { listDirectory, readFile, writeFileAtomic };
