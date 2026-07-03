const express = require('express');
const router = express.Router();
const PermissionSystem = require('../permissions');

router.post('/request', async (req, res) => {
  try {
    const { resource, action, reason } = req.body;
    const perm = await PermissionSystem.requestPermission(resource, action, reason);
    res.json({ success: true, permission: perm });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/grant', async (req, res) => {
  try {
    const { resource, action, expiresIn } = req.body;
    await PermissionSystem.grantPermission(resource, action, expiresIn);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/check/:resource/:action', async (req, res) => {
  try {
    const { resource, action } = req.params;
    const allowed = await PermissionSystem.hasPermission(resource, action);
    res.json({ allowed });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/list', async (req, res) => {
  try {
    const permissions = await PermissionSystem.listPermissions();
    res.json(permissions);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/revoke', async (req, res) => {
  try {
    const { resource, action } = req.body;
    await PermissionSystem.revokePermission(resource, action);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
