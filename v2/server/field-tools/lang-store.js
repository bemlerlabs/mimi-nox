/**
 * ◑ MiMiNox — Sprach-Store
 * server/field-tools/lang-store.js
 *
 * Immutable State Machine für Sprach-Einstellungen.
 * Unterstützte Sprachen: DE, EN, FR, ES, IT, TR
 *
 * Kein DOM — testbar mit Vitest.
 */

export const SUPPORTED_LANGUAGES = [
  { code: 'de', label: 'Deutsch',    flag: '🇩🇪', ttsLocale: 'de-DE', nativeName: 'Deutsch' },
  { code: 'en', label: 'English',    flag: '🇬🇧', ttsLocale: 'en-US', nativeName: 'English' },
  { code: 'fr', label: 'Français',   flag: '🇫🇷', ttsLocale: 'fr-FR', nativeName: 'Français' },
  { code: 'es', label: 'Español',    flag: '🇪🇸', ttsLocale: 'es-ES', nativeName: 'Español' },
  { code: 'it', label: 'Italiano',   flag: '🇮🇹', ttsLocale: 'it-IT', nativeName: 'Italiano' },
  { code: 'tr', label: 'Türkçe',     flag: '🇹🇷', ttsLocale: 'tr-TR', nativeName: 'Türkçe' },
];

const LANG_MAP = Object.fromEntries(SUPPORTED_LANGUAGES.map(l => [l.code, l]));

/** UI-Texte pro Sprache */
const UI_STRINGS = {
  de: {
    settings:    'Einstellungen',
    language:    'Sprache',
    save:        'Speichern',
    region:      'Region',
    name:        'Name des Assistenten',
    clearAll:    'Alles löschen (DSGVO)',
    export:      'Memories exportieren',
    notruf:      'Notruf',
    hint_lang:   'Ändert die Sprache der Oberfläche und der Sprachausgabe.',
  },
  en: {
    settings:    'Settings',
    language:    'Language',
    save:        'Save',
    region:      'Region',
    name:        'Assistant Name',
    clearAll:    'Delete everything (GDPR)',
    export:      'Export memories',
    notruf:      'Emergency',
    hint_lang:   'Changes the interface language and text-to-speech voice.',
  },
  fr: {
    settings:    'Paramètres',
    language:    'Langue',
    save:        'Enregistrer',
    region:      'Région',
    name:        "Nom de l'assistant",
    clearAll:    'Tout supprimer (RGPD)',
    export:      'Exporter les souvenirs',
    notruf:      'Urgence',
    hint_lang:   "Change la langue de l'interface et de la synthèse vocale.",
  },
  es: {
    settings:    'Configuración',
    language:    'Idioma',
    save:        'Guardar',
    region:      'Región',
    name:        'Nombre del asistente',
    clearAll:    'Eliminar todo (RGPD)',
    export:      'Exportar memorias',
    notruf:      'Emergencia',
    hint_lang:   'Cambia el idioma de la interfaz y de la voz.',
  },
  it: {
    settings:    'Impostazioni',
    language:    'Lingua',
    save:        'Salva',
    region:      'Regione',
    name:        "Nome dell'assistente",
    clearAll:    'Elimina tutto (GDPR)',
    export:      'Esporta memorie',
    notruf:      'Emergenza',
    hint_lang:   "Cambia la lingua dell'interfaccia e della voce.",
  },
  tr: {
    settings:    'Ayarlar',
    language:    'Dil',
    save:        'Kaydet',
    region:      'Bölge',
    name:        'Asistan Adı',
    clearAll:    'Her şeyi sil (KVKK)',
    export:      'Anıları dışa aktar',
    notruf:      'Acil',
    hint_lang:   'Arayüz ve ses sentezi dilini değiştirir.',
  },
};

/**
 * Erstellt einen leeren Sprach-Store mit Default 'de'.
 * @returns {{ lang: string }}
 */
export function createLangStore() {
  return { lang: 'de' };
}

/**
 * Setzt die Sprache (immutable).
 * @param {{ lang: string }} store
 * @param {string} code
 * @returns {{ lang: string }}
 * @throws {Error} bei ungültigem Code
 */
export function setLanguage(store, code) {
  if (!LANG_MAP[code]) {
    throw new Error(`Sprache nicht unterstützt: ${code}. Gültig: ${Object.keys(LANG_MAP).join(', ')}`);
  }
  return { ...store, lang: code };
}

/**
 * Gibt die aktuelle Sprache zurück.
 * @param {{ lang: string }} store
 * @returns {string}
 */
export function getLanguage(store) {
  return store.lang;
}

/**
 * Gibt den TTS-Locale-String für eine Sprache zurück.
 * @param {string} code
 * @returns {string} z.B. 'de-DE', 'en-US'
 */
export function getTtsLang(code) {
  return LANG_MAP[code]?.ttsLocale ?? 'de-DE';
}

/**
 * Gibt UI-Strings für eine Sprache zurück.
 * @param {string} code
 * @returns {Record<string, string>}
 */
export function getUiStrings(code) {
  return UI_STRINGS[code] ?? UI_STRINGS['de'];
}

/**
 * Gibt "Flag + Label" für eine Sprache zurück.
 * @param {string} code
 * @returns {string} z.B. '🇩🇪 Deutsch'
 */
export function formatLangLabel(code) {
  const lang = LANG_MAP[code];
  if (!lang) return code;
  return `${lang.flag} ${lang.nativeName}`;
}
