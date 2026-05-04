/**
 * ◑ MiMiNox Field-Tools — Wetter-Cache
 * server/field-tools/weather-cache.js
 *
 * Cacht die letzten bekannten Wetterdaten für Offline-Anzeige.
 * Daten werden beim letzten Online-Moment von Open-Meteo geholt
 * und in diesem Store (+ IndexedDB in der UI) gespeichert.
 *
 * Pure Logik — kein DOM, kein fetch. Testbar mit Vitest.
 */

/** Maximales Alter der Wetterdaten bevor sie als "veraltet" gelten. */
export const WEATHER_MAX_AGE_MS = 6 * 60 * 60 * 1000; // 6 Stunden

/**
 * Erstellt einen leeren Wetter-Cache.
 * @returns {WeatherCache}
 */
export function createWeatherCache() {
  return {
    data:        null,
    lastUpdated: null,
  };
}

/**
 * Speichert neue Wetterdaten im Cache (immutable).
 * @param {WeatherCache} cache
 * @param {WeatherData} data
 * @returns {WeatherCache}
 */
export function storeWeatherData(cache, data) {
  return {
    ...cache,
    data:        { ...data },
    lastUpdated: new Date(),
  };
}

/**
 * Gibt die gecachten Wetterdaten zurück, oder null wenn leer.
 * @param {WeatherCache} cache
 * @returns {WeatherData|null}
 */
export function getCachedWeather(cache) {
  return cache.data ?? null;
}

/**
 * Prüft ob die gecachten Daten veraltet sind.
 * Veraltet = älter als WEATHER_MAX_AGE_MS oder kein Cache vorhanden.
 *
 * @param {WeatherCache} cache
 * @param {Date} now
 * @returns {boolean}
 */
export function isWeatherStale(cache, now) {
  if (!cache.data || !cache.data.fetchedAt) return true;
  const age = now.getTime() - new Date(cache.data.fetchedAt).getTime();
  return age > WEATHER_MAX_AGE_MS;
}

/**
 * Formatiert Wetterdaten als lesbaren Kurztext.
 * Beispiel: "Stand 14:30 — 12°C, Leichter Regen"
 *
 * @param {WeatherData} data
 * @returns {string}
 */
export function formatWeatherSummary(data) {
  const time    = formatTime(new Date(data.fetchedAt));
  const temp    = Math.round(data.temperature);
  const desc    = data.description ?? '—';
  const wind    = data.windSpeed != null ? `, Wind ${Math.round(data.windSpeed)} km/h` : '';
  return `Stand ${time} — ${temp}°C, ${desc}${wind}`;
}

/** Hilfsfunktion: HH:MM */
function formatTime(date) {
  const h = String(date.getUTCHours()).padStart(2, '0');
  const m = String(date.getUTCMinutes()).padStart(2, '0');
  return `${h}:${m}`;
}
