const express = require('express');
const router = express.Router();
const repo = require('../catalog/catalogRepository');

router.get('/', async (_req, res, next) => {
  try {
    res.json({ items: await repo.listCatalogItems() });
  } catch (error) {
    next(error);
  }
});

module.exports = router;
