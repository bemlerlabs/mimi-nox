/**
 * ◑ MiMiNox — Handy-Verbindungs-Modal
 * components/ConnectModal.jsx
 *
 * Zeigt QR-Code → User scannt mit Handy → MiMiNox im selben WLAN öffnen
 * → "Zum Homescreen hinzufügen" → MiMiNox als App auf dem Handy
 *
 * QR-Code wird via qrcodejs (CDN, gecacht vom Service Worker) direkt im Browser gerendert.
 * Kein Node.js-Paket nötig → läuft komplett offline nach erstem Laden.
 */
import { useState, useEffect, useRef } from 'react';

const API_BASE = window.location.port === '5173' ? 'http://localhost:3001' : '';

const STEPS = [
  { icon: '📶', text: 'Handy und PC im gleichen WLAN' },
  { icon: '📷', text: 'QR-Code mit der Kamera scannen' },
  { icon: '🌐', text: 'MiMiNox öffnet sich im Handy-Browser' },
  { icon: '📱', text: '"Zum Homescreen" → fertig als App' },
];

// Lädt qrcodejs vom CDN (einmalig, danach SW-gecacht) und rendert in einen div
function QRCanvas({ url }) {
  const containerRef = useRef(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!url || !containerRef.current) return;
    const el = containerRef.current;
    el.innerHTML = ''; // Clear vorherigen QR

    const doRender = () => {
      try {
        void new window.QRCode(el, {
          text:         url,
          width:        220,
          height:       220,
          colorDark:    '#C4A265',
          colorLight:   '#0F1419',
          correctLevel: window.QRCode.CorrectLevel.M,
        });
      } catch { setError(true); }
    };

    if (window.QRCode) {
      doRender();
      return;
    }

    const id = 'qrcodejs-cdn';
    if (!document.getElementById(id)) {
      const s = document.createElement('script');
      s.id  = id;
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js';
      s.onload = doRender;
      s.onerror = () => setError(true);
      document.head.appendChild(s);
    } else {
      const t = setInterval(() => {
        if (window.QRCode) { clearInterval(t); doRender(); }
      }, 50);
      return () => clearInterval(t);
    }
  }, [url]);

  if (error) return <p className="connect-hint">⚠️ QR konnte nicht gerendert werden.<br/>Gib die URL manuell ein.</p>;
  return <div ref={containerRef} className="connect-qr-canvas" id="connect-qr-canvas" />;
}

export function ConnectModal({ onClose }) {
  const [data, setData]       = useState(null);   // { url, ip }
  const [err, setErr]         = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState(0);       // 0=QR, 1=Anleitung

  useEffect(() => {
    fetch(`${API_BASE}/api/connect`)
      .then(r => r.ok ? r.json() : Promise.reject('Backend nicht erreichbar'))
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setErr(String(e)); setLoading(false); });
  }, []);

  return (
    <div className="connect-overlay" id="connect-modal" role="dialog" aria-modal="true">
      <div className="connect-card">

        <div className="connect-header">
          <span className="connect-title">📱 Auf Handy öffnen</span>
          <button className="settings-close" onClick={onClose} aria-label="Schließen">✕</button>
        </div>

        {loading && (
          <div className="connect-loading">
            <span className="map-coords-empty">Adresse wird ermittelt…</span>
          </div>
        )}

        {err && (
          <div className="connect-error">
            <p>⚠️ Konnte lokale IP nicht ermitteln.</p>
            <p className="connect-error-hint">{err}</p>
          </div>
        )}

        {data && (
          <>
            <div className="connect-tabs">
              <button className={`connect-tab ${tab === 0 ? 'active' : ''}`} onClick={() => setTab(0)}>QR-Code</button>
              <button className={`connect-tab ${tab === 1 ? 'active' : ''}`} onClick={() => setTab(1)}>Anleitung</button>
            </div>

            {tab === 0 && (
              <div className="connect-qr-section">
                <QRCanvas url={data.url} />
                <div className="connect-url-box">
                  <span className="connect-url-label">Deine lokale Adresse:</span>
                  <a href={data.url} target="_blank" rel="noreferrer" className="connect-url" id="connect-url">
                    {data.url}
                  </a>
                </div>
                <p className="connect-hint">
                  Handy und PC müssen im <strong>selben WLAN</strong> sein.<br />
                  Nur solange dieser PC läuft.
                </p>
              </div>
            )}

            {tab === 1 && (
              <div className="connect-steps-section">
                <ol className="connect-steps-list">
                  {STEPS.map((s, i) => (
                    <li key={i} className="connect-step">
                      <span className="connect-step-icon">{s.icon}</span>
                      <span>{s.text}</span>
                    </li>
                  ))}
                </ol>
                <div className="connect-install-note">
                  <strong>iOS (iPhone/iPad):</strong><br />
                  Safari öffnen → Teilen-Button (□↑) → „Zum Home-Bildschirm"<br /><br />
                  <strong>Android (Chrome):</strong><br />
                  Menü (⋮) → „App installieren" oder „Zum Startbildschirm hinzufügen"<br /><br />
                  <strong>✅ Danach:</strong> MiMiNox erscheint als App-Icon.
                  Kein App Store. Kein Abo. Kein Internet nötig.
                </div>
              </div>
            )}
          </>
        )}

      </div>
    </div>
  );
}
