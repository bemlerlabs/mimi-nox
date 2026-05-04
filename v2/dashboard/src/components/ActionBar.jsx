/**
 * ◑ MiMiNox — Action Bar
 * Three gestures: Zeigen (📷) · Sprechen (🎙) · Fragen (▶)
 * + DACH-aware Notruf stripe (DE/AT/CH) — Feature #12
 */
import { useState, useRef } from 'react';

// DACH emergency numbers — Feature #12
const NOTRUF = {
  DE: { label: 'Notruf', num: '112',  gift: '030-19240', giftHref: 'tel:+493019240' },
  AT: { label: 'Notruf', num: '144',  gift: '01-4064343', giftHref: 'tel:+4314064343' },
  CH: { label: 'Notruf', num: '144',  gift: '145',         giftHref: 'tel:145' },
};

function getCountry() {
  return localStorage.getItem('miminox_country') || 'DE';
}


export function ActionBar({ onSubmit, onPhoto }) {
  const [value, setValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const fileRef = useRef(null);
  const recognitionRef = useRef(null);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    const text = value.trim();
    if (!text || loading) return;

    setLoading(true);
    setValue('');
    try {
      await onSubmit(text);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // 📷 Camera / Photo
  const handlePhotoClick = () => {
    fileRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Pass current text input as context for the image analysis
      const currentText = value.trim();
      onPhoto?.(file, currentText);
      setValue('');          // Clear input after sending
      e.target.value = '';
    }
  };

  // 🎙 Voice (Web Speech API — browser-native, no Whisper needed)
  const handleVoiceClick = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Spracherkennung wird in diesem Browser nicht unterstützt.');
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'de-DE';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setValue(prev => prev + transcript);
      setListening(false);
    };

    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  return (
    <div className="action-bar" id="action-bar">
      {/* Input row */}
      <form className="action-input-row" onSubmit={handleSubmit}>
        <input
          className="action-input"
          type="text"
          placeholder="Schreib, was du denkst…"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          id="main-input"
          autoComplete="off"
        />
      </form>

      {/* Three gesture buttons */}
      <div className="action-buttons">
        <div className="action-btn-group">
          <button
            className="action-btn"
            onClick={handlePhotoClick}
            title="Foto zeigen"
            id="btn-camera"
          >
            📷
          </button>
          <span className="action-btn-label">Zeigen</span>
        </div>

        <div className="action-btn-group">
          <button
            className={`action-btn ${listening ? 'primary' : ''}`}
            onClick={handleVoiceClick}
            title={listening ? 'Aufnahme stoppen' : 'Sprechen'}
            id="btn-voice"
          >
            🎙
          </button>
          <span className="action-btn-label">{listening ? 'Hört zu…' : 'Sprechen'}</span>
        </div>

        <div className="action-btn-group">
          <button
            className="action-btn primary"
            onClick={handleSubmit}
            disabled={!value.trim() || loading}
            title="Fragen"
            id="btn-send"
          >
            ▶
          </button>
          <span className="action-btn-label">Fragen</span>
        </div>
      </div>

      {/* Hidden file input for camera */}
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {/* Notruf stripe — DACH-aware, always visible (Feature #12) */}
      <div className="notruf-stripe" id="notruf-stripe">
        {(() => {
          const c = NOTRUF[getCountry()] || NOTRUF.DE;
          return <>
            🛡️ <a href={`tel:${c.num}`}>{c.label} {c.num}</a>
            {' · '}
            <a href={c.giftHref}>Giftnotruf {c.gift}</a>
          </>;
        })()}
      </div>
    </div>
  );
}
