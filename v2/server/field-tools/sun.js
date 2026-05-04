/**
 * ◑ MiMiNox Field-Tools — Sonnenuntergang-Rechner
 * server/field-tools/sun.js
 *
 * Nutzt SunCalc.js (3KB, 100% offline, kein Internet).
 * Berechnet: Sonnenaufgang, Untergang, Countdown, Sonnenposition.
 */
import SunCalc from 'suncalc';

const LAT_RANGE = [-90,  90];
const LNG_RANGE = [-180, 180];

/**
 * Validiert Koordinaten.
 * @throws {RangeError}
 */
function validateCoords(lat, lng) {
  if (lat < LAT_RANGE[0] || lat > LAT_RANGE[1]) {
    throw new RangeError(`Latitude muss zwischen ${LAT_RANGE[0]} und ${LAT_RANGE[1]} liegen, war: ${lat}`);
  }
  if (lng < LNG_RANGE[0] || lng > LNG_RANGE[1]) {
    throw new RangeError(`Longitude muss zwischen ${LNG_RANGE[0]} und ${LNG_RANGE[1]} liegen, war: ${lng}`);
  }
}

/**
 * Gibt Sonnenaufgang und -untergang für den angegebenen Tag und Ort zurück.
 *
 * @param {Date}   date
 * @param {number} lat
 * @param {number} lng
 * @returns {{ sunrise: Date, sunset: Date, solarNoon: Date }}
 */
export function getSunTimes(date, lat, lng) {
  validateCoords(lat, lng);
  const times = SunCalc.getTimes(date, lat, lng);
  return {
    sunrise:   times.sunrise,
    sunset:    times.sunset,
    solarNoon: times.solarNoon,
    dawn:      times.dawn,
    dusk:      times.dusk,
  };
}

/**
 * Gibt die Anzahl Minuten bis zum Sonnenuntergang zurück.
 * Negativ wenn es bereits nach Sonnenuntergang ist.
 *
 * @param {Date}   now
 * @param {number} lat
 * @param {number} lng
 * @returns {number} Minuten (kann negativ sein)
 */
export function getMinutesUntilSunset(now, lat, lng) {
  const { sunset } = getSunTimes(now, lat, lng);
  return Math.round((sunset.getTime() - now.getTime()) / 60_000);
}

/**
 * Gibt die aktuelle Sonnenposition zurück.
 *
 * @param {Date}   date
 * @param {number} lat
 * @param {number} lng
 * @returns {{ altitude: number, azimuth: number }}
 *   altitude: Winkel über Horizont in Radiant (positiv = über Horizont)
 *   azimuth:  Richtung in Radiant (-π ... π, 0=Süd, -π/2=Ost, π/2=West)
 */
export function getSunPosition(date, lat, lng) {
  validateCoords(lat, lng);
  const pos = SunCalc.getPosition(date, lat, lng);
  return {
    altitude: pos.altitude,
    azimuth:  pos.azimuth,
  };
}

/**
 * Formatiert ein Date-Objekt als "HH:MM" (Lokalzeit).
 *
 * @param {Date} date
 * @returns {string} z.B. "20:45"
 */
export function formatSunTime(date) {
  const h = String(date.getHours()).padStart(2, '0');
  const m = String(date.getMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}
