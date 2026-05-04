import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// ── Service Worker — Offline-First (PWA Feature #4) ─────────────
// Registriert nach dem ersten Render damit es den Start nicht verzögert
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((reg) => {
        console.log('◑ SW registriert:', reg.scope);
        // Sofort aktivieren wenn Update verfügbar
        reg.addEventListener('updatefound', () => {
          reg.installing?.addEventListener('statechange', (e) => {
            if (e.target.state === 'installed' && navigator.serviceWorker.controller) {
              navigator.serviceWorker.controller.postMessage('skipWaiting');
            }
          });
        });
      })
      .catch((err) => console.warn('SW-Fehler (nicht kritisch):', err));
  });
}

