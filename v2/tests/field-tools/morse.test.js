/**
 * ◑ MiMiNox Field-Tools — Test: SOS Morse
 * TDD: Tests FIRST.
 *
 * SOS Morse-Code: ... --- ...
 * Timing: dit=100ms, dah=300ms, Pause=100ms, Leerzeichen=700ms
 */
import { describe, it, expect } from 'vitest';
import {
  encodeMorse,
  buildMorseTimeline,
  MORSE_MAP,
  MORSE_DIT_MS,
  MORSE_DAH_MS,
} from '../../server/field-tools/morse.js';

describe('Feature 9: SOS Morse — Encoder + Timeline', () => {

  // GIVEN 'SOS'
  // WHEN encodeMorse aufgerufen wird
  // THEN gibt '... --- ...' zurück
  it('[D] GIVEN SOS WHEN encodeMorse THEN returns ... --- ...', () => {
    expect(encodeMorse('SOS')).toBe('... --- ...');
  });

  // GIVEN Buchstabe 'S'
  // WHEN in MORSE_MAP nachgeschaut
  // THEN gibt '...' zurück
  it('[D] GIVEN S in MORSE_MAP THEN returns ...', () => {
    expect(MORSE_MAP['S']).toBe('...');
  });

  // GIVEN Buchstabe 'O'
  // WHEN in MORSE_MAP nachgeschaut
  // THEN gibt '---' zurück
  it('[D] GIVEN O in MORSE_MAP THEN returns ---', () => {
    expect(MORSE_MAP['O']).toBe('---');
  });

  // GIVEN 'SOS'
  // WHEN buildMorseTimeline aufgerufen wird
  // THEN gibt Array von { type, durationMs } zurück
  it('[D] GIVEN SOS WHEN buildMorseTimeline THEN returns timeline array', () => {
    const timeline = buildMorseTimeline('SOS');
    expect(Array.isArray(timeline)).toBe(true);
    expect(timeline.length).toBeGreaterThan(0);
    // Jedes Element hat type (ON/OFF) und durationMs
    timeline.forEach(entry => {
      expect(entry).toHaveProperty('type');
      expect(entry).toHaveProperty('durationMs');
      expect(['ON', 'OFF']).toContain(entry.type);
      expect(typeof entry.durationMs).toBe('number');
      expect(entry.durationMs).toBeGreaterThan(0);
    });
  });

  // GIVEN SOS Timeline
  // WHEN ON-Einträge mit dit-Länge gezählt werden
  // THEN gibt 6 dits (S=3, S=3)
  it('[D] GIVEN SOS WHEN counting dits in timeline THEN 6 dit-ON entries', () => {
    const timeline = buildMorseTimeline('SOS');
    const dits = timeline.filter(e => e.type === 'ON' && e.durationMs === MORSE_DIT_MS);
    expect(dits.length).toBe(6); // S=... (3), S=... (3)
  });

  // GIVEN SOS Timeline
  // WHEN DAH-Einträge gezählt
  // THEN gibt 3 dahs (O=---)
  it('[D] GIVEN SOS WHEN counting dahs in timeline THEN 3 dah-ON entries', () => {
    const timeline = buildMorseTimeline('SOS');
    const dahs = timeline.filter(e => e.type === 'ON' && e.durationMs === MORSE_DAH_MS);
    expect(dahs.length).toBe(3); // O=--- (3)
  });

  // GIVEN kleinbuchstaben 'sos'
  // WHEN encodeMorse aufgerufen
  // THEN wird wie 'SOS' behandelt (case-insensitive)
  it('[D] GIVEN lowercase sos WHEN encodeMorse THEN same as SOS', () => {
    expect(encodeMorse('sos')).toBe(encodeMorse('SOS'));
  });

  // GIVEN ungültige Zeichen '@#!'
  // WHEN encodeMorse aufgerufen
  // THEN werden diese ignoriert / übersprungen
  it('[D] GIVEN invalid chars WHEN encodeMorse THEN ignored', () => {
    // 'S@S' → 'S' + ignored + 'S'
    const result = encodeMorse('S@S');
    expect(result).not.toContain('@');
    expect(result).toContain('...');
  });
});
