const express = require('express');
const router = express.Router();
const db = require('../database');

router.get('/status', async (req, res) => {
  try {
    const companion = await db.get('SELECT * FROM companion LIMIT 1');
    const toolsCount = await db.get('SELECT COUNT(*) as count FROM tools');
    const skillsCount = await db.get('SELECT COUNT(*) as count FROM skills');

    res.json({
      companion,
      stats: {
        tools: toolsCount?.count || 0,
        skills: skillsCount?.count || 0
      }
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
