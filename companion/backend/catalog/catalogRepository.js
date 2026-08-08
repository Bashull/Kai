const db = require('../database');
const { validateCatalogItem } = require('./catalogSchema');

function decode(row) {
  return {
    ...row,
    sections: JSON.parse(row.sections),
    tags: JSON.parse(row.tags),
  };
}

async function listCatalogItems() {
  const rows = await db.all('SELECT * FROM catalog_items ORDER BY updated_at DESC, title ASC');
  return rows.map(decode);
}

async function replaceCatalogItems(items) {
  const normalized = items.map(validateCatalogItem);
  await db.run('BEGIN TRANSACTION');
  try {
    await db.run('DELETE FROM catalog_items');
    for (const item of normalized) {
      await db.run(
        `INSERT INTO catalog_items
        (id,title,kind,sections,status,description,cover,tags,updated_at,canonical_source,launch_kind,launch_target,continue_target)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        [item.id,item.title,item.kind,JSON.stringify(item.sections),item.status,item.description,item.cover,
          JSON.stringify(item.tags),item.updated_at,item.canonical_source,item.launch_kind,item.launch_target,item.continue_target]
      );
    }
    await db.run('COMMIT');
    return normalized.length;
  } catch (error) {
    await db.run('ROLLBACK');
    throw error;
  }
}

module.exports = { listCatalogItems, replaceCatalogItems };
