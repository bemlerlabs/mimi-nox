/**
 * ◑ MiMiNox — Test: Sprach-Einstellungen
 * Feature: User kann Sprache wählen → UI + TTS + Antworten auf Wunsch-Sprache
 *
 * TDD: Tests FIRST — Given/When/Then
 */
import { describe, it, expect } from 'vitest';
import {
  SUPPORTED_LANGUAGES,
  getLanguage,
  setLanguage,
  createLangStore,
  formatLangLabel,
  getTtsLang,
  getUiStrings,
} from '../../server/field-tools/lang-store.js';

describe('Sprach-Einstellungen', () => {

  // GIVEN SUPPORTED_LANGUAGES
  // THEN enthält de, en, fr, es, it, tr
  it('[D] GIVEN SUPPORTED_LANGUAGES THEN has de en fr es it tr', () => {
    const codes = SUPPORTED_LANGUAGES.map(l => l.code);
    expect(codes).toContain('de');
    expect(codes).toContain('en');
    expect(codes).toContain('fr');
    expect(codes).toContain('es');
    expect(codes).toContain('it');
    expect(codes).toContain('tr');
  });

  // GIVEN jede Sprache
  // THEN hat code, label, flag, ttsLocale
  it('[D] GIVEN each language WHEN inspected THEN has code label flag ttsLocale', () => {
    for (const lang of SUPPORTED_LANGUAGES) {
      expect(lang.code).toBeDefined();
      expect(lang.label).toBeDefined();
      expect(lang.flag).toBeDefined();
      expect(lang.ttsLocale).toBeDefined();
    }
  });

  // GIVEN neuer LangStore
  // WHEN createLangStore aufgerufen
  // THEN default Sprache ist 'de'
  it('[D] GIVEN new store WHEN createLangStore THEN default is de', () => {
    const store = createLangStore();
    expect(store.lang).toBe('de');
  });

  // GIVEN LangStore mit lang='de'
  // WHEN setLanguage('en')
  // THEN lang ist 'en' (immutable, neuer Store)
  it('[D] GIVEN store WHEN setLanguage en THEN returns new store with en', () => {
    const store = createLangStore();
    const next = setLanguage(store, 'en');
    expect(next.lang).toBe('en');
    expect(store.lang).toBe('de'); // original unverändert
  });

  // GIVEN Store
  // WHEN setLanguage mit ungültigem Code
  // THEN wirft Error
  it('[D] GIVEN invalid code WHEN setLanguage THEN throws', () => {
    const store = createLangStore();
    expect(() => setLanguage(store, 'xyz')).toThrow();
  });

  // GIVEN LangStore mit lang='en'
  // WHEN getLanguage aufgerufen
  // THEN gibt 'en' zurück
  it('[D] GIVEN store lang=en WHEN getLanguage THEN returns en', () => {
    const store = setLanguage(createLangStore(), 'en');
    expect(getLanguage(store)).toBe('en');
  });

  // GIVEN lang='de'
  // WHEN getTtsLang aufgerufen
  // THEN gibt 'de-DE' zurück
  it('[D] GIVEN lang=de WHEN getTtsLang THEN returns de-DE', () => {
    expect(getTtsLang('de')).toBe('de-DE');
  });

  // GIVEN lang='en'
  // WHEN getTtsLang aufgerufen
  // THEN gibt 'en-US' zurück
  it('[D] GIVEN lang=en WHEN getTtsLang THEN returns en-US', () => {
    expect(getTtsLang('en')).toBe('en-US');
  });

  // GIVEN lang='fr'
  // WHEN getTtsLang aufgerufen
  // THEN gibt 'fr-FR' zurück
  it('[D] GIVEN lang=fr WHEN getTtsLang THEN returns fr-FR', () => {
    expect(getTtsLang('fr')).toBe('fr-FR');
  });

  // GIVEN lang='de'
  // WHEN getUiStrings aufgerufen
  // THEN gibt deutsche UI-Texte zurück
  it('[D] GIVEN lang=de WHEN getUiStrings THEN returns German strings', () => {
    const s = getUiStrings('de');
    expect(s.settings).toBe('Einstellungen');
    expect(s.language).toBeDefined();
    expect(s.save).toBeDefined();
  });

  // GIVEN lang='en'
  // WHEN getUiStrings aufgerufen
  // THEN gibt englische UI-Texte zurück
  it('[D] GIVEN lang=en WHEN getUiStrings THEN returns English strings', () => {
    const s = getUiStrings('en');
    expect(s.settings).toBe('Settings');
    expect(s.language).toBeDefined();
    expect(s.save).toBeDefined();
  });

  // GIVEN Sprache 'de'
  // WHEN formatLangLabel aufgerufen
  // THEN gibt '🇩🇪 Deutsch' zurück
  it('[D] GIVEN code=de WHEN formatLangLabel THEN returns DE label with flag', () => {
    const label = formatLangLabel('de');
    expect(label).toContain('Deutsch');
    expect(label).toContain('🇩🇪');
  });

  // GIVEN Sprache 'en'
  // WHEN formatLangLabel aufgerufen
  // THEN gibt '🇬🇧 English' zurück
  it('[D] GIVEN code=en WHEN formatLangLabel THEN returns EN label with flag', () => {
    const label = formatLangLabel('en');
    expect(label).toContain('English');
  });
});
