/**
 * ◑ MiMiNox — Einstellungs-Panel
 * components/SettingsPanel.jsx
 *
 * Einfaches Drawer-Panel für:
 *   - Assistenten-Name ändern
 *   - Region (DE/AT/CH) ändern
 *   - Familien-Profile verwalten
 *   - Chat + Memory löschen (DSGVO)
 *   - Backup / Export (Memories als JSON)
 */
import { useState, useEffect } from 'react';
import { SUPPORTED_LANGUAGES } from '../../../server/field-tools/lang-store.js';


const COUNTRIES = [
  { code: 'DE', label: '🇩🇪 Deutschland', notruf: '112' },
  { code: 'AT', label: '🇦🇹 Österreich', notruf: '144' },
  { code: 'CH', label: '🇨🇭 Schweiz', notruf: '144' },
];

const NAME_SUGGESTIONS = ['Mia', 'Nova', 'Cara', 'Lena', 'Mimi', 'Finn', 'Sam', 'Leo'];

const API_BASE = window.location.port === '5173' ? 'http://localhost:3001' : '';

export function SettingsPanel({ onClose, assistantName, onNameChange, onCountryChange, onLangChange, onModeChange }) {
  const [nameInput, setNameInput] = useState(assistantName);
  const [appMode, setAppModeLocal] = useState(localStorage.getItem('miminox_mode') || 'crisis');
  const [country, setCountry] = useState(localStorage.getItem('miminox_country') || 'DE');
  const [lang, setLang] = useState(localStorage.getItem('miminox_lang') || 'de');
  const [profiles, setProfiles] = useState([]);
  const [newProfile, setNewProfile] = useState({ name: '', age: '', weight: '', notes: '' });
  const [memories, setMemories] = useState([]);
  const [confirmClear, setConfirmClear] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/memory`)
      .then(r => r.ok ? r.json() : [])
      .then(mems => {
        setMemories(mems.filter(m => !m.key.startsWith('__')));
        // Familien-Profile aus Memory lesen
        const profileMems = mems.filter(m => m.key.startsWith('profil_'));
        setProfiles(profileMems.map(m => {
          try { return JSON.parse(m.value); } catch { return { name: m.value }; }
        }));
      })
      .catch(() => {});
  }, []);

  const handleSaveMode = async (mode) => {
    setAppModeLocal(mode);
    localStorage.setItem('miminox_mode', mode);
    onModeChange?.(mode);
    try {
      await fetch(`${API_BASE}/api/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
    } catch { /* offline — localStorage reicht */ }
  };

  const handleSaveName = async () => {
    const name = nameInput.trim() || assistantName;
    onNameChange(name);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleSaveCountry = (code) => {
    setCountry(code);
    localStorage.setItem('miminox_country', code);
    onCountryChange?.(code);
    const labelMap = { DE: 'Deutschland', AT: 'Österreich', CH: 'Schweiz' };
    fetch(`${API_BASE}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: `Ich lebe in ${labelMap[code]}` }),
    }).catch(() => {});
  };

  const handleSaveLang = (code) => {
    setLang(code);
    localStorage.setItem('miminox_lang', code);
    onLangChange?.(code);
    // Seite neu laden damit alle UI-Strings aktualisiert werden
    // (kleines Timeout damit State geschrieben wird)
    setTimeout(() => window.location.reload(), 100);
  };

  const handleAddProfile = async () => {
    if (!newProfile.name.trim()) return;
    const key = `profil_${newProfile.name.toLowerCase().replace(/\s+/g, '_')}`;
    await fetch(`${API_BASE}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: `Merke dir: ${key} = ${JSON.stringify(newProfile)}`
      }),
    }).catch(() => {});
    setProfiles(p => [...p, { ...newProfile }]);
    setNewProfile({ name: '', age: '', weight: '', notes: '' });
  };

  const handleExportMemory = () => {
    const blob = new Blob([JSON.stringify(memories, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `miminox-memories-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClearAll = async () => {
    if (!confirmClear) { setConfirmClear(true); return; }
    await Promise.all([
      fetch(`${API_BASE}/api/chat/history`, { method: 'DELETE' }),
      fetch(`${API_BASE}/api/memory`, { method: 'DELETE' }),
    ]).catch(() => {});
    setMemories([]);
    setProfiles([]);
    setConfirmClear(false);
    onClose();
  };

  return (
    <div className="settings-overlay" id="settings-panel" role="dialog" aria-modal="true">
      <div className="settings-panel">
        <div className="settings-header">
          <span className="settings-title">⚙️ Einstellungen</span>
          <button className="settings-close" onClick={onClose} aria-label="Schließen">✕</button>
        </div>

        <div className="settings-body">

          {/* ── Modus ──────────────────────────── */}
          <section className="settings-section">
            <h2 className="settings-section-title">App-Modus</h2>
            <p className="settings-hint">Wechsle zwischen Krisen- und Alltags-Assistent.</p>
            <div className="mode-btns">
              <button
                className={`mode-btn ${appMode === 'crisis' ? 'active' : ''}`}
                onClick={() => handleSaveMode('crisis')}
                id="mode-btn-crisis"
                aria-pressed={appMode === 'crisis'}
              >
                <span className="mode-btn-emoji">🟠</span>
                <span className="mode-btn-label">Krisen & Outdoor</span>
                <span className="mode-btn-desc">Erste Hilfe, Navigation, SOS</span>
              </button>
              <button
                className={`mode-btn ${appMode === 'daily' ? 'active' : ''}`}
                onClick={() => handleSaveMode('daily')}
                id="mode-btn-daily"
                aria-pressed={appMode === 'daily'}
              >
                <span className="mode-btn-emoji">🔵</span>
                <span className="mode-btn-label">Alltag</span>
                <span className="mode-btn-desc">Kochen, Planen, Allgemeinwissen</span>
              </button>
            </div>
          </section>

          {/* ── Name ──────────────────────────────────── */}
          <section className="settings-section">
            <h2 className="settings-section-title">Name des Assistenten</h2>
            <div className="settings-name-row">
              <div className="name-picker-suggestions" style={{ justifyContent: 'flex-start', marginBottom: 8 }}>
                {NAME_SUGGESTIONS.map(n => (
                  <button key={n} className="name-pill" onClick={() => setNameInput(n)}>{n}</button>
                ))}
              </div>
              <div className="name-picker-input-row">
                <input
                  className="name-picker-input"
                  value={nameInput}
                  onChange={e => setNameInput(e.target.value)}
                  placeholder="Eigener Name..."
                  maxLength={20}
                  id="settings-name-input"
                />
                <button className="name-picker-confirm" onClick={handleSaveName} id="settings-name-save">
                  {saved ? '✓' : 'Speichern'}
                </button>
              </div>
            </div>
          </section>

          {/* ── Sprache ──────────────────────────── */}
          <section className="settings-section">
            <h2 className="settings-section-title">🌍 Sprache / Language</h2>
            <p className="settings-hint">Ändert die Sprache der Oberfläche und der Sprachausgabe.</p>
            <div className="lang-btns">
              {SUPPORTED_LANGUAGES.map(l => (
                <button
                  key={l.code}
                  className={`lang-btn ${lang === l.code ? 'active' : ''}`}
                  onClick={() => handleSaveLang(l.code)}
                  id={`lang-btn-${l.code}`}
                  aria-pressed={lang === l.code}
                >
                  <span className="lang-flag">{l.flag}</span>
                  <span className="lang-name">{l.nativeName}</span>
                </button>
              ))}
            </div>
          </section>

          {/* ── Region ────────────────────────────────── */}
          <section className="settings-section">
            <h2 className="settings-section-title">Meine Region</h2>
            <p className="settings-hint">Bestimmt welche Notrufnummer unten angezeigt wird.</p>
            <div className="region-btns">
              {COUNTRIES.map(c => (
                <button
                  key={c.code}
                  className={`region-btn ${country === c.code ? 'active' : ''}`}
                  onClick={() => handleSaveCountry(c.code)}
                  id={`region-btn-${c.code.toLowerCase()}`}
                >
                  {c.label}<br /><small>Notruf {c.notruf}</small>
                </button>
              ))}
            </div>
          </section>

          {/* ── Familien-Profile ──────────────────────── */}
          <section className="settings-section">
            <h2 className="settings-section-title">Familien-Profile</h2>
            <p className="settings-hint">Für korrekte Dosierungen und personalisierte Hilfe.</p>
            {profiles.length > 0 && (
              <div className="profiles-list">
                {profiles.map((p, i) => (
                  <div key={i} className="profile-chip">
                    👤 {p.name}{p.age ? `, ${p.age}J` : ''}{p.weight ? `, ${p.weight}kg` : ''}
                  </div>
                ))}
              </div>
            )}
            <div className="profile-add-form">
              <input className="profile-input" placeholder="Name *" value={newProfile.name}
                onChange={e => setNewProfile(p => ({ ...p, name: e.target.value }))} id="profile-name" />
              <input className="profile-input" placeholder="Alter (Jahre)" type="number" value={newProfile.age}
                onChange={e => setNewProfile(p => ({ ...p, age: e.target.value }))} id="profile-age" />
              <input className="profile-input" placeholder="Gewicht (kg)" type="number" value={newProfile.weight}
                onChange={e => setNewProfile(p => ({ ...p, weight: e.target.value }))} id="profile-weight" />
              <input className="profile-input" placeholder="Besonderheiten (Allergie, etc.)" value={newProfile.notes}
                onChange={e => setNewProfile(p => ({ ...p, notes: e.target.value }))} id="profile-notes" />
              <button className="name-picker-confirm" style={{ width: '100%' }}
                onClick={handleAddProfile} id="profile-add-btn">
                + Profil hinzufügen
              </button>
            </div>
          </section>

          {/* ── Daten ─────────────────────────────────── */}
          <section className="settings-section">
            <h2 className="settings-section-title">Meine Daten</h2>
            <p className="settings-hint">{memories.length} gespeicherte Fakten · alles lokal auf diesem Gerät</p>
            <div className="settings-data-btns">
              <button className="settings-btn-secondary" onClick={handleExportMemory} id="btn-export">
                📤 Memories exportieren (.json)
              </button>
              <button
                className={`settings-btn-danger ${confirmClear ? 'confirm' : ''}`}
                onClick={handleClearAll}
                id="btn-clear-all"
              >
                {confirmClear ? '⚠️ Wirklich alles löschen?' : '🗑️ Alles löschen (DSGVO)'}
              </button>
            </div>
          </section>

          <p className="settings-footer">
            ◑ MiMiNox · Alles auf diesem Gerät · Keine Cloud
          </p>
        </div>
      </div>
    </div>
  );
}
