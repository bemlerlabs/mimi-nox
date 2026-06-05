/**
 * ◑ MiMiNox Field-Tools Panel
 * Ein Overlay mit 10 offline-fähigen Werkzeugen.
 *
 * Tabs: Licht · Ton · Navigation · Kamera · Chat
 */
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';

// ── Pure-Logic Imports (alle TDD-getestet) ───────────────────
import { toggleTorch, createTorchState, TORCH_ON } from '../../../server/field-tools/torch.js';
import { buildUtterance } from '../../../server/field-tools/tts.js';
import { encodeMorse, buildMorseTimeline, MORSE_DIT_MS, MORSE_DAH_MS } from '../../../server/field-tools/morse.js';
import { getSunTimes, getMinutesUntilSunset, formatSunTime } from '../../../server/field-tools/sun.js';
import { parseGpsExtended, formatAltitude, formatSpeed, headingToCardinal } from '../../../server/field-tools/gps-extended.js';
import { createTrackRecorder, addTrackPoint, exportGpx, RECORDER_IDLE, RECORDER_RECORDING } from '../../../server/field-tools/track-recorder.js';

const TABS = [
  { id: 'licht',   label: '🔦', title: 'Licht & Signal' },
  { id: 'ton',     label: '🔊', title: 'Ton & Morse' },
  { id: 'nav',     label: '🧭', title: 'Navigation' },
  { id: 'sonne',   label: '☀️', title: 'Sonne' },
  { id: 'track',   label: '📍', title: 'Track & GPX' },
];

// ── Torch Hook ───────────────────────────────────────────────
function useTorch() {
  const [torchState, setTorchState] = useState(createTorchState);
  const wakeLockRef = useRef(null);

  const toggle = useCallback(async () => {
    const next = toggleTorch(torchState);
    setTorchState(next);
    if (next.status === TORCH_ON) {
      try {
        wakeLockRef.current = await navigator.wakeLock?.request('screen');
      } catch { /* wake lock nicht unterstützt */ }
    } else {
      wakeLockRef.current?.release();
      wakeLockRef.current = null;
    }
  }, [torchState]);

  // Bei Overlay-Close aufräumen
  useEffect(() => () => { wakeLockRef.current?.release(); }, []);
  return { torchState, toggle };
}

// ── GPS Hook ─────────────────────────────────────────────────
function useGps() {
  const [pos, setPos] = useState(null);
  const [error, setError] = useState(() => (
    navigator.geolocation ? null : 'GPS nicht verfügbar'
  ));
  const watchRef = useRef(null);

  useEffect(() => {
    if (!navigator.geolocation) {
      return;
    }
    watchRef.current = navigator.geolocation.watchPosition(
      p  => setPos(parseGpsExtended(p.coords)),
      () => setError('GPS-Zugriff verweigert'),
      { enableHighAccuracy: true, maximumAge: 5000 }
    );
    return () => navigator.geolocation.clearWatch(watchRef.current);
  }, []);

  return { pos, error };
}

// ── Track Hook ───────────────────────────────────────────────
function useTrack(pos) {
  const [recorder, setRecorder] = useState(() => createTrackRecorder({ name: 'MiMiNox-Tour' }));

  const startStop = useCallback(() => {
    if (recorder.status === RECORDER_RECORDING) {
      setRecorder(r => ({ ...r, status: RECORDER_IDLE }));
    } else if (pos) {
      setRecorder(r => addTrackPoint(r, {
        lat: pos.latitude, lng: pos.longitude, alt: pos.altitude,
        timestamp: new Date(),
      }));
    }
  }, [recorder.status, pos]);

  // Punkt alle 5s hinzufügen wenn aufzeichnung aktiv
  useEffect(() => {
    if (recorder.status !== RECORDER_RECORDING || !pos) return;
    const id = setInterval(() => {
      setRecorder(r => addTrackPoint(r, {
        lat: pos.latitude, lng: pos.longitude, alt: pos.altitude,
        timestamp: new Date(),
      }));
    }, 5000);
    return () => clearInterval(id);
  }, [recorder.status, pos]);

  const downloadGpx = useCallback(() => {
    try {
      const gpx  = exportGpx(recorder);
      const blob = new Blob([gpx], { type: 'application/gpx+xml' });
      const url  = URL.createObjectURL(blob);
      const a    = Object.assign(document.createElement('a'), {
        href: url,
        download: `miminox-tour-${Date.now()}.gpx`,
      });
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert(e.message); }
  }, [recorder]);

  return { recorder, startStop, downloadGpx };
}

// ── Morse Hook ───────────────────────────────────────────────
function useMorse() {
  const [playing, setPlaying] = useState(false);
  const ctxRef = useRef(null);
  const stopRef = useRef(null);

  const playMorse = useCallback(async (text = 'SOS') => {
    if (playing) { stopRef.current?.(); return; }
    setPlaying(true);
    const timeline = buildMorseTimeline(text);
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) { setPlaying(false); return; }

    const ctx  = new AudioCtx();
    ctxRef.current = ctx;
    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 750;
    gain.gain.value = 0;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();

    let t = ctx.currentTime + 0.05;
    for (const entry of timeline) {
      if (entry.type === 'ON') {
        gain.gain.setValueAtTime(1, t);
        t += entry.durationMs / 1000;
        gain.gain.setValueAtTime(0, t);
      } else {
        t += entry.durationMs / 1000;
      }
    }

    stopRef.current = () => { osc.stop(); ctx.close(); setPlaying(false); };
    setTimeout(() => { osc.stop(); ctx.close(); setPlaying(false); }, t * 1000 + 200);
  }, [playing]);

  return { playing, playMorse };
}

// ── Sun Panel ────────────────────────────────────────────────
function SunPanel({ pos }) {
  const sun = useMemo(() => {
    if (!pos) return;
    const times   = getSunTimes(new Date(), pos.latitude, pos.longitude);
    const minsLeft = getMinutesUntilSunset(new Date(), pos.latitude, pos.longitude);
    return { times, minsLeft };
  }, [pos]);

  if (!pos) return <p className="ft-hint">GPS aktivieren für Sonnenzeiten.</p>;

  const { times, minsLeft } = sun;
  const isNight = minsLeft < 0;
  const h = Math.abs(Math.floor(minsLeft / 60));
  const m = Math.abs(minsLeft % 60);

  return (
    <div className="ft-sun">
      <div className="ft-sun-row">
        <span>🌅 Sonnenaufgang</span>
        <strong>{formatSunTime(times.sunrise)}</strong>
      </div>
      <div className="ft-sun-row">
        <span>🌇 Sonnenuntergang</span>
        <strong>{formatSunTime(times.sunset)}</strong>
      </div>
      <div className={`ft-sun-countdown ${isNight ? 'night' : ''}`}>
        {isNight
          ? `🌙 Seit ${h}h ${m}m dunkel`
          : `⏳ Noch ${h}h ${m}m Licht`}
      </div>
    </div>
  );
}

// ── Nav Panel ────────────────────────────────────────────────
function NavPanel({ pos, error }) {
  if (error) return <p className="ft-hint ft-error">{error}</p>;
  if (!pos)  return <p className="ft-hint">GPS-Signal wird gesucht…</p>;

  const h = pos.heading != null ? pos.heading : null;
  const needleStyle = h != null ? { transform: `rotate(${h}deg)` } : {};

  return (
    <div className="ft-nav">
      <div className="ft-compass" aria-label="Kompass">
        <div className="ft-compass-ring">
          <span className="ft-compass-n">N</span>
          <span className="ft-compass-s">S</span>
          <span className="ft-compass-e">O</span>
          <span className="ft-compass-w">W</span>
          <div className="ft-compass-needle" style={needleStyle} />
        </div>
        {h != null && (
          <p className="ft-compass-label">{Math.round(h)}° {headingToCardinal(h)}</p>
        )}
      </div>
      <div className="ft-gps-grid">
        <div className="ft-gps-cell">
          <span>Höhe</span>
          <strong>{formatAltitude(pos.altitude)}</strong>
        </div>
        <div className="ft-gps-cell">
          <span>Tempo</span>
          <strong>{formatSpeed(pos.speedKmh)}</strong>
        </div>
        <div className="ft-gps-cell">
          <span>Lat</span>
          <strong>{pos.latitude.toFixed(5)}</strong>
        </div>
        <div className="ft-gps-cell">
          <span>Lng</span>
          <strong>{pos.longitude.toFixed(5)}</strong>
        </div>
      </div>
    </div>
  );
}

// ── Blitz-Donner Tool ────────────────────────────────────────
function LightningTimer() {
  const [running, setRunning] = useState(false);
  const [start, setStart]   = useState(null);
  const [km, setKm]         = useState(null);

  const handleClick = () => {
    if (!running) {
      setRunning(true);
      setStart(performance.now());
      setKm(null);
    } else {
      const secs = (performance.now() - start) / 1000;
      setKm((secs / 3.0).toFixed(1));
      setRunning(false);
    }
  };

  return (
    <div className="ft-lightning">
      <p className="ft-hint">Blitz gesehen → Knopf drücken → Donner → nochmal drücken</p>
      <button className={`ft-btn-big ${running ? 'active' : ''}`} onClick={handleClick} id="btn-lightning">
        {running ? '⚡ Donner gehört?' : '⚡ Blitz gesehen!'}
      </button>
      {km && (
        <div className={`ft-lightning-result ${parseFloat(km) < 3 ? 'danger' : ''}`}>
          🌩 Gewitter ist ca. <strong>{km} km</strong> entfernt
          {parseFloat(km) < 3 && <span className="ft-warning"> ⚠️ Sofort Schutz suchen!</span>}
        </div>
      )}
    </div>
  );
}

// ── Haupt-Komponente ─────────────────────────────────────────
export function FieldToolsPanel({ onClose }) {
  const [activeTab, setActiveTab] = useState('licht');
  const { torchState, toggle: toggleTorchFn } = useTorch();
  const { pos, error: gpsError } = useGps();
  const { recorder, startStop, downloadGpx } = useTrack(pos);
  const { playing, playMorse } = useMorse();

  // TTS
  const speak = useCallback((text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = buildUtterance(text, { lang: 'de-DE', rate: 0.9 });
    const utt = new SpeechSynthesisUtterance(u.text);
    utt.lang = u.lang;
    utt.rate = u.rate;
    window.speechSynthesis.speak(utt);
  }, []);

  const isTorchOn = torchState.status === TORCH_ON;

  return (
    <div className={`ft-overlay ${isTorchOn ? 'torch-active' : ''}`} id="field-tools-overlay">
      <div className="ft-panel" id="field-tools-panel">

        {/* Header */}
        <div className="ft-header">
          <span className="ft-title">⚙ Feld-Tools</span>
          <button className="ft-close" onClick={onClose} id="btn-ft-close" aria-label="Schließen">✕</button>
        </div>

        {/* Tabs */}
        <nav className="ft-tabs" role="tablist">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`ft-tab ${activeTab === t.id ? 'active' : ''}`}
              onClick={() => setActiveTab(t.id)}
              id={`tab-${t.id}`}
              role="tab"
              aria-selected={activeTab === t.id}
              title={t.title}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* Tab-Inhalt */}
        <div className="ft-body">

          {/* ── Licht & Signal ── */}
          {activeTab === 'licht' && (
            <div className="ft-section" id="tab-content-licht">
              <h3 className="ft-section-title">🔦 Taschenlampe</h3>
              <button
                className={`ft-btn-big ${isTorchOn ? 'active' : ''}`}
                onClick={toggleTorchFn}
                id="btn-torch"
              >
                {isTorchOn ? '💡 AN — Tippen zum Ausschalten' : '🔦 Taschenlampe einschalten'}
              </button>

              <h3 className="ft-section-title" style={{ marginTop: '1.5rem' }}>🌙 Rot-Licht Modus</h3>
              <p className="ft-hint">Schont die Dunkeladaption der Augen.</p>
              <button
                className="ft-btn"
                onClick={() => document.querySelector('.miminox')?.classList.toggle('red-light-mode')}
                id="btn-redlight"
              >
                🔴 Rot-Licht umschalten
              </button>

              <h3 className="ft-section-title" style={{ marginTop: '1.5rem' }}>⚡ Blitz-Donner Entfernung</h3>
              <LightningTimer />
            </div>
          )}

          {/* ── Ton & Morse ── */}
          {activeTab === 'ton' && (
            <div className="ft-section" id="tab-content-ton">
              <h3 className="ft-section-title">📡 SOS Morse-Ton</h3>
              <p className="ft-hint">Spielt SOS (... --- ...) als Ton ab. International bekannt.</p>
              <div className="ft-morse-display">{encodeMorse('SOS')}</div>
              <button
                className={`ft-btn-big ${playing ? 'active' : ''}`}
                onClick={() => playMorse('SOS')}
                id="btn-sos-morse"
              >
                {playing ? '⏹ Stoppen' : '📡 SOS Morse abspielen'}
              </button>

              <h3 className="ft-section-title" style={{ marginTop: '1.5rem' }}>🔊 Vorlesen (TTS)</h3>
              <p className="ft-hint">Liest Text laut vor — 100% offline.</p>
              {[
                'Ich brauche Hilfe. Bitte ruft den Notruf.',
                'Achtung! Gewitter nähert sich. Schutz suchen.',
                'Alles in Ordnung. Kein Notfall.',
              ].map(text => (
                <button key={text} className="ft-btn" onClick={() => speak(text)} style={{ marginBottom: '0.5rem' }}>
                  🔊 {text.slice(0, 35)}…
                </button>
              ))}
            </div>
          )}

          {/* ── Navigation ── */}
          {activeTab === 'nav' && (
            <div className="ft-section" id="tab-content-nav">
              <h3 className="ft-section-title">🧭 Kompass + GPS</h3>
              <NavPanel pos={pos} error={gpsError} />
            </div>
          )}

          {/* ── Sonne ── */}
          {activeTab === 'sonne' && (
            <div className="ft-section" id="tab-content-sonne">
              <h3 className="ft-section-title">☀️ Sonnenuntergang</h3>
              <SunPanel pos={pos} />
            </div>
          )}

          {/* ── Track & GPX ── */}
          {activeTab === 'track' && (
            <div className="ft-section" id="tab-content-track">
              <h3 className="ft-section-title">📍 GPS-Track aufzeichnen</h3>
              {!pos && <p className="ft-hint ft-error">GPS wird benötigt.</p>}
              <div className="ft-track-status">
                <span className={`ft-track-dot ${recorder.status === RECORDER_RECORDING ? 'recording' : ''}`} />
                <span>
                  {recorder.status === RECORDER_RECORDING
                    ? `Aufzeichnung aktiv — ${recorder.points.length} Punkte`
                    : 'Bereit'}
                </span>
              </div>
              <button
                className={`ft-btn-big ${recorder.status === RECORDER_RECORDING ? 'active' : ''}`}
                onClick={startStop}
                id="btn-track-start"
                disabled={!pos && recorder.status !== RECORDER_RECORDING}
              >
                {recorder.status === RECORDER_RECORDING ? '⏹ Aufzeichnung stoppen' : '▶ Aufzeichnung starten'}
              </button>
              {recorder.points.length > 0 && recorder.status === RECORDER_IDLE && (
                <button className="ft-btn" onClick={downloadGpx} id="btn-track-export" style={{ marginTop: '0.75rem' }}>
                  ⬇ GPX exportieren ({recorder.points.length} Punkte)
                </button>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
