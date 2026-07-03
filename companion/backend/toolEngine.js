const { v4: uuid } = require('uuid');
const db = require('../database');
const fs = require('fs-extra');
const path = require('path');

class ToolEngine {
  static async createTool(config) {
    const id = uuid();
    const tool = {
      id,
      name: config.name,
      description: config.description,
      code: config.code,
      language: config.language || 'javascript',
      created_at: new Date(),
      enabled: true
    };

    await db.run(
      `INSERT INTO tools (id, name, description, code, language) 
       VALUES (?, ?, ?, ?, ?)`,
      [id, tool.name, tool.description, tool.code, tool.language]
    );

    const filePath = path.join(process.env.UPLOADS_PATH || './data/tools', `${id}.js`);
    await fs.writeFile(filePath, tool.code);

    return tool;
  }

  static async executeTool(toolId, params = {}) {
    const tool = await db.get(
      'SELECT * FROM tools WHERE id = ? AND enabled = 1',
      [toolId]
    );

    if (!tool) throw new Error('Tool not found or disabled');

    try {
      const fn = new Function('params', `return (async () => { ${tool.code} })()`);
      const result = await fn(params);
      
      await db.run(
        `INSERT INTO audit_log (id, action, resource, status) VALUES (?, ?, ?, ?)`,
        [uuid(), 'tool_execute', toolId, 'success']
      );

      return { success: true, result };
    } catch (error) {
      await db.run(
        `INSERT INTO audit_log (id, action, resource, status, details) VALUES (?, ?, ?, ?, ?)`,
        [uuid(), 'tool_execute', toolId, 'error', error.message]
      );
      throw error;
    }
  }

  static async listTools() {
    return db.all('SELECT * FROM tools ORDER BY created_at DESC');
  }

  static async deleteTool(toolId) {
    await db.run('DELETE FROM tools WHERE id = ?', [toolId]);
    const filePath = path.join(process.env.UPLOADS_PATH || './data/tools', `${toolId}.js`);
    await fs.remove(filePath);
  }
}

module.exports = ToolEngine;
