/**
 * ◑ MiMiNox Field-Tools — Foto-Store + GPS-Stempel
 * server/field-tools/photo-store.js
 *
 * Immutable State Machine für Foto-Verwaltung.
 * Fotos werden als Blob-URLs + Metadaten gespeichert.
 * GPS-Koordinaten werden als Stempel-Text generiert (Canvas in der UI).
 *
 * FIFO-Eviction bei MAX_STORE Fotos (Speicherschutz).
 * Kein DOM, kein Browser-API — testbar mit Vitest.
 */

export const PHOTO_MAX_STORE = 50;

/**
 * Erstellt einen leeren Foto-Store.
 * @returns {PhotoStore}
 */
export function createPhotoStore() {
  return { photos: [] };
}

/**
 * Fügt ein Foto hinzu. Bei Überschreitung von PHOTO_MAX_STORE
 * wird das älteste Foto entfernt (FIFO).
 *
 * @param {PhotoStore} store
 * @param {Photo} photo
 * @returns {PhotoStore}
 */
export function addPhoto(store, photo) {
  let photos = [...store.photos, { ...photo }];
  if (photos.length > PHOTO_MAX_STORE) {
    // Ältestes entfernen (kleinster createdAt)
    photos.sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
    photos = photos.slice(1);
  }
  return { ...store, photos };
}

/**
 * Löscht ein Foto nach ID (immutable).
 * @param {PhotoStore} store
 * @param {string} id
 * @returns {PhotoStore}
 */
export function deletePhoto(store, id) {
  return { ...store, photos: store.photos.filter(p => p.id !== id) };
}

/**
 * Gibt alle Fotos sortiert nach createdAt (neueste zuerst) zurück.
 * @param {PhotoStore} store
 * @returns {Photo[]}
 */
export function getAllPhotos(store) {
  return [...store.photos].sort(
    (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
  );
}

/**
 * Baut den GPS-Stempel-Text für Canvas-Overlay.
 * Beispiel: "48.1370°N 11.5760°E  520m  15:30 UTC"
 *
 * @param {{ lat: number, lng: number, alt?: number|null }} coords
 * @param {Date} timestamp
 * @returns {string}
 */
export function buildGpsStampText(coords, timestamp) {
  const lat  = Math.abs(coords.lat).toFixed(4) + (coords.lat >= 0 ? '°N' : '°S');
  const lng  = Math.abs(coords.lng).toFixed(4) + (coords.lng >= 0 ? '°E' : '°W');
  const alt  = coords.alt != null ? `  ${Math.round(coords.alt)}m` : '';
  const hh   = String(timestamp.getUTCHours()).padStart(2, '0');
  const mm   = String(timestamp.getUTCMinutes()).padStart(2, '0');
  const time = `  ${hh}:${mm} UTC`;
  return `${lat} ${lng}${alt}${time}`;
}

/**
 * Baut einen Dateinamen für den Foto-Export.
 * Format: miminox-foto-YYYY-MM-DD-HH-MM.jpg
 *
 * @param {Date} timestamp
 * @returns {string}
 */
export function buildExportFilename(timestamp) {
  const pad  = n => String(n).padStart(2, '0');
  const yyyy = timestamp.getUTCFullYear();
  const mo   = pad(timestamp.getUTCMonth() + 1);
  const dd   = pad(timestamp.getUTCDate());
  const hh   = pad(timestamp.getUTCHours());
  const mm   = pad(timestamp.getUTCMinutes());
  return `miminox-foto-${yyyy}-${mo}-${dd}-${hh}-${mm}.jpg`;
}
