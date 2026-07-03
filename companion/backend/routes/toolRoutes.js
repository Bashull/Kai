const express = require('express');
const router = express.Router();
const toolController = require('../controllers/toolController');

router.post('/create', toolController.createTool);
router.get('/list', toolController.listTools);
router.post('/execute/:toolId', toolController.executeTool);
router.delete('/:toolId', toolController.deleteTool);

module.exports = router;
