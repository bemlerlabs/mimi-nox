/**
 * ◑ MiMiNox — SOS Schnellmodus
 * components/SosOverlay.jsx
 *
 * Drei große Buttons. Kein Tippen nötig. Sofortige Checkliste.
 * Für Situationen wo Adrenalin fließt und Hände zittern.
 *
 * Aktiviert per: SOS-Button (lang drücken im Header) oder "SOS"-Wort im Chat
 */

const SOS_SCENARIOS = [
  {
    id: 'unfall',
    emoji: '🚨',
    label: 'Unfall / Verletzung',
    color: '#D64045',
    steps: [
      'Eigene Sicherheit prüfen — kein zweiter Unfall!',
      'Bewusstsein prüfen: Ansprechen, Schulter anfassen',
      'Bewusstlos + atmet → Stabile Seitenlage',
      'Bewusstlos + atmet NICHT → Mund-zu-Mund + Herzdruckmassage (30:2)',
      'Blutung stoppen → Stark drücken, Tuch nutzen',
      'Notruf 112 / 144 rufen — nicht auflegen!',
    ],
  },
  {
    id: 'vergiftung',
    emoji: '☠️',
    label: 'Vergiftung / Verätzung',
    color: '#8B6914',
    steps: [
      'Was wurde eingenommen? Menge? Zeitpunkt?',
      'KEIN Erbrechen herbeiführen — verschlimmert oft!',
      'Bei Bewusstlosigkeit → Stabile Seitenlage',
      'Verpackung / Pflanze sicherstellen (Foto für Arzt)',
      'SOFORT: Giftnotruf oder Notruf anrufen',
      'Kind unter 5 Jahren → immer 112 / 144 rufen',
    ],
  },
  {
    id: 'anderes',
    emoji: '⚡',
    label: 'Andere Notlage',
    color: '#2A7FBF',
    steps: [
      'Ruhe bewahren — Panik kostet Zeit',
      'Eigene Sicherheit: Bin ich selbst in Gefahr?',
      'Überblick: Wie viele Personen betroffen?',
      'Notruf 112 rufen — die fragen was nötig ist',
      'In der Leitung bleiben bis Hilfe da ist',
      'Eingang / Zugang für Rettungskräfte freihalten',
    ],
  },
];

export function SosOverlay({ onClose, country = 'DE' }) {
  const [active, setActive] = useState(null);
  const notruf = country === 'AT' ? '144' : country === 'CH' ? '144' : '112';
  const giftnotruf = country === 'AT' ? '01-4064343'
    : country === 'CH' ? '145'
    : '030-19240';

  return (
    <div className="sos-overlay" id="sos-overlay" role="dialog" aria-modal="true">
      <div className="sos-header">
        <span className="sos-title">🆘 NOTFALL</span>
        <button className="sos-close" onClick={onClose} aria-label="SOS-Modus schließen">✕</button>
      </div>

      {!active ? (
        <>
          <p className="sos-sub">Was ist passiert?</p>
          <div className="sos-scenarios">
            {SOS_SCENARIOS.map(s => (
              <button
                key={s.id}
                className="sos-scenario-btn"
                style={{ '--sos-color': s.color }}
                onClick={() => setActive(s)}
                id={`sos-btn-${s.id}`}
              >
                <span className="sos-emoji">{s.emoji}</span>
                <span className="sos-label">{s.label}</span>
              </button>
            ))}
          </div>
          <div className="sos-direct-calls">
            <a href={`tel:${notruf}`} className="sos-call-btn sos-call-primary">
              📞 Notruf {notruf}
            </a>
            <a href={`tel:${giftnotruf}`} className="sos-call-btn sos-call-secondary">
              ☠️ Giftnotruf {giftnotruf}
            </a>
          </div>
        </>
      ) : (
        <div className="sos-steps">
          <button className="sos-back" onClick={() => setActive(null)}>← Zurück</button>
          <div className="sos-steps-title">
            {active.emoji} {active.label}
          </div>
          <ol className="sos-steps-list">
            {active.steps.map((step, i) => (
              <li key={i} className="sos-step">{step}</li>
            ))}
          </ol>
          <a
            href={`tel:${notruf}`}
            className="sos-call-btn sos-call-primary sos-call-big"
          >
            📞 Notruf {notruf} JETZT RUFEN
          </a>
        </div>
      )}
    </div>
  );
}

// useState muss importiert werden
import { useState } from 'react';
