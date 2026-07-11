'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');

const SECRET_KEY = /(token|secret|password|passwd|api[_-]?key|cookie|credential|private[_-]?key|authorization)/i;

function redact(value) {
  if (Array.isArray(value)) {
    return value.map(redact);
  }

  if (!value || typeof value !== 'object') {
    return value;
  }

  return Object.fromEntries(
    Object.entries(value).map(([key, child]) => [
      key,
      SECRET_KEY.test(key) ? '<REDACTED>' : redact(child),
    ])
  );
}

class AuditLog {
  constructor(filePath) {
    this.filePath = filePath;
  }

  async append(entry) {
    await fs.mkdir(path.dirname(this.filePath), { recursive: true });
    const row = {
      timestamp: new Date().toISOString(),
      ...redact(entry),
    };
    await fs.appendFile(this.filePath, `${JSON.stringify(row)}\n`, 'utf8');
    return row;
  }

  async read(limit = 100) {
    try {
      const text = await fs.readFile(this.filePath, 'utf8');
      return text
        .trim()
        .split('\n')
        .filter(Boolean)
        .slice(-limit)
        .map(line => JSON.parse(line));
    } catch (error) {
      if (error.code === 'ENOENT') return [];
      throw error;
    }
  }
}

module.exports = { AuditLog, redact };
