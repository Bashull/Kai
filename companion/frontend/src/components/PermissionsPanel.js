import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

function PermissionsPanel() {
  const [permissions, setPermissions] = useState([]);
  const [requestForm, setRequestForm] = useState({ resource: '', action: '', reason: '' });

  useEffect(() => {
    loadPermissions();
  }, []);

  const loadPermissions = async () => {
    try {
      const response = await axios.get(`${API_BASE}/permissions/list`);
      setPermissions(response.data);
    } catch (error) {
      console.error('Error loading permissions:', error);
    }
  };

  const handleRequestPermission = async () => {
    try {
      await axios.post(`${API_BASE}/permissions/request`, requestForm);
      setRequestForm({ resource: '', action: '', reason: '' });
      loadPermissions();
      alert('Permission requested. Please review in audit log.');
    } catch (error) {
      console.error('Error requesting permission:', error);
    }
  };

  const handleGrantPermission = async (resource, action) => {
    try {
      await axios.post(`${API_BASE}/permissions/grant`, {
        resource,
        action,
        expiresIn: 24 * 60 * 60 * 1000 // 24 hours
      });
      loadPermissions();
    } catch (error) {
      console.error('Error granting permission:', error);
    }
  };

  const handleRevokePermission = async (resource, action) => {
    try {
      await axios.post(`${API_BASE}/permissions/revoke`, { resource, action });
      loadPermissions();
    } catch (error) {
      console.error('Error revoking permission:', error);
    }
  };

  return (
    <div className="permissions-panel">
      <div className="request-section">
        <h3>🔐 Request Permission</h3>
        <input
          placeholder="Resource (e.g., filesystem)"
          value={requestForm.resource}
          onChange={(e) => setRequestForm({ ...requestForm, resource: e.target.value })}
        />
        <input
          placeholder="Action (read/write/execute)"
          value={requestForm.action}
          onChange={(e) => setRequestForm({ ...requestForm, action: e.target.value })}
        />
        <textarea
          placeholder="Reason for permission"
          value={requestForm.reason}
          onChange={(e) => setRequestForm({ ...requestForm, reason: e.target.value })}
        />
        <button onClick={handleRequestPermission}>Request</button>
      </div>

      <div className="permissions-list">
        <h3>✅ Granted Permissions</h3>
        {permissions.filter(p => p.allowed).length === 0 ? (
          <p>No permissions granted yet</p>
        ) : (
          permissions.filter(p => p.allowed).map(perm => (
            <div key={perm.id} className="permission-item">
              <p><strong>{perm.resource}</strong> - {perm.action}</p>
              <button onClick={() => handleRevokePermission(perm.resource, perm.action)} className="revoke">
                Revoke
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default PermissionsPanel;
