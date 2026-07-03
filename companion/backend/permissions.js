const { v4: uuid } = require('uuid');
const db = require('./database');

class PermissionSystem {
  static ACTIONS = {
    READ: 'read',
    WRITE: 'write',
    DELETE: 'delete',
    EXECUTE: 'execute',
    CREATE: 'create'
  };

  static async requestPermission(resource, action, reason = '') {
    const perm = {
      id: uuid(),
      resource,
      action,
      reason,
      allowed: false,
      created_at: new Date().toISOString()
    };

    await db.run(
      `INSERT INTO permissions (id, resource, action, allowed, expires_at) VALUES (?, ?, ?, ?, ?)`,
      [perm.id, resource, action, 0, null]
    );

    await this.logAction('request_permission', resource, 'pending', { action, reason });
    return perm;
  }

  static async grantPermission(resource, action, expiresIn = null) {
    const expiresAt = expiresIn ? new Date(Date.now() + expiresIn).toISOString() : null;
    await db.run(
      `INSERT INTO permissions (id, resource, action, allowed, expires_at) VALUES (?, ?, ?, 1, ?)`,
      [uuid(), resource, action, expiresAt]
    );
    await this.logAction('grant_permission', resource, 'success', { action, expiresAt });
  }

  static async hasPermission(resource, action) {
    const perm = await db.get(
      `SELECT * FROM permissions
       WHERE resource = ? AND action = ? AND allowed = 1
         AND (expires_at IS NULL OR expires_at > datetime('now'))
       LIMIT 1`,
      [resource, action]
    );
    return !!perm;
  }

  static async revokePermission(resource, action) {
    await db.run(
      `UPDATE permissions SET allowed = 0 WHERE resource = ? AND action = ?`,
      [resource, action]
    );
    await this.logAction('revoke_permission', resource, 'success', { action });
  }

  static async listPermissions() {
    return db.all(`
      SELECT * FROM permissions
      WHERE expires_at IS NULL OR expires_at > datetime('now')
      ORDER BY created_at DESC
    `);
  }

  static async logAction(action, resource, status = 'success', details = '') {
    await db.run(
      `INSERT INTO audit_log (id, action, resource, status, details) VALUES (?, ?, ?, ?, ?)`,
      [uuid(), action, resource, status, typeof details === 'string' ? details : JSON.stringify(details)]
    );
  }
}

module.exports = PermissionSystem;
