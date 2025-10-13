import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './src/App';
import './src/index.css';

const container = document.getElementById('root');
const root = createRoot(container!);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Optional: Fade out loading screen
window.addEventListener('load', () => {
  const loadingScreen = document.getElementById('loading-screen');
  if (loadingScreen) {
    loadingScreen.setAttribute('data-loaded', 'true');
  }
});
