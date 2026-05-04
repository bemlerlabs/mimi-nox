/**
 * ◑ MiMiNox Field-Tools — Test: GPS-Erweiterungen
 * Feature 3: Höhe, Tempo, Richtung aus Geolocation-API
 *
 * TDD: Tests FIRST.
 *
 * Die Geolocation-API gibt bereits altitude, speed, heading zurück.
 * Diese Funktion formatiert und validiert die Rohdaten.
 */
import { describe, it, expect } from 'vitest';
import {
  parseGpsExtended,
  formatAltitude,
  formatSpeed,
  formatHeading,
  headingToCardinal,
} from '../../server/field-tools/gps-extended.js';

// Typische Browser GeolocationCoordinates (gemockt)
const FULL_POSITION = {
  latitude:         48.137,
  longitude:        11.576,
  altitude:         520.5,        // Meter über WGS84
  altitudeAccuracy: 10,
  speed:            1.389,        // m/s = 5 km/h
  heading:          267.3,        // Grad (West)
  accuracy:         8,
};

const MINIMAL_POSITION = {
  latitude:         48.137,
  longitude:        11.576,
  altitude:         null,
  altitudeAccuracy: null,
  speed:            null,
  heading:          null,
  accuracy:         50,
};

describe('Feature 3: GPS-Erweiterungen', () => {

  // GIVEN vollständige GPS-Koordinaten
  // WHEN parseGpsExtended aufgerufen wird
  // THEN gibt strukturiertes Objekt zurück
  it('[D] GIVEN full position WHEN parseGpsExtended THEN returns structured object', () => {
    const result = parseGpsExtended(FULL_POSITION);
    expect(result).toHaveProperty('altitude');
    expect(result).toHaveProperty('speedKmh');
    expect(result).toHaveProperty('heading');
    expect(result).toHaveProperty('cardinal');
  });

  // GIVEN altitude = 520.5m
  // WHEN parseGpsExtended aufgerufen
  // THEN altitude = 520.5
  it('[D] GIVEN altitude 520.5 WHEN parsed THEN altitude is 520.5', () => {
    const result = parseGpsExtended(FULL_POSITION);
    expect(result.altitude).toBeCloseTo(520.5, 1);
  });

  // GIVEN speed = 1.389 m/s
  // WHEN parseGpsExtended aufgerufen
  // THEN speedKmh ≈ 5.0 km/h
  it('[D] GIVEN speed 1.389 m/s WHEN parsed THEN speedKmh ≈ 5', () => {
    const result = parseGpsExtended(FULL_POSITION);
    expect(result.speedKmh).toBeCloseTo(5.0, 0);
  });

  // GIVEN heading = 267.3°
  // WHEN parseGpsExtended aufgerufen
  // THEN heading = 267.3
  it('[D] GIVEN heading 267.3 WHEN parsed THEN heading is 267.3', () => {
    const result = parseGpsExtended(FULL_POSITION);
    expect(result.heading).toBeCloseTo(267.3, 1);
  });

  // GIVEN altitude = null
  // WHEN parseGpsExtended aufgerufen
  // THEN altitude ist null (nicht verfügbar)
  it('[D] GIVEN null altitude WHEN parsed THEN altitude is null', () => {
    const result = parseGpsExtended(MINIMAL_POSITION);
    expect(result.altitude).toBeNull();
  });

  // GIVEN altitude = 520
  // WHEN formatAltitude aufgerufen
  // THEN gibt "520 m" zurück
  it('[D] GIVEN altitude 520 WHEN formatAltitude THEN returns "520 m"', () => {
    expect(formatAltitude(520)).toBe('520 m');
  });

  // GIVEN altitude = null
  // WHEN formatAltitude aufgerufen
  // THEN gibt "— m" zurück
  it('[D] GIVEN null altitude WHEN formatAltitude THEN returns "— m"', () => {
    expect(formatAltitude(null)).toBe('— m');
  });

  // GIVEN speedKmh = 4.8
  // WHEN formatSpeed aufgerufen
  // THEN gibt "4.8 km/h" zurück
  it('[D] GIVEN speed 4.8 WHEN formatSpeed THEN returns "4.8 km/h"', () => {
    expect(formatSpeed(4.8)).toBe('4.8 km/h');
  });

  // GIVEN speedKmh = null
  // WHEN formatSpeed aufgerufen
  // THEN gibt "— km/h" zurück
  it('[D] GIVEN null speed WHEN formatSpeed THEN returns "— km/h"', () => {
    expect(formatSpeed(null)).toBe('— km/h');
  });

  // GIVEN heading = 267
  // WHEN headingToCardinal aufgerufen
  // THEN gibt 'W' zurück
  it('[D] GIVEN heading 267 WHEN headingToCardinal THEN returns W', () => {
    expect(headingToCardinal(267)).toBe('W');
  });

  // GIVEN heading = 0
  // WHEN headingToCardinal aufgerufen
  // THEN gibt 'N' zurück
  it('[D] GIVEN heading 0 WHEN headingToCardinal THEN returns N', () => {
    expect(headingToCardinal(0)).toBe('N');
    expect(headingToCardinal(360)).toBe('N');
  });

  // GIVEN heading = 90
  // WHEN headingToCardinal aufgerufen
  // THEN gibt 'O' zurück (Ost, deutsch)
  it('[D] GIVEN heading 90 WHEN headingToCardinal THEN returns O (Ost)', () => {
    expect(headingToCardinal(90)).toBe('O');
  });

  // GIVEN heading = 180
  // WHEN headingToCardinal aufgerufen
  // THEN gibt 'S' zurück
  it('[D] GIVEN heading 180 WHEN headingToCardinal THEN returns S', () => {
    expect(headingToCardinal(180)).toBe('S');
  });
});
