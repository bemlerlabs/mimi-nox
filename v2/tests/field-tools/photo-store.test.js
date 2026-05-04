/**
 * ◑ MiMiNox Field-Tools — Test: Foto + GPS-Stempel
 * Feature 5: Foto aufnehmen, GPS-Koordinaten einbrennen, speichern
 *
 * TDD: Tests FIRST.
 *
 * getUserMedia + Canvas → JPEG Blob mit GPS-Stempel.
 * Hier testen wir: Metadaten-Store + Stempel-Text-Generator (keine Browser-APIs).
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  createPhotoStore,
  addPhoto,
  deletePhoto,
  getAllPhotos,
  buildGpsStampText,
  buildExportFilename,
  PHOTO_MAX_STORE,
} from '../../server/field-tools/photo-store.js';

const NOW    = new Date('2026-04-21T15:30:00Z');
const COORDS = { lat: 48.137, lng: 11.576, alt: 520, accuracy: 8 };

const PHOTO_A = {
  id:        'photo-001',
  title:     'Wegmarkierung Ost',
  blobUrl:   'blob:http://localhost/abc',
  coords:    COORDS,
  createdAt: NOW,
  sizeBytes: 245000,
};

describe('Feature 5: Foto + GPS-Stempel', () => {

  let store;
  beforeEach(() => {
    store = createPhotoStore();
  });

  // GIVEN neuer Store
  // WHEN createPhotoStore aufgerufen
  // THEN leer
  it('[D] GIVEN new store WHEN created THEN empty', () => {
    expect(store.photos).toHaveLength(0);
  });

  // GIVEN leerer Store + Foto
  // WHEN addPhoto aufgerufen
  // THEN Store hat 1 Foto
  it('[D] GIVEN empty store WHEN addPhoto THEN 1 photo', () => {
    const next = addPhoto(store, PHOTO_A);
    expect(next.photos).toHaveLength(1);
    expect(next.photos[0].title).toBe('Wegmarkierung Ost');
  });

  // GIVEN Store mit 2 Fotos
  // WHEN deletePhoto aufgerufen
  // THEN 1 Foto übrig
  it('[D] GIVEN 2 photos WHEN deletePhoto THEN 1 remains', () => {
    const PHOTO_B = { ...PHOTO_A, id: 'photo-002', title: 'Gipfel' };
    const s = addPhoto(addPhoto(store, PHOTO_A), PHOTO_B);
    const after = deletePhoto(s, 'photo-001');
    expect(after.photos).toHaveLength(1);
    expect(after.photos[0].id).toBe('photo-002');
  });

  // GIVEN Store mit Fotos
  // WHEN getAllPhotos aufgerufen
  // THEN sortiert nach createdAt (neueste zuerst)
  it('[D] GIVEN photos WHEN getAllPhotos THEN sorted newest first', () => {
    const OLD = { ...PHOTO_A, id: 'old', createdAt: new Date('2026-04-21T10:00:00Z') };
    const NEW = { ...PHOTO_A, id: 'new', createdAt: new Date('2026-04-21T14:00:00Z') };
    const s = addPhoto(addPhoto(store, OLD), NEW);
    const all = getAllPhotos(s);
    expect(all[0].id).toBe('new');
  });

  // GIVEN Store voll (MAX_STORE Fotos)
  // WHEN addPhoto aufgerufen
  // THEN ältestes Foto wird entfernt (FIFO)
  it('[D] GIVEN full store WHEN addPhoto THEN oldest removed (FIFO)', () => {
    let s = store;
    for (let i = 0; i < PHOTO_MAX_STORE; i++) {
      s = addPhoto(s, { ...PHOTO_A, id: `photo-${i}`, createdAt: new Date(NOW.getTime() + i * 1000) });
    }
    expect(s.photos).toHaveLength(PHOTO_MAX_STORE);
    // Jetzt ein weiteres hinzufügen
    const extra = { ...PHOTO_A, id: 'extra', createdAt: new Date(NOW.getTime() + PHOTO_MAX_STORE * 1000) };
    const after = addPhoto(s, extra);
    expect(after.photos).toHaveLength(PHOTO_MAX_STORE);
    expect(after.photos.find(p => p.id === 'photo-0')).toBeUndefined(); // ältestes entfernt
    expect(after.photos.find(p => p.id === 'extra')).toBeDefined();
  });

  // GIVEN GPS-Koordinaten + Zeitstempel
  // WHEN buildGpsStampText aufgerufen
  // THEN gibt String mit Lat/Lng + Zeit zurück
  it('[D] GIVEN coords + time WHEN buildGpsStampText THEN returns stamp string', () => {
    const stamp = buildGpsStampText(COORDS, NOW);
    expect(typeof stamp).toBe('string');
    expect(stamp).toContain('48.137');
    expect(stamp).toContain('11.576');
  });

  // GIVEN GPS-Koordinaten mit Altitude
  // WHEN buildGpsStampText aufgerufen
  // THEN enthält Höhenangabe
  it('[D] GIVEN coords with altitude WHEN buildGpsStampText THEN contains altitude', () => {
    const stamp = buildGpsStampText(COORDS, NOW);
    expect(stamp).toContain('520');
  });

  // GIVEN Foto-Metadaten
  // WHEN buildExportFilename aufgerufen
  // THEN gibt "miminox-foto-YYYY-MM-DD-HH-MM.jpg" zurück
  it('[D] GIVEN photo WHEN buildExportFilename THEN valid filename', () => {
    const filename = buildExportFilename(NOW);
    expect(filename).toMatch(/^miminox-foto-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}\.jpg$/);
  });

  // GIVEN PHOTO_MAX_STORE
  // THEN ist 50 (sinnvolles Limit für mobilen Speicher)
  it('[D] GIVEN PHOTO_MAX_STORE THEN is 50', () => {
    expect(PHOTO_MAX_STORE).toBe(50);
  });
});
