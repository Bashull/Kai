const express = require('express');
const router = express.Router();
const fileController = require('../controllers/fileController');

router.post('/upload', require('multer')({ dest: './data/uploads' }).single('file'), fileController.uploadFile);
router.post('/query', fileController.queryKnowledge);
router.get('/stats', fileController.getStats);

module.exports = router;
