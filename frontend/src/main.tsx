import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ThemeProvider } from './context/ThemeContext';
import './index.css';

// Signal bootstrap completion to root watchdog
(window as any).__QRESQ_MOUNTED__ = true;
if ((window as any).__qresqWatchdog) {
  clearTimeout((window as any).__qresqWatchdog);
}

const rootElement = document.getElementById('root')!;
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>
);

(window as any).__QRESQ_MOUNTED__ = true;
if ((window as any).__qresqWatchdog) {
  clearTimeout((window as any).__qresqWatchdog);
}
