const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('os');
const path = require('path');
const fs = require('fs');

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-home-catalog-'));
process.env.DATABASE_PATH = path.join(tempDir, 'catalog-test.db');

const db = require('../backend/database');
const { validateCatalogItem } = require('../backend/catalog/catalogSchema');
const repo = require('../backend/catalog/catalogRepository');

test.before(async () => db.init());

test('validateCatalogItem rejects unknown status', () => {
  assert.throws(() => validateCatalogItem({
    id: 'x', title: 'X', kind: 'tool', sections: ['APLICACIONES'],
    status: 'BROKEN', description: '', cover: null, tags: [],
    updated_at: '2026-08-08T00:00:00.000Z', canonical_source: null,
    launch_kind: 'concept', launch_target: null, continue_target: null
  }), /Invalid status/);
});

test('repository stores one canonical record and returns arrays', async () => {
  const item = validateCatalogItem({
    id: 'image-forge', title: 'Image Forge', kind: 'app',
    sections: ['APLICACIONES', 'CREACIÓN VISUAL'], status: 'IN_DEVELOPMENT',
    description: 'Forja visual actual', cover: null, tags: ['imagen'],
    updated_at: '2026-08-08T00:00:00.000Z', canonical_source: null,
    launch_kind: 'local_app_future', launch_target: null,
    continue_target: 'https://github.com/Bashull/Kai'
  });
  assert.equal(await repo.replaceCatalogItems([item]), 1);
  const rows = await repo.listCatalogItems();
  assert.deepEqual(rows[0].sections, ['APLICACIONES', 'CREACIÓN VISUAL']);
  assert.deepEqual(rows[0].tags, ['imagen']);
});
