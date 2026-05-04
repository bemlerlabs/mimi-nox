/**
 * ◑ MiMiNox Field-Tools — GPS Track Recorder + GPX Export
 * server/field-tools/track-recorder.js
 *
 * Immutable State Machine für GPS-Track-Aufzeichnung.
 * GPX-Export: GPS Exchange Format v1.1 (XML).
 * Kompatibel mit: Komoot, AllTrails, Google Earth, Garmin Connect.
 *
 * Kein DOM, kein Browser-API — reine Logik, testbar mit Vitest.
 */

export const RECORDER_IDLE      = 'idle';
export const RECORDER_RECORDING = 'recording';
export const RECORDER_PAUSED    = 'paused';

/**
 * Erstellt einen neuen, leeren Track-Recorder.
 *
 * @param {{ name?: string }} [opts]
 * @returns {TrackRecorder}
 */
export function createTrackRecorder(opts = {}) {
  return {
    status:    RECORDER_IDLE,
    name:      opts.name ?? 'MiMiNox-Tour',
    points:    [],
    startedAt: null,
  };
}

/**
 * Fügt einen Trackpunkt hinzu (immutable).
 * Setzt Status auf RECORDING beim ersten Punkt.
 *
 * @param {TrackRecorder} recorder
 * @param {{ lat: number, lng: number, alt: number|null, timestamp: Date }} point
 * @returns {TrackRecorder}
 */
export function addTrackPoint(recorder, point) {
  return {
    ...recorder,
    status:    RECORDER_RECORDING,
    startedAt: recorder.startedAt ?? point.timestamp,
    points:    [...recorder.points, {
      lat:       point.lat,
      lng:       point.lng,
      alt:       point.alt ?? null,
      timestamp: point.timestamp,
    }],
  };
}

/**
 * Setzt den Recorder zurück (immutable).
 * @param {TrackRecorder} recorder
 * @returns {TrackRecorder}
 */
export function clearTrack(recorder) {
  return {
    ...recorder,
    status:    RECORDER_IDLE,
    points:    [],
    startedAt: null,
  };
}

/**
 * Exportiert den Track als GPX v1.1 XML-String.
 *
 * @param {TrackRecorder} recorder
 * @returns {string} GPX-XML
 * @throws {Error} wenn keine Punkte vorhanden
 */
export function exportGpx(recorder) {
  if (recorder.points.length === 0) {
    throw new Error('GPX-Export: Keine Track-Punkte vorhanden');
  }

  const now  = new Date().toISOString();
  const name = escapeXml(recorder.name);

  const trkpts = recorder.points.map(p => {
    const ele  = p.alt != null ? `\n      <ele>${p.alt}</ele>` : '';
    const time = p.timestamp
      ? `\n      <time>${p.timestamp.toISOString()}</time>`
      : '';
    return `    <trkpt lat="${p.lat}" lon="${p.lng}">${ele}${time}\n    </trkpt>`;
  }).join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1"
  creator="MiMiNox v2"
  xmlns="http://www.topografix.com/GPX/1/1"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata>
    <name>${name}</name>
    <time>${now}</time>
  </metadata>
  <trk>
    <name>${name}</name>
    <trkseg>
${trkpts}
    </trkseg>
  </trk>
</gpx>`;
}

/** Escaped XML-Sonderzeichen. */
function escapeXml(str) {
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&apos;');
}
