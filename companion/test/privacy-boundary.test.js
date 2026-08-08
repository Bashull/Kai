const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const ignore = fs.readFileSync(path.join(root, '.gitignore'), 'utf8');

const requiredRules = [
  'companion/data/',
  'companion/.env',
  'companion/frontend/build/',
];

for (const rule of requiredRules) {
  if (!ignore.split(/\r?\n/).includes(rule)) {
    throw new Error(`Missing privacy ignore rule: ${rule}`);
  }
}
