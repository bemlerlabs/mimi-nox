/**
 * ◑ MiMiNox Field-Tools — Test: Wetter-Cache
 * Feature 6: Letzte bekannte Wetterdaten cachen + offline anzeigen
 *
 * TDD: Tests FIRST.
 *
 * Wetterdaten werden beim letzten Online-Moment gespeichert (Open-Meteo API).
 * Offline zeigt MiMiNox "Stand 14:30 — 12°C, Regen erwartet".
 */
import { describe, it, expect } from 'vitest';
import {
  createWeatherCache,
  storeWeatherData,
  getCachedWeather,
  isWeatherStale,
  formatWeatherSummary,
  WEATHER_MAX_AGE_MS,
} from '../../server/field-tools/weather-cache.js';

// Typische Open-Meteo API Antwort (gemockt)
const WEATHER_DATA = {
  temperature:    12.4,
  weatherCode:    61,          // Leichter Regen
  windSpeed:      18.5,        // km/h
  precipitation:  0.8,         // mm
  description:    'Leichter Regen',
  fetchedAt:      new Date('2026-04-21T14:30:00Z'),
};

describe('Feature 6: Wetter-Cache', () => {

  // GIVEN leerer Cache
  // WHEN createWeatherCache aufgerufen
  // THEN gibt leeres Cache-Objekt zurück
  it('[D] GIVEN nothing WHEN createWeatherCache THEN empty cache', () => {
    const cache = createWeatherCache();
    expect(cache.data).toBeNull();
    expect(cache.lastUpdated).toBeNull();
  });

  // GIVEN leerer Cache + Wetterdaten
  // WHEN storeWeatherData aufgerufen
  // THEN Cache enthält die Daten
  it('[D] GIVEN empty cache WHEN storeWeatherData THEN cache has data', () => {
    const cache = createWeatherCache();
    const updated = storeWeatherData(cache, WEATHER_DATA);
    expect(updated.data).not.toBeNull();
    expect(updated.data.temperature).toBeCloseTo(12.4, 1);
    expect(updated.lastUpdated).toBeInstanceOf(Date);
  });

  // GIVEN Cache mit Daten
  // WHEN getCachedWeather aufgerufen
  // THEN gibt gespeicherte Daten zurück
  it('[D] GIVEN cache with data WHEN getCachedWeather THEN returns data', () => {
    const cache = storeWeatherData(createWeatherCache(), WEATHER_DATA);
    const data = getCachedWeather(cache);
    expect(data.temperature).toBeCloseTo(12.4, 1);
    expect(data.description).toBe('Leichter Regen');
  });

  // GIVEN leerer Cache
  // WHEN getCachedWeather aufgerufen
  // THEN gibt null zurück
  it('[D] GIVEN empty cache WHEN getCachedWeather THEN returns null', () => {
    const cache = createWeatherCache();
    expect(getCachedWeather(cache)).toBeNull();
  });

  // GIVEN Cache mit Daten älter als WEATHER_MAX_AGE_MS
  // WHEN isWeatherStale aufgerufen mit aktuellem Timestamp
  // THEN gibt true zurück
  it('[D] GIVEN old cached data WHEN isWeatherStale THEN returns true', () => {
    const oldData = { ...WEATHER_DATA, fetchedAt: new Date(Date.now() - WEATHER_MAX_AGE_MS - 1000) };
    const cache = storeWeatherData(createWeatherCache(), oldData);
    expect(isWeatherStale(cache, new Date())).toBe(true);
  });

  // GIVEN Cache mit frischen Daten (gerade gespeichert)
  // WHEN isWeatherStale aufgerufen
  // THEN gibt false zurück
  it('[D] GIVEN fresh cached data WHEN isWeatherStale THEN returns false', () => {
    const freshData = { ...WEATHER_DATA, fetchedAt: new Date() };
    const cache = storeWeatherData(createWeatherCache(), freshData);
    expect(isWeatherStale(cache, new Date())).toBe(false);
  });

  // GIVEN leerer Cache
  // WHEN isWeatherStale aufgerufen
  // THEN gibt true zurück (kein Daten = veraltet)
  it('[D] GIVEN empty cache WHEN isWeatherStale THEN returns true', () => {
    const cache = createWeatherCache();
    expect(isWeatherStale(cache, new Date())).toBe(true);
  });

  // GIVEN Wetterdaten mit Temperatur + Beschreibung
  // WHEN formatWeatherSummary aufgerufen
  // THEN gibt lesbaren String zurück
  it('[D] GIVEN weather data WHEN formatWeatherSummary THEN readable string', () => {
    const summary = formatWeatherSummary(WEATHER_DATA);
    expect(typeof summary).toBe('string');
    expect(summary).toContain('12');       // Temperatur
    expect(summary).toContain('Regen');    // Beschreibung
  });

  // GIVEN Daten-Timestamp
  // WHEN formatWeatherSummary aufgerufen
  // THEN enthält "Stand HH:MM"
  it('[D] GIVEN fetchedAt WHEN formatWeatherSummary THEN contains Stand HH:MM', () => {
    const summary = formatWeatherSummary(WEATHER_DATA);
    expect(summary).toMatch(/Stand \d{2}:\d{2}/);
  });

  // GIVEN WEATHER_MAX_AGE_MS
  // THEN ist 6 Stunden (sinnvolles Default)
  it('[D] GIVEN WEATHER_MAX_AGE_MS THEN is 6 hours', () => {
    expect(WEATHER_MAX_AGE_MS).toBe(6 * 60 * 60 * 1000);
  });
});
