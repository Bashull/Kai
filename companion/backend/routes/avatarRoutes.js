const express = require('express');
const router = express.Router();
const avatarController = require('../controllers/avatarController');

router.get('/state', async (req, res) => {
  try {
    const state = await avatarController.getAvatarState();
    res.json(state);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/animate', async (req, res) => {
  try {
    const { animation, duration } = req.body;
    const result = await avatarController.updateAvatarAnimation(animation, duration);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/gesture', async (req, res) => {
  try {
    const { gestureName, keyframes } = req.body;
    const gesture = await avatarController.createGesture(gestureName, keyframes);
    res.json(gesture);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/gestures', async (req, res) => {
  try {
    const gestures = await avatarController.listGestures();
    res.json(gestures);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/process-input', async (req, res) => {
  try {
    const result = await avatarController.processInput(req.body);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
