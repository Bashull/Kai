'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

async function readCredentials(filePath) {
  try {
    const text = await fs.readFile(filePath, 'utf8');
    return JSON.parse(text);
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

async function writeCredentialsAtomic(filePath, credential) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temp = `${filePath}.kai-tmp-${process.pid}-${crypto.randomUUID()}`;
  let tempWritten = false;

  try {
    await fs.writeFile(temp, `${JSON.stringify(credential, null, 2)}\n`, {
      encoding: 'utf8',
      flag: 'wx',
      mode: 0o600,
    });
    tempWritten = true;
    await fs.rename(temp, filePath);
    tempWritten = false;
  } finally {
    if (tempWritten) await fs.unlink(temp).catch(() => {});
  }

  return credential;
}

module.exports = { readCredentials, writeCredentialsAtomic };
