import React, { useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { PerspectiveCamera, OrbitControls } from '@react-three/drei';
import Avatar3D from './components/Avatar3D';
import ChatPanel from './components/ChatPanel';
import ToolsPanel from './components/ToolsPanel';
import LearningPanel from './components/LearningPanel';
import PermissionsPanel from './components/PermissionsPanel';
import './App.css';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [avatarState, setAvatarState] = useState(null);
  const [stats, setStats] = useState({});

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${API_BASE}/system/status`);
        setStats(response.data);
        const avatar = await axios.get(`${API_BASE}/avatar/state`);
        setAvatarState(avatar.data);
      } catch (error) {
        console.error('Error fetching status:', error);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <div className="container">
        <div className="viewport-3d">
          <Canvas>
            <PerspectiveCamera position={[0, 2, 5]} fov={50} makeDefault />
            <OrbitControls />
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} />
            <Avatar3D />
          </Canvas>
        </div>

        <div className="panels">
          <div className="tabs">
            {['chat', 'tools', 'learning', 'permissions'].map(tab => (
              <button
                key={tab}
                className={`tab ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          <div className="tab-content">
            {activeTab === 'chat' && <ChatPanel />}
            {activeTab === 'tools' && <ToolsPanel />}
            {activeTab === 'learning' && <LearningPanel />}
            {activeTab === 'permissions' && <PermissionsPanel />}
          </div>

          <div className="stats">
            <p>🤖 Tools: {stats.stats?.tools || 0}</p>
            <p>🧠 Skills: {stats.stats?.skills || 0}</p>
            <p>⚙️ Status: {avatarState?.status || 'loading'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
