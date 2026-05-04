/**
 * ◑ MiMiNox Field-Tools — Test: Sonnenuntergang-Rechner
 * TDD: Tests FIRST.
 *
 * Nutzt SunCalc.js — reiner Algorithmus, kein Internet nötig.
 * GPS-Koordinaten + Datum → Sonnenaufgang, Untergang, Countdown.
 */
import { describe, it, expect } from 'vitest';
import {
  getSunTimes,
  getMinutesUntilSunset,
  getSunPosition,
  formatSunTime,
} from '../../server/field-tools/sun.js';

// Testdaten: München, 21. April 2026 (exakter Tag)
const MUNICH = { lat: 48.137, lng: 11.576 };
const DATE_APRIL_21 = new Date('2026-04-21T12:00:00Z');

describe('Feature 10: Sonnenuntergang-Rechner', () => {

  // GIVEN München-Koordinaten + 21. April 2026
  // WHEN getSunTimes aufgerufen wird
  // THEN gibt sunrise und sunset als Date zurück
  it('[D] GIVEN Munich coords WHEN getSunTimes THEN returns sunrise & sunset', () => {
    const times = getSunTimes(DATE_APRIL_21, MUNICH.lat, MUNICH.lng);
    expect(times.sunrise).toBeInstanceOf(Date);
    expect(times.sunset).toBeInstanceOf(Date);
    expect(times.sunset.getTime()).toBeGreaterThan(times.sunrise.getTime());
  });

  // GIVEN München im April
  // WHEN Sonnenuntergang-Stunde geprüft
  // THEN ist es zwischen 18:00 und 22:00 UTC
  it('[D] GIVEN Munich April WHEN sunset THEN between 18-22 UTC', () => {
    const times = getSunTimes(DATE_APRIL_21, MUNICH.lat, MUNICH.lng);
    const hour = times.sunset.getUTCHours();
    expect(hour).toBeGreaterThanOrEqual(18);
    expect(hour).toBeLessThanOrEqual(22);
  });

  // GIVEN es ist 2 Stunden vor Sonnenuntergang
  // WHEN getMinutesUntilSunset aufgerufen wird
  // THEN gibt ca. 120 Minuten zurück (±10min Toleranz)
  it('[D] GIVEN 2h before sunset WHEN getMinutesUntilSunset THEN ~120', () => {
    const times = getSunTimes(DATE_APRIL_21, MUNICH.lat, MUNICH.lng);
    // Erstelle "now" = 2h vor Sonnenuntergang
    const twoHoursBefore = new Date(times.sunset.getTime() - 2 * 60 * 60 * 1000);
    const minutes = getMinutesUntilSunset(twoHoursBefore, MUNICH.lat, MUNICH.lng);
    expect(minutes).toBeGreaterThan(110);
    expect(minutes).toBeLessThan(130);
  });

  // GIVEN es ist NACH Sonnenuntergang
  // WHEN getMinutesUntilSunset aufgerufen wird
  // THEN gibt negativen Wert zurück (schon dunkel)
  it('[D] GIVEN after sunset WHEN getMinutesUntilSunset THEN negative', () => {
    const times = getSunTimes(DATE_APRIL_21, MUNICH.lat, MUNICH.lng);
    const afterSunset = new Date(times.sunset.getTime() + 30 * 60 * 1000);
    const minutes = getMinutesUntilSunset(afterSunset, MUNICH.lat, MUNICH.lng);
    expect(minutes).toBeLessThan(0);
  });

  // GIVEN München-Koordinaten + Mittag
  // WHEN getSunPosition aufgerufen wird
  // THEN ist altitude > 0 (Sonne über Horizont)
  it('[D] GIVEN Munich noon WHEN getSunPosition THEN altitude > 0', () => {
    const pos = getSunPosition(DATE_APRIL_21, MUNICH.lat, MUNICH.lng);
    expect(pos.altitude).toBeGreaterThan(0);
    expect(typeof pos.azimuth).toBe('number');
  });

  // GIVEN ein Date-Objekt
  // WHEN formatSunTime aufgerufen wird
  // THEN gibt HH:MM-String zurück (z.B. "20:45")
  it('[D] GIVEN Date WHEN formatSunTime THEN returns HH:MM string', () => {
    const d = new Date('2026-04-21T18:45:00Z');
    const formatted = formatSunTime(d);
    expect(formatted).toMatch(/^\d{2}:\d{2}$/);
  });

  // GIVEN ungültige Koordinaten (lat > 90)
  // WHEN getSunTimes aufgerufen wird
  // THEN wirft RangeError
  it('[D] GIVEN invalid coords WHEN getSunTimes THEN throws RangeError', () => {
    expect(() => getSunTimes(DATE_APRIL_21, 200, 11.576)).toThrow(RangeError);
    expect(() => getSunTimes(DATE_APRIL_21, 48.137, 200)).toThrow(RangeError);
  });
});
