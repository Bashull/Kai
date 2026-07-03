const ToolEngine = require('../toolEngine');
const { v4: uuid } = require('uuid');

const toolController = {
  async createTool(req, res) {
    try {
      const { name, description, code, language } = req.body;
      const tool = await ToolEngine.createTool({
        name, description, code, language
      });
      res.json({ success: true, tool });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  },

  async executeTool(req, res) {
    try {
      const { toolId } = req.params;
      const { params } = req.body;
      const result = await ToolEngine.executeTool(toolId, params);
      res.json(result);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  },

  async listTools(req, res) {
    try {
      const tools = await ToolEngine.listTools();
      res.json(tools);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  },

  async deleteTool(req, res) {
    try {
      const { toolId } = req.params;
      await ToolEngine.deleteTool(toolId);
      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
};

module.exports = toolController;
