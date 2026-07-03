import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

function LearningPanel() {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API_BASE}/learning/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert(`File uploaded! Found ${response.data.chunks} characters of knowledge`);
      loadStats();
    } catch (error) {
      console.error('Error uploading file:', error);
    }
  };

  const handleQuery = async () => {
    try {
      const response = await axios.post(`${API_BASE}/learning/query`, { query });
      setResults(response.data);
    } catch (error) {
      console.error('Error querying knowledge:', error);
    }
  };

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/learning/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  return (
    <div className="learning-panel">
      <div className="upload-section">
        <h3>📚 Upload Knowledge</h3>
        <input
          type="file"
          onChange={handleFileUpload}
          accept=".txt,.pdf,.json,.md"
        />
        <p className="hint">Supported: TXT, PDF, JSON, MD</p>
      </div>

      <div className="query-section">
        <h3>🔍 Query Knowledge Base</h3>
        <div className="query-input">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask something..."
          />
          <button onClick={handleQuery}>Search</button>
        </div>

        {results.length > 0 && (
          <div className="results">
            {results.map((result, idx) => (
              <div key={idx} className="result-item">
                <p><strong>Source:</strong> {result.source}</p>
                <p><strong>Content:</strong> {result.content?.substring(0, 200)}...</p>
                <p><strong>Relevance:</strong> {(result.relevance * 100).toFixed(1)}%</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {stats && (
        <div className="stats">
          <h3>📊 Knowledge Stats</h3>
          <p>Total Size: {stats.totalSize?.size || 0} bytes</p>
          <p>Sources: {stats.sources?.length || 0}</p>
        </div>
      )}
    </div>
  );
}

export default LearningPanel;
