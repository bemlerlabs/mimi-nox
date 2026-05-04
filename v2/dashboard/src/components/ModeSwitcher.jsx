/**
 * ◑ MiMiNox — Modus-Wechsler
 * components/ModeSwitcher.jsx
 *
 * Kompakter Toggle im Header: 🟠 Krisen ↔ 🔵 Alltag
 * Schreibt Modus in localStorage + sendet POST /api/mode
 */
import { useState } from 'react';

const API_BASE = window.location.port === '5173' ? 'http://localhost:3001' : '';

const MODES = {
  crisis: { emoji: '🟠', label: 'Krisen',  next: 'daily',  title: 'Jetzt: Krisen-Modus — klicken für Alltag' },
  daily:  { emoji: '🔵', label: 'Alltag',  next: 'crisis', title: 'Jetzt: Alltags-Modus — klicken für Krisen' },
};

export function ModeSwitcher({ mode, onModeChange }) {
  const cfg = MODES[mode] || MODES.crisis;
  const [isLoading, setIsLoading] = useState(false);

  const handleToggle = async () => {
    if (isLoading) return;
    const next = cfg.next;
    setIsLoading(true);
    try {
      await fetch(`${API_BASE}/api/mode`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ mode: next }),
      });
      localStorage.setItem('miminox_mode', next);
      onModeChange(next);
    } catch {
      // Offline: nur lokal wechseln
      localStorage.setItem('miminox_mode', next);
      onModeChange(next);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      className={`mode-switcher mode-${mode}${isLoading ? ' loading' : ''}`}
      onClick={handleToggle}
      title={cfg.title}
      id="btn-mode-switcher"
      aria-label={`Modus wechseln (aktuell: ${cfg.label})`}
      disabled={isLoading}
    >
      <span className="mode-emoji">{isLoading ? '⏳' : cfg.emoji}</span>
      <span className="mode-label">{cfg.label}</span>
    </button>
  );
}
