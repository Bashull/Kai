const test = require('node:test');
const assert = require('node:assert/strict');
const os = require('os');
const path = require('path');
const fs = require('fs');
const request = require('supertest');

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kai-home-api-'));
process.env.DATABASE_PATH = path.join(tempDir, 'api-test.db');

const db = require('../backend/database');
const repo = require('../backend/catalog/catalogRepository');
const { app } = require('../backend/server');

test.before(async () => {
  await db.init();
  await repo.replaceCatalogItems([{
    id: 'kai', title: 'Kai', kind: 'project', sections: ['KAI'],
    status: 'IN_DEVELOPMENT', description: 'Companion', cover: null, tags: ['fusionai'],
    updated_at: '2026-08-08T00:00:00.000Z', canonical_source: null,
    launch_kind: 'concept', launch_target: null, continue_target: null
  }]);
});

test('GET /api/catalog returns canonical items', async () => {
  const res = await request(app).get('/api/catalog').expect(200);
  assert.equal(res.body.items.length, 1);
  assert.equal(res.body.items[0].id, 'kai');
});
