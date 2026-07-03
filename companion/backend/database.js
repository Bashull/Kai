const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs-extra');

const DB_PATH = process.env.DATABASE_PATH || path.join(__dirname, '..', 'data', 'companion.db');
const DATA_DIR = path.dirname(DB_PATH);

let db;

const init = async () => {
  await fs.ensureDir(DATA_DIR);
  await fs.ensureDir(process.env.UPLOADS_PATH || path.join(__dirname, '..', 'data', 'uploads'));

  return new Promise((resolve, reject) => {
    db = new sqlite3.Database(DB_PATH, (err) => {
      if (err) return reject(err);
      createTables();
      resolve();
    });
  });
};

const createTables = () => {
  const schema = `
    CREATE TABLE IF NOT EXISTS companion (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      personality TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tools (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      code TEXT NOT NULL,
      language TEXT DEFAULT 'javascript',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      enabled BOOLEAN DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS knowledge_base (
      id TEXT PRIMARY KEY,
      source TEXT,
      content TEXT,
      embeddings TEXT,
      type TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      relevance REAL DEFAULT 0.5
    );

    CREATE TABLE IF NOT EXISTS permissions (
      id TEXT PRIMARY KEY,
      resource TEXT NOT NULL,
      action TEXT NOT NULL,
      allowed BOOLEAN DEFAULT 0,
      expires_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_log (
      id TEXT PRIMARY KEY,
      action TEXT NOT NULL,
      resource TEXT,
      status TEXT,
      details TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS skills (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      proficiency REAL DEFAULT 0.0,
      category TEXT,
      learned_from TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS animations (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      frames TEXT,
      duration REAL DEFAULT 1.0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `;

  schema.split(';').forEach((statement) => {
    if (statement.trim()) {
      db.run(statement, (err) => {
        if (err) console.error('DB schema error:', err.message);
      });
    }
  });
};

const run = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function (err) {
      if (err) return reject(err);
      resolve({ id: this.lastID, changes: this.changes });
    });
  });
};

const get = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) return reject(err);
      resolve(row);
    });
  });
};

const all = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) return reject(err);
      resolve(rows || []);
    });
  });
};

module.exports = { init, run, get, all, db };
