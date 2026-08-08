const fs = require('fs');
const path = require('path');
const db = require('../backend/database');
const repo = require('../backend/catalog/catalogRepository');

async function main() {
  const input = process.argv[2];
  if (!input) throw new Error('Usage: node scripts/import-catalog.js <json-path>');
  const absolute = path.resolve(input);
  const parsed = JSON.parse(fs.readFileSync(absolute, 'utf8'));
  const items = Array.isArray(parsed) ? parsed : parsed.items;
  if (!Array.isArray(items)) throw new Error('Catalog JSON must be an array or {"items": [...]}');
  await db.init();
  const count = await repo.replaceCatalogItems(items);
  console.log(`Imported ${count} catalog items from ${absolute}`);
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
