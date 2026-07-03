const express = require('express');
const router = express.Router();
const multer = require('multer');
const fileController = require('../controllers/fileController');

const upload = multer({ dest: process.env.UPLOADS_PATH || './data/uploads' });

router.post('/upload', upload.single('file'), fileController.uploadFile);
router.post('/query', fileController.queryKnowledge);
router.get('/stats', fileController.getStats);

module.exports = router;
