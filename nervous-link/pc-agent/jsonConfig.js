'use strict';

const fs = require('node:fs');

function parseJsonText(text) {
  const normalized = String(text).replace(/^\uFEFF/, '');
  return JSON.parse(normalized);
}

function loadJsonFile(filePath) {
  return parseJsonText(fs.readFileSync(filePath, 'utf8'));
}

module.exports = {
  parseJsonText,
  loadJsonFile,
};
