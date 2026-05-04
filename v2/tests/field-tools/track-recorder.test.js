/**
 * ◑ MiMiNox Field-Tools — Test: GPS Track Recorder + GPX Export
 * Feature 1: Route aufzeichnen und als .gpx exportieren
 *
 * TDD: Tests FIRST.
 *
 * GPX = GPS Exchange Format (XML), öffenbar in AllTrails, Komoot, Google Earth.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  createTrackRecorder,
  addTrackPoint,
  clearTrack,
  exportGpx,
  RECORDER_IDLE,
  RECORDER_RECORDING,
  RECORDER_PAUSED,
} from '../../server/field-tools/track-recorder.js';

// Testdaten
const POINT_A = { lat: 48.137, lng: 11.576, alt: 520, timestamp: new Date('2026-04-21T10:00:00Z') };
const POINT_B = { lat: 48.138, lng: 11.578, alt: 525, timestamp: new Date('2026-04-21T10:05:00Z') };
const POINT_C = { lat: 48.139, lng: 11.580, alt: 530, timestamp: new Date('2026-04-21T10:10:00Z') };

describe('Feature 1: GPS Track Recorder', () => {

  let recorder;
  beforeEach(() => {
    recorder = createTrackRecorder({ name: 'TestTour' });
  });

  // GIVEN neuer Recorder
  // WHEN createTrackRecorder aufgerufen
  // THEN Status = IDLE, keine Punkte
  it('[D] GIVEN new recorder WHEN created THEN status IDLE and empty', () => {
    expect(recorder.status).toBe(RECORDER_IDLE);
    expect(recorder.points).toHaveLength(0);
    expect(recorder.name).toBe('TestTour');
  });

  // GIVEN Recorder im IDLE-Status
  // WHEN addTrackPoint aufgerufen
  // THEN Punkt wird hinzugefügt, Status → RECORDING
  it('[D] GIVEN IDLE recorder WHEN addTrackPoint THEN point added, status RECORDING', () => {
    const next = addTrackPoint(recorder, POINT_A);
    expect(next.points).toHaveLength(1);
    expect(next.status).toBe(RECORDER_RECORDING);
    expect(next.points[0].lat).toBe(48.137);
  });

  // GIVEN Recorder mit 1 Punkt
  // WHEN addTrackPoint nochmal aufgerufen
  // THEN 2 Punkte im Track
  it('[D] GIVEN recorder with 1 point WHEN addTrackPoint again THEN 2 points', () => {
    const r1 = addTrackPoint(recorder, POINT_A);
    const r2 = addTrackPoint(r1, POINT_B);
    expect(r2.points).toHaveLength(2);
  });

  // GIVEN Recorder mit 3 Punkten
  // WHEN clearTrack aufgerufen
  // THEN Punkte leer, Status → IDLE
  it('[D] GIVEN recorder with 3 points WHEN clearTrack THEN empty and IDLE', () => {
    const r = [POINT_A, POINT_B, POINT_C].reduce(addTrackPoint, recorder);
    const cleared = clearTrack(r);
    expect(cleared.points).toHaveLength(0);
    expect(cleared.status).toBe(RECORDER_IDLE);
  });

  // GIVEN Recorder mit 0 Punkten
  // WHEN exportGpx aufgerufen
  // THEN wirft Error (kein leerer Export)
  it('[D] GIVEN empty recorder WHEN exportGpx THEN throws', () => {
    expect(() => exportGpx(recorder)).toThrow();
  });

  // GIVEN Recorder mit 2 Punkten
  // WHEN exportGpx aufgerufen
  // THEN gibt validen GPX-XML-String zurück
  it('[D] GIVEN 2 points WHEN exportGpx THEN returns valid GPX XML', () => {
    const r = addTrackPoint(addTrackPoint(recorder, POINT_A), POINT_B);
    const gpx = exportGpx(r);
    expect(typeof gpx).toBe('string');
    expect(gpx).toContain('<?xml');
    expect(gpx).toContain('<gpx');
    expect(gpx).toContain('</gpx>');
    expect(gpx).toContain('<trkpt');
  });

  // GIVEN Recorder mit 2 Punkten
  // WHEN exportGpx aufgerufen
  // THEN GPX enthält korrekte Koordinaten
  it('[D] GIVEN points WHEN exportGpx THEN GPX contains correct coords', () => {
    const r = addTrackPoint(addTrackPoint(recorder, POINT_A), POINT_B);
    const gpx = exportGpx(r);
    expect(gpx).toContain('lat="48.137"');
    expect(gpx).toContain('lon="11.576"');
    expect(gpx).toContain('lat="48.138"');
  });

  // GIVEN Recorder mit Punkten inkl. Altitude
  // WHEN exportGpx aufgerufen
  // THEN GPX enthält <ele>-Tags
  it('[D] GIVEN points with altitude WHEN exportGpx THEN GPX has <ele> tags', () => {
    const r = addTrackPoint(recorder, POINT_A);
    const gpx = exportGpx(r);
    expect(gpx).toContain('<ele>');
    expect(gpx).toContain('520');
  });

  // GIVEN Recorder mit Zeitstempel
  // WHEN exportGpx aufgerufen
  // THEN GPX enthält <time>-Tags
  it('[D] GIVEN points with timestamp WHEN exportGpx THEN GPX has <time> tags', () => {
    const r = addTrackPoint(recorder, POINT_A);
    const gpx = exportGpx(r);
    expect(gpx).toContain('<time>');
    expect(gpx).toContain('2026-04-21');
  });

  // GIVEN Track-Name "TestTour"
  // WHEN exportGpx aufgerufen
  // THEN GPX enthält <name>TestTour</name>
  it('[D] GIVEN track name WHEN exportGpx THEN GPX contains name', () => {
    const r = addTrackPoint(recorder, POINT_A);
    const gpx = exportGpx(r);
    expect(gpx).toContain('<name>TestTour</name>');
  });

  // GIVEN Punkt ohne Altitude
  // WHEN addTrackPoint aufgerufen
  // THEN Punkt wird trotzdem gespeichert (alt = null)
  it('[D] GIVEN point without altitude WHEN added THEN stored with null alt', () => {
    const pointNoAlt = { lat: 48.137, lng: 11.576, alt: null, timestamp: new Date() };
    const r = addTrackPoint(recorder, pointNoAlt);
    expect(r.points[0].alt).toBeNull();
  });
});
