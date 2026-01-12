import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

// Log build version
const buildTime = import.meta.env.VITE_BUILD_TIME || 'development';
console.log(`Darwin WebUI - Build: ${buildTime} (${new Date(parseInt(buildTime) * 1000).toISOString()})`);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
