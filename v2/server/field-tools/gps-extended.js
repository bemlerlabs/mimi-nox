/**
 * ◑ MiMiNox Field-Tools — GPS-Erweiterungen
 * server/field-tools/gps-extended.js
 *
 * Parst und formatiert die erweiterten Felder der Geolocation-API:
 * altitude, speed (m/s → km/h), heading (° → Himmelsrichtung).
 *
 * Alle Felder können null sein (Hardware-abhängig).
 */

// Himmelsrichtungen auf Deutsch (N/O/S/W + Zwischenrichtungen)
const CARDINALS = ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW'];

/**
 * Wandelt Grad (0-360) in deutsche Himmelsrichtung um.
 * N=0°, O=90°, S=180°, W=270°
 *
 * @param {number|null} deg
 * @returns {string}
 */
export function headingToCardinal(deg) {
  if (deg == null) return '—';
  const idx = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
  return CARDINALS[idx];
}

/**
 * Formatiert Altitude für die Anzeige.
 * @param {number|null} alt - Meter
 * @returns {string}
 */
export function formatAltitude(alt) {
  if (alt == null) return '— m';
  return `${Math.round(alt)} m`;
}

/**
 * Formatiert Geschwindigkeit für die Anzeige.
 * @param {number|null} kmh
 * @returns {string}
 */
export function formatSpeed(kmh) {
  if (kmh == null) return '— km/h';
  return `${kmh.toFixed(1)} km/h`;
}

/**
 * Formatiert Heading für die Anzeige.
 * @param {number|null} deg
 * @returns {string}
 */
export function formatHeading(deg) {
  if (deg == null) return '—°';
  return `${Math.round(deg)}°`;
}

/**
 * Parst ein GeolocationCoordinates-Objekt und gibt strukturierte Daten zurück.
 * Konvertiert speed von m/s auf km/h.
 *
 * @param {GeolocationCoordinates} coords
 * @returns {{
 *   latitude: number,
 *   longitude: number,
 *   altitude: number|null,
 *   altitudeAccuracy: number|null,
 *   speedKmh: number|null,
 *   heading: number|null,
 *   cardinal: string,
 *   accuracy: number,
 * }}
 */
export function parseGpsExtended(coords) {
  const speedKmh = coords.speed != null
    ? Math.round(coords.speed * 3.6 * 10) / 10   // m/s → km/h, 1 Dezimalstelle
    : null;

  return {
    latitude:         coords.latitude,
    longitude:        coords.longitude,
    altitude:         coords.altitude    ?? null,
    altitudeAccuracy: coords.altitudeAccuracy ?? null,
    speedKmh,
    heading:          coords.heading     ?? null,
    cardinal:         headingToCardinal(coords.heading),
    accuracy:         coords.accuracy,
  };
}
