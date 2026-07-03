const express = require('express');
const router = express.Router();

router.post('/message', (req, res) => {
  const { message } = req.body;
  res.json({
    response: `Companion received: "${message}"`,
    timestamp: new Date()
  });
});

module.exports = router;
