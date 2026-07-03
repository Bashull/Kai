import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

function ToolsPanel() {
  const [tools, setTools] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', code: '', language: 'javascript' });

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      const response = await axios.get(`${API_BASE}/tools/list`);
      setTools(response.data);
    } catch (error) {
      console.error('Error loading tools:', error);
    }
  };

  const handleCreate = async () => {
    try {
      await axios.post(`${API_BASE}/tools/create`, form);
      setForm({ name: '', description: '', code: '', language: 'javascript' });
      setShowCreate(false);
      loadTools();
    } catch (error) {
      console.error('Error creating tool:', error);
    }
  };

  const handleExecute = async (toolId) => {
    try {
      const response = await axios.post(`${API_BASE}/tools/execute/${toolId}`, {
        params: {}
      });
      alert(`Tool result: ${JSON.stringify(response.data)}`);
    } catch (error) {
      console.error('Error executing tool:', error);
    }
  };

  const handleDelete = async (toolId) => {
    try {
      await axios.delete(`${API_BASE}/tools/${toolId}`);
      loadTools();
    } catch (error) {
      console.error('Error deleting tool:', error);
    }
  };

  return (
    <div className="tools-panel">
      <button onClick={() => setShowCreate(!showCreate)} className="create-btn">
        ➕ New Tool
      </button>

      {showCreate && (
        <div className="form">
          <input
            placeholder="Tool name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <textarea
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <textarea
            placeholder="JavaScript code"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
            style={{ minHeight: '200px' }}
          />
          <button onClick={handleCreate}>Create Tool</button>
        </div>
      )}

      <div className="tools-list">
        {tools.map(tool => (
          <div key={tool.id} className="tool-item">
            <h4>{tool.name}</h4>
            <p>{tool.description}</p>
            <div className="tool-actions">
              <button onClick={() => handleExecute(tool.id)}>Execute</button>
              <button onClick={() => handleDelete(tool.id)} className="delete">Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ToolsPanel;
