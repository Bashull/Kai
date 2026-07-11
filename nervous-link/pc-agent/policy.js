'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { ACTION_CAPABILITY } = require('./capabilities');

function loadPolicy(policyPath) {
  return JSON.parse(fs.readFileSync(policyPath, 'utf8'));
}

function authorizeAction(policy, request) {
  const expected = ACTION_CAPABILITY[request.action] ?? request.capability;
  if (expected !== request.capability) {
    return { allowed: false, reason: 'CAPABILITY_ACTION_MISMATCH' };
  }

  const allowed = policy?.capabilities?.[request.capability] === true;
  return { allowed, reason: allowed ? null : 'DEFAULT_DENY' };
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function realpathIfPossible(targetPath) {
  try {
    if (typeof fs.realpathSync.native === 'function') {
      return fs.realpathSync.native(targetPath);
    }
    return fs.realpathSync(targetPath);
  } catch {
    return path.resolve(targetPath);
  }
}

function canonicalizeCandidate(candidatePath) {
  let cursor = path.resolve(candidatePath);
  const missingParts = [];

  while (!fs.existsSync(cursor)) {
    const parent = path.dirname(cursor);
    if (parent === cursor) break;
    missingParts.unshift(path.basename(cursor));
    cursor = parent;
  }

  return path.resolve(realpathIfPossible(cursor), ...missingParts);
}

function assertPathAllowed(policy, capability, candidatePath) {
  if (typeof candidatePath !== 'string' || candidatePath.length === 0) {
    throw new Error(`Path is outside approved roots for ${capability}`);
  }

  const candidate = canonicalizeCandidate(candidatePath);
  const roots = (policy?.roots?.[capability] ?? [])
    .map(root => realpathIfPossible(path.resolve(root)));

  if (!roots.some(root => isWithin(root, candidate))) {
    throw new Error(`Path is outside approved roots for ${capability}`);
  }

  return path.resolve(candidatePath);
}

module.exports = {
  loadPolicy,
  authorizeAction,
  assertPathAllowed,
  isWithin,
  canonicalizeCandidate,
};
