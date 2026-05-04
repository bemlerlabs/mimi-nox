/**
 * ◑ MiMiNox Field-Tools — Test: TTS (Text-to-Speech)
 * TDD: Tests FIRST.
 *
 * Web Speech Synthesis — läuft offline mit OS-Stimmen.
 */
import { describe, it, expect } from 'vitest';
import {
  createTtsState,
  buildUtterance,
  TTS_IDLE,
  TTS_SPEAKING,
  TTS_STOPPED,
} from '../../server/field-tools/tts.js';

describe('Feature 8: TTS Vorlesen — State + Utterance', () => {

  // GIVEN ein neuer TTS-State
  // WHEN createTtsState aufgerufen wird
  // THEN ist Status IDLE und kein Text gesetzt
  it('[D] GIVEN new state WHEN created THEN status is IDLE', () => {
    const state = createTtsState();
    expect(state.status).toBe(TTS_IDLE);
    expect(state.text).toBe('');
  });

  // GIVEN Text "Hilfe rufen"
  // WHEN buildUtterance aufgerufen wird
  // THEN gibt Objekt mit text, lang, rate zurück
  it('[D] GIVEN text WHEN buildUtterance THEN returns utterance config', () => {
    const u = buildUtterance('Hilfe rufen', { lang: 'de-DE', rate: 0.9 });
    expect(u.text).toBe('Hilfe rufen');
    expect(u.lang).toBe('de-DE');
    expect(u.rate).toBe(0.9);
  });

  // GIVEN leerer Text
  // WHEN buildUtterance aufgerufen wird
  // THEN wirft Error
  it('[D] GIVEN empty text WHEN buildUtterance THEN throws', () => {
    expect(() => buildUtterance('')).toThrow();
    expect(() => buildUtterance('  ')).toThrow();
  });

  // GIVEN Text ohne lang-Option
  // WHEN buildUtterance aufgerufen wird
  // THEN default lang ist 'de-DE'
  it('[D] GIVEN text without lang WHEN buildUtterance THEN defaults to de-DE', () => {
    const u = buildUtterance('Test');
    expect(u.lang).toBe('de-DE');
  });

  // GIVEN rate < 0.1 oder > 2
  // WHEN buildUtterance aufgerufen wird
  // THEN wird auf gültigen Bereich geclippt
  it('[D] GIVEN rate out of range WHEN buildUtterance THEN clips to [0.1, 2]', () => {
    const fast = buildUtterance('Test', { rate: 10 });
    expect(fast.rate).toBe(2);
    const slow = buildUtterance('Test', { rate: 0 });
    expect(slow.rate).toBe(0.1);
  });

  // GIVEN TTS_SPEAKING Status
  // WHEN Status geprüft wird
  // THEN isSpeaking ist true
  it('[D] GIVEN speaking status THEN isSpeaking is true', () => {
    expect(TTS_SPEAKING).toBe('speaking');
    expect(TTS_IDLE).toBe('idle');
    expect(TTS_STOPPED).toBe('stopped');
  });

  // GIVEN Text mit mehr als 500 Zeichen
  // WHEN buildUtterance aufgerufen wird
  // THEN wird Text auf 500 Zeichen begrenzt (Browser-Limit)
  it('[D] GIVEN very long text WHEN buildUtterance THEN truncates at 500 chars', () => {
    const longText = 'a'.repeat(600);
    const u = buildUtterance(longText);
    expect(u.text.length).toBeLessThanOrEqual(500);
  });
});
