const LearningEngine = require('../learningEngine');
const multer = require('multer');
const path = require('path');

const fileController = {
  async uploadFile(req, res) {
    try {
      if (!req.file) throw new Error('No file uploaded');

      const fileType = path.extname(req.file.originalname).substring(1).toLowerCase();
      const result = await LearningEngine.ingestFile(req.file.path, fileType);

      res.json({ success: true, ...result });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  },

  async queryKnowledge(req, res) {
    try {
      const { query } = req.body;
      const results = await LearningEngine.queryKnowledge(query);
      res.json(results);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  },

  async getStats(req, res) {
    try {
      const stats = await LearningEngine.getKnowledgeStats();
      res.json(stats);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
};

module.exports = fileController;
