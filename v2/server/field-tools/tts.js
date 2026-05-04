/**
 * ◑ MiMiNox Field-Tools — TTS State + Utterance Builder
 * server/field-tools/tts.js
 *
 * Pure Logik — kein DOM, kein window.speechSynthesis.
 * Die UI-Komponente ruft window.speechSynthesis.speak(buildUtterance(...)) auf.
 */

export const TTS_IDLE     = 'idle';
export const TTS_SPEAKING = 'speaking';
export const TTS_STOPPED  = 'stopped';

const MAX_LENGTH  = 500;   // Browser-Limit für sichere Länge
const MIN_RATE    = 0.1;
const MAX_RATE    = 2;
const DEFAULT_LANG = 'de-DE';
const DEFAULT_RATE = 0.9;

/**
 * Erstellt einen frischen TTS-State.
 * @returns {TtsState}
 */
export function createTtsState() {
  return {
    status: TTS_IDLE,
    text:   '',
  };
}

/**
 * Baut eine Utterance-Konfiguration für window.speechSynthesis.
 * Validiert und sanitiert alle Eingaben.
 *
 * @param {string} text    - Zu sprechender Text
 * @param {object} [opts]  - { lang, rate, pitch, volume }
 * @returns {{ text, lang, rate, pitch, volume }}
 * @throws {Error} wenn text leer ist
 */
export function buildUtterance(text, opts = {}) {
  const trimmed = (text ?? '').trim();
  if (!trimmed) {
    throw new Error('TTS: Text darf nicht leer sein');
  }

  const truncated = trimmed.slice(0, MAX_LENGTH);

  const rate = Math.min(MAX_RATE, Math.max(MIN_RATE, opts.rate ?? DEFAULT_RATE));

  return {
    text:   truncated,
    lang:   opts.lang   ?? DEFAULT_LANG,
    rate,
    pitch:  opts.pitch  ?? 1,
    volume: opts.volume ?? 1,
  };
}
