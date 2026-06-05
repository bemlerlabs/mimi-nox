/**
 * ◑ MiMiNox — "Dein Kopf. Nur größer."
 * App.jsx — Single Surface
 *
 * Eine Oberfläche. Drei Gesten. Kein Menü.
 * Designed by Ive/Béhar/Fadell · Validated by DARPA Panel
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { io as socketIO } from 'socket.io-client';

import { ChatMessage } from './components/ChatMessage';
import { ActionBar } from './components/ActionBar';
import { PrivacyPanel } from './components/PrivacyPanel';
import { SosOverlay } from './components/SosOverlay';
import { SettingsPanel } from './components/SettingsPanel';
import { MapView } from './components/MapView';
import { ConnectModal } from './components/ConnectModal';
import { FieldToolsPanel } from './components/FieldToolsPanel';
import { ModeSwitcher } from './components/ModeSwitcher';

// Onboarding-Prompts inline (server/field-tools/app-mode.js liegt außerhalb des Vite-Projektstamms)
const ONBOARDING_PROMPTS = {
  crisis: [
    'Erste Hilfe bei Verbrennungen?',
    'Wie baue ich einen Notunterschlupf?',
    'Trinkwasser aufbereiten ohne Filter',
  ],
  daily: [
    'Was kann ich heute Abend kochen?',
    'Erstell mir eine Einkaufsliste',
    'Hilf mir beim Schreiben einer E-Mail',
  ],
};
const getOnboardingPrompts = (mode) => ONBOARDING_PROMPTS[mode] || ONBOARDING_PROMPTS.crisis;

const API_BASE = window.location.port === '5173' ? 'http://localhost:3001' : '';

/**
 * Convert a File/Blob to a base64 string (data URL stripped).
 * Images are resized to max 1024px on the longest edge at 0.80 JPEG quality
 * to keep payloads manageable for Ollama (~800 KB vs 5+ MB raw).
 * @param {File} file
 * @returns {Promise<string>} Raw base64 string (no data: prefix)
 */
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const MAX = 1024;
      let { width, height } = img;
      if (width > MAX || height > MAX) {
        const ratio = Math.min(MAX / width, MAX / height);
        width  = Math.round(width  * ratio);
        height = Math.round(height * ratio);
      }
      const canvas = document.createElement('canvas');
      canvas.width  = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(url);
      // Strip the data:image/...;base64, prefix
      const dataUrl = canvas.toDataURL('image/jpeg', 0.80);
      resolve(dataUrl.split(',')[1]);
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Image load failed')); };
    img.src = url;
  });
}

// Vorgeschlagene Namen für den Assistenten
const NAME_SUGGESTIONS = ['Mia', 'Nova', 'Cara', 'Lena', 'Mimi', 'Finn', 'Sam', 'Leo'];

function App() {
  const [messages, setMessages] = useState([]);
  const [isLive, setIsLive] = useState(false);

  // Assistent-Name — aus localStorage, sonst Namens-Picker anzeigen
  const [assistantName, setAssistantName] = useState(() =>
    localStorage.getItem('miminox_assistant_name') || ''
  );
  const [nameInput, setNameInput] = useState('');

  // showNamePicker: nur beim allerersten Start (kein Name + kein Onboarding gesehen)
  const [showNamePicker, setShowNamePicker] = useState(() =>
    !localStorage.getItem('miminox_assistant_name')
  );

  const [showOnboarding, setShowOnboarding] = useState(() => {
    return !localStorage.getItem('miminox_onboarded');
  });
  const [showPrivacy, setShowPrivacy] = useState(() => {
    return !localStorage.getItem('miminox_privacy_seen');
  });
  const [toast, setToast] = useState(null);
  const bottomRef = useRef(null);
  const toastTimer = useRef(null);

  const [isThinking, setIsThinking] = useState(false);
  const [showSos, setShowSos]           = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showMap, setShowMap]           = useState(false);
  const [showConnect, setShowConnect]       = useState(false);
  const [showFieldTools, setShowFieldTools] = useState(false);
  const [appMode, setAppMode] = useState(
    localStorage.getItem('miminox_mode') || 'crisis'
  );

  const showToast = useCallback((msg) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  }, []);

  // Poll chat history (1.5s for responsive updates during streaming)
  useEffect(() => {
    let lastCount = 0;
    async function poll() {
      try {
        const res = await fetch(`${API_BASE}/api/chat/history`, {
          signal: AbortSignal.timeout(2000),
        });
        if (res.ok) {
          const data = await res.json();
          setMessages(data);
          setIsLive(true);
          // Auto-clear thinking when response arrives
          if (data.length > lastCount && data[data.length - 1]?.from !== 'user') {
            setIsThinking(false);
          }
          lastCount = data.length;
        }
      } catch {
        setIsLive(false);
      }
    }
    poll();
    const interval = setInterval(poll, 1500);
    return () => clearInterval(interval);
  }, []);

  // ── Socket.io — Live Streaming (Echtzeit-Antworten) ──────────────
  // Empfange Streaming-Tokens direkt vom Server (kein Polling-Lag).
  useEffect(() => {
    const socket = socketIO(API_BASE || 'http://localhost:3001', {
      transports: ['websocket', 'polling'],
      reconnectionDelay: 1000,
    });

    // Streaming-Token: Zeige Antwort live während LLM generiert
    socket.on('chat_stream', (msg) => {
      setIsThinking(false);
      setMessages(prev => {
        const idx = prev.findIndex(m => m.id === msg.id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = { ...msg, type: 'message' };
          return updated;
        }
        return [...prev, { ...msg, type: 'message' }];
      });
    });

    // Finale Antwort: ersetzt Streaming-Bubble durch abgeschlossenen Text
    socket.on('chat_message', (msg) => {
      setIsThinking(false);
      setMessages(prev => {
        const idx = prev.findIndex(m => m.id === msg.id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = msg;
          return updated;
        }
        const isDupe = prev.some(m =>
          m.from === msg.from &&
          m.content === msg.content &&
          Math.abs(new Date(m.timestamp) - new Date(msg.timestamp)) < 2000
        );
        return isDupe ? prev : [...prev, msg];
      });
    });

    // Modus-Wechsel vom Server (z.B. durch anderen Client)
    socket.on('app_mode_changed', ({ mode }) => {
      setAppMode(mode);
      localStorage.setItem('miminox_mode', mode);
    });

    return () => socket.disconnect();
  }, []);

  // Feature #12: country → DACH Notruf
  // Feature: __assistant_name__ → Name im Header
  useEffect(() => {
    fetch(`${API_BASE}/api/memory`)
      .then(r => r.ok ? r.json() : [])
      .then(memories => {
        const country = memories.find(m => m.key === '__country__');
        if (country) localStorage.setItem('miminox_country', country.value);

        const nameMemory = memories.find(m => m.key === '__assistant_name__');
        if (nameMemory && nameMemory.value) {
          localStorage.setItem('miminox_assistant_name', nameMemory.value);
          setAssistantName(nameMemory.value);
        }
      })
      .catch(() => {}); // Offline — no-op
  }, []);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  // Assistenten-Namen speichern
  const handleNameSelect = useCallback(async (name) => {
    const chosen = name.trim() || 'Mia';
    setAssistantName(chosen);
    localStorage.setItem('miminox_assistant_name', chosen);
    setShowNamePicker(false);
    // Optional: auch im Backend-Memory speichern
    try {
      await fetch(`${API_BASE}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: `Merke dir: Mein Assistent heißt ${chosen}` }),
      });
    } catch { /* offline — kein Problem, localStorage reicht */ }
  }, []);

  // Submit prompt
  const handleSubmit = useCallback(async (prompt) => {
    // SOS-Wort → sofort SOS-Modus öffnen
    if (/^\s*(?:sos|notruf|hilf mir|hilfe!?)\s*$/i.test(prompt)) {
      setShowSos(true);
      return;
    }

    // Karte/Standort → Karten-Modus öffnen
    if (/^\s*(?:karte|standort|wo bin ich|gps|koordinaten|position)\s*[?!]?\s*$/i.test(prompt)) {
      setShowMap(true);
      return;
    }

    // Optimistic: show user message immediately
    setMessages(prev => [...prev, {
      from: 'user',
      content: prompt,
      type: 'message',
      timestamp: new Date().toISOString(),
    }]);

    // Show thinking indicator immediately
    setIsThinking(true);

    // Dismiss onboarding on first message
    if (showOnboarding) {
      setShowOnboarding(false);
      localStorage.setItem('miminox_onboarded', 'true');
    }

    try {
      await fetch(`${API_BASE}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
    } catch {
      setIsThinking(false);
      showToast('Offline — Antwort kommt aus dem lokalen Wissen');
    }
  }, [showOnboarding, showToast]);

  // Handle photo submit — Feature #1: Vision
  const handlePhoto = useCallback(async (file, promptText = '') => {
    // 1. Show preview immediately (optimistic UI)
    const previewUrl = URL.createObjectURL(file);
    setMessages(prev => [...prev, {
      from: 'user',
      content: promptText || '📸 Foto zur Analyse gesendet',
      photoUrl: previewUrl,
      type: 'message',
      timestamp: new Date().toISOString(),
    }]);

    // 2. Show thinking indicator
    setIsThinking(true);

    // 3. Convert to base64 (canvas-resized to max 1024px, quality 0.8)
    try {
      const base64 = await fileToBase64(file);
      const mimeType = file.type || 'image/jpeg';

      await fetch(`${API_BASE}/api/vision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: base64,
          mimeType,
          prompt: promptText || undefined,
        }),
      });
    } catch {
      setIsThinking(false);
      showToast('Foto konnte nicht analysiert werden — offline?');
    }
  }, [showToast]);

  // Privacy dismiss
  const handlePrivacyDismiss = useCallback(() => {
    setShowPrivacy(false);
    localStorage.setItem('miminox_privacy_seen', 'true');
  }, []);

  const displayName = assistantName || 'MiMiNox';

  return (
    <div className={`miminox mode-${appMode}`} id="app-root">
      {/* ── Map / SOS / Settings Overlays ───────────── */}
      {showMap && (
        <MapView onClose={() => setShowMap(false)} />
      )}
      {showConnect && (
        <ConnectModal onClose={() => setShowConnect(false)} />
      )}
      {showFieldTools && (
        <FieldToolsPanel onClose={() => setShowFieldTools(false)} />
      )}
      {showSos && (
        <SosOverlay
          onClose={() => setShowSos(false)}
          country={localStorage.getItem('miminox_country') || 'DE'}
        />
      )}
      {showSettings && (
        <SettingsPanel
          onClose={() => setShowSettings(false)}
          assistantName={displayName}
          onNameChange={(name) => {
            setAssistantName(name);
            localStorage.setItem('miminox_assistant_name', name);
            setShowSettings(false);
          }}
          onModeChange={(mode) => {
            setAppMode(mode);
          }}
        />
      )}

      {/* ── Name-Picker — nur beim allerersten Start ─────────── */}
      {showNamePicker && (
        <div className="name-picker-overlay" id="name-picker">
          <div className="name-picker-card">
            <div className="name-picker-logo">◑</div>
            <h1 className="name-picker-title">Wie soll ich heißen?</h1>
            <p className="name-picker-sub">
              Du bekommst deinen eigenen privaten Assistenten.<br />
              Such dir einen Namen aus — oder gib einen eigenen ein.
            </p>
            <div className="name-picker-suggestions">
              {NAME_SUGGESTIONS.map(n => (
                <button
                  key={n}
                  className="name-pill"
                  onClick={() => { setNameInput(n); }}
                  aria-label={`Namen ${n} wählen`}
                >
                  {n}
                </button>
              ))}
            </div>
            <div className="name-picker-input-row">
              <input
                className="name-picker-input"
                type="text"
                placeholder="Eigener Name..."
                value={nameInput}
                maxLength={20}
                onChange={e => setNameInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && nameInput.trim() && handleNameSelect(nameInput)}
                autoFocus
                aria-label="Eigenen Namen eingeben"
              />
              <button
                className="name-picker-confirm"
                onClick={() => handleNameSelect(nameInput || NAME_SUGGESTIONS[0])}
                id="name-picker-confirm"
              >
                Los →
              </button>
            </div>
            <p className="name-picker-hint">Du kannst den Namen später jederzeit ändern.</p>
          </div>
        </div>
      )}

      {/* ── Header — almost invisible ──────────────────────── */}
      <header className="header" id="miminox-header">
        <div className="header-logo">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L3 7v10l9 5 9-5V7l-9-5z" stroke="#C4A265" strokeWidth="1.5" fill="none"/>
            <circle cx="12" cy="12" r="3" fill="#7CB685" opacity="0.6"/>
          </svg>
          {displayName}
        </div>
        <div className="header-actions">
          <button
            className="header-btn sos-trigger"
            onClick={() => setShowSos(true)}
            title="SOS-Notfallmodus"
            id="btn-sos"
            aria-label="Notfall"
          >🆘</button>
          <button
            className="header-btn"
            onClick={() => setShowMap(true)}
            title="Offline-Karte"
            id="btn-map"
            aria-label="Karte"
          >🗺</button>
          <button
            className="header-btn"
            onClick={() => setShowConnect(true)}
            title="Auf Handy öffnen (QR)"
            id="btn-connect"
            aria-label="Verbinden"
          >📱</button>
          {appMode === 'crisis' && (
            <button
              className="header-btn"
              onClick={() => setShowFieldTools(true)}
              title="Feld-Tools"
              id="btn-field-tools"
              aria-label="Feld-Tools"
            >🛠️</button>
          )}
          <ModeSwitcher mode={appMode} onModeChange={setAppMode} />
          <button
            className="header-btn"
            onClick={() => setShowSettings(true)}
            title="Einstellungen"
            id="btn-settings"
            aria-label="Einstellungen"
          >⚙️</button>
          <div className="header-status">
            <span className={`status-dot ${isLive ? '' : 'offline'}`} />
            <span>{isLive ? 'Privat' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* ── Gedankenraum ───────────────────────────────────── */}
      <main className="gedankenraum" id="gedankenraum">

        {/* Onboarding (first-ever start — nach Name-Picker) */}
        {showOnboarding && !showNamePicker && (
          <div className="onboarding" id="onboarding">
            <p className="onboarding-text">
              {appMode === 'daily' ? (
                <>
                  Hallo! Ich bin <strong>{displayName}</strong> — dein smarter Alltagsassistent.
                  <br /><br />
                  Ich helfe dir beim Kochen, Planen, Schreiben und allem anderen.
                  <br />
                  Alles läuft lokal. Keine Cloud. Kein Abo.
                </>
              ) : (
                <>
                  Hallo. Ich bin <strong>{displayName}</strong> — dein privates Gedächtnis.
                  <br /><br />
                  Ich lebe auf diesem Gerät. Alles was du mir sagst, bleibt hier.
                  <br />
                  Keine Cloud. Kein Abo. Nur du und ich.
                </>
              )}
            </p>
            <p className="onboarding-question">Was möchtest du wissen?</p>
            <div className="onboarding-chips">
              {getOnboardingPrompts(appMode).slice(0, 3).map(p => (
                <button
                  key={p}
                  className="onboarding-chip"
                  onClick={() => handleSubmit(p)}
                >{p}</button>
              ))}
            </div>
          </div>
        )}

        {/* Privacy Panel — first start (Tompkins Auflage 2) */}
        {showPrivacy && showOnboarding && (
          <PrivacyPanel onDismiss={handlePrivacyDismiss} />
        )}

        {/* Chat messages */}
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <ChatMessage key={msg.id || `${msg.timestamp}-${i}`} msg={msg} />
          ))}

          {/* Thinking indicator — shows while Gemma processes */}
          {isThinking && (
            <div className="msg-nox">
              <div className="msg-card thinking-indicator">
                <span className="thinking-dots">
                  <span>◑</span> {displayName} denkt nach
                  <span className="dot-anim">...</span>
                </span>
              </div>
            </div>
          )}
        </div>

        <div ref={bottomRef} />
      </main>

      {/* ── Action Bar ─────────────────────────────────────── */}
      <ActionBar
        onSubmit={handleSubmit}
        onPhoto={handlePhoto}
      />

      {/* ── Toast ──────────────────────────────────────────── */}
      {toast && <div className="toast" id="toast">{toast}</div>}
    </div>
  );
}

export default App;
