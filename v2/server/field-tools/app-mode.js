/**
 * ◑ MiMiNox — App-Modus-Wechsler
 * server/field-tools/app-mode.js
 *
 * Immutable State Machine für den App-Modus.
 * Unterstützte Modi: 'crisis' (Krisen/Outdoor) | 'daily' (Alltag)
 *
 * Kein DOM — voll testbar mit Vitest.
 */

/** Alle unterstützten App-Modi */
export const MODES = ['crisis', 'daily'];

/**
 * Modus-Konfigurationen
 * @type {Record<string, Object>}
 */
const MODE_CONFIGS = {
  crisis: {
    label:           'Krisen & Outdoor',
    emoji:           '🟠',
    theme:           'mode-crisis',
    accentColor:     '#C4A265',         // Brass
    bgColor:         '#0D1117',         // Dunkel
    showFieldTools:  true,
    systemPromptKey: 'crisis',
    description:     'Survival, Erste Hilfe, Navigation, SOS — optimiert für den Ernstfall.',
  },
  daily: {
    label:           'Alltag',
    emoji:           '🔵',
    theme:           'mode-daily',
    accentColor:     '#5B9BD5',         // Ruhiges Blau
    bgColor:         '#F5F7FA',         // Hell
    showFieldTools:  false,
    systemPromptKey: 'daily',
    description:     'Dein smarter Alltagshelfer für Kochen, Planung, Wissen & mehr.',
  },
};

/**
 * Onboarding-Beispiel-Prompts je Modus
 * @type {Record<string, string[]>}
 */
const ONBOARDING_PROMPTS = {
  crisis: [
    'Erste Hilfe bei Verbrennungen?',
    'Wie baue ich einen Notunterschlupf?',
    'Trinkwasser aufbereiten ohne Filter',
    'SOS-Signale geben',
    'Orientierung ohne GPS',
  ],
  daily: [
    'Was kann ich heute Abend kochen?',
    'Erstell mir eine Einkaufsliste für die Woche',
    'Erkläre mir kurz die Quantenphysik',
    'Hilf mir beim Schreiben einer E-Mail',
    'Gib mir Tipps gegen Prokrastination',
  ],
};

// ── State Machine ──────────────────────────────────────────────────

/**
 * Validiert einen Modus-Code.
 * @param {*} mode
 * @throws {Error} bei ungültigem Code
 */
function validateMode(mode) {
  if (!mode || !MODES.includes(mode)) {
    throw new Error(
      `Ungültiger App-Modus: "${mode}". Gültig: ${MODES.join(', ')}`
    );
  }
}

/**
 * Erstellt einen neuen Modus-Store.
 * @param {string} [initialMode='crisis']
 * @returns {{ mode: string }}
 */
export function createModeStore(initialMode = 'crisis') {
  validateMode(initialMode);
  return { mode: initialMode };
}

/**
 * Wechselt den Modus (immutable).
 * @param {{ mode: string }} store
 * @param {string} mode
 * @returns {{ mode: string }}
 * @throws {Error} bei ungültigem Code
 */
export function setMode(store, mode) {
  validateMode(mode);
  return { ...store, mode };
}

/**
 * Gibt den aktuellen Modus zurück.
 * @param {{ mode: string }} store
 * @returns {string}
 */
export function getMode(store) {
  return store.mode;
}

// ── Config-Helfer ──────────────────────────────────────────────────

/**
 * Gibt die vollständige Konfiguration für einen Modus zurück.
 * @param {string} mode
 * @returns {Object}
 * @throws {Error} bei ungültigem Code
 */
export function getModeConfig(mode) {
  validateMode(mode);
  return MODE_CONFIGS[mode];
}

/**
 * Gibt das Label für einen Modus zurück.
 * @param {string} mode
 * @returns {string}
 */
export function getModeLabel(mode) {
  validateMode(mode);
  return MODE_CONFIGS[mode].label;
}

/**
 * Gibt das Emoji für einen Modus zurück.
 * @param {string} mode
 * @returns {string}
 */
export function getModeEmoji(mode) {
  validateMode(mode);
  return MODE_CONFIGS[mode].emoji;
}

/**
 * Gibt zurück ob Field-Tools in diesem Modus sichtbar sind.
 * @param {string} mode
 * @returns {boolean}
 */
export function showsFieldTools(mode) {
  validateMode(mode);
  return MODE_CONFIGS[mode].showFieldTools;
}

/**
 * Gibt die Onboarding-Beispiel-Prompts für einen Modus zurück.
 * @param {string} mode
 * @returns {string[]}
 */
export function getOnboardingPrompts(mode) {
  validateMode(mode);
  return ONBOARDING_PROMPTS[mode];
}
